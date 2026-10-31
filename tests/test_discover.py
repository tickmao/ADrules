"""Offline tests for the discovery/scoring engine. No network access is required."""

from datetime import datetime, timezone

import pytest
import requests

import discover

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


# -- scoring dimensions ---------------------------------------------------


@pytest.mark.parametrize(
    "age,expected",
    [
        (0.5, 5.0),
        (5, 4.5),
        (20, 3.0),
        (60, 2.0),
        (120, 1.0),
        (300, 0.5),
        (800, 0.0),
        (None, 1.5),
    ],
)
def test_score_activity(age, expected):
    assert discover.score_activity(age) == expected


@pytest.mark.parametrize(
    "commits,archived,generated,expected",
    [
        (0, False, False, 1.5),
        (1, False, False, 3.0),
        (2, False, False, 4.0),
        (20, False, False, 5.0),
        (0, False, True, 2.0),
        (20, True, False, 3.0),
        (0, True, False, 0.0),
    ],
)
def test_score_maintenance(commits, archived, generated, expected):
    assert discover.score_maintenance(commits, archived, generated) == expected


def test_official_vendor_gets_full_reputation():
    assert discover.score_reputation(None, official=True) == 5.0


@pytest.mark.parametrize(
    "stars,expected",
    [(None, 2.0), (5, 1.0), (10, 1.5), (150, 2.0), (500, 3.0), (1500, 3.5), (4000, 4.0), (50000, 5.0)],
)
def test_score_reputation_by_stars(stars, expected):
    assert discover.score_reputation(stars, official=False) == expected


@pytest.mark.parametrize(
    "dimensions,expected",
    [([], 0.0), (["ads"], 2.0), (["ads", "tracker"], 3.0),
     (["ads", "tracker", "malware"], 3.5), (["a", "b", "c", "d"], 4.0),
     (["a", "b", "c", "d", "e"], 5.0), (["ads", "ads"], 2.0)],
)
def test_score_coverage(dimensions, expected):
    assert discover.score_coverage(dimensions) == expected


def test_score_originality_prefers_upstream():
    assert discover.score_originality("original") > discover.score_originality("aggregate")


def test_score_compatibility_penalises_oversized_list():
    assert discover.score_compatibility(12.0, 200000, True, "GPL-3.0") == 3.0


def test_score_compatibility_penalises_wrong_format():
    assert discover.score_compatibility(0.5, 5000, False, "GPL-3.0") == 2.5


def test_score_compatibility_penalises_thin_and_unknown_license():
    assert discover.score_compatibility(0.1, 50, True, "Unknown") == 3.0


def test_score_compatibility_unknown_when_unreachable():
    assert discover.score_compatibility(None, 0, False, "") == 0.0


@pytest.mark.parametrize(
    "total,expected", [(4.5, "S"), (4.2, "S"), (3.9, "A"), (3.4, "A"), (3.0, "B"), (1.0, "C")]
)
def test_grade_for(total, expected):
    assert discover.grade_for(total) == expected


def test_weights_sum_to_one():
    assert round(sum(discover.WEIGHTS.values()), 6) == 1.0


