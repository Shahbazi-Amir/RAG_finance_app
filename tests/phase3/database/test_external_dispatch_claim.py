"""011 durable one-shot external Dispatch Claim: disposable PG17 only.

NEVER imports Runner/Gateway, sends HTTP, uses paid credentials, or writes staging.
One winning DB Claim is a right to attempt dispatch AFTER COMMIT, not proof of
a delivered external operation. UNKNOWN remains non-reclaimable forever.
"""
import hashlib
import os
import secrets
import subprocess
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from src.phase3.storage.postgres import repository as history

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "infra/postgres/migrations/011_external_dispatch_claim.up.sql"
DOWN = ROOT / "infra/postgres/migrations/011_external_dispatch_claim.down.sql"
DATABASES = {"history_ci", "history_dispatch_empty_ci", "history_dispatch_evidence_ci"}
ROLES = {
    "APP": ("DB_APP_DSN", "history_app"),
    "MIG": ("DB_MIG_DSN", "history_migrator"),
    "REPORT": ("DISPATCH_REPORTER_DSN", "history_dispatch_reporter"),
    "RECON": ("DISPATCH_RECON_DSN", "history_dispatch_reconciler"),
}


def connect(role="APP", db="history_ci"):
    if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("DISPATCH011_GITHUB_ACTIONS_DISPOSABLE_ONLY")
    if db not in DATABASES:
        raise RuntimeError("DISPATCH011_UNSAFE_DB")
    key, username = ROLES[role]
    dsn = os.environ[key]
    spec = conninfo_to_dict(dsn)
    if (spec.get("host"), spec.get("port"), spec.get("dbname"), spec.get("user")) != (
            "127.0.0.1", "5432", "history_ci", username):
        raise RuntimeError("DISPATCH011_UNSAFE_CONN")
    if set(spec) - {"host", "port", "dbname", "user", "password", "connect_timeout"}:
        raise RuntimeError("DISPATCH011_EXTRA_DSN_OPTIONS")
    return psycopg.connect(make_conninfo(dsn, dbname=db), autocommit=True,
                           row_factory=dict_row)


