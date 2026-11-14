"""H1-DB: deterministic History read vs explicit session revocation (PostgreSQL).

Only on disposable loopback CI Product PostgreSQL; no HTTP, BFF proof, model,
IdP, migration edit, C2, or production grant. The existing History repository
is called ONLY after 004's exact session admission succeeds on the SAME
history_app connection and inside the SAME outer PostgreSQL transaction.
The CI-only auth_l1 function grant is undone at tearDownClass.
"""
import os
import time
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg.conninfo import conninfo_to_dict

from src.phase3.storage.postgres import auth_session, repository as history
from test_auth_session import db as auth_db, owner as make_owner, issue as issue_session, digest
from test_history_l1 import db as history_db, create_req, send_req

FENCE_SIG = "auth_l1.admit_session_fenced(text,text,bigint,integer)"
REPLAY_SIG = "auth_l1.consume_service_assertion(text,bigint)"


def _trusted_ci_scope():
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("H1_DB_DISPOSABLE_GITHUB_CI_ONLY")
    for name,role in (
        ("DB_APP_DSN","history_app"),
        ("AUTH_MIG_DSN","auth_migrator"),
        ("AUTH_SESSION_DSN","auth_sessions"),
    ):
        spec = conninfo_to_dict(os.environ[name])
        if not (
            spec.get("host")=="127.0.0.1"
            and spec.get("port")=="5432"
            and spec.get("dbname")=="history_ci"
            and spec.get("user")==role
            and set(spec).issubset(
                {"host","port","dbname","user","password","connect_timeout"})
        ):
            raise RuntimeError("H1_DB_UNSAFE_TARGET:"+name)


def _fixture():
    a = make_owner()["owner_id"]
    b = make_owner()["owner_id"]
    token_a = issue_session(a, idle=180, absolute=600)
    token_b = issue_session(b, idle=180, absolute=600)
    assert a != b
    marker = uuid.uuid4().hex
    title_a = "synthetic_h1_a_" + marker
    title_b = "synthetic_h1_b_" + marker
    with history_db() as app:
        saved_a = history.create_conversation(
            app,a,create_req(title=title_a),uuid.uuid4().hex,uuid.uuid4().hex)
        saved_b = history.create_conversation(
            app,b,create_req(title=title_b),uuid.uuid4().hex,uuid.uuid4().hex)
    return a,b,token_a,token_b,title_a,title_b,saved_a,saved_b


def _admit_and_list(conn, trusted_owner, session):
    # No stand-alone admission: the owner/session FOR SHARE locks must live
    # into the repository read until outer commit. A False MUST not read.
    with conn.transaction():
        valid=auth_session.admit_session_fenced(
            conn,session.opaque,trusted_owner,session.epoch,session.generation)
        if not valid:
            return False,None
        page=history.list_conversations(conn,trusted_owner)
        return True,page


def _assert_exact_owner(test,page,actor,own_title,other_title):
    test.assertIsInstance(page,dict)
    titles=[item["title"] for item in page["items"]]
    test.assertIn(own_title,titles)
    test.assertNotIn(other_title,titles)
    test.assertTrue(all(item["owner_user_id"]==actor for item in page["items"]))
    test.assertLessEqual(len(page["items"]),20)


def _observe_specific_revocation_wait(label,holding_pid):
    # Event ordering alone is insufficient: require real PG lock evidence.
    # The revoker of 003 takes Owner FOR UPDATE. The admitted H1 transaction
    # retains Owner+Session FOR SHARE until outer commit/rollback.
    with auth_db("MIG") as observer:
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            row=observer.execute("""
              SELECT a.pid,a.wait_event_type,a.wait_event,
                     pg_blocking_pids(a.pid) AS blockers
              FROM pg_stat_activity AS a
              WHERE a.application_name=%s
                AND a.datname='history_ci'
                AND a.wait_event_type='Lock'
            """,(label,)).fetchone()
            if row and holding_pid in row["blockers"]:
                return {"wait_event_type":row["wait_event_type"],
                        "reader_backend_pid":holding_pid,
                        "revoker_backend_pid":row["pid"],
                        "pg_blocking_pids":row["blockers"],
                        "wait_event":row["wait_event"]}
            observer.execute("SELECT pg_sleep(0.03)")
    raise AssertionError("H1_EXPECTED_REAL_REVOKER_BLOCKED_BY_READ_TRANSACTION")


