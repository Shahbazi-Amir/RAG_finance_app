"""Deterministic, synthetic PostgreSQL-only History L1 evidence. No HTTP/replica."""
import copy
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from test_history_l1 import (
    FIXTURES, ROOT, db, actor_id, create_req, send_req, status_q,
)
from repository import (
    uid, scoped, create_conversation, send_t1, start_t2, finalize_t3,
    read_status, list_conversations, list_messages,
)

class PausedSQL:
    """Gate specific SQL inside a live connection/transaction, no timing sleep."""
    def __init__(self, connection, target, entered, release):
        self.connection, self.target = connection, target
        self.entered, self.release = entered, release
        self.hit = False

    def __getattr__(self, key):
        return getattr(self.connection, key)

    def execute(self, statement, *args, **kwargs):
        if not self.hit and self.target in str(statement):
            self.hit = True
            self.entered.set()
            if not self.release.wait(timeout=15):
                raise AssertionError("deterministic SQL barrier timeout")
        return self.connection.execute(statement, *args, **kwargs)

def calibrated(attempt, receipt):
    sample = next(x["document"] for x in FIXTURES["cases"]
                  if x["case_id"] == "valid_confidence_calibrated_example")
    answer = copy.deepcopy(sample)
    answer.update(answer_id=attempt["reserved_answer_id"],
                  conversation_id=receipt["resolved_conversation_id"],
                  message_id=uid(),
                  request_id=attempt["attempt_request_id"],
                  trace_id=attempt["attempt_trace_id"])
    assert set(answer["confidence"]) == {"value","meaning","calibration_scope"}
    return answer

def complete(t, status, attempt, receipt, answer):
    t.assertEqual(status["status"], "answer_committed")
    t.assertEqual(status["attempt_id"], attempt["id"])
    t.assertEqual(status["reserved_answer_id"], attempt["reserved_answer_id"])
    t.assertEqual(status["answer_id"], attempt["reserved_answer_id"])
    t.assertEqual(status["answer"], answer)
    t.assertEqual(status["message_id"], receipt["message_id"])
    t.assertEqual(status["attempt_request_id"],attempt["attempt_request_id"])
    t.assertEqual(status["attempt_trace_id"],attempt["attempt_trace_id"])
    t.assertNotEqual(status["message_id"],answer["message_id"])

