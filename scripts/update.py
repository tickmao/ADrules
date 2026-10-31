#!/usr/bin/env python3
"""
ADrules automatic rule updater.

Downloads every configured filter list, skips the ones whose content did not
change, validates the rest, then replaces the local file atomically.

Exit codes:
    0  every source was updated or skipped
    1  at least one source failed (successful sources are still written).
       Sources marked `optional: true` are reported but never fatal.
"""

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml

USER_AGENT = "ADrules-updater/2.0 (+https://github.com/tickmao/ADrules)"
METADATA_SCAN_LINES = 100
METADATA_LINE_RE = re.compile(r"^([A-Za-z][A-Za-z ]{0,20}):\s*(.+)$")
RULE_MARKERS = ("||", "@@", "##", "#@#", "#?#", "#$#", "!#if")
COSMETIC_PREFIXES = ("##", "#@#", "#?#", "#$#")
BACKOFF_SECONDS = (1, 2, 4)
MAX_RETRY_AFTER_SECONDS = 30
REQUIRED_STRATEGY_KEYS = (
    "verify_format",
    "min_lines",
    "max_size_mb",
    "max_shrink_ratio",
    "default_timeout",
    "retries",
)


class ConfigError(Exception):
    """Raised when scripts/config.yaml is missing or malformed."""


class DownloadError(Exception):
    """Raised when a source cannot be downloaded within the retry budget."""


def parse_metadata(content: str, scan_lines: int = METADATA_SCAN_LINES) -> Dict[str, str]:
    """Extract metadata keys from the leading comment block of a filter list.

    Tolerates every marker style seen upstream: `! Title: x`, `!Title: x`,
    `! ! Version: x`, `!!!note! ...`. Keys are lowercased and spaces collapsed.
    """
    metadata: Dict[str, str] = {}

    for raw_line in content.split("\n")[:scan_lines]:
        line = raw_line.strip()
        while line[:1] in ("!", "#"):
            line = line[1:].strip()

        match = METADATA_LINE_RE.match(line)
        if not match:
            continue

        key = " ".join(match.group(1).lower().split())
        value = match.group(2).strip()
        if value and key not in metadata:
            metadata[key] = value

    return metadata


