#!/usr/bin/env python3
"""CI-only log witness. Emits only aggregate counters, never raw log or secret data.
Literal lab credential and synthetic PII checks are bounded, not a general DLP claim.
"""
import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_from_bytes, unquote_to_bytes

MAX_LOG_BYTES = 32 * 1024 * 1024
MAX_SECRET_BYTES = 4096
ROLE_FILES = ("history_app", "auth_revoker", "auth_trust_api", "auth_login_bootstrap",
              "auth_login_claim_reader", "auth_login_issuer", "auth_mapper",
              "auth_login_binder", "auth_login_reader")


def secret_values(root, work):
    candidates = []
    for name in ("web/proof", "web/csrf", "web/alias", "bootstrap/seal"):
        candidates.append(("lab_secret", (root / name).read_bytes().strip()))
    for role in ROLE_FILES:
        candidates.append(("db_role_password", (work / (role + ".password")).read_bytes().strip()))
    users = json.loads((root / "browser/users.json").read_text())
    if set(users) != {"a", "b"}:
        raise ValueError("unexpected lab subjects")
    for user in users.values():
        for field in ("username", "password", "subject"):
            candidates.append(("synthetic_identity" if field != "password" else "lab_secret",
                               user[field].encode("utf-8")))
    # Known text from the synthetic History fixture, not financial or real-user data.
    candidates.extend(("synthetic_history", value) for value in (b"lab browser A", b"lab browser B"))
    if any(not (12 <= len(value) <= MAX_SECRET_BYTES) for _, value in candidates):
        raise ValueError("invalid expected secret or fixture")
    return tuple(candidates)


def scan(stream, candidates, max_bytes=MAX_LOG_BYTES):
    if not candidates or max_bytes < 1:
        raise ValueError("invalid scan bounds")
    # A bounded complete in-memory read, avoiding missed matches at chunk edges.
    raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        return {"result": "INCOMPLETE_LOG_LIMIT", "bytes_checked": 0, "matches": {}}
    if not raw.strip():
        return {"result": "INCOMPLETE_EMPTY_LOG", "bytes_checked": 0, "matches": {}}
    # One bounded percent-decode catches mixed-case and partially escaped
    # markers. Do not recursively expand or accept arbitrary encodings.
    decoded = unquote_to_bytes(raw)
    matches = {}
    for category, value in candidates:
        if not value:
            raise ValueError("empty marker")
        # Encoded forms can appear in query strings or diagnostic payloads.
        variants = {value, quote_from_bytes(value, safe='').encode('ascii'),
                    base64.b64encode(value), base64.urlsafe_b64encode(value),
                    base64.b64encode(value).rstrip(b"="),
                    base64.urlsafe_b64encode(value).rstrip(b"="),
                    json.dumps(value.decode("utf-8", errors="strict"), ensure_ascii=True)[1:-1].encode("ascii")}
        if any(v in raw or v in decoded for v in variants):
            matches[category] = matches.get(category, 0) + 1
    # Construct the literal from parts so the source secret scanner does not
    # confuse this detector itself with key material.
    if re.search(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?" + rb"PRIVATE KEY-----", raw):
        matches["private_key_header"] = 1
    # Dynamic credentials are detected by conservative shapes; no matching
    # substring is ever printed. This is not proof of complete token redaction.
    patterns = {
        "jwt_shape": rb"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{12,}\b",
        "session_cookie_shape": rb"(?i)__Host-rag-(?:session|login-init)\s*=\s*[A-Za-z0-9_-]{16,}",
        "authorization_shape": rb"(?i)\b(?:Bearer|BFF-Assertion)\s+[A-Za-z0-9_.-]{16,}",
        "oauth_query_shape": rb"(?i)[?&](?:code|access_token|refresh_token|id_token)=([A-Za-z0-9_.%~-]{16,})",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, raw) or re.search(pattern, decoded):
            matches[name] = 1
    return {"result": "LEAK_FOUND" if matches else "NO_LITERAL_MATCHES",
            "bytes_checked": len(raw), "matches": matches}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--stage", choices=("source", "restore"), required=True)
    p.add_argument("--service-group", choices=("app", "postgres"), default="app")
    args = p.parse_args()
    try:
        if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("CI only")
        runner = Path(os.environ["RUNNER_TEMP"]).resolve()
        root, work = args.root.resolve(), args.work.resolve()
        if root.parent != work or root.name != "browser-journey" or not work.is_relative_to(runner):
            raise ValueError("outside lab")
        receipt = scan(sys.stdin.buffer, secret_values(root, work))
    except Exception:
        # Never print exception text, input data, path content, or a traceback.
        receipt = {"result": "INCOMPLETE_INPUT_OR_ENV", "bytes_checked": 0, "matches": {}}
    print("F3_LAB_LOG_GUARD", json.dumps({"stage": args.stage, "service_group": args.service_group, **receipt,
        "scope": "literal and encoded lab credentials, fixture data and selected token shapes; not complete PII/DLP policy",
        "target_acceptance": "NOT_ACCEPTED"}, sort_keys=True), flush=True)
    return 0 if receipt["result"] == "NO_LITERAL_MATCHES" else 70


if __name__ == "__main__":
    sys.exit(main())
