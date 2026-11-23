#!/usr/bin/env python3
"""Offline L2 evidence consistency verifier for an isolated Mac UI NO_DISPATCH run.

This tool does NOT create, sign, simulate or accept real Mac/OIDC/PG/OS evidence.
It checks already-collected sanitized receipts and prints machine-readable gaps.
L2/Gate acceptance always requires independent human/owner authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SCHEMA = "ui.l2.nodispatch.v0_1"
KIND = "ui_f3_mac_no_dispatch_l2_receipt"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALIAS = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
REQUIRED_FILES = ("browser", "api", "db", "os")
STATUS_PATH = "/api/history/message-requests/status"
CONVERSATIONS_PATH = "/api/history/conversations"


def dictionary(value):
    return value if isinstance(value, dict) else {}


def valid_sha(value, digits=40):
    return isinstance(value, str) and bool((HEX40 if digits == 40 else HEX64).fullmatch(value))


def bool_exact(value, expected):
    return type(value) is bool and value is expected


def int_exact(value, expected):
    return type(value) is int and value == expected


def safe_witness_path(root: Path, raw: object) -> Path | None:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute() or any(part in ("", ".", "..") for part in candidate.parts):
        return None
    root_abs = root.resolve()
    target = (root_abs / candidate).resolve()
    if not target.is_relative_to(root_abs) or not target.is_file():
        return None
    return target


def evaluate(doc: object, root: Path, *, allow_synthetic: bool = False) -> list[str]:
    """Return deterministic failed assertions, no acceptance decision."""
    d = dictionary(doc)
    failed: list[str] = []

    def require(condition: bool, assertion: str):
        if not condition:
            failed.append(assertion)

    require(d.get("kind") == KIND and d.get("schema_version") == SCHEMA,
            "RECEIPT_SCHEMA_UNKNOWN")
    require(bool_exact(d.get("fixture_only"), False) or
            (allow_synthetic and bool_exact(d.get("fixture_only"), True)),
            "NO_SYNTHETIC_L2_ACCEPTANCE")

    provenance = dictionary(d.get("provenance"))
    for field in ("integrated_sha", "ui_sha", "api_sha", "db_sha", "engine_sha"):
        require(valid_sha(provenance.get(field)), "EXACT_SHA_MISSING_" + field)
    require(isinstance(provenance.get("ops_approval_ref"), str) and
            bool(provenance.get("ops_approval_ref", "").strip()), "OPS_SCOPE_AUTHORIZATION_MISSING")
    require(provenance.get("runner_mode") == "NO_DISPATCH_ONLY", "RUNNER_MODE_NOT_NO_DISPATCH")
    require(d.get("environment") == "isolated_mac_https_oidc", "REAL_MAC_ENVIRONMENT_NOT_ATTESTED")

    browser = dictionary(d.get("browser"))
    origin = browser.get("https_origin")
    try:
        u = urlsplit(origin if isinstance(origin, str) else "")
        origin_ok = (u.scheme == "https" and bool(u.hostname) and
                     u.hostname not in {"localhost", "127.0.0.1", "::1"} and
                     not u.username and not u.password and not u.path.strip("/") and
                     not u.query and not u.fragment and u.port in (None, 443))
    except ValueError:
        origin_ok = False
    require(origin_ok, "BROWSER_HTTPS_OIDC_ORIGIN_MISSING")
    a, b = browser.get("actor_a_session_alias"), browser.get("actor_b_session_alias")
    require(isinstance(a, str) and isinstance(b, str) and
            bool(ALIAS.fullmatch(a)) and bool(ALIAS.fullmatch(b)) and a != b,
            "DISTINCT_SANITIZED_A_B_SESSIONS_MISSING")
    for field in ("oidc_a_validated", "oidc_b_validated", "logout_navigated",
                  "owner_switch_clears_ui", "revocation_clears_ui",
                  "late_get_cannot_restore", "mobile_rtl_a11y_pass",
                  "owner_a_revalidated_same"):
        require(bool_exact(browser.get(field), True), "BROWSER_" + field.upper() + "_NOT_PROVEN")
    require(bool_exact(browser.get("tab_b_a_data_visible"), False),
            "CROSS_TAB_ACCOUNT_LEAK")
    require(bool_exact(browser.get("stale_thread_after_recovery_visible"), False),
            "STALE_HISTORY_RESURRECTED_AFTER_RECOVERY")

    corr = dictionary(d.get("correlation"))
    for field in ("t2_id", "attempt_id", "attempt_trace_id", "client_message_id", "idempotency_key"):
        val = corr.get(field)
        require(isinstance(val, str) and bool(ALIAS.fullmatch(val)),
                "T2_ATTEMPT_CORRELATOR_MISSING_" + field)
    require(valid_sha(corr.get("question_sha256"), 64), "QUESTION_DIGEST_MISSING")

    events = d.get("http_events")
    require(isinstance(events, list) and 0 < len(events) <= 200,
            "BOUND_BROWSER_API_EVENT_LOG_MISSING")
    events = events if isinstance(events, list) else []
    normalized = [dictionary(x) for x in events]
    seqs = [x.get("seq") for x in normalized]
    require(all(type(s) is int and s > 0 for s in seqs) and
            len(seqs) == len(set(seqs)) and seqs == sorted(seqs),
            "HTTP_EVENT_SEQUENCE_INVALID")
    require(all(x.get("phase") in {"initial", "outage", "recovery", "refresh", "cross_owner", "revoked"} and
                x.get("actor") in {"A", "B"} and
                x.get("layer") in {"browser", "api"} and
                x.get("method") in {"GET", "POST"} and
                isinstance(x.get("path"), str) and x["path"].startswith("/api/history/") and
                type(x.get("status")) is int and 100 <= x["status"] <= 599
                for x in normalized), "UNTRUSTED_OR_MALFORMED_HTTP_EVENTS")

    for field in ("t2_id", "attempt_id", "attempt_trace_id", "client_message_id", "idempotency_key"):
        require(all(x.get(field) == corr.get(field) for x in normalized),
                "CROSS_LAYER_CORRELATION_MISMATCH_" + field)

    def select(phase, actor=None, layer=None, method=None, path=None, status=None):
        return [x for x in normalized
                if x.get("phase") == phase and
                (actor is None or x.get("actor") == actor) and
                (layer is None or x.get("layer") == layer) and
                (method is None or x.get("method") == method) and
                (path is None or x.get("path") == path) and
                (status is None or x.get("status") == status)]

    initial_post = [x for x in normalized if x.get("method") == "POST"]
    require(len(initial_post) == 2 and
            len(select("initial", "A", "browser", "POST", "/api/history/messages", 202)) == 1 and
            len(select("initial", "A", "api", "POST", "/api/history/messages", 202)) == 1,
            "EXACTLY_ONE_INITIAL_SEND_POST_PER_LAYER")
    require(not any(x.get("method") == "POST" and x.get("phase") != "initial"
                    for x in normalized), "NO_POST_ON_REFRESH_OR_RECOVERY")
    require(len(select("outage", "A", "api", "GET", CONVERSATIONS_PATH, 503)) >= 1 and
            len(select("recovery", "A", "api", "GET", CONVERSATIONS_PATH, 200)) >= 1,
            "OWNER_LIST_503_RECOVERY_GET_NOT_PROVEN")
    require(len(select("initial", "A", "api", "GET", STATUS_PATH, 200)) >= 1 and
            len(select("refresh", "A", "api", "GET", STATUS_PATH, 200)) >= 1 and
            len(select("refresh", "A", "browser", "GET", CONVERSATIONS_PATH, 200)) >= 1,
            "REFRESH_DOES_NOT_READ_ORIGINAL_STATUS")
    try:
        browser_post = select("initial", "A", "browser", "POST", "/api/history/messages", 202)[0]["seq"]
        api_post = select("initial", "A", "api", "POST", "/api/history/messages", 202)[0]["seq"]
        status_get = select("initial", "A", "api", "GET", STATUS_PATH, 200)[0]["seq"]
        outage_get = select("outage", "A", "api", "GET", CONVERSATIONS_PATH, 503)[0]["seq"]
        recovery_get = select("recovery", "A", "api", "GET", CONVERSATIONS_PATH, 200)[0]["seq"]
        refresh_get = select("refresh", "A", "api", "GET", STATUS_PATH, 200)[0]["seq"]
        ordered = browser_post < api_post < status_get < outage_get < recovery_get < refresh_get
    except (IndexError, TypeError, KeyError):
        ordered = False
    require(ordered, "OPERATION_503_RECOVERY_ORDER_INVALID")
    require(len(select("cross_owner", "B", "api", "GET", STATUS_PATH, 404)) >= 1,
            "CROSS_OWNER_NOT_PROVED_404")
    require(len(select("revoked", "A", "api", "GET", CONVERSATIONS_PATH, 401)) >= 1,
            "REVOKE_NOT_PROVED_401")

    db = dictionary(d.get("database"))
    runner = dictionary(d.get("runner"))
    for field in ("t2_id", "attempt_id", "attempt_trace_id"):
        require(db.get(field) == corr.get(field), "DB_T2_MISMATCH_" + field)
    for field in ("attempt_id", "attempt_trace_id"):
        require(runner.get(field) == corr.get(field), "OS_ATTEMPT_MISMATCH_" + field)
    for name, wanted in (("owner_b_cross_history_rows", 0),
                         ("new_attempt_rows_after_refresh", 0),
                         ("new_user_messages_after_refresh", 0),
                         ("new_answer_rows_after_refresh", 0)):
        require(int_exact(db.get(name), wanted), "DB_" + name.upper() + "_INVALID")
    require(int_exact(db.get("owner_a_history_rows"), 1) or
            (type(db.get("owner_a_history_rows")) is int and db["owner_a_history_rows"] > 1),
            "DB_OWNER_A_HISTORY_NOT_PERSISTED")
    require(bool_exact(db.get("original_request_unique"), True), "DB_ORIGINAL_REQUEST_NOT_UNIQUE")
    for field, value in (("c018_child_count_before_refresh", 1),
                         ("c018_child_count_after_refresh", 1),
                         ("top10_before", 10), ("top10_after", 10),
                         ("generation_calls_before", 0),
                         ("generation_calls_after", 0)):
        require(int_exact(runner.get(field), value), "OS_" + field.upper() + "_INVALID")
    require(bool_exact(runner.get("dispatch_performed"), False),
            "NO_DISPATCH_MUST_REMAIN_FALSE")
    require(valid_sha(runner.get("c018_artifact_sha256"), 64),
            "C018_ARTIFACT_SHA256_MISSING")

    witnesses = dictionary(d.get("witnesses"))
    resolved_paths: list[str] = []
    for key in REQUIRED_FILES:
        entry = dictionary(witnesses.get(key))
        path = safe_witness_path(root, entry.get("path"))
        require(path is not None, "WITNESS_FILE_ABSENT_OR_OUTSIDE_ROOT_" + key)
        require(valid_sha(entry.get("sha256"), 64), "WITNESS_SHA256_MISSING_" + key)
        if path is not None:
            resolved_paths.append(str(path))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            require(digest == entry.get("sha256"), "WITNESS_HASH_MISMATCH_" + key)
    require(len(resolved_paths) == len(set(resolved_paths)), "INDEPENDENT_WITNESS_FILES_REUSED")
    return sorted(set(failed))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt_json", type=Path, help="Already-collected sanitized L2 receipt JSON")
    parser.add_argument("--json", action="store_true", help="Machine-readable report (always output JSON)")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.receipt_json.read_text(encoding="utf-8"))
        issues = evaluate(document, args.receipt_json.parent)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        issues = ["EVIDENCE_NOT_READABLE_OR_VALID_JSON:" + type(exc).__name__]
    report = {
        "schema_version": SCHEMA,
        "status": ("RECEIPT_INTERNALLY_CONSISTENT_NOT_GATE_ACCEPTED"
                   if not issues else "NOT_VERIFIED"),
        "gate_accepted": False,
        "real_mac_execution_performed_by_this_tool": False,
        "independent_owner_review_required": True,
        "failed_assertions": issues,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
