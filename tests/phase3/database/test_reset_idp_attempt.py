"""CR-DB-01C durable IdP attempt/outcome on real disposable PG17.11 only.

No HTTP, IdP, real Recovery, credential changes, C2, retries, or live users.
All new checks use actual 008 migrations on isolated synthetic PostgreSQL.
"""
import os
import unittest
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InsufficientPrivilege, UniqueViolation
from psycopg.rows import dict_row

from src.phase3.storage.postgres import reset_idp_attempt as idp
from src.phase3.storage.postgres import reset_c1
from test_auth_session import db, owner, observed_wait
from test_reset_c1 import mint, reset_db, commit, run, states
from test_reset_identity_lookup import lookup_db


def recorder_db():
    if os.getenv("CI")!="true":
        raise RuntimeError("CR_IDP_DISPOSABLE_CI_ONLY")
    dsn=os.environ["AUTH_RESET_IDP_DSN"]
    p=conninfo_to_dict(dsn)
    if not(p.get("host")=="127.0.0.1" and p.get("port")=="5432"
           and p.get("dbname")=="history_ci" and p.get("user")=="auth_reset_idp_recorder"
           and set(p).issubset({"host","port","dbname","user","password","connect_timeout"})):
        raise RuntimeError("CR_IDP_UNSAFE_DB_TARGET")
    return psycopg.connect(dsn,autocommit=True,row_factory=dict_row)


def start_c1():
    oid=owner()["owner_id"]
    cap=mint(oid)
    operation=uuid.uuid4()
    result=run(cap,op=operation)
    assert result["revoked_epoch"]==1 and result["status"]=="REVOKED_PENDING_IDP"
    return oid,cap,operation


def claim(conn,oid,cap,operation,attempt=None,epoch=1,kind=None):
    return idp.record_attempt(conn,cap.opaque,owner_id=oid,
        kind=cap.kind if kind is None else kind,revoked_epoch=epoch,
        operation_id=operation,attempt_id=attempt)


def outcome(conn,oid,cap,operation,attempt,status,code,epoch=1):
    return idp.record_outcome(conn,cap.opaque,owner_id=oid,kind=cap.kind,
        revoked_epoch=epoch,operation_id=operation,attempt_id=attempt,
        outcome=status,code=code)


def record(oid,cap,operation,attempt=None):
    with recorder_db() as c:
        with c.transaction():
            return claim(c,oid,cap,operation,attempt)


def data(oid):
    with db("MIG") as c:
        return c.execute("""SELECT attempt_id,operation_id,owner_id,
           authorization_sha256,kind,purpose,revoked_epoch,recorded_at,
           outcome,outcome_code,finalized_at
           FROM auth_l1.reset_idp_attempts WHERE owner_id=%s
           ORDER BY recorded_at""",(oid,)).fetchall()


def state(oid):
    return states(oid)[0]


class InjectedRollback(Exception): pass


