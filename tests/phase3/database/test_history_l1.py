"""Actual PostgreSQL test harness, SYNTHETIC ONLY. HDB-01..10.
Requires disposable loopback CI databases and independently configured app/migrator roles.
This does not assert production authentication, real crash/process kill or replica behavior.
"""
import copy
import json
import os
import sys
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg.errors import ForeignKeyViolation, InsufficientPrivilege, UniqueViolation

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src/phase3/storage/postgres"))
from repository import (NotFound,Conflict,IntegrityAnomaly,InjectedRollback,
                        create_conversation,send_t1,start_t2,mark_attempt,finalize_t3,
                        read_status,list_conversations,list_messages,scoped,uid)

def ensure_ci():
    if os.getenv("CI")!="true":
        raise RuntimeError("CI_ONLY: no local or production DB accepted")
    for key in ("DB_APP_DSN","DB_MIG_DSN","DB_LEGACY_APP_DSN","DB_LEGACY_MIG_DSN"):
        v=os.getenv(key,"")
        if "host=127.0.0.1" not in v or "localhost" in v or "dbname=history_" not in v:
            raise RuntimeError("CI_ONLY: reject DB outside designated loopback temp databases")

def db(name="DB_APP_DSN"):
    ensure_ci()
    return psycopg.connect(os.environ[name],autocommit=True,row_factory=psycopg.rows.dict_row)

def actor_id(suffix):
    return "synthetic_"+suffix+"_"+uuid.uuid4().hex[:12]

def create_req(title="Original",client=None,key="create_key_1234"):
    return dict(kind="create_conversation_request",contract_version="product.v1",
                client_conversation_id=client or uid(),idempotency_key=key,title=title)

def send_req(cid=None,client=None,key="send_key_1234",question="Synthetic question"):
    return dict(kind="send_message_request",contract_version="product.v1",
                requested_conversation_id=cid,client_message_id=client or uid(),
                idempotency_key=key,question=question)

def status_q(req):
    return dict(kind="message_request_status_query",contract_version="product.v1",
                requested_conversation_id=req["requested_conversation_id"],
                client_message_id=req["client_message_id"],idempotency_key=req["idempotency_key"])

FIXTURES=json.loads((ROOT/"packages/contracts/fixtures/product.v1.cases.json").read_text(encoding="utf8"))
def synthetic_answer(att,receipt):
    case=next(x for x in FIXTURES["cases"] if x["case_id"]=="valid_answer_unresolved_source")
    a=copy.deepcopy(case["document"])
    a.update(answer_id=att["reserved_answer_id"],message_id=uid(),
             conversation_id=receipt["resolved_conversation_id"],
             request_id=att["attempt_request_id"],trace_id=att["attempt_trace_id"])
    return a