class HistoryEvidenceExtension(unittest.TestCase):
    def test_HDB09_T3_inflight_and_status_snapshot_spanning_commit(self):
        owner = actor_id("race")
        req = send_req()
        with db() as c:
            receipt=send_t1(c,owner,req,uid(),uid())
            att=start_t2(c,owner,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
        answer=calibrated(att,receipt)
        started, release=threading.Event(),threading.Event()
        def writer():
            with db() as conn:
                gated=PausedSQL(conn,"UPDATE history_l1.execution_attempts SET state='answer_committed'",started,release)
                return finalize_t3(gated,owner,att["id"],answer,"Synthetic in-flight outcome")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(writer)
            try:
                self.assertTrue(started.wait(15),"T3 never reached in-transaction barrier")
                with db() as observer:
                    s=read_status(observer,owner,status_q(req),uid(),uid())
                    self.assertEqual(s["status"],"attempt_pending")
                    self.assertEqual(s["attempt_id"],att["id"])
                    self.assertIsNone(s["answer_id"])
                    self.assertIsNone(s["answer"])
                    with observer.transaction():
                        scoped(observer,owner)
                        self.assertEqual(observer.execute(
                            "SELECT count(*) AS n FROM history_l1.answers WHERE owner_id=%s AND attempt_id=%s",
                            (owner,att["id"])).fetchone()["n"],0)
                        self.assertEqual(observer.execute(
                            "SELECT count(*) AS n FROM history_l1.messages WHERE owner_id=%s AND id=%s",
                            (owner,answer["message_id"])).fetchone()["n"],0)
            finally:
                release.set()
            self.assertEqual(future.result(timeout=15),answer)
        with db() as observer:
            s=read_status(observer,owner,status_q(req),uid(),uid())
            complete(self,s,att,receipt,answer)
            page=list_messages(observer,owner,receipt["resolved_conversation_id"])
            self.assertEqual(page["answers"],[answer])
            self.assertIn(answer["message_id"],[m["message_id"] for m in page["items"]])

        # A separate reader takes a REPEATABLE READ snapshot after T1 lookup,
        # pauses before T2 lookup, and continues after a writer commits T3.
        req2=send_req()
        with db() as conn:
            r2=send_t1(conn,owner,req2,uid(),uid())
            a2=start_t2(conn,owner,None,req2["client_message_id"],req2["idempotency_key"],uid(),uid())
        ans2=calibrated(a2,r2)
        reader_started,reader_release=threading.Event(),threading.Event()
        def reader():
            with db() as c:
                gate=PausedSQL(c,"SELECT a.* FROM history_l1.execution_attempts a",
                              reader_started,reader_release)
                return read_status(gate,owner,status_q(req2),uid(),uid())
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(reader)
            try:
                self.assertTrue(reader_started.wait(15),"reader never reached T2 lookup barrier")
                with db() as writer:
                    finalize_t3(writer,owner,a2["id"],ans2,"Synthetic committed outcome")
            finally:
                reader_release.set()
            old=future.result(timeout=15)
        self.assertEqual(old["status"],"attempt_pending")
        self.assertEqual(old["attempt_id"],a2["id"])
        self.assertIsNone(old["answer"])
        self.assertIsNone(old["answer_id"])
        with db() as c:
            complete(self,read_status(c,owner,status_q(req2),uid(),uid()),a2,r2,ans2)
        # No replica, HTTP response order, or process kill asserted.

    def test_P3M15_multi_page_tied_timestamp_anchor_with_interleaved_inserts(self):
        owner=actor_id("pages")
        timestamp=datetime(2026,1,1,tzinfo=timezone.utc)
        with db() as app:
            original=[create_conversation(app,owner,create_req(title=f"Synthetic {i}"),uid(),uid())
                      ["conversation"]["conversation_id"] for i in range(7)]
        with db("DB_MIG_DSN") as migrator:
            with migrator.transaction():
                migrator.execute(
                    "UPDATE history_l1.conversations SET created_at=%s WHERE owner_id=%s AND id=ANY(%s)",
                    (timestamp,owner,original))
            ordered=migrator.execute(
                "SELECT id,created_at FROM history_l1.conversations WHERE owner_id=%s "
                "ORDER BY created_at DESC,id DESC",(owner,)).fetchall()
        self.assertEqual(len(ordered),7)
        self.assertEqual({r["created_at"] for r in ordered},{timestamp})
        anchor=(ordered[0]["created_at"],ordered[0]["id"])
        with db() as app:
            seen=[]; last=None; added=None
            while True:
                page=list_conversations(app,owner,limit=2,anchor=anchor,last=last)
                seen.extend(x["conversation_id"] for x in page["items"])
                if added is None:
                    added=create_conversation(app,owner,create_req(title="After anchor"),uid(),uid())
                    added=added["conversation"]["conversation_id"]
                if not page["has_more"]: break
                self.assertIsNotNone(page["last"])
                last=page["last"]
            self.assertEqual(seen,[x["id"] for x in ordered])
            self.assertEqual(len(seen),len(set(seen)))
            self.assertNotIn(added,seen)
            cutoff=ordered[3]
            result=list_conversations(app,owner,limit=100,
                anchor=(cutoff["created_at"],cutoff["id"]))
            self.assertEqual([x["conversation_id"] for x in result["items"]],
                             [x["id"] for x in ordered[3:]])
            cid=original[0]
            for n in range(5):
                req=send_req(cid=cid,question=f"Synthetic page question {n}")
                receipt=send_t1(app,owner,req,uid(),uid())
                if n<4:
                    att=start_t2(app,owner,cid,req["client_message_id"],req["idempotency_key"],uid(),uid())
                    ans=calibrated(att,receipt)
                    finalize_t3(app,owner,att["id"],ans,f"Assistant page {n}")
        with db("DB_MIG_DSN") as migrator:
            with migrator.transaction():
                migrator.execute("UPDATE history_l1.messages SET created_at=%s "
                                 "WHERE owner_id=%s AND conversation_id=%s",
                                 (timestamp,owner,cid))
            messages=migrator.execute("SELECT id,created_at FROM history_l1.messages "
                "WHERE owner_id=%s AND conversation_id=%s ORDER BY created_at,id",
                (owner,cid)).fetchall()
        self.assertEqual(len(messages),9)
        self.assertEqual({x["created_at"] for x in messages},{timestamp})
        msg_anchor=(messages[-1]["created_at"],messages[-1]["id"])
        expected=[x["id"] for x in messages]
        with db() as app:
            seen=[]; last=None; answers=set(); late=None
            while True:
                page=list_messages(app,owner,cid,limit=2,anchor=msg_anchor,last=last)
                ids={m["message_id"] for m in page["items"]}
                seen.extend(m["message_id"] for m in page["items"])
                page_refs={m["answer_id"] for m in page["items"] if m["answer_id"]}
                self.assertEqual({a["answer_id"] for a in page["answers"]},page_refs)
                self.assertEqual(len(page["answers"]),len(page_refs))
                for ans in page["answers"]:
                    self.assertIn(ans["message_id"],ids)
                    self.assertNotIn(ans["answer_id"],answers)
                    answers.add(ans["answer_id"])
                if late is None:
                    req=send_req(cid=cid,question="Inserted after first page")
                    receipt=send_t1(app,owner,req,uid(),uid())
                    att=start_t2(app,owner,cid,req["client_message_id"],req["idempotency_key"],uid(),uid())
                    ans=calibrated(att,receipt)
                    finalize_t3(app,owner,att["id"],ans,"Late assistant")
                    late={receipt["message_id"],ans["message_id"]}
                if not page["has_more"]: break
                self.assertIsNotNone(page["last"])
                last=page["last"]
            self.assertEqual(seen,expected)
            self.assertEqual(len(seen),len(set(seen)))
            self.assertTrue(late.isdisjoint(seen))
            self.assertEqual(len(answers),4)
            cut=messages[4]
            subset=list_messages(app,owner,cid,limit=100,anchor=(cut["created_at"],cut["id"]))
            self.assertEqual([m["message_id"] for m in subset["items"]],expected[:5])
        # Anchor is not an MVCC snapshot against privileged backdated inserts.

    def test_P3M04_populated_001_then_002_up_down_up_preserves_answer(self):
        owner=actor_id("seed")
        with db("DB_SEEDED_APP_DSN") as app:
            created=create_conversation(app,owner,create_req("Synthetic seeded"),uid(),uid())
            cid=created["conversation"]["conversation_id"]
            req=send_req(cid=cid,question="Synthetic fixture before migration")
            receipt=send_t1(app,owner,req,uid(),uid())
            attempt=start_t2(app,owner,cid,req["client_message_id"],req["idempotency_key"],uid(),uid())
            answer=calibrated(attempt,receipt)
            finalize_t3(app,owner,attempt["id"],answer,"Synthetic seeded assistant")
        def chain(conn):
            rows=conn.execute("""SELECT c.owner_id,c.id AS cid,cr.created_snapshot,
                r.id AS rid,r.user_message_id,um.role AS user_role,
                a.id AS attempt_id,a.reserved_answer_id,a.state AS attempt_state,
                ans.id AS answer_id,ans.message_id AS assistant_id,
                ans.payload,am.role AS assistant_role
                FROM history_l1.conversations c
                JOIN history_l1.create_receipts cr ON cr.owner_id=c.owner_id AND cr.conversation_id=c.id
                JOIN history_l1.send_receipts r ON r.owner_id=c.owner_id AND r.resolved_conversation_id=c.id
                JOIN history_l1.messages um ON um.owner_id=r.owner_id AND um.id=r.user_message_id
                   AND um.conversation_id=c.id
                JOIN history_l1.execution_attempts a ON a.owner_id=r.owner_id AND a.send_receipt_id=r.id
                JOIN history_l1.answers ans ON ans.owner_id=a.owner_id AND ans.attempt_id=a.id
                   AND ans.id=a.reserved_answer_id
                JOIN history_l1.messages am ON am.owner_id=ans.owner_id AND am.id=ans.message_id
                   AND am.conversation_id=c.id
                WHERE c.owner_id=%s AND c.id=%s AND r.id=%s""",
                (owner,cid,attempt["send_receipt_id"])).fetchall()
            self.assertEqual(len(rows),1)
            row=rows[0]
            self.assertEqual(row["cid"],cid)
            self.assertEqual(row["rid"],attempt["send_receipt_id"])
            self.assertEqual(row["user_message_id"],receipt["message_id"])
            self.assertEqual(row["user_role"],"user")
            self.assertEqual(row["attempt_id"],attempt["id"])
            self.assertEqual(row["reserved_answer_id"],answer["answer_id"])
            self.assertEqual(row["answer_id"],answer["answer_id"])
            self.assertEqual(row["assistant_id"],answer["message_id"])
            self.assertEqual(row["assistant_role"],"assistant")
            self.assertEqual(row["attempt_state"],"answer_committed")
            self.assertEqual(row["created_snapshot"],created["conversation"])
            self.assertEqual(row["payload"],answer)
            for part in ("confidence","provenance","claims","citations"):
                self.assertEqual(row["payload"][part],answer[part])
            return row
        directory=ROOT/"infra/postgres/migrations"
        up=(directory/"002_one_attempt.up.sql").read_text(encoding="utf8")
        down=(directory/"002_one_attempt.down.sql").read_text(encoding="utf8")
        with db("DB_SEEDED_MIG_DSN") as migrator:
            before=chain(migrator)
            query="SELECT to_regclass('history_l1.one_attempt_per_send_receipt') AS idx"
            self.assertIsNone(migrator.execute(query).fetchone()["idx"])
            with migrator.transaction():
                migrator.execute(up)
            self.assertIsNotNone(migrator.execute(query).fetchone()["idx"])
            self.assertEqual(chain(migrator),before)
            with migrator.transaction():
                migrator.execute(down)
            self.assertIsNone(migrator.execute(query).fetchone()["idx"])
            self.assertEqual(chain(migrator),before)
            with migrator.transaction():
                migrator.execute(up)
            self.assertIsNotNone(migrator.execute(query).fetchone()["idx"])
            self.assertEqual(chain(migrator),before)
        # 001 destructive rollback intentionally NOT run in populated-chain DB.

if __name__=="__main__":
    unittest.main(verbosity=2)