class DurableIdpAttempt(unittest.TestCase):
    def test_IDP01_uncommitted_c1_and_nonexistent_op_denied_without_waiting(self):
        oid=owner()["owner_id"]; cap=mint(oid); op=uuid.uuid4()
        with recorder_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_ATTEMPT_DENIED"):
                with c.transaction(): claim(c,oid,cap,op)
        with reset_db() as executor:
            with executor.transaction():
                receipt=commit(executor,cap,op=op)
                self.assertEqual(receipt["revoked_epoch"],1)
                # The independent recorder must NOT wait for an uncommitted C1
                # then turn a pre-commit request into a successful claim.
                with ThreadPoolExecutor(max_workers=1) as pool:
                    def before_commit():
                        with recorder_db() as c:
                            with c.transaction():
                                with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_ATTEMPT_DENIED"):
                                    claim(c,oid,cap,op)
                        return "denied"
                    self.assertEqual(pool.submit(before_commit).result(timeout=5),"denied")
                self.assertEqual(data(oid),[])
        self.assertEqual(len(data(oid)),0)
        self.assertEqual(record(oid,cap,op)["status"],idp.NO_OUTCOME_RECORDED)
        self.assertEqual(len(data(oid)),1)

    def test_IDP02_scope_owner_epoch_kind_digest_operation_invalid(self):
        oid,cap,op=start_c1()
        another=owner()["owner_id"]
        invalid=[
            (oid,cap,uuid.uuid4(),1,cap.kind),
            (another,cap,op,1,cap.kind),
            (oid,cap,op,0,cap.kind),
            (oid,cap,op,2,cap.kind),
            (oid,cap,op,1,reset_c1.KIND_AUTHENTICATED),
        ]
        with recorder_db() as c:
            for o,proof,operation,epoch,kind in invalid:
                with self.subTest(owner=o,epoch=epoch,kind=kind,op=operation):
                    with self.assertRaises(psycopg.Error):
                        with c.transaction(): claim(c,o,proof,operation,epoch=epoch,kind=kind)
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_ATTEMPT_DENIED"):
                with c.transaction():
                    c.execute("SELECT auth_l1.record_reset_idp_attempt(%s,%s,%s,%s,%s,%s,%s)",
                        (reset_c1.digest_authorization(cap.opaque),oid,cap.kind,
                         "WRONG_PURPOSE",1,op,uuid.uuid4()))
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_ATTEMPT_DENIED"):
                with c.transaction():
                    c.execute("SELECT auth_l1.record_reset_idp_attempt(%s,%s,%s,%s,%s,%s,%s)",
                        (None,oid,cap.kind,reset_c1.PURPOSE,1,op,uuid.uuid4()))
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_ATTEMPT_DENIED"):
                with c.transaction():
                    c.execute("SELECT auth_l1.record_reset_idp_attempt(%s,%s,%s,%s,%s,%s,%s)",
                        ("b"*64,oid,cap.kind,reset_c1.PURPOSE,1,op,uuid.uuid4()))
        self.assertEqual(data(oid),[])

    def test_IDP03_one_committed_attempt_per_operation_and_no_gate_open(self):
        oid,cap,op=start_c1()
        first=uuid.uuid4()
        result=record(oid,cap,op,first)
        self.assertEqual(result,{"attempt_id":str(first),"operation_id":str(op),
                                 "status":idp.NO_OUTCOME_RECORDED})
        with recorder_db() as c:
            for attempt in (first,uuid.uuid4()):
                with self.assertRaises(UniqueViolation):
                    with c.transaction(): claim(c,oid,cap,op,attempt)
        rows=data(oid)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["attempt_id"],first)
        self.assertEqual(rows[0]["operation_id"],op)
        self.assertIsNone(rows[0]["outcome"])
        self.assertIsNone(rows[0]["finalized_at"])
        o=state(oid)
        self.assertEqual((o["session_epoch"],o["reset_gate"]),(1,"pending_reauth"))

    def test_IDP04_two_independent_connections_unique_wait_commit_one_wins(self):
        oid,cap,op=start_c1()
        first=uuid.uuid4(); second=uuid.uuid4()
        ready=threading.Event(); release=threading.Event()
        app="cr_idp_contend_"+uuid.uuid4().hex[:12]
        def first_worker():
            with recorder_db() as c:
                with c.transaction():
                    claim(c,oid,cap,op,first)
                    ready.set()
                    self.assertTrue(release.wait(10))
            return "committed"
        def second_worker():
            with recorder_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(app,))
                with c.transaction():
                    claim(c,oid,cap,op,second)
            return "unexpected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1=pool.submit(first_worker)
            self.assertTrue(ready.wait(8))
            f2=pool.submit(second_worker)
            try:
                observed_wait([app])
                self.assertFalse(f2.done())
            finally:
                release.set()
            self.assertEqual(f1.result(timeout=10),"committed")
            with self.assertRaises(UniqueViolation): f2.result(timeout=10)
        self.assertEqual([x["attempt_id"] for x in data(oid)],[first])
        self.assertEqual(state(oid)["reset_gate"],"pending_reauth")

    def test_IDP05_rollback_attempt_allows_later_claim_if_no_committed_evidence(self):
        oid,cap,op=start_c1()
        first=uuid.uuid4()
        with recorder_db() as c:
            with self.assertRaises(InjectedRollback):
                with c.transaction():
                    claim(c,oid,cap,op,first)
                    raise InjectedRollback()
        self.assertEqual(data(oid),[])
        second=uuid.uuid4()
        self.assertEqual(record(oid,cap,op,second)["attempt_id"],str(second))
        self.assertEqual([r["attempt_id"] for r in data(oid)],[second])

    def test_IDP06_rollback_holder_unique_waiter_commits_its_only_attempt(self):
        oid,cap,op=start_c1()
        a=uuid.uuid4(); b=uuid.uuid4()
        ready=threading.Event(); release=threading.Event()
        app="cr_idp_wait_rb_"+uuid.uuid4().hex[:9]
        def holder():
            with recorder_db() as c:
                try:
                    with c.transaction():
                        claim(c,oid,cap,op,a)
                        ready.set()
                        if not release.wait(10): raise AssertionError("holder release timeout")
                        raise InjectedRollback()
                except InjectedRollback:
                    return "rolledback"
        def waiter():
            with recorder_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(app,))
                with c.transaction(): claim(c,oid,cap,op,b)
            return "committed"
        with ThreadPoolExecutor(max_workers=2) as pool:
            w1=pool.submit(holder)
            self.assertTrue(ready.wait(8))
            w2=pool.submit(waiter)
            try:
                observed_wait([app])
            finally:
                release.set()
            self.assertEqual(w1.result(timeout=10),"rolledback")
            self.assertEqual(w2.result(timeout=10),"committed")
        self.assertEqual([r["attempt_id"] for r in data(oid)],[b])

    def test_IDP07_commit_then_close_connection_persists_attempt_without_outcome(self):
        oid,cap,op=start_c1()
        with recorder_db() as c:
            with c.transaction():
                result=claim(c,oid,cap,op)
                attempt=uuid.UUID(result["attempt_id"])
        # First connection is closed; a fresh independent connection sees record.
        with recorder_db() as fresh:
            with self.assertRaises(UniqueViolation):
                with fresh.transaction(): claim(fresh,oid,cap,op,uuid.uuid4())
        row=data(oid)[0]
        self.assertEqual(row["attempt_id"],attempt)
        self.assertEqual(row["authorization_sha256"],reset_c1.digest_authorization(cap.opaque))
        self.assertIsNotNone(row["recorded_at"])
        self.assertIsNone(row["outcome"])
        self.assertIsNone(row["outcome_code"])
        self.assertIsNone(row["finalized_at"])

    def test_IDP08_three_distinct_outcomes_and_limited_codes(self):
        cases=[
            (idp.OBSERVED_REMOTE_SUCCESS,"REMOTE_2XX_OBSERVED"),
            (idp.DEFINITIVE_REJECTION,"POLICY_REJECTED"),
            (idp.DEFINITIVE_REJECTION,"ACCOUNT_REJECTED"),
            (idp.UNKNOWN,"TIMEOUT"),
            (idp.UNKNOWN,"DISCONNECT"),
            (idp.UNKNOWN,"REMOTE_5XX"),
            (idp.UNKNOWN,"UNVERIFIABLE"),
            (idp.UNKNOWN,"OTHER_UNKNOWN"),
        ]
        for status,code in cases:
            with self.subTest(status=status,code=code):
                oid,cap,op=start_c1()
                receipt=record(oid,cap,op)
                aid=uuid.UUID(receipt["attempt_id"])
                with recorder_db() as c:
                    with c.transaction():
                        saved=outcome(c,oid,cap,op,aid,status,code)
                self.assertEqual(saved,{"attempt_id":str(aid),"outcome":status,"code":code})
                row=data(oid)[0]
                self.assertEqual((row["outcome"],row["outcome_code"]),(status,code))
                self.assertIsNotNone(row["finalized_at"])
                self.assertEqual(state(oid)["reset_gate"],"pending_reauth")

    def test_IDP09_attempt_id_owner_op_digest_epoch_mismatch_rejected(self):
        oid,cap,op=start_c1()
        other,other_cap,other_op=start_c1()
        attempt=uuid.UUID(record(oid,cap,op)["attempt_id"])
        with recorder_db() as c:
            cases=[
                (oid,cap,op,uuid.uuid4(),1),
                (oid,cap,uuid.uuid4(),attempt,1),
                (other,cap,op,attempt,1),
                (oid,other_cap,op,attempt,1),
                (oid,cap,op,attempt,2),
            ]
            for the_owner,proof,operation,attempt_id,epoch in cases:
                with self.subTest(owner=the_owner,epoch=epoch):
                    with self.assertRaises(psycopg.Error):
                        with c.transaction():
                            outcome(c,the_owner,proof,operation,attempt_id,idp.UNKNOWN,"TIMEOUT",epoch)
        self.assertIsNone(data(oid)[0]["outcome"])
        self.assertEqual(len(data(other)),0)

    def test_IDP10_repeated_conflicting_late_outcome_cannot_rewrite(self):
        oid,cap,op=start_c1(); aid=uuid.UUID(record(oid,cap,op)["attempt_id"])
        with recorder_db() as c:
            with c.transaction():
                outcome(c,oid,cap,op,aid,idp.UNKNOWN,"DISCONNECT")
        initial=data(oid)[0]
        for status,code in (
            (idp.UNKNOWN,"DISCONNECT"),
            (idp.OBSERVED_REMOTE_SUCCESS,"REMOTE_2XX_OBSERVED"),
            (idp.DEFINITIVE_REJECTION,"ACCOUNT_REJECTED")
        ):
            with recorder_db() as c:
                with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_OUTCOME_ALREADY_FINAL_OR_INVALID"):
                    with c.transaction(): outcome(c,oid,cap,op,aid,status,code)
        later=data(oid)[0]
        self.assertEqual((later["outcome"],later["outcome_code"],later["finalized_at"]),
                         (initial["outcome"],initial["outcome_code"],initial["finalized_at"]))
        self.assertEqual(state(oid)["reset_gate"],"pending_reauth")

    def test_IDP11_concurrent_outcomes_exactly_one_cas_winner(self):
        oid,cap,op=start_c1(); aid=uuid.UUID(record(oid,cap,op)["attempt_id"])
        ready=threading.Event(); release=threading.Event()
        app="cr_idp_out_wait_"+uuid.uuid4().hex[:8]
        def holder():
            with recorder_db() as c:
                with c.transaction():
                    outcome(c,oid,cap,op,aid,idp.UNKNOWN,"TIMEOUT")
                    ready.set()
                    self.assertTrue(release.wait(12))
        def waiter():
            with recorder_db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(app,))
                with c.transaction():
                    outcome(c,oid,cap,op,aid,idp.OBSERVED_REMOTE_SUCCESS,"REMOTE_2XX_OBSERVED")
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1=pool.submit(holder)
            self.assertTrue(ready.wait(8))
            f2=pool.submit(waiter)
            try:
                observed_wait([app])
                self.assertFalse(f2.done())
            finally: release.set()
            f1.result(timeout=10)
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_OUTCOME_ALREADY_FINAL_OR_INVALID"):
                f2.result(timeout=10)
        self.assertEqual((data(oid)[0]["outcome"],data(oid)[0]["outcome_code"]),
                         (idp.UNKNOWN,"TIMEOUT"))

    def test_IDP12_invalid_codes_arbitrary_text_null_and_preclaim_result_denied(self):
        oid,cap,op=start_c1(); aid=uuid.uuid4()
        with recorder_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_OUTCOME_DENIED"):
                with c.transaction():
                    outcome(c,oid,cap,op,aid,idp.UNKNOWN,"TIMEOUT")
        record(oid,cap,op,aid)
        with recorder_db() as c:
            for status,code in (
                (idp.UNKNOWN,"REMOTE_2XX_OBSERVED"),
                (idp.OBSERVED_REMOTE_SUCCESS,"TIMEOUT"),
                (idp.DEFINITIVE_REJECTION,"HTTP_500"),
                ("PASSWORD_CHANGED","REMOTE_2XX_OBSERVED"),
                (idp.UNKNOWN,"raw HTTP 500\npassword=secret"),
                (None,None),
            ):
                with self.subTest(status=status,code=code):
                    with self.assertRaises(ValueError):
                        with c.transaction():
                            outcome(c,oid,cap,op,aid,status,code)
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_OUTCOME_DENIED"):
                with c.transaction():
                    c.execute("SELECT auth_l1.record_reset_idp_outcome(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (reset_c1.digest_authorization(cap.opaque),oid,cap.kind,
                         reset_c1.PURPOSE,1,op,aid,None,None))
        self.assertIsNone(data(oid)[0]["outcome"])

    def test_IDP13_no_outcome_is_unknown_no_second_attempt_or_gate_reopen(self):
        oid,cap,op=start_c1(); aid=uuid.UUID(record(oid,cap,op)["attempt_id"])
        self.assertIsNone(data(oid)[0]["outcome"])
        self.assertEqual(state(oid)["reset_gate"],"pending_reauth")
        with recorder_db() as c:
            with self.assertRaises(UniqueViolation):
                with c.transaction(): claim(c,oid,cap,op,uuid.uuid4())
        with db("REAUTH") as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_C1_GATE_STAYS_CLOSED"):
                with c.transaction():
                    c.execute("SELECT auth_l1.finish_simulated_reauth(%s,%s)",(oid,1))
        with recorder_db() as c:
            with c.transaction(): outcome(c,oid,cap,op,aid,idp.UNKNOWN,"UNVERIFIABLE")
            with self.assertRaises(UniqueViolation):
                with c.transaction(): claim(c,oid,cap,op,uuid.uuid4())
        self.assertEqual(data(oid)[0]["outcome"],idp.UNKNOWN)
        self.assertEqual(state(oid)["reset_gate"],"pending_reauth")

    def test_IDP14_lookup_and_previous_roles_not_escalated(self):
        oid,cap,op=start_c1(); key=reset_c1.digest_authorization(cap.opaque)
        signature_attempt="auth_l1.record_reset_idp_attempt(text,text,text,text,bigint,uuid,uuid)"
        signature_outcome="auth_l1.record_reset_idp_outcome(text,text,text,text,bigint,uuid,uuid,text,text)"
        with recorder_db() as c:
            flags=c.execute("""SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,
              rolinherit FROM pg_roles WHERE rolname=current_user""").fetchone()
            self.assertFalse(any(flags.values()))
            queries=[
                "SELECT * FROM auth_l1.reset_idp_attempts",
                "SELECT * FROM auth_l1.reset_c1_operations",
                "SELECT * FROM auth_l1.reset_c1_authorizations",
                "SELECT * FROM auth_l1.owners",
                "SELECT * FROM auth_l1.sessions",
                "SELECT * FROM auth_l1.identity_links",
                "SELECT * FROM history_l1.conversations",
                "CREATE TABLE auth_l1.idp_illicit(x int)",
                "SELECT auth_l1.execute_reset_c1(repeat('a',64),'fake','RECOVERY','CONTROLLED_RESET_C1',0,'00000000-0000-4000-8000-000000000001'::uuid)",
                "SELECT auth_l1.issue_reset_c1_authorization(repeat('a',64),'fake','RECOVERY','CONTROLLED_RESET_C1',0,42,NULL,NULL)",
                "SELECT auth_l1.resolve_reset_identity(repeat('a',64),'fake','RECOVERY','CONTROLLED_RESET_C1',0,'fake')",
                "SELECT auth_l1.revoke_all('fake',0)",
                "SELECT auth_l1.finish_simulated_reauth('fake',1)",
            ]
            for query in queries:
                with self.subTest(query=query[:55]):
                    with self.assertRaises(InsufficientPrivilege):
                        with c.transaction(): c.execute(query)
        for other_role in ("MAP","SESSION","REVOKER","REAUTH"):
            with db(other_role) as c:
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction():
                        c.execute("SELECT auth_l1.record_reset_idp_attempt(%s,%s,%s,%s,%s,%s,%s)",
                                  (key,oid,cap.kind,reset_c1.PURPOSE,1,op,uuid.uuid4()))
        for other in (lookup_db,lambda: reset_db("ISSUER"),lambda: reset_db("EXEC")):
            with other() as c:
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction():
                        c.execute("SELECT auth_l1.record_reset_idp_attempt(%s,%s,%s,%s,%s,%s,%s)",
                                  (key,oid,cap.kind,reset_c1.PURPOSE,1,op,uuid.uuid4()))
        with db("MIG") as admin:
            for sig in (signature_attempt,signature_outcome):
                row=admin.execute("SELECT prosecdef,proconfig FROM pg_proc WHERE oid=%s::regprocedure",(sig,)).fetchone()
                self.assertTrue(row["prosecdef"])
                self.assertIn("search_path=pg_catalog",row["proconfig"])
                self.assertTrue(admin.execute("SELECT has_function_privilege('auth_reset_idp_recorder',%s,'EXECUTE') AS ok",(sig,)).fetchone()["ok"])
                self.assertFalse(admin.execute("""SELECT EXISTS (
                  SELECT 1 FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) acl
                  WHERE p.oid=%s::regprocedure AND acl.grantee=0 AND acl.privilege_type='EXECUTE'
                ) AS yes""",(sig,)).fetchone()["yes"])
            self.assertFalse(admin.execute("SELECT has_table_privilege('auth_reset_idp_recorder','auth_l1.reset_idp_attempts','SELECT') AS ok").fetchone()["ok"])
            rls=admin.execute("""SELECT relrowsecurity,relforcerowsecurity FROM pg_class
               WHERE oid='auth_l1.reset_idp_attempts'::regclass""").fetchone()
            self.assertTrue(all(rls.values()))
            self.assertFalse(admin.execute("SELECT has_schema_privilege('auth_reset_idp_recorder','history_l1','USAGE') AS ok").fetchone()["ok"])

    def test_IDP15_only_allowed_identifiers_codes_and_db_times_persisted(self):
        oid,cap,op=start_c1()
        aid=uuid.UUID(record(oid,cap,op)["attempt_id"])
        with recorder_db() as c:
            with c.transaction():
                outcome(c,oid,cap,op,aid,idp.OBSERVED_REMOTE_SUCCESS,"REMOTE_2XX_OBSERVED")
        with db("MIG") as admin:
            cols={r["column_name"] for r in admin.execute("""SELECT column_name FROM information_schema.columns
                WHERE table_schema='auth_l1' AND table_name='reset_idp_attempts'""").fetchall()}
            self.assertEqual(cols,{
                "attempt_id","operation_id","owner_id","authorization_sha256",
                "kind","purpose","revoked_epoch","recorded_at","outcome",
                "outcome_code","finalized_at"
            })
            row=data(oid)[0]
            self.assertNotIn(cap.opaque,str(row))
            self.assertLessEqual(row["recorded_at"],row["finalized_at"])
            self.assertTrue({"password","cookie","token","email","response_body",
                             "request_body","raw_error","idp_url"}.isdisjoint(cols))
        self.assertEqual(state(oid)["reset_gate"],"pending_reauth")

    def test_IDP16_owner_epoch_drift_after_attempt_denies_late_outcome(self):
        oid,cap,op=start_c1()
        aid=uuid.UUID(record(oid,cap,op)["attempt_id"])
        # Fixture-only privileged epoch drift: NOT a production C2 implementation.
        with db("MIG") as c:
            c.execute("""UPDATE auth_l1.owners SET session_epoch=session_epoch+1
                WHERE owner_id=%s""",(oid,))
        with recorder_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDP_OUTCOME_DENIED"):
                with c.transaction(): outcome(c,oid,cap,op,aid,idp.UNKNOWN,"TIMEOUT")
        self.assertIsNone(data(oid)[0]["outcome"])
        self.assertEqual(state(oid)["reset_gate"],"pending_reauth")