class HistoryH1DbFencedReadRace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _trusted_ci_scope()
        with history_db() as app:
            who=app.execute("""
                SELECT current_user AS login, r.rolsuper,r.rolbypassrls,
                       has_table_privilege(current_user,'history_l1.conversations','SELECT') AS may_select,
                       has_table_privilege(current_user,
                           (SELECT c.oid FROM pg_class AS c JOIN pg_namespace AS n
                              ON n.oid=c.relnamespace
                            WHERE n.nspname='auth_l1' AND c.relname='sessions'),
                           'SELECT') AS auth_table_read
                FROM pg_roles AS r WHERE r.rolname=current_user
            """).fetchone()
            if (who["login"]!="history_app" or who["rolsuper"] or who["rolbypassrls"]
                or not who["may_select"] or who["auth_table_read"]):
                raise RuntimeError("H1_UNSAFE_APP_ROLE")
        with auth_db("MIG") as admin:
            # TEST-ONLY bridge to reproduce API H1's same-transaction executor.
            # It is NOT a migration, runtime privilege, or production approval.
            admin.execute("GRANT USAGE ON SCHEMA auth_l1 TO history_app")
            admin.execute(
                "GRANT EXECUTE ON FUNCTION "+FENCE_SIG+" TO history_app")
            admin.execute(
                "GRANT EXECUTE ON FUNCTION "+REPLAY_SIG+" TO history_app")
        cls._fixture_granted = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls,"_fixture_granted",False):
            with auth_db("MIG") as admin:
                admin.execute(
                    "REVOKE EXECUTE ON FUNCTION "+REPLAY_SIG+" FROM history_app")
                admin.execute(
                    "REVOKE EXECUTE ON FUNCTION "+FENCE_SIG+" FROM history_app")
                admin.execute("REVOKE USAGE ON SCHEMA auth_l1 FROM history_app")

    def test_H1DB01_revoke_commit_first_old_session_cannot_read(self):
        a,b,session_a,session_b,title_a,title_b,_,_=_fixture()
        committed=threading.Event()

        def revoke_first():
            # Independent physical connection, explicit committed revoke_one.
            with auth_db("SESSION") as c:
                accepted=auth_session.revoke_one(c,session_a.opaque,0)
            committed.set()
            return accepted

        with ThreadPoolExecutor(max_workers=1) as executor:
            prior=executor.submit(revoke_first)
            self.assertTrue(committed.wait(12),"revoke_one never committed")
            self.assertIs(prior.result(timeout=12),True)
        with history_db() as app:
            # The guarded repository must not run if 004 says DENIED.
            admitted,page=_admit_and_list(app,a,session_a)
            self.assertFalse(admitted)
            self.assertIsNone(page)
        with auth_db("MIG") as admin:
            status=admin.execute("""
                SELECT status FROM auth_l1.sessions WHERE digest_sha256=%s
            """,(digest(session_a.opaque),)).fetchone()
            self.assertEqual(status["status"],"revoked")
        with history_db() as app:
            # Independent unaffected owner B remains readable.
            admitted,page=_admit_and_list(app,b,session_b)
            self.assertTrue(admitted)
            _assert_exact_owner(self,page,b,title_b,title_a)
        print("H1DB01_REVOKE_COMMIT_FIRST_DENIED")

    def test_H1DB02_read_admission_first_revoke_waits_until_outer_commit(self):
        a,b,session_a,session_b,title_a,title_b,_,_=_fixture()
        worker_started=threading.Event()
        name="h1_db_revoke_after_"+uuid.uuid4().hex[:10]
        def revoke_worker():
            with auth_db("SESSION") as revoker:
                revoker.execute(
                    "SELECT set_config('application_name',%s,false)",(name,))
                revoker.execute("SET statement_timeout='11000ms'")
                worker_started.set()
                return auth_session.revoke_one(revoker,session_a.opaque,0)

        with ThreadPoolExecutor(max_workers=1) as pool:
            with history_db() as reader:
                holding_pid=reader.info.backend_pid
                with reader.transaction():
                    # 004 Owner FOR SHARE then Session FOR SHARE. Kept until
                    # this OUTER transaction ends, including History reads.
                    self.assertTrue(auth_session.admit_session_fenced(
                        reader,session_a.opaque,a,session_a.epoch,
                        session_a.generation))
                    page=history.list_conversations(reader,a)
                    _assert_exact_owner(self,page,a,title_a,title_b)
                    pending=pool.submit(revoke_worker)
                    self.assertTrue(worker_started.wait(8))
                    wait=_observe_specific_revocation_wait(name,holding_pid)
                    self.assertEqual(wait["wait_event_type"],"Lock")
                    self.assertEqual(wait["reader_backend_pid"],holding_pid)
                    self.assertIn(holding_pid,wait["pg_blocking_pids"])
                    print(
                        "H1DB02_REAL_PG_BLOCKER"
                        f" reader_backend_pid={holding_pid}"
                        f" revoker_backend_pid={wait['revoker_backend_pid']}"
                        f" pg_blocking_pids={wait['pg_blocking_pids']}"
                        f" wait_event_type={wait['wait_event_type']}"
                        f" wait_event={wait['wait_event']}",
                        flush=True,
                    )
                    self.assertFalse(pending.done(),
                        "revoke must not commit while admitted History TX holds lock")
                    # Read still succeeds inside the SAME already-admitted TX
                    # while the explicit revocation remains blocked.
                    second=history.list_conversations(reader,a)
                    _assert_exact_owner(self,second,a,title_a,title_b)
                # Outer commit released Owner+Session locks.
            self.assertIs(pending.result(timeout=12),True)
        with history_db() as reader_after:
            admitted,later_page=_admit_and_list(reader_after,a,session_a)
            self.assertFalse(admitted)
            self.assertIsNone(later_page)
        with history_db() as b_reader:
            admitted,b_page=_admit_and_list(b_reader,b,session_b)
            self.assertTrue(admitted)
            _assert_exact_owner(self,b_page,b,title_b,title_a)
        print("H1DB02_READ_ADMITTED_FIRST_REVOKE_WAITED_THEN_DENIED")

    def test_H1DB03_read_only_history_app_role_rls_isolates_owner_a(self):
        a,b,session_a,session_b,title_a,title_b,_,_=_fixture()
        with history_db() as reader:
            role=reader.execute("""SELECT rolname,rolsuper,rolbypassrls
                FROM pg_roles WHERE rolname=current_user""").fetchone()
            self.assertEqual(role["rolname"],"history_app")
            self.assertFalse(role["rolsuper"])
            self.assertFalse(role["rolbypassrls"])
            with reader.transaction():
                self.assertTrue(auth_session.admit_session_fenced(
                    reader,session_a.opaque,a,session_a.epoch,
                    session_a.generation))
                page=history.list_conversations(reader,a)
                _assert_exact_owner(self,page,a,title_a,title_b)
                # History's actual FORCE RLS enforces current app.owner_id.
                # This deliberately unfiltered SQL must still exclude B.
                observed=reader.execute("""
                  SELECT owner_id,title FROM history_l1.conversations
                  ORDER BY title
                """).fetchall()
                self.assertGreaterEqual(len(observed),1)
                self.assertTrue(all(r["owner_id"]==a for r in observed))
                self.assertIn(title_a,[r["title"] for r in observed])
                self.assertNotIn(title_b,[r["title"] for r in observed])
                for relation in ("conversations","messages","answers"):
                    row=reader.execute("""
                        SELECT relrowsecurity,relforcerowsecurity
                        FROM pg_class WHERE oid=%s::regclass
                    """,("history_l1."+relation,)).fetchone()
                    self.assertTrue(row["relrowsecurity"])
                    self.assertTrue(row["relforcerowsecurity"])
        print("H1DB03_HISTORY_APP_NO_BYPASSRLS_OWNER_A_ONLY")

    def test_H1DB04_repeatable_read_revoke_after_replay_snapshot_serialization_40001(self):
        """Real PG serialization 40001 must abort the 005 JTI insert and forbid reads.

        The revoker COMMIT is strictly AFTER the first RR snapshot (005 INSERT)
        but BEFORE 004's FOR SHARE row locks. This is not a mock SQL exception.
        """
        a,b,token_a,token_b,title_a,title_b,_,_=_fixture()
        jti_digest=digest("synthetic_h1_rr_replay_"+uuid.uuid4().hex)
        with history_db() as reader:
            reader.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
            with self.assertRaises(psycopg.errors.SerializationFailure) as failure:
                with reader.transaction():
                    consumed=reader.execute(
                        "SELECT auth_l1.consume_service_assertion(%s,%s) AS accepted",
                        (jti_digest,int(time.time())+22)).fetchone()
                    self.assertTrue(consumed["accepted"])
                    # 005's INSERT has fixed this transaction's MVCC snapshot.
                    with auth_db("SESSION") as revoker:
                        self.assertTrue(auth_session.revoke_one(
                            revoker,token_a.opaque,token_a.epoch))
                    # 004 now sees the pre-commit snapshot but must lock
                    # the updated owner/session and raises real 40001.
                    auth_session.admit_session_fenced(
                        reader,token_a.opaque,a,token_a.epoch,token_a.generation)
            self.assertEqual(failure.exception.sqlstate,"40001")
            self.assertEqual(reader.info.transaction_status,
                             psycopg.pq.TransactionStatus.IDLE)
        with auth_db("MIG") as admin:
            n=admin.execute("""SELECT count(*) AS n
                FROM auth_l1.service_assertion_replays
                WHERE issuer_jti_sha256=%s""",(jti_digest,)).fetchone()["n"]
            self.assertEqual(n,0,"rolled-back RR authorization must not consume 005 JTI")
        with history_db() as afterwards:
            admitted,page=_admit_and_list(afterwards,a,token_a)
            self.assertFalse(admitted)
            self.assertIsNone(page)
            admitted_b,page_b=_admit_and_list(afterwards,b,token_b)
            self.assertTrue(admitted_b)
            _assert_exact_owner(self,page_b,b,title_b,title_a)
        print("H1DB04_REAL_PG17_RR_40001_FULL_005_ROLLBACK_A_DENIED_B_ONLY",flush=True)

    def test_H1DB05_repeatable_read_005_004_then_history_revoke_waits(self):
        """Actual 005 write, RR 004 admission and owner-scoped History in one TX."""
        a,b,token_a,token_b,title_a,title_b,_,_=_fixture()
        jti_digest=digest("synthetic_h1_rr_read_"+uuid.uuid4().hex)
        started=threading.Event()
        app_name="h1_rr_revoker_"+uuid.uuid4().hex[:9]
        def revoke():
            with auth_db("SESSION") as revoker:
                revoker.execute(
                    "SELECT set_config('application_name',%s,false)",(app_name,))
                revoker.execute("SET statement_timeout='11000ms'")
                started.set()
                return auth_session.revoke_one(revoker,token_a.opaque,token_a.epoch)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with history_db() as reader:
                reader.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
                holding_pid=reader.info.backend_pid
                with reader.transaction():
                    self.assertTrue(reader.execute(
                        "SELECT auth_l1.consume_service_assertion(%s,%s) AS accepted",
                        (jti_digest,int(time.time())+22)).fetchone()["accepted"])
                    self.assertTrue(auth_session.admit_session_fenced(
                        reader,token_a.opaque,a,token_a.epoch,token_a.generation))
                    page1=history.list_conversations(reader,a)
                    _assert_exact_owner(self,page1,a,title_a,title_b)
                    pending=pool.submit(revoke)
                    self.assertTrue(started.wait(8))
                    witness=_observe_specific_revocation_wait(app_name,holding_pid)
                    self.assertIn(holding_pid,witness["pg_blocking_pids"])
                    self.assertFalse(pending.done())
                    page2=history.list_conversations(reader,a)
                    _assert_exact_owner(self,page2,a,title_a,title_b)
                    self.assertEqual(page1["items"],page2["items"])
                    print(
                        "H1DB05_REAL_PG_RR_LOCK"
                        f" reader_pid={holding_pid}"
                        f" revoker_pid={witness['revoker_backend_pid']}"
                        f" pg_blocking_pids={witness['pg_blocking_pids']}"
                        f" wait_event={witness['wait_event']}",flush=True)
            self.assertTrue(pending.result(timeout=12))
        with auth_db("MIG") as admin:
            self.assertEqual(admin.execute("""SELECT count(*) AS n
                FROM auth_l1.service_assertion_replays
                WHERE issuer_jti_sha256=%s""",(jti_digest,)).fetchone()["n"],1)
        with history_db() as later:
            self.assertFalse(_admit_and_list(later,a,token_a)[0])
            admitted,page=_admit_and_list(later,b,token_b)
            self.assertTrue(admitted)
            _assert_exact_owner(self,page,b,title_b,title_a)
        print("H1DB05_REAL_PG17_RR_005_004_HISTORY_REVOKE_COMMIT_BOUNDARY",flush=True)

    def test_H1DB06_real_40001_after_t1_t2_rolls_back_replay_and_history(self):
        """Real PG 40001 after BOTH T1 and T2 savepoints undoes entire outer TX.

        Concurrent independent writer commits an UPDATE to an older History
        conversation after RR snapshot; subsequent FOR SHARE produces actual
        SerializationFailure. This is not a synthetic thrown exception.
        """
        a,b,token_a,token_b,title_a,title_b,saved_a,_=_fixture()
        old_id=saved_a["conversation"]["conversation_id"]
        marker=uuid.uuid4().hex
        jti_digest=digest("synthetic_h1_rr_full_tx_"+marker)
        request=send_req(None,client="client_"+marker,key="key_"+marker,
                         question="Synthetic rollback verification "+marker)
        created_conversation=None
        with history_db() as reader:
            reader.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
            with self.assertRaises(psycopg.errors.SerializationFailure) as failure:
                with reader.transaction():
                    self.assertTrue(reader.execute(
                        "SELECT auth_l1.consume_service_assertion(%s,%s) AS accepted",
                        (jti_digest,int(time.time())+25)).fetchone()["accepted"])
                    self.assertTrue(auth_session.admit_session_fenced(
                        reader,token_a.opaque,a,token_a.epoch,token_a.generation))
                    # Exactly #52's nesting shape: T1 and T2 are SAVEPOINTs
                    # inside the protected outer 005+004 transaction.
                    receipt=history.send_t1(
                        reader,a,request,history.uid(),history.uid())
                    self.assertEqual(receipt["disposition"],"created")
                    created_conversation=receipt["resolved_conversation_id"]
                    attempt=history.start_t2(
                        reader,a,None,request["client_message_id"],
                        request["idempotency_key"],history.uid(),history.uid())
                    self.assertEqual(attempt["state"],"attempt_pending")
                    with history_db() as other:
                        with other.transaction():
                            history.scoped(other,a)
                            changed=other.execute(
                                """UPDATE history_l1.conversations
                                   SET title=%s
                                   WHERE owner_id=%s AND id=%s
                                   RETURNING id""",
                                ("synthetic_conflict_"+marker,a,old_id)).fetchone()
                            self.assertIsNotNone(changed)
                    # RR snapshot pre-dates writer UPDATE; FOR SHARE
                    # now sees changed tuple and PG must raise SQLSTATE 40001.
                    reader.execute(
                        """SELECT id FROM history_l1.conversations
                           WHERE owner_id=%s AND id=%s FOR SHARE""",
                        (a,old_id))
            self.assertEqual(failure.exception.sqlstate,"40001")
            self.assertEqual(reader.info.transaction_status,
                             psycopg.pq.TransactionStatus.IDLE)
        with auth_db("MIG") as admin:
            self.assertEqual(admin.execute(
                """SELECT count(*) AS n FROM auth_l1.service_assertion_replays
                   WHERE issuer_jti_sha256=%s""",(jti_digest,)
            ).fetchone()["n"],0)
        with history_db() as viewer:
            with viewer.transaction():
                history.scoped(viewer,a)
                for sql,params in (
                    ("""SELECT count(*) AS n FROM history_l1.send_receipts
                        WHERE owner_id=%s AND client_message_id=%s
                          AND idempotency_key=%s""",
                     (a,request["client_message_id"],request["idempotency_key"])),
                    ("""SELECT count(*) AS n FROM history_l1.conversations
                        WHERE owner_id=%s AND id=%s""",(a,created_conversation)),
                    ("""SELECT count(*) AS n FROM history_l1.messages
                        WHERE owner_id=%s AND body=%s""",(a,request["question"]))
                ):
                    self.assertEqual(viewer.execute(sql,params).fetchone()["n"],0)
        with history_db() as b_reader:
            admitted,page=_admit_and_list(b_reader,b,token_b)
            self.assertTrue(admitted)
            _assert_exact_owner(self,page,b,title_b,title_a)
        print("H1DB06_REAL_PG17_40001_AFTER_T1_T2_ALL_005_RECEIPT_ATTEMPT_MESSAGE_ROLLED_BACK",flush=True)
