#!/usr/bin/env python3
"""
ADrules source discovery and health report.

Probes every shipped source and every candidate, scores them on six dimensions,
and writes a Markdown report (docs/sources-report.md by default).

Modes:
    default      score shipped sources + candidate pool
    --search     additionally search GitHub for new repositories and probe their
                 candidate list files

Exit codes:
    0  report generated (warnings are printed as GitHub annotations)
    1  configuration error
"""

import argparse
import email.utils
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
import yaml

from update import (
    USER_AGENT,
    is_rule_line,
    parse_metadata,
    source_endpoints,
)

WEIGHTS = {
    "activity": 0.30,
    "maintenance": 0.20,
    "reputation": 0.25,
    "coverage": 0.10,
    "originality": 0.10,
    "compatibility": 0.05,
}

GRADES = ((4.2, "S"), (3.4, "A"), (2.6, "B"), (0.0, "C"))

STALE_DAYS = 30
MAX_REPORTED_FAILURES = 20

OFFICIAL_HOSTS = (
    "easylist.to",
    "easylist-downloads.adblockplus.org",
    "filters.adtidy.org",
    "ublockorigin.github.io",
    "secure.fanboy.co.nz",
    "anti-ad.net",
    "pgl.yoyo.org",
)

SEARCH_QUERIES = (
    "topic:adblock-list",
    "topic:adblock-filter-list",
    "adblock rules filter list in:name,description",
    "easylist china in:name,description",
    "广告 过滤 规则 in:name,description",
)

SEARCH_SORTS = ("updated", "stars")

MIN_DISCOVERY_STARS = 100
SELF_REPOS = ("tickmao/ADrules",)
MAX_DISCOVERY_AGE_DAYS = 90

REPO_PATTERNS = (
    re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)"),
    re.compile(r"raw\.githubusercontent\.com/([^/\s]+)/([^/\s#?]+)"),
    re.compile(r"jsdelivr\.net/gh/([^/\s@]+)/([^/\s@#?]+)"),
)


# -- scoring helpers ------------------------------------------------------


def parse_http_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_iso_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_since(moment: Optional[datetime], now: datetime) -> Optional[float]:
    if moment is None:
        return None
    return max(0.0, (now - moment).total_seconds() / 86400.0)


def bucket(value: float, thresholds: Iterable[Tuple[float, float]], default: float = 0.0) -> float:
    """Return the score of the first threshold the value satisfies."""
    for limit, score in thresholds:
        if value <= limit:
            return score
    return default


def score_activity(age_days: Optional[float]) -> float:
    if age_days is None:
        return 1.5
    return bucket(
        age_days,
        ((2, 5.0), (7, 4.5), (14, 4.0), (30, 3.0), (90, 2.0), (180, 1.0), (365, 0.5)),
        default=0.0,
    )


def score_maintenance(commits_30d: int, archived: bool, generated: bool) -> float:
    base = bucket(
        float(commits_30d),
        ((0, 1.5), (1, 3.0), (3, 4.0), (8, 4.5)),
        default=5.0,
    )
    if generated:
        base += 0.5
    if archived:
        base -= 2.0
    return max(0.0, min(5.0, base))


def at_least(value: float, thresholds: Iterable[Tuple[float, float]], default: float = 0.0) -> float:
    """Return the score of the first threshold the value reaches."""
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return default


def score_reputation(stars: Optional[int], official: bool) -> float:
    if official:
        return 5.0
    if stars is None:
        return 2.0
    return at_least(
        float(stars),
        ((10000, 5.0), (5000, 4.5), (3000, 4.0), (1000, 3.5), (300, 3.0), (100, 2.0), (10, 1.5)),
        default=1.0,
    )


def score_coverage(dimensions: List[str]) -> float:
    count = len(set(dimensions or []))
    if count >= 5:
        return 5.0
    if count == 4:
        return 4.0
    if count == 3:
        return 3.5
    if count == 2:
        return 3.0
    if count == 1:
        return 2.0
    return 0.0


def score_originality(kind: str) -> float:
    return 5.0 if kind == "original" else 2.5


def score_compatibility(size_mb: Optional[float], rule_lines: int, abp_ok: bool, license_name: str) -> float:
    score = 5.0
    if size_mb is None:
        return 0.0
    if size_mb > 10:
        score -= 2.0
    elif size_mb > 5:
        score -= 1.0
    if rule_lines < 200:
        score -= 1.0
    if not abp_ok:
        score -= 2.5
    if (license_name or "unknown").lower() == "unknown":
        score -= 1.0
    return max(0.0, score)


def grade_for(total: float) -> str:
    for threshold, letter in GRADES:
        if total >= threshold:
            return letter
    return GRADES[-1][1]


def official_host(urls: List[str]) -> bool:
    return any(any(host in url for host in OFFICIAL_HOSTS) for url in urls)


