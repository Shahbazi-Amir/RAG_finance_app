"""CR-DB-01A — real PostgreSQL 17.11, synthetic C1 ONLY; no live IdP/API.

Run ONLY in disposable Actions PostgreSQL. The independently trusted issuer
and executor are distinct DB roles. Lock races use separate real connections
and pg_stat_activity.wait_event_type='Lock', not sleep as race evidence.
"""
import os
import sys
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InsufficientPrivilege, UniqueViolation
from psycopg.rows import dict_row

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src/phase3/storage/postgres"))
import reset_c1 as reset
import auth_session as auth
from test_auth_session import db, owner, issue, observed_wait, digest

def reset_db(role="EXEC"):
    if os.getenv("CI")!="true": raise RuntimeError("CI_ONLY")
    key="AUTH_RESET_ISSUER_DSN" if role=="ISSUER" else "AUTH_RESET_EXEC_DSN"
    target="auth_reset_issuer" if role=="ISSUER" else "auth_reset_executor"
    val=os.environ[key]; d=conninfo_to_dict(val)
    if not (d.get("host")=="127.0.0.1" and d.get("port")=="5432"
            and d.get("dbname")=="history_ci" and d.get("user")==target
            and set(d).issubset({"host","port","dbname","user","password","connect_timeout"})):
        raise RuntimeError("UNSAFE_RESET_DB_TARGET")
    return psycopg.connect(val,autocommit=True,row_factory=dict_row)

def clock_epoch(delta=60):
    with db("MIG") as c:
        return c.execute("SELECT floor(extract(epoch from clock_timestamp()))::bigint + %s AS t",
                         (delta,)).fetchone()["t"]

def mint(oid,kind=reset.KIND_RECOVERY,delta=90,epoch=0,session=None,gen=None):
    with reset_db("ISSUER") as c:
        return reset.issue_synthetic_verified_authorization(
            c,oid,kind,epoch,clock_epoch(delta),
            trusted_session_digest=session,trusted_session_generation=gen)

def commit(c,cap,*,owner_id=None,kind=None,epoch=None,op=None):
    return reset.commit_c1(c,cap.opaque,owner_id=cap.owner_id if owner_id is None else owner_id,
        kind=cap.kind if kind is None else kind,
        expected_epoch=cap.expected_epoch if epoch is None else epoch,operation_id=op)

def states(oid,cap=None):
    with db("MIG") as c:
        o=c.execute("SELECT state,session_epoch,reset_gate FROM auth_l1.owners WHERE owner_id=%s",(oid,)).fetchone()
        n=c.execute("SELECT status,count(*) AS n FROM auth_l1.sessions WHERE owner_id=%s GROUP BY status",(oid,)).fetchall()
        ops=c.execute("SELECT operation_id,status,active,expected_epoch,revoked_epoch FROM auth_l1.reset_c1_operations WHERE owner_id=%s",(oid,)).fetchall()
        consumed=None
        if cap:
            consumed=c.execute("SELECT consumed_operation_id,consumed_at FROM auth_l1.reset_c1_authorizations WHERE authorization_sha256=%s",
                               (reset.digest_authorization(cap.opaque),)).fetchone()
        return o,{s["status"]:s["n"] for s in n},ops,consumed

def run(cap,op=None):
    with reset_db() as c:
        with c.transaction():
            return commit(c,cap,op=op)

class InjectedAbort(Exception): pass