# -- timestamps -----------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("202601290624", datetime(2026, 1, 29, tzinfo=timezone.utc)),
        ("2026-01-29 14:14:05(GMT+8)", datetime(2026, 1, 29, tzinfo=timezone.utc)),
        ("2026年01月26日 08:05", datetime(2026, 1, 26, tzinfo=timezone.utc)),
        ("2026/11/03 16:06 +0800", datetime(2026, 11, 3, tzinfo=timezone.utc)),
        ("no date here", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_metadata_date(value, expected):
    assert discover.parse_metadata_date(value) == expected


def test_metadata_age_prefers_last_modified():
    metadata = {"last modified": "2026-10-29", "version": "202601010000"}
    assert discover.metadata_age(metadata, NOW) == pytest.approx(2.5, abs=0.01)


def test_metadata_age_falls_back_to_version():
    assert discover.metadata_age({"version": "202601010000"}, NOW) > 300


# -- entry helpers --------------------------------------------------------


def test_official_host_detects_vendor_domains():
    assert discover.official_host(["https://filters.adtidy.org/extension/ublock/filters/2.txt"])
    assert not discover.official_host(["https://example.test/list.txt"])


def test_repo_of_reads_urls_and_homepage():
    assert discover.repo_of({"urls": ["https://raw.githubusercontent.com/a/b/main/x.txt"]}) == "a/b"
    assert discover.repo_of({"urls": ["https://x.test"], "homepage": "https://github.com/c/d"}) == "c/d"
    assert discover.repo_of({"urls": ["https://x.test"]}) is None


def test_status_for_marks_stale_sources():
    assert discover.status_for({"age_days": 3}) == "ok"
    assert discover.status_for({"age_days": discover.STALE_DAYS + 1}) == "stale"
    assert discover.status_for({}) == "unknown"


def test_score_entry_combines_dimensions():
    entry = {
        "id": "x",
        "name": "X",
        "urls": ["https://example.test/list.txt"],
        "dimensions": ["ads", "tracker"],
        "kind": "original",
        "license": "GPL-3.0",
    }
    probe = {"status": 200, "size_mb": 1.0, "rule_lines": 5000, "abp_ok": True,
             "generated": True, "age_days": 1.0}
    meta = {"stars": 4000, "archived": False, "commits_30d": 10}
    scored = discover.score_entry(entry, probe, meta)

    assert scored["status"] == "ok"
    assert scored["grade"] in {"S", "A", "B"}
    assert scored["score"] > 3.5
    assert set(scored["parts"]) == set(discover.WEIGHTS)


def test_score_entry_unreachable_scores_low():
    entry = {"id": "x", "name": "X", "urls": ["https://x.test"], "dimensions": [], "kind": "original"}
    scored = discover.score_entry(entry, {"status": 404}, {})
    assert scored["status"] == "unreachable"


# -- probing --------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


def test_probe_source_falls_back_to_mirror(monkeypatch):
    body = ("! Title: X\n" + "||ads.example.com^\n" * 300).encode()
    calls = []

    def fake_get(url, timeout, headers):
        calls.append(url)
        if url.endswith("primary.txt"):
            return FakeResponse(503)
        return FakeResponse(200, body, {"Last-Modified": "Fri, 30 Oct 2026 10:00:00 GMT"})

    monkeypatch.setattr(requests, "get", fake_get)
    entry = {"id": "x", "name": "X", "urls": ["https://a.test/primary.txt", "https://b.test/mirror.txt"]}
    probe = discover.probe_source(entry, NOW)

    assert calls == ["https://a.test/primary.txt", "https://b.test/mirror.txt"]
    assert probe["status"] == 200
    assert probe["url"].endswith("mirror.txt")
    assert probe["rule_lines"] == 300
    assert probe["abp_ok"] is True
    assert probe["age_days"] == pytest.approx(1 + 2 / 24, abs=0.01)


def test_probe_source_reports_all_failures(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, timeout, headers: FakeResponse(404))
    probe = discover.probe_source({"id": "x", "name": "X", "urls": ["https://a.test/x"]}, NOW)
    assert probe["status"] == 404
    assert "HTTP 404" in probe["error"]


def test_probe_source_survives_network_errors(monkeypatch):
    def boom(url, timeout, headers):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    probe = discover.probe_source({"id": "x", "name": "X", "urls": ["https://a.test/x"]}, NOW)
    assert probe["status"] is None
    assert probe["error"] == "ConnectionError"


# -- reporting ------------------------------------------------------------


def row(name, dimension_list, status="ok", age=1.0, score=4.0):
    return {
        "id": name,
        "name": name,
        "category": "ads",
        "region": "global",
        "dimensions": dimension_list,
        "urls": ["https://x.test"],
        "status": status,
        "age_days": age,
        "score": score,
        "grade": discover.grade_for(score),
    }


def test_render_coverage_flags_single_point_risk():
    lines = "\n".join(discover.render_coverage([row("A", ["ads"]), row("B", ["ads", "tracker"])]))
    assert "单点风险" in lines
    assert "偏少" in lines


def test_render_findings_reports_unreachable_and_stale():
    findings = "\n".join(
        discover.render_findings(
            [
                row("A", ["ads"]),
                row("Dead", ["ads"], status="unreachable"),
                row("Old", ["ads"], status="stale", age=99),
            ]
        )
    )
    assert "不可达" in findings
    assert "Old" in findings and "99 天前" in findings


def test_render_findings_reports_unknown_age():
    findings = "\n".join(discover.render_findings([row("Mystery", ["ads"], status="unknown", age=None)]))
    assert "无法确定最近更新时间" in findings


def test_render_findings_is_quiet_when_all_healthy():
    assert "无需处理" in discover.render_findings([row("A", ["ads"])])[0]


def test_build_report_contains_all_sections():
    shipped = [row("A", ["ads"]), row("Dead", ["tracker"], status="unreachable")]
    candidates = [{**row("Cand", ["ads"], score=3.0), "status": "candidate", "note": "观察中"}]
    discovered = [{"repo": "o/r", "stars": 500, "pushed": "2026-10-30T00:00:00Z",
                   "list_url": "https://raw.githubusercontent.com/o/r/HEAD/x.txt"}]

    report = discover.build_report(shipped, candidates, discovered, NOW)

    for section in ("## 正式源", "## 维度覆盖", "## 需要关注", "## 候选池", "## 自动搜索发现"):
        assert section in report
    assert "正式源：2 个，其中健康 1 个" in report
    assert "o/r" in report


def test_build_report_omits_discovery_section_without_search():
    report = discover.build_report([row("A", ["ads"])], [], [], NOW)
    assert "## 自动搜索发现" not in report