def repo_of(entry: dict) -> Optional[str]:
    for url in list(entry.get("urls") or []) + [entry.get("homepage") or ""]:
        for pattern in REPO_PATTERNS:
            match = pattern.search(url)
            if match:
                return f"{match.group(1)}/{match.group(2)}".removesuffix(".git")
    return None


def score_entry(entry: dict, probe: dict, meta: dict) -> dict:
    urls = source_endpoints(entry)
    generated = probe.get("generated", False)
    parts = {
        "activity": score_activity(probe.get("age_days")),
        "maintenance": score_maintenance(
            int(meta.get("commits_30d") or 0), bool(meta.get("archived")), generated
        ),
        "reputation": score_reputation(meta.get("stars"), official_host(urls)),
        "coverage": score_coverage(entry.get("dimensions") or []),
        "originality": score_originality(entry.get("kind", "original")),
        "compatibility": score_compatibility(
            probe.get("size_mb"), probe.get("rule_lines", 0), probe.get("abp_ok", False),
            entry.get("license", ""),
        ),
    }
    total = round(sum(WEIGHTS[key] * value for key, value in parts.items()), 2)
    return {
        "parts": {key: round(value, 2) for key, value in parts.items()},
        "score": total,
        "grade": grade_for(total),
        "status": "unreachable" if probe.get("status") != 200 else status_for(probe),
    }


def status_for(probe: dict) -> str:
    age = probe.get("age_days")
    if age is None:
        return "unknown"
    return "stale" if age > STALE_DAYS else "ok"


METADATA_DATE_PATTERNS = (
    re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})"),
    re.compile(r"^(\d{4})(\d{2})(\d{2})\d{4,6}$"),
)


def parse_metadata_date(value: Optional[str]) -> Optional[datetime]:
    """Parse the many timestamp shapes filter lists put in their headers."""
    if not value:
        return None
    for pattern in METADATA_DATE_PATTERNS:
        match = pattern.search(value)
        if not match:
            continue
        year, month, day = (int(part) for part in match.groups())
        try:
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def metadata_age(metadata: dict, now: datetime) -> Optional[float]:
    for key in ("last modified", "last-modified", "updated", "version"):
        moment = parse_metadata_date(metadata.get(key))
        if moment:
            return days_since(moment, now)
    return None

# -- probing --------------------------------------------------------------


def probe_source(entry: dict, now: datetime, timeout: int = 30) -> dict:
    urls = source_endpoints(entry)
    result = {"status": None, "url": urls[0] if urls else ""}
    if not urls:
        result["status"] = 0
        return result

    for url in urls:
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        except requests.RequestException as error:
            result["error"] = f"{type(error).__name__}"
            continue
        if response.status_code != 200:
            result["status"] = response.status_code
            result["error"] = f"HTTP {response.status_code}"
            continue

        body = response.content
        text = body.decode("utf-8", errors="replace")
        metadata = parse_metadata(text)
        rule_lines = sum(1 for line in text.split("\n") if is_rule_line(line))
        result.update(
            {
                "status": 200,
                "url": url,
                "size_mb": round(len(body) / 1048576, 2),
                "rule_lines": rule_lines,
                "abp_ok": rule_lines > 0 and any(mark in text for mark in ("||", "@@", "##", "#@#")),
                "generated": bool(
                    re.search(r"(?im)^!\s*(checksum|diff-path)\s*:", text[:2000])
                ),
                "version": metadata.get("version", "-"),
                "title": metadata.get("title", entry.get("name", "")),
            }
        )

        moment = parse_http_date(response.headers.get("Last-Modified"))
        result["age_days"] = (
            days_since(moment, now) if moment else metadata_age(metadata, now)
        )
        return result

    return result


def gh_json(args: List[str]) -> Optional[dict]:
    try:
        raw = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if raw.returncode != 0 or not raw.stdout.strip():
        return None
    try:
        return json.loads(raw.stdout)
    except json.JSONDecodeError:
        return None


def github_meta(repo: Optional[str], since: datetime) -> dict:
    if not repo:
        return {}
    info = gh_json(["api", f"repos/{repo}"])
    if not info:
        return {}
    commits = gh_json(
        [
            "api",
            f"repos/{repo}/commits?since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}&per_page=100",
        ]
    )
    return {
        "repo": repo,
        "stars": info.get("stargazers_count"),
        "archived": info.get("archived", False),
        "commits_30d": len(commits) if isinstance(commits, list) else 0,
        "pushed": info.get("pushed_at"),
    }