class AtomicResetC1(unittest.TestCase):
    def test_CR01_commit_many_sessions_pending_gate_and_new_admission_denial(self):
        oid=owner()["owner_id"]; sessions=[issue(oid) for _ in range(3)]
        cap=mint(oid); op=uuid.uuid4()
        with reset_db() as c:
            with self.assertRaisesRegex(RuntimeError,"REQUIRES_OUTER_TRANSACTION"):
                commit(c,cap,op=op)
            with c.transaction():
                receipt=commit(c,cap,op=op)
                self.assertEqual(receipt["status"],"REVOKED_PENDING_IDP")
                self.assertEqual(receipt["revoked_epoch"],1)
        o,session_rows,ops,consumed=states(oid,cap)
        self.assertEqual((o["session_epoch"],o["reset_gate"]),(1,"pending_reauth"))
        self.assertEqual(session_rows,{"revoked":3})
        self.assertEqual(len(ops),1)
        self.assertEqual(ops[0]["operation_id"],op)
        self.assertEqual(ops[0]["status"],"REVOKED_PENDING_IDP")
        self.assertEqual(consumed["consumed_operation_id"],op)
        for sess in sessions:
            with db("SESSION") as c:
                with c.transaction():
                    self.assertFalse(auth.admit_session_fenced(c,sess.opaque,oid,0,0))
                    self.assertFalse(auth.admit_session_fenced(c,sess.opaque,oid,1,0))
            with db("SESSION") as c:
                with self.assertRaises(psycopg.Error):
                    auth.issue(c,oid,1,idle_seconds=30,absolute_seconds=200)

    def test_CR02_injected_rollback_discards_authz_consumption_op_epoch_and_revocation(self):
        oid=owner()["owner_id"]; s=issue(oid); cap=mint(oid)
        with reset_db() as c:
            with self.assertRaises(InjectedAbort):
                with c.transaction():
                    commit(c,cap)
                    raise InjectedAbort()
        o,sessions,ops,consumed=states(oid,cap)
        self.assertEqual((o["session_epoch"],o["reset_gate"]),(0,"open"))
        self.assertEqual(sessions,{"active":1})
        self.assertEqual(ops,[])
        self.assertIsNone(consumed["consumed_at"])
        with db("SESSION") as c:
            with c.transaction(): self.assertTrue(auth.admit_session_fenced(c,s.opaque,oid,0,0))
        run(cap)
        self.assertEqual(states(oid)[0]["session_epoch"],1)

    def test_CR03_same_authorization_two_real_connections_one_winner(self):
        oid=owner()["owner_id"]; cap=mint(oid)
        name="cr03_"+uuid.uuid4().hex[:8]
        def loser():
            with reset_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                c.execute("SET statement_timeout='10000ms'")
                try:
                    with c.transaction(): commit(c,cap)
                    return "unexpected"
                except psycopg.Error: return "denied"
        with ThreadPoolExecutor(max_workers=1) as pool:
            with reset_db() as holder:
                with holder.transaction():
                    commit(holder,cap)
                    future=pool.submit(loser)
                    observed_wait([name])
                    self.assertFalse(future.done())
            self.assertEqual(future.result(timeout=12),"denied")
        o,_,ops,_=states(oid,cap)
        self.assertEqual(o["session_epoch"],1)
        self.assertEqual(len(ops),1)
        with reset_db() as c:
            with self.assertRaises(psycopg.Error):
                with c.transaction(): commit(c,cap)
        self.assertEqual(states(oid)[0]["session_epoch"],1)

    def test_CR04_different_authorizations_same_owner_active_operation_exclusion(self):
        oid=owner()["owner_id"]; a=mint(oid); b=mint(oid)
        name="cr04_"+uuid.uuid4().hex[:8]
        def competitor():
            with reset_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                c.execute("SET statement_timeout='10000ms'")
                try:
                    with c.transaction(): commit(c,b)
                    return "unexpected"
                except psycopg.Error: return "denied"
        with ThreadPoolExecutor(max_workers=1) as pool:
            with reset_db() as c:
                with c.transaction():
                    commit(c,a)
                    waiter=pool.submit(competitor)
                    observed_wait([name])
                self.assertEqual(waiter.result(timeout=12),"denied")
        self.assertEqual(states(oid)[0]["session_epoch"],1)
        self.assertEqual(len(states(oid)[2]),1)
        self.assertIsNone(states(oid,b)[3]["consumed_at"])
        with reset_db("ISSUER") as issuer:
            with self.assertRaises(psycopg.Error):
                reset.issue_synthetic_verified_authorization(
                    issuer,oid,reset.KIND_RECOVERY,1,clock_epoch(60))

    def test_CR05_independent_owners_progress_even_if_first_owner_locked(self):
        a=owner()["owner_id"]; b=owner()["owner_id"]
        ca=mint(a); cb=mint(b)
        with reset_db() as c:
            with c.transaction():
                commit(c,ca)
                # Owner A lock held; separate B transaction still commits.
                with ThreadPoolExecutor(max_workers=1) as ex:
                    f=ex.submit(run,cb)
                    self.assertEqual(f.result(timeout=8)["status"],"REVOKED_PENDING_IDP")
                self.assertEqual(states(b)[0]["session_epoch"],1)
        self.assertEqual(states(a)[0]["session_epoch"],1)

    def test_CR06_invalid_null_cross_owner_kind_purpose_and_epoch_have_no_effect(self):
        a=owner()["owner_id"]; b=owner()["owner_id"]; cap=mint(a)
        with reset_db() as c:
            for kwargs in (
                {"owner_id":b},{"kind":reset.KIND_AUTHENTICATED},{"epoch":1}
            ):
                with self.assertRaises(psycopg.Error):
                    with c.transaction(): commit(c,cap,**kwargs)
            for args in (
                (None,a,reset.KIND_RECOVERY,reset.PURPOSE,0,uuid.uuid4()),
                (reset.digest_authorization(cap.opaque),a,None,reset.PURPOSE,0,uuid.uuid4()),
                (reset.digest_authorization(cap.opaque),a,reset.KIND_RECOVERY,None,0,uuid.uuid4()),
                (reset.digest_authorization(cap.opaque),a,reset.KIND_RECOVERY,reset.PURPOSE,None,uuid.uuid4()),
                (reset.digest_authorization(cap.opaque),a,reset.KIND_RECOVERY,reset.PURPOSE,0,None),
                ("malformed",a,reset.KIND_RECOVERY,reset.PURPOSE,0,uuid.uuid4())
            ):
                with self.assertRaises(psycopg.Error):
                    with c.transaction():
                        c.execute("SELECT auth_l1.execute_reset_c1(%s,%s,%s,%s,%s,%s)",args)
        self.assertEqual((states(a)[0]["session_epoch"],states(b)[0]["session_epoch"]),(0,0))
        self.assertIsNone(states(a,cap)[3]["consumed_at"])
        self.assertEqual(states(a)[2],[])
        run(cap)
        self.assertEqual(states(a)[0]["session_epoch"],1)

    def test_CR07_expiration_checked_after_actual_owner_lock_wait(self):
        oid=owner()["owner_id"]; cap=mint(oid,delta=3)
        name="cr07_"+uuid.uuid4().hex[:8]
        def worker():
            with reset_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                c.execute("SET statement_timeout='10000ms'")
                try:
                    with c.transaction(): commit(c,cap)
                    return "unexpected"
                except psycopg.Error: return "expired"
        with ThreadPoolExecutor(max_workers=1) as ex:
            with db("MIG") as lock_holder:
                with lock_holder.transaction():
                    lock_holder.execute("SELECT 1 FROM auth_l1.owners WHERE owner_id=%s FOR UPDATE",(oid,))
                    f=ex.submit(worker)
                    observed_wait([name])
                    self.assertFalse(f.done())
                    # Only waiting for expiry; the *race* is proven by pg_stat_activity Lock.
                    time.sleep(3.6)
                self.assertEqual(f.result(timeout=12),"expired")
        self.assertEqual(states(oid)[0]["session_epoch"],0)
        self.assertEqual(states(oid)[2],[])
        self.assertIsNone(states(oid,cap)[3]["consumed_at"])

    def test_CR08_admission_before_C1_holds_lock_then_reset_wins(self):
        oid=owner()["owner_id"]; sess=issue(oid); cap=mint(oid)
        name="cr08_"+uuid.uuid4().hex[:8]
        def reset_worker():
            with reset_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                c.execute("SET statement_timeout='10000ms'")
                return run_on_connection(c,cap)
        with ThreadPoolExecutor(max_workers=1) as ex:
            with db("SESSION") as admitted:
                with admitted.transaction():
                    self.assertTrue(auth.admit_session_fenced(admitted,sess.opaque,oid,0,0))
                    f=ex.submit(reset_worker)
                    observed_wait([name])
                    self.assertFalse(f.done())
                self.assertEqual(f.result(timeout=12)["revoked_epoch"],1)
        with db("SESSION") as c:
            with c.transaction(): self.assertFalse(auth.admit_session_fenced(c,sess.opaque,oid,0,0))

    def test_CR09_rotation_revoke_and_new_admission_races_obey_owner_order(self):
        for action in ("rotate","revoke_one","revoke_all","issue"):
            with self.subTest(action=action):
                oid=owner()["owner_id"]; sess=issue(oid); cap=mint(oid)
                name="cr09_"+action+"_"+uuid.uuid4().hex[:6]
                def worker():
                    role="REVOKER" if action=="revoke_all" else "SESSION"
                    with db(role) as c:
                        c.execute("SELECT set_config('application_name',%s,false)",(name,))
                        c.execute("SET statement_timeout='10000ms'")
                        try:
                            if action=="rotate": auth.rotate(c,sess.opaque,0,0)
                            elif action=="revoke_one": return auth.revoke_one(c,sess.opaque,0)
                            elif action=="revoke_all": auth.revoke_all(c,oid,0)
                            else: auth.issue(c,oid,0,idle_seconds=30,absolute_seconds=100)
                            return "unexpected"
                        except psycopg.Error: return "denied"
                with ThreadPoolExecutor(max_workers=1) as ex:
                    with reset_db() as c:
                        with c.transaction():
                            commit(c,cap)
                            f=ex.submit(worker)
                            observed_wait([name])
                        result=f.result(timeout=12)
                        self.assertIn(result,("denied",False))
                self.assertEqual(states(oid)[0]["session_epoch"],1)

    def test_CR10_roles_rls_definer_no_self_issue_or_table_access(self):
        oid=owner()["owner_id"]; cap=mint(oid)
        for role in ("EXEC","ISSUER"):
            with reset_db(role) as c:
                attrs=c.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user").fetchone()
                self.assertFalse(any(attrs.values()))
                for sql in (
                    "SELECT * FROM auth_l1.reset_c1_authorizations",
                    "SELECT * FROM auth_l1.reset_c1_operations",
                    "SELECT * FROM auth_l1.sessions",
                    "SELECT * FROM history_l1.conversations",
                    "CREATE TABLE auth_l1.illicit_reset(x integer)",
                    "SELECT auth_l1.finish_simulated_reauth('no_owner',0)"
                ):
                    with self.assertRaises(InsufficientPrivilege):
                        with c.transaction(): c.execute(sql)
        with reset_db("EXEC") as c:
            with self.assertRaises(InsufficientPrivilege):
                with c.transaction():
                    c.execute("SELECT auth_l1.issue_reset_c1_authorization(%s,%s,%s,%s,%s,%s,%s,%s)",
                              (reset.digest_authorization(cap.opaque),oid,cap.kind,reset.PURPOSE,0,clock_epoch(),None,None))
        with reset_db("ISSUER") as c:
            with self.assertRaises(InsufficientPrivilege):
                with c.transaction():
                    c.execute("SELECT auth_l1.execute_reset_c1(%s,%s,%s,%s,%s,%s)",
                              (reset.digest_authorization(cap.opaque),oid,cap.kind,reset.PURPOSE,0,uuid.uuid4()))
        with db("MIG") as c:
            for name in ("reset_c1_authorizations","reset_c1_operations"):
                x=c.execute("""SELECT relrowsecurity,relforcerowsecurity FROM pg_class
                  WHERE oid=(%s)::regclass""",("auth_l1."+name,)).fetchone()
                self.assertTrue(all(x.values()))
            funcs=c.execute("""SELECT proname,prosecdef,proconfig FROM pg_proc
              WHERE pronamespace='auth_l1'::regnamespace AND proname IN
              ('issue_reset_c1_authorization','execute_reset_c1','block_c1_gate_open')""").fetchall()
            self.assertEqual(len(funcs),3)
            self.assertTrue(all(x["prosecdef"] and "search_path=pg_catalog" in x["proconfig"] for x in funcs))
        run(cap)
        with db("REAUTH") as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_C1_GATE_STAYS_CLOSED"):
                auth.finish_simulated_reauth(c,oid,1)
        self.assertEqual(states(oid)[0]["reset_gate"],"pending_reauth")

    def test_CR11_authenticated_kind_binds_exact_session_digest_generation(self):
        oid=owner()["owner_id"]; s=issue(oid)
        wrong=mint(oid,kind=reset.KIND_AUTHENTICATED,
                   session="f"*64,gen=0)
        with reset_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_C1_SESSION_DENIED"):
                with c.transaction(): commit(c,wrong)
        self.assertEqual(states(oid)[0]["session_epoch"],0)
        self.assertIsNone(states(oid,wrong)[3]["consumed_at"])
        good=mint(oid,kind=reset.KIND_AUTHENTICATED,session=digest(s.opaque),gen=0)
        run(good)
        self.assertEqual(states(oid)[0]["reset_gate"],"pending_reauth")

    def test_CR12_duplicate_operation_id_rolls_back_second_owner(self):
        a=owner()["owner_id"]; b=owner()["owner_id"]
        first=mint(a); second=mint(b); op=uuid.uuid4()
        run(first,op=op)
        with reset_db() as c:
            with self.assertRaises(UniqueViolation):
                with c.transaction(): commit(c,second,op=op)
        self.assertEqual(states(b)[0]["session_epoch"],0)
        self.assertEqual(states(b)[2],[])
        self.assertIsNone(states(b,second)[3]["consumed_at"])
        run(second)
        self.assertEqual(states(b)[0]["session_epoch"],1)