class HistoryPostgresL1(unittest.TestCase):
    def test_HDB01_create_concurrent_replay_conflict(self):
        owner=actor_id("create")
        request=create_req()
        def do(_):
            with db() as conn:
                return create_conversation(conn,owner,request,uid(),uid())
        with ThreadPoolExecutor(max_workers=4) as pool:
            vals=list(pool.map(do,range(8)))
        self.assertEqual(sum(x["disposition"]=="created" for x in vals),1)
        self.assertEqual(len({x["conversation"]["conversation_id"] for x in vals}),1)
        self.assertTrue(all(x["conversation"]==vals[0]["conversation"] for x in vals))
        with db() as conn:
            with self.assertRaises(Conflict):
                create_conversation(conn,owner,{**request,"title":"Changed"},uid(),uid())
            with conn.transaction():
                scoped(conn,owner)
                n=conn.execute("SELECT count(*) AS n FROM history_l1.create_receipts WHERE owner_id=%s",(owner,)).fetchone()["n"]
                self.assertEqual(n,1)

    def test_HDB02_immutable_snapshot_current_authorization(self):
        owner=actor_id("snap")
        req=create_req(title="First title")
        with db() as conn:
            first=create_conversation(conn,owner,req,uid(),uid())
            cid=first["conversation"]["conversation_id"]
            with conn.transaction():
                scoped(conn,owner)
                conn.execute("UPDATE history_l1.conversations SET title='new title',updated_at=clock_timestamp() WHERE owner_id=%s AND id=%s",(owner,cid))
            replay=create_conversation(conn,owner,req,uid(),uid())
            self.assertEqual(replay["conversation"],first["conversation"])
            self.assertEqual(replay["conversation"]["title"],"First title")
            foreign=create_conversation(conn,actor_id("foreign"),req,uid(),uid())
            self.assertNotEqual(foreign["conversation"]["conversation_id"],cid)
            with conn.transaction():
                scoped(conn,owner)
                conn.execute("UPDATE history_l1.conversations SET state='deletion_requested' WHERE owner_id=%s AND id=%s",(owner,cid))
            with self.assertRaises(NotFound):
                create_conversation(conn,owner,req,uid(),uid())
            with conn.transaction():
                scoped(conn,owner)
                saved=conn.execute("SELECT created_snapshot FROM history_l1.create_receipts WHERE owner_id=%s",(owner,)).fetchone()["created_snapshot"]
                self.assertEqual(saved,first["conversation"])

    def test_HDB03_null_first_send_concurrent(self):
        owner=actor_id("null")
        request=send_req(cid=None)
        def do(_):
            with db() as conn:
                return send_t1(conn,owner,request,uid(),uid())
        with ThreadPoolExecutor(max_workers=5) as pool:
            records=list(pool.map(do,range(10)))
        self.assertEqual(sum(x["disposition"]=="created" for x in records),1)
        self.assertTrue(all(x["requested_conversation_id"] is None for x in records))
        self.assertEqual(len({x["message_id"] for x in records}),1)
        self.assertEqual(len({x["resolved_conversation_id"] for x in records}),1)
        with db() as conn:
            with conn.transaction():
                scoped(conn,owner)
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM history_l1.send_receipts WHERE owner_id=%s",(owner,)).fetchone()["n"],1)
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM history_l1.messages WHERE owner_id=%s",(owner,)).fetchone()["n"],1)
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM history_l1.conversations WHERE owner_id=%s",(owner,)).fetchone()["n"],1)

    def test_HDB04_scopes_conflict_nonnull_and_owner(self):
        a,b=actor_id("scope_a"),actor_id("scope_b")
        req=create_req(client="client_shared",key="key_shared_123")
        with db() as conn:
            cid=create_conversation(conn,a,req,uid(),uid())["conversation"]["conversation_id"]
            other=create_conversation(conn,b,req,uid(),uid())["conversation"]["conversation_id"]
            self.assertNotEqual(cid,other)
            same=send_req(cid=cid,client="message_shared",key="key_shared_123")
            first=send_t1(conn,a,same,uid(),uid())
            self.assertEqual(send_t1(conn,a,same,uid(),uid())["message_id"],first["message_id"])
            with self.assertRaises(Conflict):
                send_t1(conn,a,{**same,"question":"Changed"},uid(),uid())
            with self.assertRaises(NotFound):
                send_t1(conn,b,same,uid(),uid())
            other_send=send_t1(conn,b,{**same,"requested_conversation_id":other},uid(),uid())
            self.assertNotEqual(other_send["message_id"],first["message_id"])
            self.assertEqual(first["requested_conversation_id"],cid)

    def test_HDB05_t2_concurrent_one_attempt_and_readonly_status(self):
        owner=actor_id("t2")
        request=send_req()
        with db() as conn:
            receipt=send_t1(conn,owner,request,uid(),uid())
            before=read_status(conn,owner,status_q(request),uid(),uid())
            self.assertEqual(before["status"],"persisted")
        def do(_):
            with db() as c:
                return start_t2(c,owner,None,request["client_message_id"],
                                request["idempotency_key"],uid(),uid())
        with ThreadPoolExecutor(max_workers=4) as pool:
            attempts=list(pool.map(do,range(8)))
        self.assertEqual(len({x["id"] for x in attempts}),1)
        self.assertEqual(len({x["attempt_trace_id"] for x in attempts}),1)
        with db() as conn:
            before_count=read_status(conn,owner,status_q(request),uid(),uid())
            again=send_t1(conn,owner,request,uid(),uid())
            self.assertEqual(again["message_id"],receipt["message_id"])
            after_count=read_status(conn,owner,status_q(request),uid(),uid())
            self.assertEqual(before_count["attempt_id"],after_count["attempt_id"])
            self.assertNotEqual(before_count["request_id"],after_count["request_id"])
            with conn.transaction():
                scoped(conn,owner)
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM history_l1.execution_attempts WHERE owner_id=%s",(owner,)).fetchone()["n"],1)

    def test_HDB06_injected_rollbacks_connection_close_and_postcommit(self):
        owner=actor_id("rollback")
        req=send_req()
        with db() as conn:
            with self.assertRaises(InjectedRollback):
                send_t1(conn,owner,req,uid(),uid(),rollback=True)
            with self.assertRaises(NotFound):
                read_status(conn,owner,status_q(req),uid(),uid())
            receipt=send_t1(conn,owner,req,uid(),uid())
            with self.assertRaises(InjectedRollback):
                start_t2(conn,owner,None,req["client_message_id"],req["idempotency_key"],
                         uid(),uid(),rollback=True)
            self.assertEqual(read_status(conn,owner,status_q(req),uid(),uid())["status"],"persisted")
            attempt=start_t2(conn,owner,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
            answer=synthetic_answer(attempt,receipt)
            with self.assertRaises(InjectedRollback):
                finalize_t3(conn,owner,attempt["id"],answer,"Synthetic answer",rollback=True)
            self.assertEqual(read_status(conn,owner,status_q(req),uid(),uid())["status"],"attempt_pending")
        # Close the prior connection AFTER all commits, reconnect (not process crash).
        with db() as new_conn:
            again=send_t1(new_conn,owner,req,uid(),uid())
            self.assertEqual(again["message_id"],receipt["message_id"])
            final=finalize_t3(new_conn,owner,attempt["id"],answer,"Synthetic answer")
            self.assertEqual(final["answer_id"],attempt["reserved_answer_id"])
        with db() as after_close:
            result=read_status(after_close,owner,status_q(req),uid(),uid())
            self.assertEqual(result["status"],"answer_committed")
            self.assertEqual(result["answer_id"],attempt["reserved_answer_id"])
            self.assertNotEqual(result["answer"]["message_id"],result["message_id"])
            self.assertEqual(result["answer"],answer)

    def test_HDB07_legacy_multi_attempt_migration_fails_without_mutation(self):
        owner=actor_id("legacy")
        with db("DB_LEGACY_APP_DSN") as conn:
            req=send_req()
            receipt=send_t1(conn,owner,req,uid(),uid())
            first=start_t2(conn,owner,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
            with conn.transaction():
                scoped(conn,owner)
                conn.execute("""INSERT INTO history_l1.execution_attempts
                  (owner_id,id,send_receipt_id,attempt_request_id,attempt_trace_id,reserved_answer_id)
                  VALUES(%s,%s,%s,%s,%s,%s)""",(owner,uid(),first["send_receipt_id"],uid(),uid(),uid()))
            with self.assertRaises(IntegrityAnomaly):
                read_status(conn,owner,status_q(req),uid(),uid())
            with self.assertRaises(IntegrityAnomaly):
                start_t2(conn,owner,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
        sql=(ROOT/"infra/postgres/migrations/002_one_attempt.up.sql").read_text(encoding="utf8")
        with db("DB_LEGACY_MIG_DSN") as migrator:
            with self.assertRaisesRegex(psycopg.Error, 'HISTORY_LEGACY_MULTI_ATTEMPT'):
                with migrator.transaction():
                    migrator.execute(sql)
        with db("DB_LEGACY_APP_DSN") as conn:
            with conn.transaction():
                scoped(conn,owner)
                rows=conn.execute("SELECT id FROM history_l1.execution_attempts WHERE owner_id=%s",(owner,)).fetchall()
                self.assertEqual(len(rows),2)
                self.assertIn(first["id"],[r["id"] for r in rows])
        # Do NOT delete/rewrite synthetic rows even in this disposable legacy DB.

    def test_HDB08_db_verified_status_refuses_client_witness(self):
        owner=actor_id("witness")
        req=send_req()
        with db() as conn:
            receipt=send_t1(conn,owner,req,uid(),uid())
            attempt=start_t2(conn,owner,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
            mark_attempt(conn,owner,attempt["id"],"attempt_unknown",error_code="SYNTHETIC_TIMEOUT")
            s=read_status(conn,owner,status_q(req),uid(),uid())
            self.assertEqual(s["status"],"attempt_unknown")
            self.assertIsNone(s["answer"])
            with self.assertRaises(Conflict):
                finalize_t3(conn,owner,attempt["id"],synthetic_answer(attempt,receipt),"Fake completion")
            with self.assertRaises(TypeError):
                read_status(conn,owner,status_q(req),uid(),uid(),server_commit_evidence={"verified":True})
            self.assertEqual(read_status(conn,owner,status_q(req),uid(),uid())["status"],"attempt_unknown")

    def test_HDB09_coherent_status_and_poll_order_without_replica(self):
        owner=actor_id("read")
        req=send_req()
        with db() as conn:
            receipt=send_t1(conn,owner,req,uid(),uid())
            attempt=start_t2(conn,owner,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
            pre=read_status(conn,owner,status_q(req),"current_http_a","current_trace_a")
            self.assertEqual(pre["status"],"attempt_pending")
            answer=synthetic_answer(attempt,receipt)
            finalize_t3(conn,owner,attempt["id"],answer,"Verified synthetic")
        def read(_):
            with db() as c:
                return read_status(c,owner,status_q(req),uid(),uid())
        with ThreadPoolExecutor(max_workers=6) as pool:
            snapshots=list(pool.map(read,range(12)))
        for s in snapshots:
            self.assertEqual(s["status"],"answer_committed")
            self.assertEqual(s["answer_id"],s["reserved_answer_id"])
            self.assertEqual(s["answer"]["request_id"],s["attempt_request_id"])
            self.assertEqual(s["answer"]["trace_id"],s["attempt_trace_id"])
            self.assertNotEqual(s["request_id"],s["attempt_request_id"])
        # Replica lag, HTTP response arrival and signed server revisions are NOT tested.

    def test_HDB10_rls_context_ownership_foreign_keys_and_pagination(self):
        a,b=actor_id("owner_a"),actor_id("owner_b")
        with db() as conn:
            created=create_conversation(conn,a,create_req(),uid(),uid())
            cid=created["conversation"]["conversation_id"]
            req=send_req(cid=cid)
            receipt=send_t1(conn,a,req,uid(),uid())
            attempt=start_t2(conn,a,cid,req["client_message_id"],req["idempotency_key"],uid(),uid())
            ans=synthetic_answer(attempt,receipt)
            finalize_t3(conn,a,attempt["id"],ans,"Synthetic answer text")
            with self.assertRaises(NotFound):
                read_status(conn,b,status_q(req),uid(),uid())
            with self.assertRaises(NotFound):
                list_messages(conn,b,cid)
            with self.assertRaises(NotFound):
                send_t1(conn,b,send_req(cid=cid),uid(),uid())
            self.assertEqual(list_conversations(conn,b)["items"],[])
            with conn.transaction():
                scoped(conn,a)
                role=conn.execute("""SELECT r.rolsuper,r.rolbypassrls
                  FROM pg_roles r WHERE r.rolname=current_user""").fetchone()
                self.assertFalse(role["rolsuper"])
                self.assertFalse(role["rolbypassrls"])
                self.assertEqual(conn.execute("""SELECT count(*) AS n FROM history_l1.messages
                      WHERE owner_id=%s""",(a,)).fetchone()["n"],2)
                # Same-owner row cannot reference another user's conversation.
                with self.assertRaises(ForeignKeyViolation):
                    with conn.transaction():
                        conn.execute("""INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
                          VALUES(%s,%s,%s,'user','synthetic')""",(a,uid(),uid()))
            with conn.transaction():
                # No app.owner_id is set in this fresh transaction.
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM history_l1.conversations").fetchone()["n"],0)
                with self.assertRaises(InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute("CREATE TABLE history_l1.illicit (x int)")
            with self.assertRaises(InsufficientPrivilege):
                with conn.transaction():
                    scoped(conn,a)
                    conn.execute("UPDATE history_l1.create_receipts SET created_snapshot='{}'::jsonb WHERE owner_id=%s",(a,))
            with self.assertRaises(InsufficientPrivilege):
                with conn.transaction():
                    scoped(conn,a)
                    conn.execute("UPDATE history_l1.answers SET payload='{}'::jsonb WHERE owner_id=%s",(a,))
            with conn.transaction():
                scoped(conn,a)
                attrs=conn.execute("""SELECT c.relrowsecurity,c.relforcerowsecurity
                      FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                      WHERE n.nspname='history_l1' AND c.relname='messages'""").fetchone()
                self.assertTrue(attrs["relrowsecurity"])
                self.assertTrue(attrs["relforcerowsecurity"])
            # Only test-migrator on a disposable DB can seed equal timestamps;
            # app role has no UPDATE permission on immutable Message rows.
            with db("DB_MIG_DSN") as migrator:
                with migrator.transaction():
                    migrator.execute("UPDATE history_l1.messages SET created_at=%s WHERE owner_id=%s AND conversation_id=%s",
                         ("2026-01-01T00:00:00Z",a,cid))
            page1=list_messages(conn,a,cid,limit=1)
            page2=list_messages(conn,a,cid,limit=1,last=page1["last"])
            self.assertTrue(page1["has_more"])
            self.assertFalse(page2["has_more"])
            all_ids=[x["message_id"] for x in page1["items"]+page2["items"]]
            self.assertEqual(len(set(all_ids)),2)
            for page in (page1,page2):
                self.assertEqual({x["answer_id"] for x in page["items"] if x["answer_id"]},
                                 {x["answer_id"] for x in page["answers"]})
            cpage=list_conversations(conn,a,limit=20)
            self.assertEqual(len(cpage["items"]),1)

if __name__=="__main__":
    unittest.main(verbosity=2)