def evaluate(entries: List[dict], now: datetime, with_github: bool = True) -> List[dict]:
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []
    cache: Dict[str, dict] = {}
    for entry in entries:
        probe = probe_source(entry, now)
        meta = {}
        if with_github:
            repo = repo_of(entry)
            if repo:
                if repo not in cache:
                    cache[repo] = github_meta(repo, since)
                meta = cache[repo]
        if probe.get("age_days") is None and meta.get("pushed"):
            probe["age_days"] = days_since(parse_iso_date(meta["pushed"]), now)
        scored = score_entry(entry, probe, meta)
        rows.append({**entry, **probe, **{f"gh_{k}": v for k, v in meta.items()}, **scored})
    return rows


# -- reporting ------------------------------------------------------------


def format_age(age_days: Optional[float]) -> str:
    if age_days is None:
        return "-"
    if age_days < 1:
        return "刚刚"
    return f"{age_days:.0f} 天前"


def render_source_table(rows: List[dict]) -> List[str]:
    lines = ["| 源 | 类别 | 区域 | 等级 | 评分 | 状态 | 最近更新 | 体积 | 端点 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in sorted(rows, key=lambda item: -item["score"]):
        size = f"{row['size_mb']:.2f}MB" if row.get("size_mb") else "-"
        endpoints = len(source_endpoints(row))
        lines.append(
            f"| {row['name']} | {row['category']} | {row.get('region', '-')} | "
            f"{row['grade']} | {row['score']:.2f} | {row['status']} | "
            f"{format_age(row.get('age_days'))} | {size} | {endpoints} |"
        )
    return lines


def render_coverage(rows: List[dict]) -> List[str]:
    by_dimension: Dict[str, List[str]] = {}
    for row in rows:
        for dimension in row.get("dimensions") or []:
            by_dimension.setdefault(dimension, []).append(row["name"])

    lines = ["| 维度 | 覆盖源数 | 来源 | 冗余判断 |", "| --- | --- | --- | --- |"]
    for dimension in sorted(by_dimension):
        names = by_dimension[dimension]
        verdict = "充分" if len(names) >= 3 else ("偏少" if len(names) == 2 else "单点风险")
        lines.append(f"| {dimension} | {len(names)} | {', '.join(names)} | {verdict} |")
    return lines


def render_findings(rows: List[dict]) -> List[str]:
    problems = [row for row in rows if row["status"] != "ok"]
    if not problems:
        return ["- 全部源可达且 30 天内更新过，无需处理。"]

    lines = []
    for row in problems[:MAX_REPORTED_FAILURES]:
        if row["status"] == "unreachable":
            detail = row.get("error") or "所有端点均不可达"
            lines.append(f"- **{row['name']}** 不可达：{detail}；建议从候选池同类别源中替换")
        elif row["status"] == "unknown":
            lines.append(f"- **{row['name']}** 无法确定最近更新时间（缺少日期头，可用 --search 补充仓库信息）")
        else:
            lines.append(
                f"- **{row['name']}** 已 {format_age(row.get('age_days'))} 未更新"
                f"（阈值 {STALE_DAYS} 天），先确认上游是否仍在维护"
            )
    return lines


def render_candidates(rows: List[dict]) -> List[str]:
    lines = [
        "| 源 | 状态 | 等级 | 评分 | 最近更新 | 体积 | 说明 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(rows, key=lambda item: -item["score"]):
        size = f"{row['size_mb']:.2f}MB" if row.get("size_mb") else "-"
        note = (row.get("note") or "").replace("|", "/")
        lines.append(
            f"| {row['name']} | {row.get('status', 'candidate')} | {row['grade']} | "
            f"{row['score']:.2f} | {format_age(row.get('age_days'))} | {size} | {note} |"
        )
    return lines


def build_report(shipped: List[dict], candidates: List[dict], discovered: List[dict], now: datetime) -> str:
    healthy = sum(1 for row in shipped if row["status"] == "ok")
    lines = [
        "# 源健康与发现报告",
        "",
        f"- 生成时间：{now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- 正式源：{len(shipped)} 个，其中健康 {healthy} 个",
        f"- 候选池：{len(candidates)} 个（仅观察，不参与订阅）",
        "",
        "评分机制见 [sources.md](sources.md)：活跃度 30%、维护度 20%、口碑 25%、"
        "维度覆盖 10%、独立来源 10%、可用性 5%。",
        "",
        "## 正式源",
        "",
        *render_source_table(shipped),
        "",
        "## 维度覆盖",
        "",
        *render_coverage(shipped),
        "",
        "## 需要关注",
        "",
        *render_findings(shipped),
        "",
        "## 候选池",
        "",
        *render_candidates(candidates),
    ]
    if discovered:
        lines += [
            "",
            "## 自动搜索发现",
            "",
            "以下条目由 GitHub 搜索自动产生，未经人工审核，仅作线索：",
            "",
            "| 仓库 | Stars | 最近提交 | 探测到的订阅文件 |",
            "| --- | --- | --- | --- |",
        ]
        for item in discovered:
            lines.append(
                f"| {item['repo']} | {item.get('stars', '-')} | "
                f"{item.get('pushed', '-')[:10]} | {item.get('list_url', '-')} |"
            )
    return "\n".join(lines) + "\n"


# -- discovery ------------------------------------------------------------


def search_repositories(now: datetime, limit: int = 10) -> List[dict]:
    """Collect recently pushed, reasonably popular repositories for manual review."""
    seen: Dict[str, dict] = {}
    for query in SEARCH_QUERIES:
        for sort in SEARCH_SORTS:
            found = gh_json(
                [
                    "api",
                    "-X",
                    "GET",
                    "search/repositories",
                    "-f",
                    f"q={query}",
                    "-f",
                    f"sort={sort}",
                    "-f",
                    "order=desc",
                    "-f",
                    f"per_page={limit}",
                ]
            )
            for item in (found or {}).get("items", []):
                repo = item.get("full_name")
                if not repo or repo in seen:
                    continue
                age = days_since(parse_iso_date(item.get("pushed_at")), now)
                if age is None or age > MAX_DISCOVERY_AGE_DAYS:
                    continue
                if int(item.get("stargazers_count") or 0) < MIN_DISCOVERY_STARS:
                    continue
                seen[repo] = {
                    "repo": repo,
                    "stars": item.get("stargazers_count"),
                    "pushed": item.get("pushed_at"),
                    "description": (item.get("description") or "")[:80],
                }
    return list(seen.values())


def find_list_file(repo: str) -> Optional[str]:
    tree = gh_json(["api", f"repos/{repo}/git/trees/HEAD?recursive=1"])
    if not tree:
        return None
    best = None
    for node in tree.get("tree", []):
        path = node.get("path", "")
        if not path.endswith(".txt") or node.get("size", 0) < 20000:
            continue
        lowered = path.lower()
        if not any(word in lowered for word in ("adblock", "filter", "rule", "easylist", "adguard")):
            continue
        if best is None or node.get("size", 0) > best[1]:
            best = (path, node.get("size", 0))
    if not best:
        return None
    return f"https://raw.githubusercontent.com/{repo}/HEAD/{best[0]}"


def run_search(known_repos: set, now: datetime) -> List[dict]:
    discovered = []
    ignored = set(known_repos) | set(SELF_REPOS)
    for item in search_repositories(now):
        if item["repo"].lower() in {repo.lower() for repo in ignored}:
            continue
        item["list_url"] = find_list_file(item["repo"]) or "-"
        discovered.append(item)
    return discovered


# -- config plumbing ------------------------------------------------------


def load_yaml(path: Path, key: str) -> List[dict]:
    if not path.exists():
        raise SystemExit(f"config error: {path} not found")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get(key) or []
    if not isinstance(entries, list) or not entries:
        raise SystemExit(f"config error: {path} has no '{key}' list")
    return entries


def main(argv: Optional[List[str]] = None) -> int:
    scripts_dir = Path(__file__).parent
    parser = argparse.ArgumentParser(description="Report source health and discover new sources.")
    parser.add_argument("--config", default=str(scripts_dir / "config.yaml"))
    parser.add_argument("--candidates", default=str(scripts_dir / "candidates.yaml"))
    parser.add_argument("--report", default=str(scripts_dir.parent / "docs" / "sources-report.md"))
    parser.add_argument("--json", default=None, help="also write machine-readable rows here")
    parser.add_argument("--search", action="store_true", help="search GitHub for new sources")
    parser.add_argument("--no-github", action="store_true", help="skip GitHub metadata lookups")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    shipped_entries = load_yaml(Path(args.config), "sources")
    candidate_entries = load_yaml(Path(args.candidates), "candidates")

    shipped = evaluate(shipped_entries, now, with_github=not args.no_github)
    candidates = evaluate(candidate_entries, now, with_github=not args.no_github)

    discovered: List[dict] = []
    if args.search and not args.no_github:
        known = {repo_of(entry) for entry in shipped_entries + candidate_entries}
        known.discard(None)
        discovered = run_search(known, now)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    content = build_report(shipped, candidates, discovered, now)
    changed = not report_path.exists() or report_path.read_text(encoding="utf-8") != content
    if changed:
        report_path.write_text(content, encoding="utf-8")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"shipped": shipped, "candidates": candidates, "discovered": discovered},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    problems = [row for row in shipped if row["status"] != "ok"]
    print(f"shipped={len(shipped)} healthy={len(shipped) - len(problems)} "
          f"candidates={len(candidates)} discovered={len(discovered)} "
          f"report={'updated' if changed else 'unchanged'}")
    for row in problems:
        print(f"::warning::{row['name']} is {row['status']}: {row.get('error', 'stale')}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