def run_on_connection(c,cap):
    with c.transaction(): return commit(c,cap)


# CR13–CR17: real migration-file concurrency regression, disposable CI only.
import subprocess
import threading
from psycopg.conninfo import make_conninfo

RACE_DB_NAMES={
 "reset_c1_issue_commit_ci","reset_c1_issue_abort_ci",
 "reset_c1_exec_commit_ci","reset_c1_exec_abort_ci",
 "reset_c1_down_first_ci",
}
REAL_DOWN=ROOT/"infra/postgres/migrations/006_atomic_reset_c1.down.sql"

def scoped_race_db(database,role="MIG"):
    if os.environ.get("CI")!="true" or database not in RACE_DB_NAMES:
        raise RuntimeError("CR_DISPOSABLE_CI_ONLY")
    key,user={
        "MIG":("AUTH_MIG_DSN","auth_migrator"),
        "ISSUER":("AUTH_RESET_ISSUER_DSN","auth_reset_issuer"),
        "EXEC":("AUTH_RESET_EXEC_DSN","auth_reset_executor"),
    }[role]
    dsn=os.environ[key]; v=conninfo_to_dict(dsn)
    if not(v.get("host")=="127.0.0.1" and v.get("port")=="5432"
           and v.get("dbname")=="history_ci" and v.get("user")==user
           and set(v).issubset({"host","port","dbname","user","password","connect_timeout"})):
        raise RuntimeError("UNSAFE_CR_RACE_TARGET")
    return psycopg.connect(make_conninfo(dsn,dbname=database),
                           autocommit=True,row_factory=dict_row)

