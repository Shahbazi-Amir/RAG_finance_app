#!/usr/bin/env python3
"""Real Product/Bootstrap *DB authority preflight* using PINNED application code.
Two separate ephemeral processes, two separate role-only passfiles, one private Docker network.
Never imports a CI stub, calls ASGI HTTP, executes user SQL, starts C018, or uses a Gateway.
No passwords, DSNs or private file names are logged. NOT full HTTP product admission.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/appsrc")

import psycopg
from src.phase3.auth.staging_service_profile import (
    PrivateStagingProfile, RUNNER_C018_SHA256, StagingConfigDenied,
)
from apps.api.private_staging_asgi import verify_staging_database_authority
from apps.api.private_staging_bootstrap_asgi import (
    ROLES as BOOT_ROLES, verify_bootstrap_roles,
)

API_ROLES = ("history_app", "auth_revoker")
BOOT_EXPECTED = (
    "auth_trust_api", "auth_login_bootstrap", "auth_login_claim_reader",
    "auth_login_issuer", "auth_mapper", "auth_login_binder", "auth_login_reader",
)

def assert_equal(actual, expected, code):
    if actual != expected:
        raise RuntimeError(code)

def dsn(role, host, db):
    if not role.replace("_", "").isalnum():
        raise RuntimeError("INVALID_ROLE")
    return (
        f"host={host} port=5432 dbname={db} user={role} "
        "connect_timeout=5 sslmode=verify-full "
        "sslrootcert=/run/role_secrets/ca.crt "
        "passfile=/run/role_secrets/pgpass"
    )

def check_tls_role(role, connection_string, db):
    # Independent read-only network query on precisely the DSN used by the original API verifier.
    with psycopg.connect(connection_string, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_user, current_database(), current_setting('server_version'),"
                " s.ssl, s.version, s.cipher"
                " FROM pg_stat_ssl AS s WHERE s.pid=pg_backend_pid()"
            )
            row = cur.fetchone()
        if not row or row[0] != role or row[1] != db or not row[2].startswith("17.11"):
            raise RuntimeError("ROLE_OR_DATABASE_OR_VERSION_MISMATCH")
        if row[3] is not True or row[4] not in ("TLSv1.2", "TLSv1.3") or not row[5]:
            raise RuntimeError("TLS_NOT_ACTUALLY_NEGOTIATED")
    return {"role": role, "ssl": "verify-full", "tls_version": row[4],
            "postgres": row[2], "user_verified": True}

def app_profile(history, revoke):
    return PrivateStagingProfile(
        issuer="urn:f3-db-disposable-witness",
        audience="urn:f3-db-disposable-api",
        kid="labwitness",
        public_key_path=Path("/appsrc/.lab-unused-publickey.pem"),
        history_dsn=history,
        revoke_dsn=revoke,
        peer_verifier=lambda _scope: False,
        runner_sha256=RUNNER_C018_SHA256,
    )

def expect_negative(fn, label):
    try:
        fn()
    except (StagingConfigDenied, psycopg.Error):
        return
    raise RuntimeError("UNSAFE_ACCEPTED_" + label)

def run():
    mode = sys.argv[1] if len(sys.argv) == 2 else None
    if mode not in ("product", "bootstrap"):
        raise RuntimeError("BAD_MODE")
    host = os.environ.get("PG_EXPECTED_HOST")
    db = os.environ.get("PG_EXPECTED_DB")
    if (host, db) not in (("demo-db", "rag_finance_f3_lab"),
                          ("restore-db", "rag_finance_f3_lab_restore")):
        raise RuntimeError("UNPINNED_LAB_ENDPOINT")
    if not Path("/run/role_secrets/ca.crt").is_file():
        raise RuntimeError("CA_NOT_MOUNTED")
    expected = API_ROLES if mode == "product" else BOOT_EXPECTED
    dsns = {r: dsn(r, host, db) for r in expected}
    receipts = [check_tls_role(r, dsns[r], db) for r in expected]
    if mode == "product":
        verify_staging_database_authority(
            app_profile(dsns["history_app"], dsns["auth_revoker"]))
        expect_negative(
            lambda: verify_staging_database_authority(
                app_profile(dsns["auth_revoker"], dsns["history_app"])),
            "PRODUCT_SWAPPED_ROLE")
        expect_negative(
            lambda: verify_staging_database_authority(
                app_profile(dsns["history_app"].replace("verify-full", "require"),
                            dsns["auth_revoker"])),
            "PRODUCT_WEAK_TLS_DSN")
        marker = "PRODUCT_API_REAL_DB_PREFLIGHT"
    else:
        assert_equal(set(BOOT_ROLES.values()), set(BOOT_EXPECTED),
                     "BOOTSTRAP_SOURCE_ROLE_DRIFT")
        verify_bootstrap_roles(
            {operation: dsns[role] for operation, role in BOOT_ROLES.items()})
        swapped = dict(dsns)
        swapped["auth_login_bootstrap"] = dsns["auth_login_issuer"]
        expect_negative(
            lambda: verify_bootstrap_roles(
                {op: swapped[role] for op, role in BOOT_ROLES.items()}),
            "BOOTSTRAP_SWAPPED_ROLE")
        weak = dict(dsns)
        weak["auth_mapper"] = weak["auth_mapper"].replace("verify-full", "require")
        expect_negative(
            lambda: verify_bootstrap_roles(
                {op: weak[role] for op, role in BOOT_ROLES.items()}),
            "BOOTSTRAP_WEAK_TLS_DSN")
        marker = "BOOTSTRAP_API_REAL_DB_PREFLIGHT"
    print(json.dumps({
        "contract": "f3.db.shared_stack.db_authority.v1",
        "mode": mode,
        "status": "PASS",
        "db": db, "host": host,
        "application_module": "actual pinned apps.api.private_staging_*.py",
        "role_count": len(expected),
        "roles": receipts,
        "negative_wrong_role": "DENIED",
        "negative_non_verify_full": "DENIED",
        "asgi_http_listener_started": False,
        "runner_calls": 0, "gateway_calls": 0,
    }, ensure_ascii=False, sort_keys=True))
    print(f"{marker}={len(expected)}/{len(expected)}_PASS")

if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        # Fail closed without potentially leaking a psycopg DSN or password.
        print("SHARED_STACK_REAL_CODE_DB_PREFLIGHT=FAIL", file=sys.stderr)
        sys.exit(70)
