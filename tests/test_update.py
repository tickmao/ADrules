"""Offline tests for the ADrules updater. No network access is required."""

from pathlib import Path

import pytest
import requests
import yaml

import update


# -- helpers --------------------------------------------------------------


def make_list(rule_lines: int = 200, version: str = "1") -> bytes:
    lines = [
        "[Adblock Plus 2.0]",
        f"! Version: {version}",
        "! Title: Test List",
        "!",
    ]
    lines += [f"||ads{i}.example.com^" for i in range(rule_lines)]
    return ("\n".join(lines) + "\n").encode()


def strategy(**overrides) -> dict:
    base = {
        "verify_format": True,
        "min_lines": 100,
        "max_size_mb": 50,
        "max_shrink_ratio": 0,
        "default_timeout": 5,
        "retries": 1,
    }
    base.update(overrides)
    return base


def make_updater(tmp_path: Path, sources, **strategy_overrides) -> update.RuleUpdater:
    """Build an updater whose root_dir is tmp_path."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    config = {"sources": sources, "update_strategy": strategy(**strategy_overrides)}
    config_path = scripts_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return update.RuleUpdater(str(config_path))


def source(
    name="Test",
    source_id="test",
    filename="Test.txt",
    urls=("https://example.test/list.txt",),
    **extra,
):
    return {"id": source_id, "name": name, "urls": list(urls), "filename": filename, **extra}


def serve(content):
    """Fake `_download_source` that always succeeds on the first endpoint."""

    def _fake(source_config):
        endpoints = update.source_endpoints(source_config)
        return content, endpoints[0]

    return _fake


def fake_downloader(mapping):
    """Fake `_download_source` keyed by endpoint URL."""

    def _fake(source_config):
        for url in update.source_endpoints(source_config):
            result = mapping.get(url)
            if isinstance(result, Exception):
                continue
            if result is not None:
                return result, url
        raise update.DownloadError(f"all endpoints failed for {source_config['name']}")

    return _fake


class FakeResponse:
    def __init__(self, status_code, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


# -- endpoint resolution --------------------------------------------------


def test_source_endpoints_uses_urls_in_order():
    assert update.source_endpoints({"urls": ["a", "b"]}) == ["a", "b"]


def test_source_endpoints_accepts_legacy_url():
    assert update.source_endpoints({"url": "a"}) == ["a"]


def test_source_endpoints_empty_when_missing():
    assert update.source_endpoints({}) == []


# -- metadata parsing -----------------------------------------------------


@pytest.mark.parametrize(
    "header,expected",
    [
        ("! Version: 202601290624", "202601290624"),
        ("!Version: 20260129025824", "20260129025824"),
        ("! ! Version: 2026-01-29 14:14:05(GMT+8)", "2026-01-29 14:14:05(GMT+8)"),
        ("!!!Version: 42", "42"),
    ],
)
def test_parse_metadata_version_styles(header, expected):
    assert update.parse_metadata(header + "\n||ads.example.com^\n")["version"] == expected


@pytest.mark.parametrize(
    "header",
    [
        "! Last modified: 29 Jan 2026 06:24 UTC",
        "! Last Modified: 2026年01月26日 08:05",
    ],
)
def test_parse_metadata_last_modified(header):
    assert "last modified" in update.parse_metadata(header + "\n")


def test_parse_metadata_scans_100_lines():
    padded = "\n".join(["! filler"] * 40 + ["! Version: 7"])
    assert update.parse_metadata(padded)["version"] == "7"

    too_far = "\n".join(["! filler"] * 120 + ["! Version: 7"])
    assert "version" not in update.parse_metadata(too_far)


def test_parse_metadata_ignores_unknown_headers():
    content = "[Adblock Plus 2.0]\n!Title: anti-AD\n!!!note! see https://x.test\n"
    metadata = update.parse_metadata(content)
    assert metadata["title"] == "anti-AD"
    assert "note! see https" not in metadata


def test_parse_metadata_empty_content():
    assert update.parse_metadata("") == {}


# -- normalization --------------------------------------------------------


def test_normalize_converts_crlf_to_lf():
    assert update.normalize(b"a\r\nb\r\n") == b"a\nb\n"


def test_normalize_collapses_trailing_newlines():
    assert update.normalize(b"a\n\n\n") == b"a\n"


def test_normalize_adds_missing_trailing_newline():
    assert update.normalize(b"a") == b"a\n"


def test_normalize_makes_crlf_and_lf_hash_equal():
    assert update.content_hash(update.normalize(b"a\r\nb")) == update.content_hash(
        update.normalize(b"a\nb")
    )


# -- rule line counting ---------------------------------------------------


def test_cosmetic_filters_are_rules():
    text = "! comment\n\n##.ad-banner\n#@#.ad-banner\n||ads.test^\n"
    assert update.count_rule_lines(text) == 3


def test_bare_hash_lines_are_comments():
    assert update.count_rule_lines("# comment\n#\n\r\n") == 0


# -- validation -----------------------------------------------------------


def test_validate_rejects_too_few_rule_lines():
    reason = update.validate(make_list(5), None, source(), strategy())
    assert reason is not None and "too few rule lines" in reason


def test_validate_accepts_valid_list():
    assert update.validate(make_list(200), None, source(), strategy()) is None


def test_validate_rejects_comment_only_content():
    content = ("! header\n" + "! comment\n" * 200).encode()
    reason = update.validate(content, None, source(), strategy(min_lines=10))
    assert reason is not None
    assert "too few rule lines" in reason or "marker" in reason


def test_validate_rejects_oversized_file():
    reason = update.validate(make_list(200), None, source(), strategy(max_size_mb=0.001))
    assert reason is not None and "too large" in reason


def test_validate_rejects_suspicious_shrink():
    old = b"||ads.example.com^\n" * 200
    new = b"||ads.example.com^\n" * 80
    reason = update.validate(new, old, source(), strategy(min_lines=1, max_shrink_ratio=0.5))
    assert reason is not None and "suspicious shrink" in reason


def test_validate_allows_shrink_with_override():
    old = b"||ads.example.com^\n" * 200
    new = b"||ads.example.com^\n" * 80
    assert (
        update.validate(
            new,
            old,
            source(allow_shrink=True),
            strategy(min_lines=1, max_shrink_ratio=0.5),
        )
        is None
    )


def test_validate_skips_checks_when_disabled():
    assert update.validate(b"x", None, source(), strategy(verify_format=False)) is None


# -- single source decisions ----------------------------------------------


def test_unchanged_content_is_skipped_and_file_untouched(tmp_path):
    content = make_list(200)
    target = tmp_path / "Test.txt"
    target.write_bytes(content)
    mtime_before = target.stat().st_mtime_ns

    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(content)

    result = updater.update_source(source())
    assert result["status"] == "skipped"
    assert target.stat().st_mtime_ns == mtime_before


def test_crlf_remote_matches_lf_local(tmp_path):
    target = tmp_path / "Test.txt"
    target.write_bytes(make_list(200))

    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(make_list(200).replace(b"\n", b"\r\n"))

    assert updater.update_source(source())["status"] == "skipped"


def test_changed_content_is_written_atomically(tmp_path):
    target = tmp_path / "Test.txt"
    target.write_bytes(make_list(200, version="old"))

    new_content = make_list(210, version="new")
    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(new_content)

    result = updater.update_source(source())
    assert result["status"] == "updated"
    assert target.read_bytes() == update.normalize(new_content)
    assert not list(tmp_path.glob(".*.tmp"))


def test_invalid_content_leaves_file_untouched(tmp_path):
    original = make_list(200)
    target = tmp_path / "Test.txt"
    target.write_bytes(original)

    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(b"||ads.test^\n")

    result = updater.update_source(source())
    assert result["status"] == "failed"
    assert target.read_bytes() == original


def test_dry_run_writes_nothing(tmp_path):
    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(make_list(200))

    code = updater.run(dry_run=True)
    assert code == 0
    assert updater.results[0]["status"] == "would-update"
    assert not (tmp_path / "Test.txt").exists()


# -- mirror fallback ------------------------------------------------------


def test_mirror_is_used_when_primary_fails(tmp_path):
    primary = "https://primary.test/list.txt"
    mirror = "https://mirror.test/list.txt"
    content = make_list(200)

    updater = make_updater(tmp_path, [source(urls=(primary, mirror))])
    calls = []

    def fake_download(url, timeout=60, retries=3):
        calls.append(url)
        if url == primary:
            raise update.DownloadError("HTTP 503")
        return content

    updater._fetch = fake_download
    result = updater.update_source(source(urls=(primary, mirror)))

    assert calls == [primary, mirror]
    assert result["status"] == "updated"
    assert result["endpoint"] == mirror


def test_all_endpoints_failing_reports_every_attempt(tmp_path):
    urls = ("https://a.test/x", "https://b.test/x")
    updater = make_updater(tmp_path, [source(urls=urls)])
    updater._fetch = lambda url, timeout=60, retries=3: (_ for _ in ()).throw(
        update.DownloadError(f"HTTP 404 for {url}")
    )

    result = updater.update_source(source(urls=urls))
    assert result["status"] == "failed"
    assert "endpoint 1" in result["reason"] and "endpoint 2" in result["reason"]


def test_endpoint_is_recorded_for_primary(tmp_path):
    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(make_list(200))

    result = updater.update_source(source())
    assert result["endpoint"] == "https://example.test/list.txt"


# -- download retries -----------------------------------------------------


def test_download_retries_on_server_error(monkeypatch):
    responses = [FakeResponse(503), FakeResponse(200, b"ok")]
    calls, sleeps = [], []
    monkeypatch.setattr(
        update.requests,
        "get",
        lambda url, timeout, headers: (calls.append(url), responses.pop(0))[1],
    )
    monkeypatch.setattr(update.time, "sleep", sleeps.append)

    assert update.download("https://example.test", retries=3) == b"ok"
    assert len(calls) == 2
    assert sleeps == [1]


def test_download_sends_user_agent(monkeypatch):
    headers_seen = {}

    def fake_get(url, timeout, headers):
        headers_seen.update(headers)
        return FakeResponse(200, b"ok")

    monkeypatch.setattr(update.requests, "get", fake_get)
    update.download("https://example.test")
    assert headers_seen["User-Agent"] == update.USER_AGENT


def test_download_does_not_retry_client_error(monkeypatch):
    calls = []
    monkeypatch.setattr(
        update.requests,
        "get",
        lambda url, timeout, headers: (calls.append(url), FakeResponse(404))[1],
    )

    with pytest.raises(update.DownloadError):
        update.download("https://example.test", retries=3)
    assert len(calls) == 1


def test_download_gives_up_after_budget(monkeypatch):
    calls = []
    sleeps = []

    def fake_get(url, timeout, headers):
        calls.append(url)
        raise requests.Timeout("boom")

    monkeypatch.setattr(update.requests, "get", fake_get)
    monkeypatch.setattr(update.time, "sleep", sleeps.append)

    with pytest.raises(update.DownloadError):
        update.download("https://example.test", retries=3)
    assert len(calls) == 3
    assert sleeps == [1, 2]


def test_download_honours_retry_after(monkeypatch):
    responses = [FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200, b"ok")]
    sleeps = []
    monkeypatch.setattr(
        update.requests, "get", lambda url, timeout, headers: responses.pop(0)
    )
    monkeypatch.setattr(update.time, "sleep", sleeps.append)

    assert update.download("https://example.test", retries=3) == b"ok"
    assert sleeps == [7]


def test_download_caps_retry_after(monkeypatch):
    responses = [
        FakeResponse(429, headers={"Retry-After": "600"}),
        FakeResponse(200, b"ok"),
    ]
    sleeps = []
    monkeypatch.setattr(
        update.requests, "get", lambda url, timeout, headers: responses.pop(0)
    )
    monkeypatch.setattr(update.time, "sleep", sleeps.append)

    update.download("https://example.test", retries=3)
    assert sleeps == [update.MAX_RETRY_AFTER_SECONDS]


# -- run summary and exit codes -------------------------------------------


def test_partial_failure_exits_non_zero_but_keeps_writes(tmp_path):
    ok_a = source(name="A", source_id="a", filename="A.txt", urls=("https://example.test/a",))
    ok_b = source(name="B", source_id="b", filename="B.txt", urls=("https://example.test/b",))
    bad = source(name="C", source_id="c", filename="C.txt", urls=("https://example.test/c",))

    updater = make_updater(tmp_path, [ok_a, ok_b, bad])
    updater._download_source = fake_downloader(
        {
            "https://example.test/a": make_list(200),
            "https://example.test/b": make_list(200),
            "https://example.test/c": update.DownloadError("HTTP 500"),
        }
    )

    assert updater.run() == 1
    assert (tmp_path / "A.txt").exists()
    assert (tmp_path / "B.txt").exists()
    assert not (tmp_path / "C.txt").exists()
    statuses = {r["name"]: r["status"] for r in updater.results}
    assert statuses == {"A": "updated", "B": "updated", "C": "failed"}


def test_all_skipped_exits_zero(tmp_path):
    (tmp_path / "Test.txt").write_bytes(make_list(200))
    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(make_list(200))

    assert updater.run() == 0


def test_optional_source_failure_is_not_fatal(tmp_path):
    ok = source(name="A", source_id="a", filename="A.txt", urls=("https://example.test/a",))
    optional = source(
        name="B", source_id="b", filename="B.txt", urls=("https://example.test/b",), optional=True
    )

    updater = make_updater(tmp_path, [ok, optional])
    updater._download_source = fake_downloader(
        {
            "https://example.test/a": make_list(200),
            "https://example.test/b": update.DownloadError("HTTP 403"),
        }
    )

    assert updater.run() == 0
    assert (tmp_path / "A.txt").exists()
    statuses = {r["name"]: r["status"] for r in updater.results}
    assert statuses == {"A": "updated", "B": "failed"}


def test_unexpected_error_does_not_abort_batch(tmp_path):
    ok = source(name="A", source_id="a", filename="A.txt", urls=("https://example.test/a",))
    boom = source(name="B", source_id="b", filename="B.txt", urls=("https://example.test/b",))

    updater = make_updater(tmp_path, [ok, boom])
    updater._download_source = fake_downloader(
        {"https://example.test/a": make_list(200), "https://example.test/b": ValueError("x")}
    )

    assert updater.run() == 1
    assert (tmp_path / "A.txt").exists()


def test_step_summary_is_written(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    updater = make_updater(tmp_path, [source()])
    updater._download_source = serve(make_list(200))
    updater.run()

    text = summary.read_text(encoding="utf-8")
    assert "## ADrules update" in text
    assert "| source | status |" in text


# -- configuration validation ---------------------------------------------


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"sources": []},
        {"sources": [{"name": "x", "urls": ["https://x.test"]}]},
        {"sources": [{"id": "x", "name": "x", "filename": "x.txt"}]},
        {"sources": [{"id": "x", "name": "x", "filename": "x.txt", "urls": []}]},
        {
            "sources": [
                {"id": "x", "name": "x", "filename": "x.txt", "urls": ["https://x.test"]},
                {"id": "x", "name": "y", "filename": "y.txt", "urls": ["https://y.test"]},
            ]
        },
        {
            "sources": [{"id": "x", "name": "x", "filename": "x.txt", "urls": ["https://x.test"]}],
            "update_strategy": {"verify_format": True},
        },
    ],
)
def test_load_config_rejects_invalid(tmp_path, config):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(update.ConfigError):
        update.load_config(path)


def test_load_config_rejects_missing_file(tmp_path):
    with pytest.raises(update.ConfigError):
        update.load_config(tmp_path / "nope.yaml")