def hash256(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def send_request():
    return {
        "kind": "send_message_request", "contract_version": "product.v1",
        "requested_conversation_id": None,
        "client_message_id": history.uid(),
        "idempotency_key": "synthetic_"+history.uid(),
        "question": "Synthetic dispatch permission test "+history.uid(),
    }


def make_attempt(db="history_ci", *, claim_in_tx=False, req=None):
    owner="synthetic_dispatch_owner_"+history.uid()
    req=req or send_request()
    with connect("APP",db) as c:
        with c.transaction():
            history.scoped(c, owner)
            receipt=history.send_t1(c,owner,req,history.uid(),history.uid())
            att=history.start_t2(
                c,owner,req["requested_conversation_id"],req["client_message_id"],
                req["idempotency_key"],history.uid(),history.uid())
            value=claim(c,owner,att) if claim_in_tx else None
    return owner,receipt,att,value


def claim(c,owner,attempt,*,trace=None,attempt_id=None):
    return c.execute("""SELECT claim_won,claim_id,claimed_at
      FROM history_l1.claim_external_dispatch(%s,%s,%s)""",
      (owner,attempt_id if attempt_id is not None else attempt["id"],
       trace if trace is not None else attempt["attempt_trace_id"])).fetchone()


def status(c,owner,attempt,*,trace=None,attempt_id=None):
    return c.execute("""SELECT dispatch_state,claimed_at,unknown_at,reconciled_at
        FROM history_l1.status_external_dispatch(%s,%s,%s)""",
        (owner,attempt_id if attempt_id is not None else attempt["id"],
         trace if trace is not None else attempt["attempt_trace_id"])).fetchone()


def with_owner(c,owner):
    history.scoped(c,owner)


def mark_unknown(c,owner,attempt,claim_id,reason):
    return c.execute("""SELECT history_l1.flag_external_dispatch_unknown(
       %s,%s,%s,%s,%s) AS ok""",
       (owner,attempt["id"],attempt["attempt_trace_id"],claim_id,reason)
    ).fetchone()["ok"]


def reconcile(c,owner,attempt,outcome,evidence):
    return c.execute("""SELECT history_l1.reconcile_external_dispatch(
      %s,%s,%s,%s,%s) AS ok""",
      (owner,attempt["id"],attempt["attempt_trace_id"],outcome,evidence)
    ).fetchone()["ok"]


def observe_lock(waiter_name,holder_pid):
    with connect("MIG") as observer:
        end=time.monotonic()+10
        while time.monotonic()<end:
            row=observer.execute("""SELECT pid,wait_event_type,wait_event,
                     pg_blocking_pids(pid) AS blockers
                FROM pg_stat_activity
                WHERE datname='history_ci'
                  AND application_name=%s AND wait_event_type='Lock'""",
                (waiter_name,)).fetchone()
            if row and holder_pid in row["blockers"]:
                print("DISPATCH011_REAL_PG_BLOCKER "
                      f"holder={holder_pid} waiter={row['pid']} "
                      f"pg_blocking_pids={row['blockers']} "
                      f"wait_event={row['wait_event']}",flush=True)
                return row
            observer.execute("SELECT pg_sleep(0.02)")
    raise AssertionError("DISPATCH011_TRUE_PG_BLOCKER_NOT_OBSERVED")


def apply_migration(database,path):
    if database not in ("history_dispatch_empty_ci","history_dispatch_evidence_ci"):
        raise RuntimeError("DISPATCH011_DESTRUCTIVE_TARGET_DENIED")
    if path not in (UP,DOWN):
        raise RuntimeError("DISPATCH011_NON_REPOSITORY_MIGRATION_DENIED")
    creds=conninfo_to_dict(os.environ["DB_MIG_DSN"])
    env=dict(os.environ)
    env.update(PGHOST="127.0.0.1",PGPORT="5432",
               PGDATABASE=database,PGUSER="history_migrator",
               PGPASSWORD=creds["password"])
    return subprocess.run(
        ["psql","-X","-v","ON_ERROR_STOP=1","-d",database,"-f",str(path)],
        capture_output=True,text=True,timeout=20,env=env)


class DispatchClaim011(unittest.TestCase):
    def test_DC01_t1_t2_claim_one_outer_commit(self):
        owner,receipt,attempt,first=make_attempt(claim_in_tx=True)
        self.assertEqual(receipt["disposition"],"created")
        self.assertTrue(first["claim_won"])
        self.assertIsInstance(first["claim_id"],uuid.UUID)
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,owner)
                self.assertEqual(status(c,owner,attempt)["dispatch_state"],"CLAIMED")
                second=claim(c,owner,attempt)
                self.assertFalse(second["claim_won"])
                self.assertIsNone(second["claim_id"])
        with connect("MIG") as c:
            row=c.execute("""SELECT count(*) AS n FROM history_l1.external_dispatch_claims
                   WHERE owner_id=%s AND attempt_id=%s""",
                   (owner,attempt["id"])).fetchone()
            self.assertEqual(row["n"],1)
        print("DC01_T1_T2_CLAIM_SAME_ATOMIC_OUTER_COMMIT_ONE_RIGHT",flush=True)

    def test_DC02_two_workers_actual_row_wait_one_claim_winner(self):
        owner,receipt,attempt,_=make_attempt()
        held,release=threading.Event(),threading.Event()
        label="dispatch011_waiter_"+uuid.uuid4().hex[:8]
        pid={}
        def winner():
            with connect("APP") as c:
                with c.transaction():
                    with_owner(c,owner)
                    result=claim(c,owner,attempt)
                    self.assertTrue(result["claim_won"])
                    pid["holder"]=c.info.backend_pid
                    held.set()
                    self.assertTrue(release.wait(12))
                return result
        def loser():
            with connect("APP") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(label,))
                with c.transaction():
                    with_owner(c,owner)
                    return claim(c,owner,attempt)
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1=pool.submit(winner)
            self.assertTrue(held.wait(10))
            f2=pool.submit(loser)
            try:
                witness=observe_lock(label,pid["holder"])
                self.assertIn(pid["holder"],witness["blockers"])
                self.assertFalse(f2.done())
            finally:
                release.set()
            first=f1.result(timeout=12)
            second=f2.result(timeout=12)
        self.assertTrue(first["claim_won"])
        self.assertFalse(second["claim_won"])
        self.assertIsNone(second["claim_id"])
        print("DC02_TWO_PHYSICAL_WORKERS_ONE_WINNER_ONE_GATEWAY_RIGHT",flush=True)

    def test_DC03_process_restart_new_connection_and_http_replay_no_reclaim(self):
        owner,receipt,att,first=make_attempt(claim_in_tx=True)
        for _ in range(4):
            with connect("APP") as brand_new_worker:
                with brand_new_worker.transaction():
                    with_owner(brand_new_worker,owner)
                    replay=claim(brand_new_worker,owner,att)
                    self.assertFalse(replay["claim_won"])
                    self.assertIsNone(replay["claim_id"])
                    self.assertEqual(status(brand_new_worker,owner,att)["dispatch_state"],"CLAIMED")
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,owner)
                duplicate=history.send_t1(
                    c,owner,send_request_for_receipt(receipt,att),history.uid(),history.uid())
                self.assertEqual(duplicate["disposition"],"replayed")
        print("DC03_RESTART_REPLAY_NEVER_SECOND_DISPATCH_AUTHORIZATION",flush=True)

    def test_DC04_attempt_owner_trace_scope_and_cross_owner_denied(self):
        a,receipt,att,_=make_attempt()
        b,receipt_b,att_b,_=make_attempt()
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,b)
                self.assertFalse(claim(c,b,att_b,attempt_id=att["id"])["claim_won"])
                self.assertIsNone(status(c,b,att_b,attempt_id=att["id"]))
                self.assertFalse(claim(c,b,att,trace=att["attempt_trace_id"])["claim_won"])
                self.assertFalse(claim(c,a,att)["claim_won"])  # GUC remains B
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,a)
                self.assertFalse(claim(c,a,att,trace="foreign_"+history.uid())["claim_won"])
                self.assertIsNone(status(c,a,att,trace="foreign_"+history.uid()))
                self.assertTrue(claim(c,a,att)["claim_won"])
        print("DC04_OWNER_AND_IMMUTABLE_ATTEMPT_TRACE_SCOPE_ENFORCED",flush=True)

    def test_DC05_timeout_unknown_and_manual_reconciliation_never_requeues(self):
        owner,_,att,first=make_attempt(claim_in_tx=True)
        with connect("REPORT") as reporter:
            self.assertFalse(mark_unknown(reporter,owner,att,uuid.uuid4(),"TIMEOUT"))
            self.assertTrue(mark_unknown(reporter,owner,att,first["claim_id"],"TIMEOUT"))
            self.assertTrue(mark_unknown(reporter,owner,att,first["claim_id"],"TIMEOUT"))
            self.assertFalse(mark_unknown(reporter,owner,att,first["claim_id"],"LOST_RESPONSE"))
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,owner)
                self.assertEqual(status(c,owner,att)["dispatch_state"],"UNKNOWN")
                self.assertFalse(claim(c,owner,att)["claim_won"])
        evidence=hash256("synthetic-independent-ops-evidence-"+history.uid())
        with connect("RECON") as reconciliation:
            self.assertTrue(reconcile(reconciliation,owner,att,
                     "RECONCILED_NOT_DELIVERED",evidence))
            self.assertTrue(reconcile(reconciliation,owner,att,
                     "RECONCILED_NOT_DELIVERED",evidence))
            self.assertFalse(reconcile(reconciliation,owner,att,
                     "RECONCILED_DELIVERED",evidence))
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,owner)
                self.assertEqual(status(c,owner,att)["dispatch_state"],
                                 "RECONCILED_NOT_DELIVERED")
                self.assertFalse(claim(c,owner,att)["claim_won"])
        print("DC05_UNKNOWN_RECOVERY_MANUAL_EVIDENCE_NO_REDISPATCH",flush=True)

    def test_DC06_crash_after_committed_claim_stale_status_unknown_no_reclaim(self):
        owner,_,att,first=make_attempt(claim_in_tx=True)
        # CI-only migrator simulates 181 seconds passing, without sleeping.
        with connect("MIG") as c:
            c.execute("""UPDATE history_l1.external_dispatch_claims
                SET claimed_at=clock_timestamp()-interval '181 seconds'
                WHERE owner_id=%s AND attempt_id=%s""",(owner,att["id"]))
        with connect("APP") as new_worker:
            with new_worker.transaction():
                with_owner(new_worker,owner)
                self.assertEqual(status(new_worker,owner,att)["dispatch_state"],"UNKNOWN")
                self.assertFalse(claim(new_worker,owner,att)["claim_won"])
        with connect("MIG") as c:
            raw=c.execute("""SELECT state FROM history_l1.external_dispatch_claims
                 WHERE owner_id=%s AND attempt_id=%s""",(owner,att["id"])).fetchone()
            self.assertEqual(raw["state"],"CLAIMED")
        # UNKNOWN is a read-only stale observation, never a Claim lease.
        print("DC06_CRASH_STALE_CLAIM_OBSERVED_UNKNOWN_NO_LEASE_REQUEUE",flush=True)

    def test_DC07_rollback_before_commit_never_authorizes_external_dispatch(self):
        owner="synthetic_dispatch_rollback_"+history.uid()
        req=send_request()
        attempt=None
        with connect("APP") as c:
            with self.assertRaisesRegex(RuntimeError,"SIMULATED_BEFORE_COMMIT"):
                with c.transaction():
                    with_owner(c,owner)
                    receipt=history.send_t1(c,owner,req,history.uid(),history.uid())
                    attempt=history.start_t2(c,owner,None,req["client_message_id"],
                                             req["idempotency_key"],history.uid(),history.uid())
                    self.assertTrue(claim(c,owner,attempt)["claim_won"])
                    raise RuntimeError("SIMULATED_BEFORE_COMMIT")
        with connect("MIG") as c:
            self.assertEqual(c.execute("""SELECT count(*) AS n
              FROM history_l1.external_dispatch_claims WHERE owner_id=%s""",
              (owner,)).fetchone()["n"],0)
            self.assertEqual(c.execute("""SELECT count(*) AS n
              FROM history_l1.execution_attempts WHERE owner_id=%s AND id=%s""",
              (owner,attempt["id"])).fetchone()["n"],0)
            self.assertEqual(c.execute("""SELECT count(*) AS n
              FROM history_l1.send_receipts WHERE owner_id=%s""",
              (owner,)).fetchone()["n"],0)
        print("DC07_UNKNOWN_COMMIT_NEVER_ASSUMED_SUCCESS_ROLLBACK_ALL",flush=True)

    def test_DC08_attempt_terminal_before_claim_denied(self):
        owner,receipt,att,_=make_attempt()
        with connect("APP") as c:
            with_owner(c,owner)
            history.mark_attempt(c,owner,att["id"],"attempt_unknown")
            with c.transaction():
                with_owner(c,owner)
                self.assertFalse(claim(c,owner,att)["claim_won"])
                self.assertEqual(status(c,owner,att)["dispatch_state"],"NOT_CLAIMED")
        print("DC08_TERMINAL_ATTEMPT_UNAUTHORIZED_FOR_GATEWAY",flush=True)

    def test_DC09_role_matrix_positive_negative_function_only(self):
        signatures={
          "claim":"history_l1.claim_external_dispatch(text,text,text)",
          "status":"history_l1.status_external_dispatch(text,text,text)",
          "unknown":"history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text)",
          "reconcile":"history_l1.reconcile_external_dispatch(text,text,text,text,text)",
        }
        with connect("MIG") as c:
            for role in ("history_app","history_dispatch_reporter","history_dispatch_reconciler"):
                p=c.execute("""SELECT rolsuper,rolbypassrls,rolinherit,rolcreatedb,
                    rolcreaterole FROM pg_roles WHERE rolname=%s""",(role,)).fetchone()
                self.assertIsNotNone(p)
                self.assertFalse(any(p.values()))
            for role,expected in (
                ("history_app",{"claim","status"}),
                ("history_dispatch_reporter",{"unknown"}),
                ("history_dispatch_reconciler",{"reconcile"})
            ):
                for method,sig in signatures.items():
                    yes=c.execute("""SELECT has_function_privilege(%s,%s,'EXECUTE') AS can""",
                                  (role,sig)).fetchone()["can"]
                    self.assertEqual(yes,method in expected,(role,method))
                direct=c.execute("""SELECT has_table_privilege(
                   %s,'history_l1.external_dispatch_claims','SELECT') AS readable""",
                   (role,)).fetchone()["readable"]
                self.assertFalse(direct)
            for sig in signatures.values():
                count=c.execute("""SELECT count(*) AS n FROM pg_proc p,
                  LATERAL aclexplode(p.proacl) x
                  WHERE p.oid=%s::regprocedure AND x.grantee=0
                    AND x.privilege_type='EXECUTE'""",(sig,)).fetchone()["n"]
                self.assertEqual(count,0)
            flags=c.execute("""SELECT relrowsecurity,relforcerowsecurity
                 FROM pg_class WHERE oid='history_l1.external_dispatch_claims'::regclass"""
                 ).fetchone()
            self.assertTrue(flags["relrowsecurity"] and flags["relforcerowsecurity"])
        with connect("REPORT") as c:
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT * FROM history_l1.external_dispatch_claims")
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT * FROM history_l1.execution_attempts")
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT history_l1.claim_external_dispatch('a','b','c')")
        with connect("APP") as c:
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT * FROM history_l1.external_dispatch_claims")
            with self.assertRaises(psycopg.Error):
                c.execute("""SELECT history_l1.flag_external_dispatch_unknown(
                  'a','b','c',gen_random_uuid(),'TIMEOUT')""")
        print("DC09_EXACT_EXECUTE_GRANTS_NO_DIRECT_TABLE_OR_PUBLIC",flush=True)

    def test_DC10_read_is_immutable_never_triggers_claim(self):
        owner,_,att,_=make_attempt()
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,owner)
                for _ in range(4):
                    self.assertEqual(status(c,owner,att)["dispatch_state"],"NOT_CLAIMED")
                winner=claim(c,owner,att)
                self.assertTrue(winner["claim_won"])
                for _ in range(4):
                    self.assertEqual(status(c,owner,att)["dispatch_state"],"CLAIMED")
                    self.assertFalse(claim(c,owner,att)["claim_won"])
        print("DC10_STATUS_POLL_NO_DISPATCH_SIDE_EFFECT",flush=True)

    def test_DC11_two_distinct_attempts_one_claim_each(self):
        owner_a,_,a,_=make_attempt()
        owner_b,_,b,_=make_attempt()
        with connect("APP") as c:
            with c.transaction():
                with_owner(c,owner_a)
                self.assertTrue(claim(c,owner_a,a)["claim_won"])
            with c.transaction():
                with_owner(c,owner_b)
                self.assertTrue(claim(c,owner_b,b)["claim_won"])
        with connect("MIG") as c:
            self.assertEqual(c.execute("""SELECT count(*) AS n
              FROM history_l1.external_dispatch_claims WHERE
                (owner_id=%s AND attempt_id=%s)
                OR (owner_id=%s AND attempt_id=%s)""",
                (owner_a,a["id"],owner_b,b["id"])).fetchone()["n"],2)
        print("DC11_DISPATCH_RIGHT_PER_ATTEMPT_NOT_PER_WORKER",flush=True)

    def test_DC12_guarded_actual_down_up_down_up_and_evidence_refusal(self):
        for path in (DOWN,UP,DOWN,UP):
            result=apply_migration("history_dispatch_empty_ci",path)
            self.assertEqual(result.returncode,0,result.stderr[-1800:])
        owner,_,att,first=make_attempt(
            db="history_dispatch_evidence_ci",claim_in_tx=True)
        prior=None
        with connect("MIG","history_dispatch_evidence_ci") as c:
            prior=c.execute("""SELECT claim_id,state,attempt_trace_id FROM
              history_l1.external_dispatch_claims
              WHERE owner_id=%s AND attempt_id=%s""",
              (owner,att["id"])).fetchone()
        denied=apply_migration("history_dispatch_evidence_ci",DOWN)
        self.assertNotEqual(denied.returncode,0)
        self.assertIn("DISPATCH_011_DOWN_REFUSED_EVIDENCE_EXISTS",denied.stderr)
        with connect("MIG","history_dispatch_evidence_ci") as c:
            again=c.execute("""SELECT claim_id,state,attempt_trace_id FROM
              history_l1.external_dispatch_claims
              WHERE owner_id=%s AND attempt_id=%s""",
              (owner,att["id"])).fetchone()
            self.assertEqual(again,prior)
            self.assertTrue(c.execute("""SELECT to_regprocedure(
                'history_l1.claim_external_dispatch(text,text,text)')
                IS NOT NULL AS present""").fetchone()["present"])
        print("DC12_REAL_011_EMPTY_UP_DOWN_UP_AND_EVIDENCE_DOWN_REFUSED",flush=True)


    def test_DC13_real_fresh_os_process_after_commit_cannot_claim_again(self):
        """Distinct OS process has ZERO Python in-memory state from the winner."""
        import sys
        owner,_,attempt,first=make_attempt(claim_in_tx=True)
        self.assertTrue(first["claim_won"])
        worker = """
import os,sys,psycopg
from psycopg.rows import dict_row
owner,attempt_id,trace=sys.argv[1:]
with psycopg.connect(os.environ['DB_APP_DSN'],autocommit=True,row_factory=dict_row) as c:
    with c.transaction():
        c.execute("SELECT set_config('app.owner_id',%s,true)",(owner,))
        r=c.execute("SELECT claim_won,claim_id FROM history_l1.claim_external_dispatch(%s,%s,%s)",
                    (owner,attempt_id,trace)).fetchone()
        assert r['claim_won'] is False and r['claim_id'] is None, r
        status=c.execute("SELECT dispatch_state FROM history_l1.status_external_dispatch(%s,%s,%s)",
                         (owner,attempt_id,trace)).fetchone()
        assert status['dispatch_state']=='CLAIMED',status
print('REAL_NEW_OS_PROCESS_CLAIM_REJECTED_NO_REDISPATCH')
"""
        env={"DB_APP_DSN":os.environ["DB_APP_DSN"],"CI":"true",
             "GITHUB_ACTIONS":"true","PATH":"/usr/bin:/bin"}
        for _ in range(2):
            completed=subprocess.run(
                [sys.executable,"-c",worker,owner,attempt["id"],
                 attempt["attempt_trace_id"]],
                env=env,capture_output=True,text=True,timeout=12)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertIn("REAL_NEW_OS_PROCESS_CLAIM_REJECTED_NO_REDISPATCH",
                          completed.stdout)
        print("DC13_TWO_FRESH_OS_PROCESSES_RESTART_NO_SECOND_DISPATCH_RIGHT",flush=True)



def send_request_for_receipt(receipt,att):
    # Only used to verify exact same scoped send idempotency after new Worker.
    # The original question is persisted in messages and must be loaded from
    # RLS-bound History, not reconstructed from receipt metadata alone.
    with connect("MIG") as c:
        msg=c.execute("""SELECT body FROM history_l1.messages
             WHERE owner_id=%s AND id=%s""",
             (att["owner_id"],receipt["message_id"])).fetchone()
    return {"kind":"send_message_request","contract_version":"product.v1",
            "requested_conversation_id":receipt["requested_conversation_id"],
            "client_message_id":receipt["client_message_id"],
            "idempotency_key":receipt["idempotency_key"],
            "question":msg["body"]}