def seed_race_owner(database,with_session=False):
    oid="synthetic_cr_race_"+uuid.uuid4().hex
    with scoped_race_db(database) as c:
        c.execute("INSERT INTO auth_l1.owners(owner_id) VALUES(%s)",(oid,))
        if with_session:
            c.execute("""WITH ts AS (SELECT clock_timestamp() AS t)
                INSERT INTO auth_l1.sessions
                (digest_sha256,owner_id,session_epoch,generation,status,
                 created_at,last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)
                SELECT %s,%s,0,0,'active',ts.t,ts.t,
                  ts.t+interval '10 minutes',ts.t+interval '1 hour',600 FROM ts""",
                ("f"*64,oid))
    return oid

def mint_race(c,oid):
    expiry=c.execute("SELECT floor(extract(epoch from clock_timestamp()))::bigint+120 AS exp").fetchone()["exp"]
    return reset.issue_synthetic_verified_authorization(
        c,oid,reset.KIND_RECOVERY,0,expiry)

def migration_env(database,app):
    if os.environ.get("CI")!="true" or database not in RACE_DB_NAMES:
        raise RuntimeError("CR_DISPOSABLE_CI_ONLY")
    env=dict(os.environ)
    env.update(PGHOST="127.0.0.1",PGPORT="5432",PGUSER="auth_migrator",
               PGPASSWORD="synthetic_auth_migrator_only",PGDATABASE=database,
               PGAPPNAME=app)
    return env

