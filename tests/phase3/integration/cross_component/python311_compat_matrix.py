#!/usr/bin/env python3
"""Exact 3.11.3 Linux matrix against #49's disposable, already-READY demo.

The launcher owns its PostgreSQL container and ephemeral source worktree.
Never point these legacy CI tests at arbitrary host databases or a user's Mac.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("compat_launcher", ROOT / "scripts/phase3-demo/launcher.py")
launcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(launcher)

def fail(message: str) -> None:
    raise RuntimeError("PY3113_COMPAT_MATRIX: " + message)

def call(argv: list[str], *, cwd: Path, env: dict[str, str], stdin: str | None = None) -> str:
    p = subprocess.run(argv, cwd=cwd, env=env, input=stdin,
                       capture_output=True, text=True, timeout=200)
    lines = (p.stdout + "\n" + p.stderr).splitlines()
    if p.returncode:
        # Output from synthetic CI tests only. No credentials, Cookie or secrets.
        for key in ("password", "PGPASSWORD"):
            if key in env and env[key]:
                lines = [line.replace(env[key], "[REDACTED]") for line in lines]
        print("\n".join(lines[-35:]), flush=True)
        fail(f"TEST_EXIT_{p.returncode} command={argv[-1]}")
    summary = [line for line in lines if line.startswith("Ran ") or line.strip() == "OK"]
    return " ".join(summary[-2:]) or "completed"

def postgres_sql(container: str, sql: str, *, user: str = "postgres",
                 password: str | None = None, database: str = "postgres") -> None:
    cmd = ["docker", "exec", "-i"]
    if password is not None:
        cmd += ["-e", "PGPASSWORD=" + password]
    cmd += [container, "psql"]
    if password is not None:
        cmd += ["-h", "127.0.0.1"]
    cmd += ["-U", user, "-d", database, "-v", "ON_ERROR_STOP=1", "-q"]
    p = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=90)
    if p.returncode:
        print(p.stderr[-1500:].replace(password or "\0", "[REDACTED]"), flush=True)
        fail(f"POSTGRES_SETUP_{user}_{database}")

def main() -> None:
    if sys.version_info[:3] != (3, 11, 3):
        fail("EXECUTING_INTERPRETER_NOT_EXACTLY_3_11_3:" + sys.version.split()[0])
    launcher.state_is_safe()
    manifest = launcher.read_json(launcher.MANIFEST)
    if not (launcher.READY.exists() and launcher.docker_owned(manifest)):
        fail("DEMO_NOT_READY_AND_OWNED")
    src_root = launcher.SOURCE
    py = launcher.STATE / "venv" / "bin" / "python"
    installed = subprocess.check_output([str(py), "-c",
        "import sys; assert sys.version_info[:3] == (3,11,3); print(sys.version.split()[0])"],
        text=True).strip()
    if installed != "3.11.3":
        fail("LAUNCHER_VENV_INTERPRETER_MISMATCH")
    env = os.environ.copy()
    env.update(launcher.read_json(launcher.STATE / "private-db-env.json"))
    env["CI"] = "true"
    env["API_CURSOR_KEY"] = "only-ci-compat-history-cursor-signing-verified-32bytes"
    env["API_CURSOR_TTL_SECONDS"] = "300"
    print("COMPAT_PYTHON_HOST=3.11.3 COMPAT_LAUNCHER_VENV=3.11.3")
    for package in ("fastapi", "httpx", "psycopg", "psycopg-binary",
                    "jsonschema", "PyJWT", "cryptography", "uvicorn", "playwright"):
        probe = subprocess.check_output([str(py), "-c",
            "from importlib.metadata import version; import sys; print(version(sys.argv[1]))", package],
            text=True).strip()
        print(f"COMPAT_INSTALLED_{package.replace('-', '_')}={probe}")
    print("COMPAT_DB_POSTGRES_IMAGE=postgres:17.11")
    container = manifest["postgres_id"]

    # The original CI-only DB suites require these two fixture schemas.
    postgres_sql(container, """CREATE SCHEMA auth_fence_ci;
REVOKE ALL ON SCHEMA auth_fence_ci FROM PUBLIC;
CREATE TABLE auth_fence_ci.protected_actions(owner_id text NOT NULL, marker text PRIMARY KEY);
GRANT USAGE ON SCHEMA auth_fence_ci TO auth_sessions;
GRANT INSERT ON auth_fence_ci.protected_actions TO auth_sessions;
CREATE SCHEMA service_replay_ci;
REVOKE ALL ON SCHEMA service_replay_ci FROM PUBLIC;
CREATE TABLE service_replay_ci.protected_actions(marker text PRIMARY KEY);
GRANT USAGE ON SCHEMA service_replay_ci TO auth_trust_api;
GRANT INSERT ON service_replay_ci.protected_actions TO auth_trust_api;
""", database="history_ci")
    print("COMPAT_DB_SYNTHETIC_TEST_SCHEMAS_READY")

    # History HTTP tests demand their OWN exact-named disposable database.
    postgres_sql(container, """CREATE DATABASE history_api_ci;
GRANT CONNECT,CREATE ON DATABASE history_api_ci TO history_migrator;
GRANT CONNECT ON DATABASE history_api_ci TO history_app;""")
    for key, role, migration in (
        ("DB_MIG_DSN", "history_migrator", "001_history_l1"),
        ("DB_MIG_DSN", "history_migrator", "002_one_attempt"),
    ):
        from psycopg.conninfo import conninfo_to_dict
        dsn = conninfo_to_dict(env[key])
        pgsql = (src_root / "infra/postgres/migrations" / (migration + ".up.sql")).read_text()
        postgres_sql(container, pgsql, user=role, password=dsn["password"],
                     database="history_api_ci")
        print("COMPAT_API_DB_MIGRATION=" + migration[:3])
    env["API_HISTORY_DSN"] = env["DB_APP_DSN"].replace("dbname=history_ci", "dbname=history_api_ci")
    env["API_MIG_DSN"] = env["DB_MIG_DSN"].replace("dbname=history_ci", "dbname=history_api_ci")

    tasks = [
        ("API_CONTRACTS", "tests/phase3/contracts", "test_history.py"),
        ("API_SERVICE_PROOF", "tests/phase3/api", "test_*.py"),
        ("DB_SESSION", "tests/phase3/database", "test_auth_session.py"),
        ("DB_NULL_FENCE", "tests/phase3/database", "test_auth_null_fence.py"),
        ("DB_FENCE", "tests/phase3/database", "test_auth_session_fence.py"),
        ("DB_REPLAY", "tests/phase3/database", "test_service_replay.py"),
        ("API_HISTORY_HTTP_PG", "tests/phase3/integration/api", "test_http_postgres.py"),
    ]
    for ident, directory, glob in tasks:
        print("COMPAT_START_" + ident, flush=True)
        result = call([str(py), "-m", "unittest", "discover", "-s", directory,
                       "-p", glob, "-v"], cwd=src_root, env=env)
        print(f"COMPAT_PASS_{ident} {result}", flush=True)
    print("COMPAT_MATRIX_API_CONTRACT_SESSION_HISTORY_DB_PASS", flush=True)

if __name__ == "__main__":
    main()
