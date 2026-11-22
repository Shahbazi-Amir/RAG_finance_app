#!/usr/bin/env python3
"""SOURCE/static-only validations: no PostgreSQL execution in this test."""
from __future__ import annotations
import csv
import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = ROOT / "MIGRATIONS_001_010_PINNED.tsv"
EXPECTED = "9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7"
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == EXPECTED
rows = list(csv.DictReader(manifest.open(newline=""), delimiter="\t"))
assert len(rows) == 20
assert [row["migration_id"] for row in rows] == [f"{i:03}" for i in range(1,11) for _ in range(2)]
assert [row["direction"] for row in rows] == [d for _ in range(10) for d in ("UP", "DOWN")]
assert len({row["path"] for row in rows}) == 20
for r in rows:
    assert re.fullmatch(r"[0-9a-f]{40}", r["source_commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", r["git_blob_sha1"])
    assert r["path"].startswith("infra/postgres/migrations/")
    assert r["path"].endswith(".up.sql" if r["direction"] == "UP" else ".down.sql")
    assert "011_" not in r["path"]
    num = int(r["migration_id"])
    assert r["source_commit"] == (
        "d93dcf7cbf9290acd4cd3aa0164ef05689049da4" if num <= 8 else
        "656604356dadea953031fcdb74650a5d42df4e9b" if num == 9 else
        "1678e87b7984094b74ec995383b8d4383e5f5ae7")
assert next(r["git_blob_sha1"] for r in rows if r["migration_id"] == "007" and r["direction"] == "DOWN") == "440764eb11fb201a5d63b7742415cfe924d54a9e"

scripts = sorted((ROOT/"scripts").glob("*.sh"))
assert len(scripts) >= 9, len(scripts)
for script in scripts:
    subprocess.run(["bash", "-n", str(script)], check=True)
compose = (ROOT / "compose.lab.yaml").read_text()
assert "linux/amd64" in compose
assert "73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a" in compose
assert "internal: true" in compose
assert "ports:" not in compose
assert "rag_finance_f3_demo_pg17_20261121" not in compose
assert "rag_finance_f3_demo" not in compose
assert "profiles: [\"restore\"]" in compose
assert "- lab_pgdata:/var/lib/postgresql/data" in compose
try:
    import yaml
    doc = yaml.safe_load(compose)
    assert set(doc["services"]) == {"lab-db", "restore-db"}
    assert not any("ports" in s for s in doc["services"].values())
    assert doc["networks"]["private"]["internal"] is True
except ImportError:
    pass

source = (ROOT / "scripts/03_apply_pinned_001_010.sh").read_text()
assert "STARTED" in source and "APPLIED" in source and "STOP_PARTIAL_LEDGER_MANUAL_RECONCILIATION" in source
assert "STOP_MISSING_OR_011_SQL" in source
source = (ROOT / "scripts/07_cleanup_lab_ONLY.sh").read_text()
assert "ALLOW_DELETE_F3_LAB" in source and "STOP_VOLUME_NOT_OWNED_BY_PROJECT" in source
roles = (ROOT / "scripts/05_test_roles_tls_rls.sh").read_text()
assert "sslmode=verify-full" in roles and "sslmode=disable" in roles
assert "72|72" in roles and "9|9" in roles
print("STATIC_CHECKS_PASS: 20 Git pins, source isolation, Bash syntax, Compose, role matrices, no-011, no-demo-touch")
print("REAL_POSTGRES_TESTS=NOT_RUN_IN_THIS_RUNTIME")