def start_real_down(database,app):
    # Runs the actual repository file with psql's single transaction mode.
    return subprocess.Popen(
        ["psql","-X","-1","-v","ON_ERROR_STOP=1","-d",database,"-f",str(REAL_DOWN)],
        env=migration_env(database,app),stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,text=True)

def await_real_down(proc,success):
    try: out,err=proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.communicate(timeout=5)
        raise AssertionError("006_DOWN_STALLED")
    if success:
        if proc.returncode!=0: raise AssertionError("expected empty rollback success: "+err[-900:])
    else:
        if proc.returncode==0 or "RESET_C1_ROLLBACK_REFUSED_EVIDENCE_EXISTS" not in err:
            raise AssertionError("committed reset evidence not protected: "+err[-900:])

def race_state(database,oid):
    with scoped_race_db(database) as c:
        o=c.execute("SELECT session_epoch,reset_gate FROM auth_l1.owners WHERE owner_id=%s",(oid,)).fetchone()
        has_auth=c.execute("SELECT to_regclass('auth_l1.reset_c1_authorizations') IS NOT NULL AS ok").fetchone()["ok"]
        has_ops=c.execute("SELECT to_regclass('auth_l1.reset_c1_operations') IS NOT NULL AS ok").fetchone()["ok"]
        trigger=c.execute("""SELECT count(*) AS n FROM pg_trigger WHERE
            tgrelid='auth_l1.owners'::regclass AND tgname='block_c1_gate_open_trg'""").fetchone()["n"]
        au=c.execute("SELECT count(*) AS n FROM auth_l1.reset_c1_authorizations").fetchone()["n"] if has_auth else None
        op=c.execute("SELECT count(*) AS n FROM auth_l1.reset_c1_operations").fetchone()["n"] if has_ops else None
        sessions=c.execute("SELECT status,count(*) AS n FROM auth_l1.sessions WHERE owner_id=%s GROUP BY status",(oid,)).fetchall()
        return (o["session_epoch"],o["reset_gate"],has_auth,has_ops,trigger,au,op,
                {r["status"]:r["n"] for r in sessions})

