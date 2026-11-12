"""009 initial-login binding: real disposable PostgreSQL 17.11, DB-only DBL01..16.

No live IdP, HTTP, browser, raw session verifier in SQL, or production grants.
API verifies Code/JWKS/bootstrap; this file tests ONLY database operations.
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
from src.phase3.storage.postgres import auth_session

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "infra/postgres/migrations/009_initial_login_attempt_binding.up.sql"
DOWN = ROOT / "infra/postgres/migrations/009_initial_login_attempt_binding.down.sql"

ROLES = {
 "BOOT": ("LOGIN_BOOTSTRAP_DSN","auth_login_bootstrap"),
 "ISSUE": ("LOGIN_ISSUER_DSN","auth_login_issuer"),
 "BIND": ("LOGIN_BINDER_DSN","auth_login_binder"),
 "STATUS": ("LOGIN_READER_DSN","auth_login_reader"),
 "CLEAN": ("LOGIN_CLEANER_DSN","auth_login_cleaner"),
 "MAP": ("AUTH_MAP_DSN","auth_mapper"),
 "SESSION": ("AUTH_SESSION_DSN","auth_sessions"),
 "REVOKE": ("AUTH_REVOKER_DSN","auth_revoker"),
 "MIG": ("AUTH_MIG_DSN","auth_migrator"),
 "APP": ("DB_APP_DSN","history_app"),
 "REPLAY": ("REPLAY_API_DSN","auth_trust_api"),
}
DATABASES = {"history_ci","login_009_empty_ci","login_009_evidence_ci"}


def conn(role="MIG",database="history_ci"):
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
        raise RuntimeError("LOGIN_009_GITHUB_DISPOSABLE_ONLY")
    if database not in DATABASES:
        raise RuntimeError("LOGIN_009_DATABASE_NOT_ALLOWED")
    var,user = ROLES[role]
    data = conninfo_to_dict(os.environ[var])
    if (data.get("host")!="127.0.0.1" or data.get("port")!="5432"
        or data.get("dbname")!="history_ci" or data.get("user")!=user
        or set(data)-{"host","port","dbname","user","password","connect_timeout"}):
        raise RuntimeError("LOGIN_009_UNSAFE_CONNECTION")
    return psycopg.connect(make_conninfo(os.environ[var],dbname=database),
                           autocommit=True,row_factory=dict_row)


def digest(raw):
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def token():
    return secrets.token_urlsafe(36)


def new_attempt(ttl=180, database="history_ci"):
    issuer="https://synthetic.invalid/initial-"+uuid.uuid4().hex
    subject="subject_"+uuid.uuid4().hex
    with conn("MAP",database) as c:
        identity=auth_session.map_identity(c,issuer,subject)
    x={"attempt":uuid.uuid4(), "bff_attempt":uuid.uuid4(),
       "principal":"synthetic-bff-fixed-v1", "start_key":token(),
       "request_digest":digest(token()),"state_digest":digest(token()),
       "initiator_digest":digest(token()),"issuer":issuer,
       "subject":subject,"owner":identity["owner_id"],"epoch":identity["epoch"]}
    with conn("BOOT",database) as c:
        assert start(c,x,ttl)
    return x


def start(c,x,ttl=180):
    return c.execute("""SELECT auth_l1.start_initial_login_attempt(
      %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS accepted""",
      (x["attempt"],x["principal"],x["bff_attempt"],x["start_key"],
       x["request_digest"],x["state_digest"],x["initiator_digest"],
       x["issuer"],b"\x7f"*48,b"\x71"*48,ttl)).fetchone()["accepted"]


def claim(c,x):
    return c.execute("""SELECT auth_l1.claim_initial_login_exchange(
       %s,%s,%s,%s) AS accepted""",
       (x["attempt"],x["principal"],x["initiator_digest"],
        x["state_digest"])).fetchone()["accepted"]


def unknown(c,x):
    return c.execute("""SELECT auth_l1.mark_initial_login_unknown(
       %s,%s,%s) AS accepted""",
       (x["attempt"],x["principal"],x["initiator_digest"])).fetchone()["accepted"]


def issue(c,x,raw=None):
    raw=raw or token()
    info=c.execute("""SELECT auth_l1.issue_initial_login_pending(
      %s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS receipt""",
      (x["attempt"],x["principal"],x["initiator_digest"],x["owner"],
       x["issuer"],x["subject"],x["epoch"],digest(raw),120,500)
    ).fetchone()["receipt"]
    return info,raw


def ack(c,x,receipt,alias=None):
    alias=alias or digest("synthetic-bff-alias-fixed")
    return c.execute("""SELECT auth_l1.ack_initial_login_binding(
      %s,%s,%s,%s,%s,%s,%s) AS accepted""",
      (x["attempt"],uuid.UUID(str(receipt)),x["principal"],
       x["initiator_digest"],x["owner"],x["epoch"],alias)
    ).fetchone()["accepted"]


def abort(c,x,receipt):
    return c.execute("""SELECT auth_l1.abort_initial_login_binding(
      %s,%s,%s,%s,%s,%s) AS accepted""",
      (x["attempt"],uuid.UUID(str(receipt)),x["principal"],
       x["initiator_digest"],x["owner"],x["epoch"])
    ).fetchone()["accepted"]


def status(c,x,principal=None,initiator=None):
    return c.execute("""SELECT auth_l1.status_initial_login_attempt(
      %s,%s,%s) AS payload""",
      (x["attempt"],principal or x["principal"],
       initiator or x["initiator_digest"])).fetchone()["payload"]


def stored(x,database="history_ci"):
    with conn("MIG",database) as c:
        return c.execute("""SELECT a.state,a.receipt_id,a.alias_sha256,
          a.session_digest,a.owner_id,a.issued_epoch,a.state_version,
          s.status AS session_status,s.session_epoch,o.session_epoch AS owner_epoch,
          o.reset_gate
          FROM auth_l1.initial_login_attempts AS a
          LEFT JOIN auth_l1.sessions AS s ON s.digest_sha256=a.session_digest
          LEFT JOIN auth_l1.owners AS o ON o.owner_id=a.owner_id
          WHERE a.attempt_id=%s""",(x["attempt"],)).fetchone()


def ready(ttl=180):
    x=new_attempt(ttl)
    with conn("BOOT") as c:
        assert claim(c,x)
    with conn("ISSUE") as c:
        info,raw=issue(c,x)
    return x,info,raw


def wait_for_blocker(application_name,reader_pid):
    with conn("MIG") as observer:
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            row=observer.execute("""SELECT a.pid,a.wait_event_type,a.wait_event,
                       pg_blocking_pids(a.pid) AS blockers
                   FROM pg_stat_activity AS a
                   WHERE a.datname='history_ci' AND a.application_name=%s
                     AND a.wait_event_type='Lock'""",(application_name,)).fetchone()
            if row and reader_pid in row["blockers"]:
                print("LOGIN_009_REAL_PG_WAIT blocker_pid="+str(reader_pid)+
                      " waiter_pid="+str(row["pid"])+
                      " pg_blocking_pids="+str(row["blockers"])+
                      " wait_event="+str(row["wait_event"]),flush=True)
                return row
            observer.execute("SELECT pg_sleep(0.03)")
    raise AssertionError("LOGIN_009_EXPECTED_REAL_BLOCKER_NOT_OBSERVED")


def run_down(database,sql_path=DOWN):
    if database not in DATABASES-{"history_ci"}:
        raise RuntimeError("LOGIN_009_NO_DESTRUCTIVE_TEST_ON_HISTORY")
    data=conninfo_to_dict(os.environ["AUTH_MIG_DSN"])
    env=dict(os.environ)
    env.update(PGHOST="127.0.0.1",PGPORT="5432",
               PGDATABASE=database,PGUSER="auth_migrator",
               PGPASSWORD=data["password"])
    try:
        return subprocess.run(["psql","-X","-v","ON_ERROR_STOP=1","-d",database,
                               "-f",str(sql_path)],env=env,capture_output=True,
                              text=True,timeout=15,check=False)
    except subprocess.TimeoutExpired:
        raise AssertionError("LOGIN_009_DOWN_TIMEOUT_NOT_EXPECTED")


class InitialLoginBinding009(unittest.TestCase):
    def test_DBL01_concurrent_two_worker_claim_exactly_one(self):
        x=new_attempt()
        first_holds=threading.Event()
        release=threading.Event()
        app="login009_second_claim_"+uuid.uuid4().hex[:8]
        def first():
            with conn("BOOT") as c:
                with c.transaction():
                    pid=c.info.backend_pid
                    self.assertTrue(claim(c,x))
                    first_holds.set()
                    if not release.wait(12):
                        raise AssertionError("first worker barrier timed out")
                    return pid
        def second():
            with conn("BOOT") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(app,))
                with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                    with c.transaction():
                        claim(c,x)
            return "DENIED"
        with ThreadPoolExecutor(max_workers=2) as pool:
            first_task=pool.submit(first)
            self.assertTrue(first_holds.wait(10))
            with conn("MIG") as admin:
                holder=admin.execute("""SELECT pid FROM pg_stat_activity
                  WHERE application_name LIKE 'login009_no_such_marker'""").fetchone()
                self.assertIsNone(holder)
            # first worker's real backend PID, returned through explicit barrier.
            # A second Event+list allows the observer to target it without sleeps.
            with conn("MIG") as admin:
                row=admin.execute("""SELECT a.pid FROM pg_stat_activity AS a
                      JOIN pg_locks AS l ON l.pid=a.pid
                     WHERE a.datname='history_ci' AND l.locktype='relation'
                       AND l.relation='auth_l1.initial_login_attempts'::regclass
                       AND a.state='idle in transaction'
                  ORDER BY a.backend_start DESC LIMIT 1""").fetchone()
                self.assertIsNotNone(row)
                pid=row["pid"]
            second_task=pool.submit(second)
            try:
                wait_for_blocker(app,pid)
                self.assertFalse(second_task.done())
            finally:
                release.set()
            self.assertEqual(first_task.result(timeout=12),pid)
            self.assertEqual(second_task.result(timeout=12),"DENIED")
        self.assertEqual(stored(x)["state"],"EXCHANGE_STARTED")
        print("DBL01_ONE_CLAIM_TWO_PHYSICAL_WORKERS",flush=True)

    def test_DBL02_unknown_exchange_never_reclaims_or_issues(self):
        x=new_attempt()
        with conn("BOOT") as c:
            self.assertTrue(claim(c,x))
            self.assertTrue(unknown(c,x))
            self.assertTrue(unknown(c,x))
            with self.assertRaises(psycopg.Error):
                claim(c,x)
        with conn("ISSUE") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_ISSUE_UNCOMMITTED_OR_INVALID"):
                issue(c,x)
        self.assertEqual(stored(x)["state"],"UNKNOWN_RECONCILIATION_REQUIRED")

    def test_DBL03_exactly_one_pending_issue_even_with_second_digest(self):
        x=new_attempt()
        with conn("BOOT") as c:self.assertTrue(claim(c,x))
        def issue_attempt(_):
            with conn("ISSUE") as c:
                try: return issue(c,x)[0]
                except psycopg.Error: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            two=list(pool.map(issue_attempt,range(2)))
        wins=[t for t in two if t]
        self.assertEqual(len(wins),1)
        with conn("MIG") as c:
            n=c.execute("""SELECT count(*) AS n FROM auth_l1.sessions
              WHERE digest_sha256=(SELECT session_digest
                FROM auth_l1.initial_login_attempts WHERE attempt_id=%s)""",
                (x["attempt"],)).fetchone()["n"]
        self.assertEqual(n,1)
        self.assertEqual(stored(x)["session_status"],"PENDING_BINDING")

    def test_DBL04_pending_never_inspect_or_admit_or_rotate(self):
        x,info,raw=ready()
        with conn("SESSION") as c:
            self.assertIsNone(auth_session.inspect(c,raw))
            with c.transaction():
                self.assertFalse(auth_session.admit_session_fenced(c,raw,x["owner"],0,0))
            with self.assertRaises(psycopg.Error):
                auth_session.touch(c,raw,0)
            with self.assertRaises(psycopg.Error):
                auth_session.rotate(c,raw,0,0)
        self.assertEqual(stored(x)["state"],"ISSUED_PENDING_BINDING")

    def test_DBL05_epoch_or_gate_drift_blocks_issue_and_ack(self):
        x=new_attempt()
        with conn("BOOT") as c:claim(c,x)
        with conn("REVOKE") as c:
            self.assertEqual(auth_session.revoke_all(c,x["owner"],0),1)
        with conn("ISSUE") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_OWNER_EPOCH_OR_GATE_DENIED"):
                issue(c,x)
        y,receipt,raw=ready()
        with conn("REVOKE") as c:
            self.assertEqual(auth_session.revoke_all(c,y["owner"],0),1)
        with conn("BIND") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_ACK_STALE_OR_REVOKED"):
                ack(c,y,receipt["receipt_id"])
        self.assertEqual(stored(y)["session_status"],"PENDING_BINDING")

    def test_DBL06_revoke_waits_for_already_admitted_active_read(self):
        x,receipt,raw=ready()
        with conn("BIND") as c:
            self.assertTrue(ack(c,x,receipt["receipt_id"]))
        name="login009_revoker_"+uuid.uuid4().hex[:8]
        started=threading.Event()
        def revoke():
            with conn("SESSION") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                started.set()
                return auth_session.revoke_one(c,raw,0)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with conn("SESSION") as reader:
                reader_pid=reader.info.backend_pid
                with reader.transaction():
                    self.assertTrue(auth_session.admit_session_fenced(
                        reader,raw,x["owner"],0,0))
                    work=pool.submit(revoke)
                    self.assertTrue(started.wait(8))
                    wait_for_blocker(name,reader_pid)
                    self.assertFalse(work.done())
            self.assertTrue(work.result(timeout=10))
        with conn("SESSION") as c:
            with c.transaction():
                self.assertFalse(auth_session.admit_session_fenced(
                    c,raw,x["owner"],0,0))
        self.assertEqual(stored(x)["session_status"],"revoked")

    def test_DBL07_new_jti_does_not_reopen_login_attempt(self):
        x=new_attempt()
        with conn("BOOT") as c:
            claim(c,x)
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                claim(c,x)
        with conn("REPLAY") as c:
            with self.assertRaises(psycopg.Error):
                c.execute("""SELECT auth_l1.claim_initial_login_exchange(
                    %s,%s,%s,%s)""",
                    (x["attempt"],x["principal"],x["initiator_digest"],x["state_digest"]))

    def test_DBL08_ack_twice_stable_and_conflicting_alias_denied(self):
        x,receipt,raw=ready()
        alias=digest(token())
        with conn("BIND") as c:
            self.assertTrue(ack(c,x,receipt["receipt_id"],alias))
            version=stored(x)["state_version"]
            self.assertTrue(ack(c,x,receipt["receipt_id"],alias))
            self.assertEqual(stored(x)["state_version"],version)
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_ACK_CONFLICT"):
                ack(c,x,receipt["receipt_id"],digest(token()))
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_ABORT_CONFLICT"):
                abort(c,x,receipt["receipt_id"])
        with conn("SESSION") as c:
            self.assertEqual(auth_session.inspect(c,raw)["owner_id"],x["owner"])

    def test_DBL09_abort_twice_and_late_ack_denied(self):
        x,receipt,raw=ready()
        with conn("BIND") as c:
            self.assertTrue(abort(c,x,receipt["receipt_id"]))
            version=stored(x)["state_version"]
            self.assertTrue(abort(c,x,receipt["receipt_id"]))
            self.assertEqual(stored(x)["state_version"],version)
            with self.assertRaises(psycopg.Error):
                ack(c,x,receipt["receipt_id"])
        self.assertEqual(stored(x)["session_status"],"revoked")
        with conn("SESSION") as c:self.assertIsNone(auth_session.inspect(c,raw))

    def test_DBL10_lost_issue_reply_cannot_reissue_or_recover_verifier(self):
        x,receipt,raw=ready()
        with conn("ISSUE") as c:
            with self.assertRaises(psycopg.Error):
                issue(c,x,token())
        with conn("STATUS") as c:
            observed=status(c,x)
            self.assertEqual(observed["state"],"ISSUED_PENDING_BINDING")
            self.assertNotIn("receipt",str(observed))
            self.assertNotIn("verifier",str(observed))
            self.assertNotIn(raw,str(observed))
            self.assertNotIn(x["owner"],str(observed))
        self.assertEqual(stored(x)["session_status"],"PENDING_BINDING")

    def test_DBL11_status_bound_to_principal_and_initiator(self):
        x,receipt,raw=ready()
        with conn("STATUS") as c:
            self.assertIsNone(status(c,x,principal="other-bff"))
            self.assertIsNone(status(c,x,initiator=digest(token())))
            self.assertEqual(status(c,x)["state"],"ISSUED_PENDING_BINDING")
        with conn("APP") as c:
            with self.assertRaises(psycopg.Error):
                status(c,x)
        self.assertEqual(stored(x)["session_status"],"PENDING_BINDING")

    def test_DBL12_ack_only_proves_db_activation_not_browser_cookie(self):
        x,receipt,raw=ready()
        with conn("BIND") as c: self.assertTrue(ack(c,x,receipt["receipt_id"]))
        with conn("STATUS") as c:
            snapshot=status(c,x)
            self.assertEqual(snapshot["state"],"ACTIVE")
            self.assertNotIn("cookie",str(snapshot).lower())
        # Browser Set-Cookie delivery is outside this PG test, delegated to UI.

    def test_DBL13_parallel_ack_and_revoke_all_owner_first(self):
        x,receipt,raw=ready()
        ready_tx=threading.Event()
        release=threading.Event()
        rev_name="login009_epoch_revoke_"+uuid.uuid4().hex[:8]
        def ack_holds():
            with conn("BIND") as c:
                with c.transaction():
                    pid=c.info.backend_pid
                    self.assertTrue(ack(c,x,receipt["receipt_id"]))
                    ready_tx.set()
                    if not release.wait(12):
                        raise AssertionError("ACK worker timeout")
                    return pid
        def revoke_second():
            with conn("REVOKE") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(rev_name,))
                return auth_session.revoke_all(c,x["owner"],0)
        with ThreadPoolExecutor(max_workers=2) as pool:
            holder=pool.submit(ack_holds)
            self.assertTrue(ready_tx.wait(10))
            with conn("MIG") as c:
                row=c.execute("""SELECT a.pid FROM pg_stat_activity AS a
                    JOIN pg_locks AS l ON l.pid=a.pid
                    WHERE a.state='idle in transaction'
                      AND l.relation='auth_l1.owners'::regclass
                      AND l.locktype='relation'
                    ORDER BY a.backend_start DESC LIMIT 1""").fetchone()
                self.assertIsNotNone(row)
                blocker=row["pid"]
            rev=pool.submit(revoke_second)
            try: wait_for_blocker(rev_name,blocker)
            finally: release.set()
            self.assertEqual(holder.result(timeout=12),blocker)
            self.assertEqual(rev.result(timeout=12),1)
        self.assertEqual(stored(x)["owner_epoch"],1)
        with conn("SESSION") as c:
            self.assertIsNone(auth_session.inspect(c,raw))
        with conn("BIND") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_ACK_STALE_OR_REVOKED"):
                ack(c,x,receipt["receipt_id"])

    def test_DBL14_owner_scoped_history_and_post_revoke_fence(self):
        x,receipt,raw=ready()
        with conn("BIND") as c:ack(c,x,receipt["receipt_id"])
        other=new_attempt()
        from test_history_l1 import create_req
        with conn("APP") as c:
            from src.phase3.storage.postgres import repository as history
            a=history.create_conversation(c,x["owner"],create_req(
                title="synthetic-login009-A"),token(),token())
            b=history.create_conversation(c,other["owner"],create_req(
                title="synthetic-login009-B"),token(),token())
            with c.transaction():
                history.scoped(c,x["owner"])
                titles=[v["title"] for v in c.execute(
                  "SELECT title FROM history_l1.conversations").fetchall()]
                self.assertIn("synthetic-login009-A",titles)
                self.assertNotIn("synthetic-login009-B",titles)
        with conn("SESSION") as c:
            self.assertIsNotNone(auth_session.inspect(c,raw))
            self.assertTrue(auth_session.revoke_one(c,raw,0))
            with c.transaction():
                self.assertFalse(auth_session.admit_session_fenced(c,raw,x["owner"],0,0))

    def test_DBL15_roles_denied_direct_tables_and_cross_function(self):
        with conn("MIG") as c:
            for role in ("auth_login_bootstrap","auth_login_issuer",
                         "auth_login_binder","auth_login_reader","auth_login_cleaner"):
                r=c.execute("""SELECT rolsuper,rolbypassrls,rolinherit,
                    rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=%s""",
                    (role,)).fetchone()
                self.assertFalse(any(r.values()),role)
            for table in ("auth_l1.initial_login_attempts","auth_l1.sessions"):
                r=c.execute("""SELECT relrowsecurity,relforcerowsecurity
                  FROM pg_class WHERE oid=%s::regclass""",(table,)).fetchone()
                self.assertTrue(r["relrowsecurity"])
                self.assertTrue(r["relforcerowsecurity"])
        for role in ("BOOT","ISSUE","BIND","STATUS","CLEAN","APP","REPLAY"):
            with conn(role) as c:
                with self.assertRaises(psycopg.Error):
                    c.execute("SELECT count(*) FROM auth_l1.initial_login_attempts")
        x=new_attempt()
        with conn("ISSUE") as c:
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT auth_l1.issue_session(%s,%s,%s,%s,%s)",
                          (x["owner"],0,digest(token()),120,500))
        with conn("BOOT") as c:
            with self.assertRaises(psycopg.Error):
                c.execute("""SELECT auth_l1.ack_initial_login_binding(
                  %s,%s,%s,%s,%s,%s,%s)""",
                  (x["attempt"],uuid.uuid4(),x["principal"],x["initiator_digest"],
                   x["owner"],0,digest(token())))

    def test_DBL16_real_009_up_down_up_and_evidence_rollback_refusal(self):
        # Reuse independently bootstrapped 003..009 empty/evidence DBs.
        empty="login_009_empty_ci"
        for sql in (DOWN,UP,DOWN,UP):
            done=run_down(empty,sql)
            self.assertEqual(done.returncode,0,done.stderr[-1100:])
        with conn("MIG",empty) as c:
            self.assertTrue(c.execute("""SELECT to_regclass(
              'auth_l1.initial_login_attempts') IS NOT NULL AS ok""").fetchone()["ok"])
            self.assertEqual(c.execute("""SELECT count(*) AS n FROM auth_l1.owners
              """).fetchone()["n"],0)
        evidence="login_009_evidence_ci"
        x=new_attempt(database=evidence)
        forbidden=run_down(evidence)
        self.assertNotEqual(forbidden.returncode,0)
        self.assertIn("LOGIN_009_DOWN_REFUSED_EVIDENCE_EXISTS",forbidden.stderr)
        self.assertNotIn("deadlock detected",forbidden.stderr.lower())
        self.assertNotIn("timeout",forbidden.stderr.lower())
        self.assertEqual(stored(x,evidence)["state"],"INITIATED")
        with conn("MIG",evidence) as c:
            self.assertTrue(c.execute("""SELECT to_regprocedure(
                'auth_l1.issue_initial_login_pending(uuid,text,text,text,text,text,bigint,text,integer,integer)')
                IS NOT NULL AS ok""").fetchone()["ok"])
        print("DBL16_ACTUAL_009_EMPTY_UP_DOWN_UP_PASS_EVIDENCE_DOWN_REFUSED",flush=True)

    def test_DBL17_pending_cleanup_and_idempotent_terminal_tombstone(self):
        x,receipt,raw=ready(ttl=1)
        time.sleep(1.15)
        with conn("CLEAN") as c:
            result=c.execute("""SELECT auth_l1.cleanup_initial_login_attempt(%s)
              AS outcome""",(x["attempt"],)).fetchone()["outcome"]
            self.assertEqual(result,"EXPIRED_PENDING_REVOKED")
            again=c.execute("""SELECT auth_l1.cleanup_initial_login_attempt(%s)
              AS outcome""",(x["attempt"],)).fetchone()["outcome"]
            self.assertEqual(again,"TERMINAL_NO_CHANGE")
        self.assertEqual(stored(x)["session_status"],"revoked")
        with conn("BIND") as c:
            with self.assertRaises(psycopg.Error):ack(c,x,receipt["receipt_id"])
        with conn("SESSION") as c:self.assertIsNone(auth_session.inspect(c,raw))

    def test_DBL18_expired_unclaimed_or_ambiguous_claim_preserved(self):
        x=new_attempt(ttl=1)
        y=new_attempt(ttl=1)
        with conn("BOOT") as c:claim(c,y)
        time.sleep(1.15)
        with conn("CLEAN") as c:
            a=c.execute("""SELECT auth_l1.cleanup_initial_login_attempt(%s)
              AS outcome""",(x["attempt"],)).fetchone()["outcome"]
            b=c.execute("""SELECT auth_l1.cleanup_initial_login_attempt(%s)
              AS outcome""",(y["attempt"],)).fetchone()["outcome"]
        self.assertEqual(a,"EXPIRED_UNCLAIMED")
        self.assertEqual(b,"UNKNOWN_EXCHANGE")
        with conn("BOOT") as c:
            with self.assertRaises(psycopg.Error):claim(c,x)
            with self.assertRaises(psycopg.Error):claim(c,y)

    def _race_ack_abort(self,first_action):
        x,receipt,raw=ready()
        first_ready=threading.Event()
        release=threading.Event()
        witness={}
        label="login009_"+first_action+"_versus_"+uuid.uuid4().hex[:8]
        def first_worker():
            with conn("BIND") as c:
                with c.transaction():
                    witness["pid"]=c.info.backend_pid
                    if first_action=="ACK":
                        self.assertTrue(ack(c,x,receipt["receipt_id"]))
                    else:
                        self.assertTrue(abort(c,x,receipt["receipt_id"]))
                    first_ready.set()
                    if not release.wait(12):
                        raise AssertionError("ACK/ABORT first transaction timed out")
                return first_action
        def second_worker():
            with conn("BIND") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(label,))
                if first_action=="ACK":
                    with self.assertRaisesRegex(psycopg.Error,"LOGIN_ABORT_CONFLICT"):
                        with c.transaction():
                            abort(c,x,receipt["receipt_id"])
                else:
                    with self.assertRaisesRegex(psycopg.Error,"LOGIN_ACK_STALE_OR_REVOKED"):
                        with c.transaction():
                            ack(c,x,receipt["receipt_id"])
                return "CONFLICT_DENIED"
        with ThreadPoolExecutor(max_workers=2) as pool:
            winner=pool.submit(first_worker)
            self.assertTrue(first_ready.wait(10))
            loser=pool.submit(second_worker)
            try:
                observation=wait_for_blocker(label,witness["pid"])
                self.assertIn(witness["pid"],observation["blockers"])
                self.assertFalse(loser.done(),"No verified competing TX wait")
            finally:
                release.set()
            self.assertEqual(winner.result(timeout=12),first_action)
            self.assertEqual(loser.result(timeout=12),"CONFLICT_DENIED")
        saved=stored(x)
        self.assertEqual(saved["state"],"ACTIVE" if first_action=="ACK" else "ABORTED")
        self.assertEqual(saved["session_status"],"active" if first_action=="ACK" else "revoked")
        with conn("SESSION") as c:
            actual=auth_session.inspect(c,raw)
            self.assertEqual(actual is not None,first_action=="ACK")
        print("LOGIN009_ACK_ABORT_REAL_LOCK_"+first_action+"_FIRST",flush=True)

    def test_DBL19_simultaneous_ack_first_abort_waits_and_denied(self):
        self._race_ack_abort("ACK")

    def test_DBL20_simultaneous_abort_first_ack_waits_and_denied(self):
        self._race_ack_abort("ABORT")