def normalize(content: bytes) -> bytes:
    """Normalize line endings to LF and guarantee exactly one trailing newline."""
    text = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    text = text.rstrip(b"\n")
    return text + b"\n"


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def is_rule_line(line: str) -> bool:
    """Tell filter rules from comments.

    `!` starts an adblock comment, but `##`, `#@#`, `#?#` and `#$#` start
    cosmetic filters, so only bare `#` lines count as comments.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("!"):
        return False
    if stripped.startswith("#") and not stripped.startswith(COSMETIC_PREFIXES):
        return False
    return True


def count_rule_lines(text: str) -> int:
    """Count rule lines; these carry the actual filters."""
    return sum(1 for line in text.split("\n") if is_rule_line(line))


def has_rule_marker(text: str) -> bool:
    return any(marker in text for marker in RULE_MARKERS)


def validate(
    content: bytes,
    old_content: Optional[bytes],
    rule_config: dict,
    strategy: dict,
) -> Optional[str]:
    """Return a rejection reason, or None when the content is acceptable."""
    if not strategy["verify_format"]:
        return None

    text = content.decode("utf-8", errors="replace")

    rule_lines = count_rule_lines(text)
    if rule_lines < strategy["min_lines"]:
        return f"too few rule lines: {rule_lines} < {strategy['min_lines']}"

    size_mb = len(content) / (1024 * 1024)
    if size_mb > strategy["max_size_mb"]:
        return f"file too large: {size_mb:.2f}MB > {strategy['max_size_mb']}MB"

    if not has_rule_marker(text):
        return "no filter syntax marker found"

    ratio = strategy["max_shrink_ratio"]
    if (
        ratio
        and old_content
        and not rule_config.get("allow_shrink", False)
        and len(content) < len(old_content) * ratio
    ):
        return (
            f"suspicious shrink: {len(content)}B < "
            f"{ratio:.0%} of {len(old_content)}B (set allow_shrink to override)"
        )

    return None


def write_atomic(path: Path, content: bytes) -> None:
    """Replace `path` in one step so a crash can never leave a half-written list."""
    tmp_path = path.with_name("." + path.name + ".tmp")
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def backoff_delay(attempt: int) -> int:
    return BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]


def download(url: str, timeout: int = 60, retries: int = 3) -> bytes:
    """Fetch `url`, retrying transient failures with exponential backoff."""
    attempts = max(1, retries)
    last_error = "unknown error"

    for attempt in range(attempts):
        try:
            response = requests.get(
                url, timeout=timeout, headers={"User-Agent": USER_AGENT}
            )
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = f"{type(error).__name__}: {error}"
        except requests.RequestException as error:
            raise DownloadError(f"request failed: {error}") from error
        else:
            if response.status_code == 200:
                return response.content
            last_error = f"HTTP {response.status_code}"
            retryable = response.status_code == 429 or response.status_code >= 500
            if not retryable:
                raise DownloadError(f"HTTP {response.status_code} for {url}")
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after), MAX_RETRY_AFTER_SECONDS))
                continue

        if attempt + 1 < attempts:
            time.sleep(backoff_delay(attempt))

    raise DownloadError(f"gave up after {attempts} attempts: {last_error}")


def source_endpoints(source: dict) -> List[str]:
    """Return the ordered download endpoints of one source."""
    urls = source.get("urls")
    if urls:
        return [url for url in urls if url]
    if source.get("url"):
        return [source["url"]]
    return []


def load_config(config_path: Path) -> dict:
    """Load and sanity-check the configuration file."""
    if not config_path.exists():
        raise ConfigError(f"config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    if not isinstance(config, dict) or not config.get("sources"):
        raise ConfigError("config must contain a non-empty 'sources' list")

    sources = config["sources"]
    if not isinstance(sources, list):
        raise ConfigError("'sources' must be a list")

    seen_ids = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ConfigError(f"sources[{index}] must be a mapping")
        for key in ("id", "name", "filename"):
            if not source.get(key):
                raise ConfigError(f"sources[{index}] is missing '{key}'")
        if not source_endpoints(source):
            raise ConfigError(f"sources[{index}] has no 'urls'")
        if source["id"] in seen_ids:
            raise ConfigError(f"duplicate source id: {source['id']}")
        seen_ids.add(source["id"])

    strategy = config.get("update_strategy")
    if not isinstance(strategy, dict):
        raise ConfigError("config must contain an 'update_strategy' mapping")
    missing = [key for key in REQUIRED_STRATEGY_KEYS if key not in strategy]
    if missing:
        raise ConfigError(
            "update_strategy is missing keys: " + ", ".join(sorted(missing))
        )

    return config


class RuleUpdater:
    def __init__(self, config_path: str, root_dir: Optional[Path] = None):
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.root_dir = root_dir or self.config_path.parent.parent
        self.strategy = self.config["update_strategy"]
        self.results: List[dict] = []
        self.dry_run = False
        self._fetch = download

    # -- single source ----------------------------------------------------

    def _download_source(self, source: dict) -> Tuple[bytes, str]:
        """Download from the first reachable endpoint, in configured order."""
        endpoints = source_endpoints(source)
        errors: List[str] = []
        timeout = source.get("timeout", self.strategy["default_timeout"])

        for index, url in enumerate(endpoints, 1):
            try:
                content = self._fetch(
                    url, timeout=timeout, retries=self.strategy["retries"]
                )
                return content, url
            except DownloadError as error:
                errors.append(f"endpoint {index} ({url}): {error}")
                if index < len(endpoints):
                    print(f"   endpoint {index} failed, trying mirror {index + 1}/{len(endpoints)}")

        raise DownloadError("; ".join(errors))

    def update_source(self, source: dict) -> dict:
        name = source["name"]
        filename = source["filename"]
        path = self.root_dir / filename
        result = {
            "id": source["id"],
            "name": name,
            "filename": filename,
            "optional": bool(source.get("optional", False)),
        }

        print(f"\n-> {name}")
        for index, url in enumerate(source_endpoints(source), 1):
            print(f"   url{'' if index == 1 else f' #{index}'}: {url}")

        try:
            raw, endpoint = self._download_source(source)
        except DownloadError as error:
            print(f"   FAILED download: {error}")
            return {**result, "status": "failed", "reason": str(error)}

        result["endpoint"] = endpoint
        content = normalize(raw)
        metadata = parse_metadata(content.decode("utf-8", errors="replace"))
        result["version"] = metadata.get("version", "-")
        print(f"   version: {result['version']}")

        old_content = None
        if path.exists():
            old_content = normalize(path.read_bytes())
            if content_hash(content) == content_hash(old_content):
                print("   SKIPPED: content unchanged")
                return {**result, "status": "skipped", "reason": "content unchanged"}

        reason = validate(content, old_content, source, self.strategy)
        if reason:
            print(f"   FAILED validation: {reason}")
            return {**result, "status": "failed", "reason": reason}

        line_count = len(content.split(b"\n")) - 1
        result["lines"] = line_count
        result["size_kb"] = round(len(content) / 1024, 1)

        if self.dry_run:
            print(f"   WOULD UPDATE ({line_count} lines, {result['size_kb']}KB)")
            return {**result, "status": "would-update", "reason": "dry run"}

        try:
            write_atomic(path, content)
        except OSError as error:
            print(f"   FAILED write: {error}")
            return {**result, "status": "failed", "reason": f"write failed: {error}"}

        print(f"   UPDATED ({line_count} lines, {result['size_kb']}KB)")
        return {**result, "status": "updated", "reason": "content changed"}

    # -- run --------------------------------------------------------------

    def run(self, dry_run: bool = False) -> int:
        self.dry_run = dry_run

        print("=" * 60)
        print("ADrules updater" + (" (dry run)" if dry_run else ""))
        print("=" * 60)

        sources = self.config["sources"]
        for index, source in enumerate(sources, 1):
            print(f"\n[{index}/{len(sources)}]")
            try:
                self.results.append(self.update_source(source))
            except Exception as error:  # never let one source kill the batch
                print(f"   FAILED unexpected: {error}")
                self.results.append(
                    {
                        "id": source.get("id", "?"),
                        "name": source.get("name", "?"),
                        "filename": source.get("filename", "?"),
                        "optional": bool(source.get("optional", False)),
                        "status": "failed",
                        "reason": f"unexpected error: {error}",
                    }
                )

        return self._report()

    def _report(self) -> int:
        updated = sum(1 for r in self.results if r["status"] == "updated")
        skipped = sum(1 for r in self.results if r["status"] == "skipped")
        would_update = sum(1 for r in self.results if r["status"] == "would-update")
        failed = [r for r in self.results if r["status"] == "failed"]
        fatal = [r for r in failed if not r.get("optional")]
        optional_failures = [r for r in failed if r.get("optional")]

        print("\n" + "=" * 60)
        print("summary")
        print("=" * 60)
        if self.dry_run:
            print(f"would update: {would_update}")
        else:
            print(f"updated: {updated}")
        print(f"skipped: {skipped}")
        print(f"failed:  {len(fatal)}")
        if optional_failures:
            print(f"optional failures: {len(optional_failures)} (not fatal)")
        print(f"total:   {len(self.results)}")

        for result in fatal:
            print(f"  ! {result['name']}: {result['reason']}")
        for result in optional_failures:
            print(f"  ~ {result['name']}: {result['reason']}")

        self._write_step_summary(
            updated, skipped, len(fatal), would_update, len(optional_failures)
        )
        return 1 if fatal else 0

    def _write_step_summary(
        self,
        updated: int,
        skipped: int,
        failed: int,
        would_update: int,
        optional_failures: int = 0,
    ) -> None:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_path:
            return

        lines = [
            "## ADrules update",
            "",
            f"- updated: {updated}",
            f"- skipped: {skipped}",
            f"- failed: {failed}",
        ]
        if optional_failures:
            lines.append(f"- optional failures (not fatal): {optional_failures}")
        if self.dry_run:
            lines.append(f"- would update: {would_update}")
        lines += ["", "| source | status | version | lines | size | reason |"]
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for result in self.results:
            lines.append(
                "| {name} | {status} | {version} | {lines} | {size_kb} | {reason} |".format(
                    name=result["name"],
                    status=result["status"],
                    version=result.get("version", "-"),
                    lines=result.get("lines", "-"),
                    size_kb=result.get("size_kb", "-"),
                    reason=result.get("reason", "-"),
                )
            )

        try:
            with open(summary_path, "a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
        except OSError as error:
            print(f"warning: cannot write step summary: {error}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update ADrules filter lists.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent / "config.yaml"),
        help="path to config.yaml (default: next to this script)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing any file",
    )
    args = parser.parse_args(argv)

    try:
        updater = RuleUpdater(args.config)
    except ConfigError as error:
        print(f"config error: {error}", file=sys.stderr)
        return 1

    return updater.run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