class C1RollbackTOCTOU(unittest.TestCase):
    def held_writer_vs_real_down(self,database,kind,decision,with_session=False):
        oid=seed_race_owner(database,with_session)
        if kind=="execute":
            with scoped_race_db(database,"ISSUER") as issuer:
                cap=mint_race(issuer,oid)
        else: cap=None
        ready=threading.Event(); release=threading.Event()
        app="cr_down_wait_"+uuid.uuid4().hex[:10]
        def writer():
            nonlocal cap
            with scoped_race_db(database,"ISSUER" if kind=="issue" else "EXEC") as c:
                try:
                    with c.transaction():
                        if kind=="issue": cap=mint_race(c,oid)
                        else:
                            result=reset.commit_c1(c,cap.opaque,owner_id=oid,
                                kind=cap.kind,expected_epoch=0)
                            assert result["status"]=="REVOKED_PENDING_IDP"
                        ready.set()
                        if not release.wait(12): raise AssertionError("writer Event timeout")
                        if decision=="rollback": raise InjectedAbort()
                    return "committed"
                except InjectedAbort:
                    return "rolledback"
                finally: ready.set()
        with ThreadPoolExecutor(max_workers=1) as pool:
            w=pool.submit(writer); down=None
            try:
                self.assertTrue(ready.wait(10))
                self.assertFalse(w.done())
                down=start_real_down(database,app)
                # Verifiable distinct PostgreSQL connection waiting for Owner table.
                observed_wait([app])
                self.assertIsNone(down.poll())
            finally:
                release.set()
            self.assertEqual(w.result(timeout=15),
                             "rolledback" if decision=="rollback" else "committed")
            try:
                await_real_down(down,success=(kind=="issue" and decision=="rollback"))
            finally:
                if down is not None and down.poll() is None:
                    down.kill(); down.communicate(timeout=5)
        return race_state(database,oid)

    def test_CR13_issuer_commit_wins_and_real_down_preserves_authority(self):
        s=self.held_writer_vs_real_down("reset_c1_issue_commit_ci","issue","commit")
        self.assertEqual(s[:2],(0,"open"))
        self.assertEqual(s[2:7],(True,True,1,1,0))

    def test_CR14_issuer_rollback_then_real_down_succeeds_without_evidence(self):
        s=self.held_writer_vs_real_down("reset_c1_issue_abort_ci","issue","rollback")
        self.assertEqual(s[:2],(0,"open"))
        self.assertEqual(s[2:7],(False,False,0,None,None))

    def test_CR15_c1_commit_wins_and_real_down_preserves_gate_ledger_sessions(self):
        s=self.held_writer_vs_real_down("reset_c1_exec_commit_ci","execute","commit",True)
        self.assertEqual(s[:2],(1,"pending_reauth"))
        self.assertEqual(s[2:7],(True,True,1,1,1))
        self.assertEqual(s[7],{"revoked":1})

    def test_CR16_c1_rollback_then_down_refuses_previously_committed_authority(self):
        s=self.held_writer_vs_real_down("reset_c1_exec_abort_ci","execute","rollback",True)
        self.assertEqual(s[:2],(0,"open"))
        self.assertEqual(s[2:7],(True,True,1,1,0))
        self.assertEqual(s[7],{"active":1})

    def test_CR17_real_down_wins_before_new_issuer_and_c1_attempt(self):
        database="reset_c1_down_first_ci"
        oid=seed_race_owner(database)
        app="cr_down_first_"+uuid.uuid4().hex[:9]
        issuer_app="cr_issuer_wait_"+uuid.uuid4().hex[:9]
        marker="CR_DOWN_LOCKS_HELD_"+uuid.uuid4().hex
        p=subprocess.Popen(
            ["psql","-X","-q","-A","-t","-v","ON_ERROR_STOP=1","-d",database],
            env=migration_env(database,app),stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        held=threading.Event()
        def reader():
            for line in p.stdout:
                if marker in line: held.set()
        thread=threading.Thread(target=reader,daemon=True)
        thread.start()
        try:
            # \i executes the exact real migration file in this open BEGIN.
            # SELECT marker is an Event barrier AFTER all DDL, BEFORE COMMIT.
            p.stdin.write("BEGIN;\n\\i "+str(REAL_DOWN)+"\nSELECT '"+marker+"';\n")
            p.stdin.flush()
            self.assertTrue(held.wait(12),"migration file did not reach held-lock barrier")
            self.assertIsNone(p.poll())
            def issuer():
                with scoped_race_db(database,"ISSUER") as c:
                    c.execute("SELECT set_config('application_name',%s,false)",(issuer_app,))
                    try:
                        mint_race(c,oid)
                        return "unexpected"
                    except psycopg.Error: return "denied"
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending=pool.submit(issuer)
                observed_wait([issuer_app])
                self.assertFalse(pending.done())
                p.stdin.write("COMMIT;\n\\q\n")
                p.stdin.flush()
                self.assertEqual(p.wait(timeout=15),0)
                self.assertEqual(pending.result(timeout=15),"denied")
            with scoped_race_db(database,"EXEC") as c:
                with self.assertRaises(psycopg.Error):
                    with c.transaction():
                        reset.commit_c1(c,"synthetic_not_issued_"+"x"*40,
                            owner_id=oid,kind=reset.KIND_RECOVERY,expected_epoch=0)
            s=race_state(database,oid)
            self.assertEqual(s[:2],(0,"open"))
            self.assertEqual(s[2:7],(False,False,0,None,None))
        finally:
            if p.poll() is None:
                try:
                    p.stdin.write("ROLLBACK;\n\\q\n")
                    p.stdin.flush()
                    p.wait(timeout=5)
                except (BrokenPipeError,subprocess.TimeoutExpired):
                    p.kill(); p.wait(timeout=5)
            p.stdin.close()
            thread.join(timeout=2)
            p.stderr.close()
