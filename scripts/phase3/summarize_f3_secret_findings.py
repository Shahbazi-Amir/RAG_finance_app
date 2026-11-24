#!/usr/bin/env python3
"""Redact Gitleaks matches into a path/cohort triage receipt (NOT approval).

This processes a *temporary* raw scan report in CI. Never store or upload
Secret, Match, line source, author, commit or entropy values. Finding count
is not confirmed leakage, and test fixtures require individual review too.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PurePosixPath
import re

SAFE_FILE = re.compile(r"^[A-Za-z0-9._/+-]{1,160}$")
SAFE_RULE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def sanitize_path(raw: object) -> str:
    if not isinstance(raw, str):
        return "REDACTED_UNKNOWN_PATH"
    value = raw.replace("\\", "/").removeprefix("./")
    if not SAFE_FILE.fullmatch(value):
        return "REDACTED_UNKNOWN_PATH"
    components = PurePosixPath(value).parts
    if not components or value.startswith("/") or ".." in components:
        return "REDACTED_UNKNOWN_PATH"
    return value


def classify(path: str) -> str:
    if path.startswith(("tests/", "test/", "fixtures/")) or "/fixtures/" in path:
        return "TEST_OR_FIXTURE_REQUIRES_REVIEW"
    if path.startswith(".github/"):
        return "WORKFLOW_REQUIRES_REVIEW"
    if path.startswith(("apps/", "src/", "packages/", "infra/", "scripts/")):
        return "RUNTIME_OR_INFRA_SOURCE_REQUIRES_REVIEW"
    if path.startswith(("docs/", "coordination/", "references/")):
        return "DOC_OR_REFERENCE_REQUIRES_REVIEW"
    return "OTHER_OR_UNCLASSIFIED_REQUIRES_REVIEW"


def summarize(raw: list[dict], sha: str) -> dict:
    if len(sha) != 40 or not re.fullmatch("[a-f0-9]{40}", sha):
        raise ValueError("INVALID_CHECKOUT_SHA")
    if not isinstance(raw, list):
        raise ValueError("GITLEAKS_REPORT_MUST_BE_LIST")
    rules: Counter[str] = Counter()
    cohorts: Counter[str] = Counter()
    paths: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "lines": set()})
    for match in raw:
        if not isinstance(match, dict):
            raise ValueError("INVALID_GITLEAKS_MATCH")
        path = sanitize_path(match.get("File"))
        cohort = classify(path)
        rule = match.get("RuleID")
        rule = rule if isinstance(rule, str) and SAFE_RULE.fullmatch(rule) else "REDACTED_UNKNOWN_RULE"
        rules[rule] += 1
        cohorts[cohort] += 1
        record = paths[(cohort, path)]
        record["count"] += 1
        line = match.get("StartLine")
        if isinstance(line, int) and not isinstance(line, bool) and 0 < line < 10000000:
            record["lines"].add(line)
    items = [{
        "cohort": cohort, "relative_path": path, "potential_findings": data["count"],
        "line_numbers": sorted(data["lines"]),
        "security_review": "OPEN_NOT_EXEMPTED",
    } for (cohort, path), data in sorted(paths.items())]
    return {
        "schema": "foundation.f3.gitleaks_path_triage_no_secrets.v1",
        "git_sha": sha,
        "scanner_scope": "CHECKED_OUT_FILES_ONLY_NO_GIT_HISTORY",
        "potential_findings_total": len(raw),
        "by_rule": dict(sorted(rules.items())),
        "by_cohort": dict(sorted(cohorts.items())),
        "source_locations": items,
        "possible_secret_exfiltration_review": "PENDING_OWNER",
        "all_test_fixture_matches_require_review": True,
        "no_raw_secret_lines_or_matches_uploaded": True,
        "security_release_gate": "HOLD_PENDING_REVIEW",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    if not args.raw.is_file():
        raise SystemExit("GITLEAKS_RAW_REPORT_MISSING")
    report = json.loads(args.raw.read_text(encoding="utf-8"))
    summary = summarize(report, args.sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + chr(10),
        encoding="utf-8")
    print("F3_GITLEAKS_PATH_TRIAGE_REDACTED_" +
          str(summary["potential_findings_total"]) + "_HOLD")


if __name__ == "__main__":
    main()
