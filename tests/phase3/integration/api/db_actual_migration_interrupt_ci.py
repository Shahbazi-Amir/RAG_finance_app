"""Disposable CI only: terminate the exact blocked 002 migration backend.

Do not modify the pinned SQL or synthesize ledger intent. No product records,
production host, or existing user-owned databases may be touched.
"""
import os
import re
import subprocess
import time
from pathlib import Path
from hashlib import sha256
import psycopg
from psycopg import sql

DB="history_migration_fault_ci"
ROOT=Path(os.environ["GITHUB_WORKSPACE"])
assert os.environ.get("CI")==os.environ.get("GITHUB_ACTIONS")=="true"
assert os.environ.get("PGHOST")=="127.0.0.1" and os.environ.get("PGPORT")=="5432"
assert re.fullmatch(r"[0-9]+",os.environ["GITHUB_RUN_ID"])
assert Path.cwd()==ROOT and ROOT.as_posix().startswith("/home/runner/work/")
assert not (ROOT/"infra/postgres/migrations/011_product_answer_claims.up.sql").exists()
opts=dict(host="127.0.0.1",port=5432,user="postgres",
          password=os.environ["PGPASSWORD"],connect_timeout=3)
def snapshot(conn):
    names=conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='history_l1' ORDER BY 1").fetchall()
    return {name:sha256(conn.execute(sql.SQL("SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM history_l1.{} t").format(sql.Identifier(name))).fetchone()[0].encode()).hexdigest() for (name,) in names}
def ledger(conn):
    return conn.execute("SELECT version,status,applied_at,applied_txid,to_jsonb(t)::text FROM db55_audit.migration_runs t ORDER BY version").fetchall()
def run_env():
    return dict(os.environ,F3_LEDGER_DB=DB,PGAPPNAME="f3_ci_interrupt_002")
command=["bash","-euo","pipefail","-c",
         "source scripts/phase3/f3_browser_pinned_migration_ledger.sh; export PGUSER=history_migrator PGPASSWORD=synthetic_mig_only; f3_ledger_apply 002 infra/postgres/migrations/002_one_attempt.up.sql"]
with psycopg.connect(**opts,dbname="history_ci",autocommit=True) as source:
    before=ledger(source)
    assert len(before)==1 and before[0][:2]==("001","APPLIED")
    source_rows=snapshot(source)
with psycopg.connect(**opts,dbname="postgres",autocommit=True) as admin:
    assert admin.execute("SHOW server_version").fetchone()[0].startswith("17.11")
    assert not admin.execute("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=%s)",(DB,)).fetchone()[0]
    admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE history_ci OWNER postgres").format(sql.Identifier(DB)))
    child=None
    try:
        with psycopg.connect(**opts,dbname=DB,autocommit=True) as lock, psycopg.connect(**opts,dbname=DB,autocommit=True) as observer:
            baseline=snapshot(observer)
            assert observer.execute("SELECT count(*) FROM history_l1.conversations").fetchone()[0]>0
            assert observer.execute("SELECT to_regclass('history_l1.one_attempt_per_send_receipt') IS NULL").fetchone()[0]
            with lock.transaction():
                lock.execute("LOCK TABLE history_l1.execution_attempts IN ROW EXCLUSIVE MODE")
                blocker=lock.execute("SELECT pg_backend_pid()").fetchone()[0]
                child=subprocess.Popen(command,env=run_env(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                deadline=time.monotonic()+15
                target=None
                while time.monotonic()<deadline:
                    hits=observer.execute("""SELECT pid FROM pg_stat_activity WHERE datname=current_database()
                       AND usename='history_migrator' AND application_name='f3_ci_interrupt_002'
                       AND wait_event_type='Lock' AND query LIKE 'CREATE UNIQUE INDEX one_attempt_per_send_receipt%'
                       AND %s=ANY(pg_blocking_pids(pid))""",(blocker,)).fetchall()
                    assert len(hits)<=1
                    if hits:
                        target=hits[0][0]
                        break
                    assert child.poll() is None,"MIGRATION_EXITED_BEFORE_EXPECTED_LOCK"
                    time.sleep(.05)
                assert target is not None and target!=blocker
                intent=ledger(observer)
                assert len(intent)==2 and intent[1][:4]==("002","STARTED",None,None)
                assert observer.execute("SELECT pg_terminate_backend(%s,5000)",(target,)).fetchone()[0] is True
                out,err=child.communicate(timeout=10)
                assert child.returncode==70 and b"STOP_BROWSER_MIGRATION_002_FAILED_INTENT_RETAINED" in err
                assert not observer.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE pid=%s)",(target,)).fetchone()[0]
            assert ledger(observer)==intent
            assert snapshot(observer)==baseline
            assert observer.execute("SELECT to_regclass('history_l1.one_attempt_per_send_receipt') IS NULL").fetchone()[0]
            retry=subprocess.run(command,env=run_env(),capture_output=True,timeout=15)
            assert retry.returncode==70
            assert b"STOP_BROWSER_MIGRATION_002_FAILED_INTENT_RETAINED" not in retry.stderr
            assert ledger(observer)==intent and snapshot(observer)==baseline
            print("DB_COMMON_REAL_002_BLOCKED_BACKEND_TERMINATED_STARTED_RETAINED_NO_AUTORETRY=PASS",flush=True)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate(timeout=5)
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(DB)))
with psycopg.connect(**opts,dbname="history_ci",autocommit=True) as source:
    assert ledger(source)==before and snapshot(source)==source_rows
    assert source.execute("SELECT to_regclass('history_l1.one_attempt_per_send_receipt') IS NULL").fetchone()[0]
print("DB_COMMON_INTERRUPTED_002_CLONE_CLEANUP_SOURCE_UNCHANGED=PASS",flush=True)
marker=Path(os.environ["RUNNER_TEMP"])/"f3-actual-migration-interrupted-verified.txt"
marker.write_text("PASS\n")
