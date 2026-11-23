#!/usr/bin/env python3
"""Foundation F3: fail-closed *intake preflight*, never authority to accept/deploy.

Checks immutable local Release artifact bytes and constrained/sanitized Ops receipt
structure. A structurally valid receipt is NOT proof of execution or identity.
No network, Docker, database, private configs or model calls.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
REQ_RELEASE = frozenset(("data", "chunks", "embeddings", "index", "config", "nb23",
                         "request_schema", "response_schema", "locator_audit", "attribution_audit"))
STAGES = ("snapshot", "build", "auth_l2", "c018", "restore", "load", "trace")


class InvalidEvidence(ValueError):
    pass


def need(check, label):
    if not check:
        raise InvalidEvidence(label)


def read_json(path):
    try:
        with Path(path).open("rb") as f:
            data = f.read(1024 * 1024 + 1)
        need(len(data) <= 1024 * 1024, "JSON_OVER_1MB")
        doc = json.loads(data)
        need(type(doc) is dict, "JSON_OBJECT_REQUIRED")
        return doc
    except (OSError, ValueError, UnicodeError) as exc:
        if isinstance(exc, InvalidEvidence):
            raise
        raise InvalidEvidence("MALFORMED_OR_UNREADABLE_JSON") from exc


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_artifact(root, raw_path):
    need(type(raw_path) is str and raw_path and "\\" not in raw_path and "\x00" not in raw_path,
         "UNSAFE_ARTIFACT_PATH")
    rel = Path(raw_path)
    need(not rel.is_absolute() and all(p not in ("", ".", "..") for p in rel.parts), "UNSAFE_ARTIFACT_PATH")
    cur = root
    for part in rel.parts:
        cur = cur / part
        need(not cur.is_symlink(), "SYMLINK_ARTIFACT_PATH")
    need(cur.is_file(), "ARTIFACT_MISSING")
    return cur


def verify_release(manifest_file, artifact_root):
    doc = read_json(manifest_file)
    need(doc.get("schema") == "f3.phase2_release_intake.v1", "RELEASE_SCHEMA_UNSUPPORTED")
    rid = doc.get("release_id")
    need(type(rid) is str and RELEASE_ID.fullmatch(rid) is not None, "RELEASE_ID_INVALID")
    need(type(doc.get("upstream_git_sha")) is str and GIT_SHA.fullmatch(doc["upstream_git_sha"]),
         "UPSTREAM_GIT_SHA_INVALID")
    need(doc.get("phase2_accepted_for_phase3") is not True, "GATE00_RESULT_MUST_NOT_BE_INPUT")
    items = doc.get("artifacts")
    need(type(items) is list, "ARTIFACT_LIST_REQUIRED")
    types, seen_paths = set(), set()
    root = Path(artifact_root).resolve(strict=True)
    for entry in items:
        need(type(entry) is dict, "ARTIFACT_ENTRY_INVALID")
        kind, path, sha, size = (entry.get(k) for k in ("kind", "path", "sha256", "size_bytes"))
        need(type(kind) is str and kind in REQ_RELEASE and kind not in types, "ARTIFACT_KIND_MISSING_DUPLICATE_OR_UNKNOWN")
        need(type(path) is str and path not in seen_paths, "DUPLICATE_ARTIFACT_PATH")
        need(type(sha) is str and SHA256.fullmatch(sha) is not None, "ARTIFACT_SHA_INVALID")
        need(type(size) is int and size >= 0, "ARTIFACT_SIZE_INVALID")
        file = safe_artifact(root, path)
        need(file.stat().st_size == size, "ARTIFACT_SIZE_DRIFT_" + kind)
        need(hash_file(file) == sha, "ARTIFACT_HASH_DRIFT_" + kind)
        seen_paths.add(path)
        types.add(kind)
    need(types == REQ_RELEASE, "RELEASE_MISSING_ARTIFACT_TYPES")
    return {"scope": "BYTE_INTEGRITY_ONLY_NO_GATE00", "release_id": rid,
            "artifacts_verified": len(types), "phase2_acceptance": "NOT_ESTABLISHED",
            "semantic_authority_locator_audit": "NOT_VERIFIED_BY_THIS_SCRIPT"}


def nonempty_str(doc, key):
    need(type(doc.get(key)) is str and bool(doc[key].strip()), "MISSING_" + key.upper())


def exact_bool(doc, key, wanted):
    need(type(doc.get(key)) is bool and doc[key] is wanted, "BAD_" + key.upper())


def exact_int(doc, key, wanted):
    need(type(doc.get(key)) is int and doc[key] == wanted, "BAD_" + key.upper())


def check_no_secrets(value):
    """Receipt field names may never carry raw private runtime credentials."""
    if type(value) is dict:
        for k, v in value.items():
            need(type(k) is str, "NONSTRING_FIELD_NAME")
            need(not re.search(r"(?i)(private[_-]?key|password|authorization[_-]?header|client[_-]?secret|access[_-]?token|refresh[_-]?token|cookie|dsn)", k), "SECRET_FIELD_DISALLOWED")
            check_no_secrets(v)
    elif type(value) is list:
        for v in value:
            check_no_secrets(v)


def verify_receipt(receipt_file, *, expected_sha, expected_tree, stage):
    need(stage in STAGES, "UNKNOWN_STAGE")
    need(GIT_SHA.fullmatch(expected_sha) is not None and GIT_SHA.fullmatch(expected_tree) is not None,
         "EXPECTED_GIT_SHA_INVALID")
    doc = read_json(receipt_file)
    check_no_secrets(doc)
    need(doc.get("schema") == "f3.target_receipt_intake.v1", "TARGET_SCHEMA_UNSUPPORTED")
    need(doc.get("stage") == stage, "STAGE_MISMATCH")
    need(doc.get("source_sha") == expected_sha and doc.get("source_tree") == expected_tree, "SOURCE_PIN_MISMATCH")
    need(doc.get("environment") == "MAC_ISOLATED_CANDIDATE", "ENVIRONMENT_NOT_ISOLATED")
    need(doc.get("arvan") == "HOLD", "ARVAN_NOT_HOLD")
    exact_bool(doc, "frozen_demo_untouched", True)
    exact_bool(doc, "paid_gateway_calls_allowed", False)
    nonempty_str(doc, "ops_authorization_reference")
    nonempty_str(doc, "operator_receipt_reference")
    if stage == "snapshot":
        for key in ("dedicated_worktree", "compose_project", "source_archive_sha256"):
            nonempty_str(doc, key)
        need(SHA256.fullmatch(doc["source_archive_sha256"]) is not None, "SNAPSHOT_DIGEST_INVALID")
        need("rag_finance_f3_demo" not in doc["dedicated_worktree"], "FROZEN_DEMO_WORKTREE")
        need(doc["compose_project"] != "rag_finance_f3_demo", "FROZEN_DEMO_COMPOSE")
        exact_bool(doc, "isolated_volumes_and_ports", True)
    elif stage == "build":
        images = doc.get("images")
        need(type(images) is list and len(images) >= 3, "INSUFFICIENT_BUILT_IMAGES")
        names = set()
        for img in images:
            need(type(img) is dict, "IMAGE_ENTRY_INVALID")
            nonempty_str(img, "service")
            need(img["service"] not in names, "DUPLICATE_IMAGE_SERVICE")
            names.add(img["service"])
            for k in ("image_id", "sbom_sha256", "scan_receipt_sha256"):
                nonempty_str(img, k)
            need(re.fullmatch(r"sha256:[0-9a-f]{64}", img["image_id"]) is not None, "INVALID_IMAGE_ID")
            need(SHA256.fullmatch(img["sbom_sha256"]) and SHA256.fullmatch(img["scan_receipt_sha256"]), "SCAN_DIGEST_INVALID")
            need(img.get("platform") == "linux/amd64", "PLATFORM_NOT_AMD64")
            exact_int(img, "unresolved_critical", 0)
        exact_bool(doc, "engine_lock_and_wheelhouse_attested", True)
    elif stage == "auth_l2":
        for key in ("real_https", "oidc_login", "signed_bff_mtls_rs256", "pg_verified_two_owners", "same_attempt_t1_t2"):
            exact_bool(doc, key, True)
        for key, expected in (("send_http", 202), ("replay_http", 200),
                              ("owner_b_http", 404), ("revoked_http", 401),
                              ("refresh_extra_post", 0)):
            exact_int(doc, key, expected)
        exact_bool(doc, "refresh_get_only", True)
        exact_bool(doc, "no_dispatch", True)
        # Auth/History L2 may be run WITHOUT C018, which has a separate authorization.
    elif stage == "c018":
        nonempty_str(doc, "separate_c018_authorization_reference")
        for key in ("index_copy_sha256", "original_runner_sha256"):
            nonempty_str(doc, key)
            need(SHA256.fullmatch(doc[key]) is not None, "C018_HASH_INVALID")
        for key, wanted in (("os_child_count", 1), ("new_child_after_refresh", 0),
                            ("top_k", 10), ("generation_calls", 0), ("refresh_extra_post", 0)):
            exact_int(doc, key, wanted)
        exact_bool(doc, "dispatch", False)
        need("answer" in doc and doc["answer"] is None, "C018_ANSWER_MUST_BE_NULL")
        need(doc.get("state") == "CONTEXT_READY", "C018_CONTEXT_NOT_READY")
        exact_bool(doc, "same_attempt_trace", True)
    elif stage == "restore":
        for key in ("backup_sha256", "encrypted_backup_sha256", "qdrant_copy_sha256", "qdrant_restore_sha256"):
            nonempty_str(doc, key)
            need(SHA256.fullmatch(doc[key]) is not None, "RESTORE_DIGEST_INVALID")
        for key in ("source_pg_cluster_id", "restored_pg_cluster_id", "backup_encryption_key_reference"):
            nonempty_str(doc, key)
        need(doc["source_pg_cluster_id"] != doc["restored_pg_cluster_id"], "RESTORE_SAME_CLUSTER")
        for key in ("separate_empty_restore_target", "restore_acl_rls_verified", "deletion_tombstone_no_resurrection"):
            exact_bool(doc, key, True)
        for key in ("measured_rpo_seconds", "measured_rto_seconds", "approved_rpo_seconds", "approved_rto_seconds"):
            value = doc.get(key)
            need(type(value) in (int, float) and 0 <= value < float("inf"), "INVALID_" + key.upper())
        need(doc["measured_rpo_seconds"] <= doc["approved_rpo_seconds"], "RPO_EXCEEDS_APPROVED_BOUND")
        need(doc["measured_rto_seconds"] <= doc["approved_rto_seconds"], "RTO_EXCEEDS_APPROVED_BOUND")
        nonempty_str(doc, "signed_rpo_rto_policy_reference")
    elif stage == "load":
        nonempty_str(doc, "approved_workload_policy_reference")
        need(type(doc.get("sample_requests")) is int and doc["sample_requests"] > 0, "INVALID_LOAD_SAMPLE_COUNT")
        for key in ("p50_ms", "p95_ms", "p99_ms", "approved_p95_ms", "error_rate_pct", "approved_error_rate_pct"):
            val = doc.get(key)
            need(type(val) in (int, float) and 0 <= val < float("inf"), "INVALID_" + key.upper())
        need(0 <= doc["error_rate_pct"] <= 100 and 0 <= doc["approved_error_rate_pct"] <= 100,
             "ERROR_PERCENT_OUT_OF_RANGE")
        need(doc["p50_ms"] <= doc["p95_ms"] <= doc["p99_ms"], "PERCENTILE_ORDER_INVALID")
        need(doc["p95_ms"] <= doc["approved_p95_ms"], "P95_EXCEEDS_APPROVED_BOUND")
        need(doc["error_rate_pct"] <= doc["approved_error_rate_pct"], "ERROR_RATE_EXCEEDS_APPROVED_BOUND")
    elif stage == "trace":
        for key in ("server_issued_trace_correlation", "request_id_present", "sanitized_log_coverage",
                    "alert_trigger_and_resolution_tested", "no_pii_or_secret_in_sampled_logs",
                    "incident_runbook_exercised"):
            exact_bool(doc, key, True)
        nonempty_str(doc, "redacted_trace_receipt_sha256")
        need(SHA256.fullmatch(doc["redacted_trace_receipt_sha256"]) is not None, "TRACE_RECEIPT_DIGEST_INVALID")
    return {"stage": stage, "scope": "STRUCTURE_AND_SELF_REPORTED_INVARIANTS_ONLY",
            "source_sha": expected_sha, "outcome": "PRECHECK_ONLY_NOT_ACCEPTED",
            "real_execution_identity_and_signatures": "NOT_VERIFIED_BY_THIS_SCRIPT"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail-closed Foundation F3 receipt preflight; never Gate acceptance")
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument("--release", help="Phase2 release manifest JSON")
    choices.add_argument("--receipt", help="One sanitized Ops receipt JSON")
    parser.add_argument("--artifact-root", help="Root of real, local Phase2 artifact files")
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--expected-sha")
    parser.add_argument("--expected-tree")
    opts = parser.parse_args(argv)
    try:
        if opts.release:
            need(opts.artifact_root is not None, "ARTIFACT_ROOT_REQUIRED")
            result = verify_release(opts.release, opts.artifact_root)
        else:
            need(bool(opts.stage and opts.expected_sha and opts.expected_tree), "RECEIPT_PIN_AND_STAGE_REQUIRED")
            result = verify_receipt(opts.receipt, expected_sha=opts.expected_sha,
                                    expected_tree=opts.expected_tree, stage=opts.stage)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InvalidEvidence, OSError) as exc:
        # Deliberately no raw JSON/credentials/content in printed errors.
        print(json.dumps({"result": "BLOCKED_NOT_ACCEPTED", "reason": str(exc) if isinstance(exc, InvalidEvidence) else "MISSING_OR_UNREADABLE_INPUT"}, sort_keys=True))
        return 78


if __name__ == "__main__":
    sys.exit(main())
