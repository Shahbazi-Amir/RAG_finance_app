"""Disposable CI: committed 002 SQL with interrupted APPLIED acknowledgment.
Transfer of the prior offline package's scenario; no production ledger repair.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

DB="history_migration_fault_ci"
SOURCE="history_ci"
CMD=["bash","-euo","pipefail","-c",
     "source scripts/phase3/f3_browser_pinned_migration_ledger.sh; export PGUSER=history_migrator PGPASSWORD=synthetic_mig_only; f3_ledger_apply 002 infra/postgres/migrations/002_one_attempt.up.sql"]

def require(ok, code):
    if not ok:
        raise RuntimeError(code)

def main():
    env=os.environ
    require(env.get("CI")==env.get("GITHUB_ACTIONS")=="true","CI_ONLY")
    require(re.fullmatch(r"[0-9]{1,24}",env.get("GITHUB_RUN_ID","")),"RUN_ID_REQUIRED")
    require(env.get("PGHOST")=="127.0.0.1" and env.get("PGPORT")=="5432","LOOPBACK_ONLY")
    require(re.search(r"(?:^| )dbname=history_ci(?: |$)",env.get("AUTH_MIG_DSN","")),"EXPECTED_INSTALLER_DB")
    root=Path(env["GITHUB_WORKSPACE"])
    require(root.resolve()==Path.cwd() and root.as_posix().startswith("/home/runner/work/"),"EXACT_CI_CHECKOUT_REQUIRED")
    require(env["PGPASSWORD"]=="synthetic_ci_only_not_a_secret","SYNTHETIC_CI_INPUT_REQUIRED")
    sha=env["F3_EXACT_SHA"]
    require(re.fullmatch(r"[a-f0-9]{40}",sha) and subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==sha,"CHECKOUT_SHA_DRIFT")
    require(not (root/"infra/postgres/migrations/011_product_answer_claims.up.sql").exists(),"011_NOT_AUTHORIZED")
    import psycopg
    from psycopg import sql
    opts=dict(host="127.0.0.1",port=5432,user="postgres",password=env["PGPASSWORD"],connect_timeout=3)
    app="f3_ci_002_postcommit_"+env["GITHUB_RUN_ID"]
    key=int(hashlib.sha256(app.encode()).hexdigest()[:15],16)
    worker=dict(env,F3_LEDGER_DB=DB,PGAPPNAME=app)
    marker=Path(env["RUNNER_TEMP"])/"f3-postcommit-migration-interrupt-verified.txt"
    receipt=root/"ci_receipts/db_postcommit_migration.json"
    require(not marker.exists() and not receipt.exists(),"STALE_RECEIPT")
    def connect(db):
        return psycopg.connect(**opts,dbname=db,autocommit=True)
    def snapshot(conn):
        names=conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='history_l1' ORDER BY 1").fetchall()
        require(len(names)==6,"EXPECTED_SIX_HISTORY_TABLES")
        return {name:hashlib.sha256(conn.execute(sql.SQL(
            "SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM history_l1.{} t"
        ).format(sql.Identifier(name))).fetchone()[0].encode()).hexdigest() for (name,) in names}
    def ledger(conn):
        return conn.execute("SELECT version,status,applied_at,applied_txid,to_jsonb(t)::text FROM db55_audit.migration_runs t ORDER BY version").fetchall()
    def check_ledger(rows, expected):
        require(len(rows)==len(expected),"LEDGER_COUNT_DRIFT")
        for row,(version,state) in zip(rows,expected):
            require(row[:2]==(version,state),"LEDGER_STATE_DRIFT")
            require((row[2] is None and row[3] is None) if state=="STARTED" else (row[2] is not None and row[3] is not None),"LEDGER_FIELDS_DRIFT")
    def check_index(conn,present):
        row=conn.execute("""SELECT i.indisunique,i.indisvalid,i.indisready,n.nspname,t.relname,
          ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum,ord)
                JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum ORDER BY k.ord),
          i.indpred IS NOT NULL,i.indexprs IS NOT NULL
          FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace
          WHERE i.indexrelid=to_regclass('history_l1.one_attempt_per_send_receipt')""").fetchone()
        require(row==(True,True,True,"history_l1","execution_attempts",["owner_id","send_receipt_id"],False,False) if present else row is None,"PINNED_INDEX_DRIFT")
    with connect(SOURCE) as source:
        require(source.execute("SELECT current_database(),current_user").fetchone()==(SOURCE,"postgres"),"WRONG_INSTALLER_DB")
        require(source.execute("SHOW server_version").fetchone()[0].startswith("17.11"),"PG_VERSION_DRIFT")
        before_ledger,before_rows=ledger(source),snapshot(source)
        check_ledger(before_ledger,[("001","APPLIED")])
        check_index(source,False)
        require(source.execute("SELECT count(*) FROM history_l1.conversations").fetchone()[0]>0,"DATA_BEARING_SOURCE_REQUIRED")
    def check_source():
        with connect(SOURCE) as source:
            require(ledger(source)==before_ledger and snapshot(source)==before_rows,"SOURCE_DRIFT")
            check_index(source,False)
    with connect("postgres") as admin:
        def create():
            require(not admin.execute("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=%s)",(DB,)).fetchone()[0],"EXISTING_CLONE_DENIED")
            admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE history_ci OWNER postgres").format(sql.Identifier(DB)))
            return admin.execute("SELECT oid FROM pg_database WHERE datname=%s",(DB,)).fetchone()[0]
        def drop(oid):
            require(admin.execute("SELECT oid FROM pg_database WHERE datname=%s",(DB,)).fetchone()==(oid,),"CLONE_ID_DRIFT_REFUSE_DROP")
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(DB)))
        first=create()
        child=None
        try:
            with connect(DB) as lock,connect(DB) as observer:
                require(snapshot(observer)==before_rows and ledger(observer)==before_ledger,"CLONE_BASELINE_DRIFT")
                check_index(observer,False)
                observer.execute(sql.SQL("""CREATE FUNCTION db55_audit.f3_ci_hold_applied() RETURNS trigger LANGUAGE plpgsql AS $body$
                   BEGIN PERFORM pg_advisory_xact_lock({}); RETURN NEW; END; $body$""").format(sql.Literal(key)))
                observer.execute("""CREATE TRIGGER f3_ci_hold_applied BEFORE UPDATE OF status ON db55_audit.migration_runs
                  FOR EACH ROW WHEN (NEW.version='002' AND NEW.status='APPLIED') EXECUTE FUNCTION db55_audit.f3_ci_hold_applied()""")
                lock.execute("SELECT pg_advisory_lock(%s)",(key,))
                blocker=lock.execute("SELECT pg_backend_pid()").fetchone()[0]
                child=subprocess.Popen(CMD,env=worker,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                deadline=time.monotonic()+25
                target=None
                while time.monotonic()<deadline:
                    hits=observer.execute("""SELECT pid FROM pg_stat_activity WHERE datname=current_database()
                       AND usename='postgres' AND application_name=%s AND wait_event_type='Lock'
                       AND query LIKE %s AND %s=ANY(pg_blocking_pids(pid))""",
                       (app,"UPDATE db55_audit.migration_runs SET status='APPLIED'%",blocker)).fetchall()
                    require(len(hits)<=1,"AMBIGUOUS_LEDGER_UPDATER")
                    if hits:
                        target=hits[0][0]
                        break
                    require(child.poll() is None,"INSTALLER_EXITED_BEFORE_LEDGER_LOCK")
                    time.sleep(.05)
                require(isinstance(target,int) and target>0 and target!=blocker,"APPLIED_UPDATE_LOCK_NOT_OBSERVED")
                intent=ledger(observer)
                check_ledger(intent,[("001","APPLIED"),("002","STARTED")])
                require(intent[0]==before_ledger[0],"PRIOR_INTENT_DRIFT")
                check_index(observer,True)
                require(snapshot(observer)==before_rows,"POSTCOMMIT_ROW_DRIFT")
                require(observer.execute("SELECT pg_terminate_backend(%s,5000)",(target,)).fetchone()[0] is True,"TERMINATE_FAILED")
                out,err=child.communicate(timeout=15)
                require(child.returncode!=0 and b"F3_BROWSER_ACTUAL_MIGRATION_002_PINNED_APPLIED=PASS" not in out+err,"FAILED_ACK_EXPECTED")
                require(not observer.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE pid=%s)",(target,)).fetchone()[0],"BACKEND_STILL_PRESENT")
                lock.execute("SELECT pg_advisory_unlock(%s)",(key,))
                require(ledger(observer)==intent and snapshot(observer)==before_rows,"STARTED_INTENT_OR_ROW_DRIFT")
                check_index(observer,True)
                retry=subprocess.run(CMD,env=worker,cwd=root,capture_output=True,timeout=20)
                require(retry.returncode==70 and b"STOP_BROWSER_MIGRATION_002_FAILED_INTENT_RETAINED" not in retry.stderr,"PARTIAL_LEDGER_RETRY_NOT_REFUSED")
                require(ledger(observer)==intent and snapshot(observer)==before_rows,"RETRY_CHANGED_DATA_OR_LEDGER")
                check_index(observer,True)
                print("DB_COMMON_002_COMMITTED_INDEX_STARTED_LEDGER_TERMINATED_NO_AUTORETRY=PASS",flush=True)
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
            drop(first)
        check_source()
        second=create()
        try:
            require(second!=first,"NEW_DATABASE_ID_REQUIRED")
            result=subprocess.run(CMD,env=worker,cwd=root,capture_output=True,timeout=30)
            require(result.returncode==0 and b"F3_BROWSER_ACTUAL_MIGRATION_002_PINNED_APPLIED=PASS" in result.stdout,"NEW_CLONE_MIGRATION_FAILED")
            with connect(DB) as recovered:
                final=ledger(recovered)
                check_ledger(final,[("001","APPLIED"),("002","APPLIED")])
                require(final[0]==before_ledger[0] and snapshot(recovered)==before_rows,"FRESH_CLONE_PARITY_DRIFT")
                check_index(recovered,True)
        finally:
            drop(second)
    check_source()
    print("DB_COMMON_002_AMBIGUOUS_CLONE_DISCARDED_FRESH_CLONE_REINSTALL_SOURCE_UNCHANGED=PASS",flush=True)
    receipt.parent.mkdir(exist_ok=True)
    with receipt.open("x",encoding="utf-8") as f:
        json.dump({"source_sha":sha,"run_id":env["GITHUB_RUN_ID"],"scope":"CI_ONLY_POSTCOMMIT_LEDGER_AMBIGUITY",
                   "migration":"002","actual_committed_index_observed":True,"actual_applied_updater_terminated":True,
                   "started_retained":True,"auto_retry_refused":True,"history_rows_exact":True,"ambiguous_clone_discarded":True,
                   "fresh_clone_distinct_database_oid":True,"fresh_clone_002_applied":True,"source_unchanged":True,
                   "target_verified":False,"accepted":False,"sql_011":False,"engine_calls":0},f,indent=2)
        f.write("\n")
    with marker.open("x",encoding="ascii") as f:
        f.write("PASS\n")

if __name__=="__main__":
    main()
