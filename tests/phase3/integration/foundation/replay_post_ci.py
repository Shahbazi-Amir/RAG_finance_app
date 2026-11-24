"""M10-A10: real signed POST/retry on temporary PG; explicit CI-only scope."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import secrets
import subprocess
import sys
import time
from urllib.parse import urlencode
import uuid
import unittest

import httpx
import psycopg
from psycopg.rows import dict_row

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/"tests/phase3/integration/api")]
import test_product_session_011 as base

class ReplayPostCI(base.RealProductSession011):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.lab=cls.temp/"replay-post-ci"
            cls.lab.mkdir(mode=0o700)
            cls.cursor_key=secrets.token_urlsafe(48)
            cls.stop_api()
            cls.start_api()
        except BaseException:
            cls._cleanup()
            raise

    @classmethod
    def stop_api(cls):
        assert len(cls.children)==1
        child=cls.children[0]
        child.terminate()
        try: child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
        cls.children.remove(child)

    @classmethod
    def start_api(cls):
        env={k:os.environ[k] for k in ("PATH","HOME","DB_APP_DSN","AUTH_REVOKER_DSN")}
        env.update(CI="true",GITHUB_ACTIONS="true",F3_REPLAY_PERSISTENCE_CI_ONLY="true",
                   API_RUNNER_EXECUTION_MODE="NO_DISPATCH_ONLY",
                   API_CURSOR_KEY=cls.cursor_key,API_CURSOR_TTL_SECONDS="300",
                   F3_REPLAY_LAB_DIR=str(cls.lab),
                   API_PRODUCT_PROOF_PUBLIC_KEY_PATH=str(cls.pubkey),
                   API_PRODUCT_PROOF_ISSUER=base.ISSUER,API_PRODUCT_PROOF_AUDIENCE=base.AUDIENCE,
                   API_PRODUCT_PROOF_KID=base.KID,APP_ONLY_CI_API_PORT=str(cls.api_port),
                   APP_ONLY_CI_CLIENT_CERT=cls.fixture.cert,
                   APP_ONLY_CI_SERVER_CERT=str(cls.temp/"server.pem"),
                   APP_ONLY_CI_SERVER_KEY=str(cls.temp/"server.key"),
                   APP_ONLY_CI_CLIENT_CA=cls.fixture.ca)
        env={k:str(v) for k,v in env.items()}
        child=subprocess.Popen([sys.executable,"-u",str(Path(__file__).with_name(
            "replay_post_ci_server.py"))],cwd=ROOT,env=env,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cls.children.append(child)
        for _ in range(100):
            if child.poll() is not None:
                raise AssertionError("REPLAY_CI_SERVER_EXITED")
            try:
                with httpx.Client(verify=cls.tls,trust_env=False,timeout=1) as c:
                    if c.get(cls.url+base.LIST).status_code==401:
                        return
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        raise AssertionError("REPLAY_CI_SERVER_NOT_READY")

    def snapshot(self,owner,client,key):
        with psycopg.connect(os.environ["DB_MIG_DSN"],autocommit=True,
                             row_factory=dict_row) as c:
            rows=c.execute("""SELECT r.id AS receipt_id,r.user_message_id,
                r.resolved_conversation_id,r.initial_request_id,r.initial_trace_id,
                t.id AS attempt_id,t.attempt_request_id,t.attempt_trace_id,t.state
                FROM history_l1.send_receipts r JOIN history_l1.execution_attempts t
                ON t.owner_id=r.owner_id AND t.send_receipt_id=r.id
                WHERE r.owner_id=%s AND r.client_message_id=%s AND r.idempotency_key=%s""",
                (owner,client,key)).fetchall()
            if not rows: return None
            self.assertEqual(len(rows),1)
            r=rows[0]
            counts=c.execute("""SELECT
                (SELECT count(*) FROM history_l1.send_receipts
                 WHERE owner_id=%s AND client_message_id=%s AND idempotency_key=%s) AS t1,
                (SELECT count(*) FROM history_l1.execution_attempts
                 WHERE owner_id=%s AND send_receipt_id=%s) AS t2,
                (SELECT count(*) FROM history_l1.messages
                 WHERE owner_id=%s AND conversation_id=%s AND role='user') AS user_messages,
                (SELECT count(*) FROM history_l1.answers
                 WHERE owner_id=%s AND attempt_id=%s) AS t3""",
                (owner,client,key,owner,r["receipt_id"],owner,r["resolved_conversation_id"],
                 owner,r["attempt_id"])).fetchone()
            self.assertEqual(counts,{"t1":1,"t2":1,"user_messages":1,"t3":0})
            return r

    def callback_witness(self,row):
        for _ in range(100):
            with sqlite3.connect(self.lab/"outcomes.sqlite") as c:
                records=c.execute("SELECT attempt_id,product_request_id,trace_id,state FROM outcomes").fetchall()
            if records and records[0][3]=="UNKNOWN": break
            time.sleep(.05)
        self.assertEqual(records,[(row["attempt_id"],row["attempt_request_id"],
                                    row["attempt_trace_id"],"UNKNOWN")])
        self.assertEqual((self.lab/"callback-counts").read_text().splitlines(),["reserve","callback"])

    def test_actual_post_retry_parallel_conflict_restart_and_revoke(self):
        a,b=self.login("A"),self.login("B")
        self.assertNotEqual(a["owner_id"],b["owner_id"])
        payload={"kind":"send_message_request","contract_version":"product.v1",
                 "requested_conversation_id":None,"client_message_id":base.history_api.uid(),
                 "idempotency_key":"replay_ci_"+uuid.uuid4().hex,
                 "question":"synthetic replay persistence CI only"}
        def post(actor,doc,cert=True):
            body=json.dumps(doc,separators=(",",":")).encode()
            token,claims=self.signed(actor,"POST","/v1/messages",body)
            r=self.request("POST","/v1/messages",token,body=body,cert=cert)
            if r is not None:
                self.assertEqual(r.headers.get("cache-control"),"no-store")
            return r,claims["jti"]
        self.assertIsNone(self.snapshot(a["owner_id"],payload["client_message_id"],payload["idempotency_key"]))
        missing,_=post(a,payload,cert=False)
        self.assertTrue(missing is None or missing.status_code==401)
        # Eight actual fresh signed HTTP requests, same application key.
        with ThreadPoolExecutor(max_workers=8) as pool:
            replies=list(pool.map(lambda _:post(a,payload),range(8)))
        self.assertEqual(len({j for _,j in replies}),8)
        self.assertEqual(sorted(r.status_code for r,_ in replies),[200]*7+[202])
        docs=[r.json() for r,_ in replies]
        self.assertEqual(sum(d["disposition"]=="created" for d in docs),1)
        self.assertEqual(sum(d["disposition"]=="replayed" for d in docs),7)
        self.assertEqual(len({d["message_id"] for d in docs}),1)
        self.assertEqual(len({d["resolved_conversation_id"] for d in docs}),1)
        self.assertEqual(len({d["request_id"] for d in docs}),8)
        def snap():
            return self.snapshot(a["owner_id"],payload["client_message_id"],payload["idempotency_key"])
        original=snap()
        self.assertEqual(original["user_message_id"],docs[0]["message_id"])
        self.assertEqual(original["resolved_conversation_id"],docs[0]["resolved_conversation_id"])
        self.callback_witness(original)
        bad,_=post(a,{**payload,"question":"different synthetic payload"})
        self.assertEqual(bad.status_code,409)
        foreign,_=post(b,{**payload,"requested_conversation_id":original["resolved_conversation_id"]})
        self.assertEqual(foreign.status_code,404)
        self.assertEqual(snap(),original)
        self.assertIsNone(self.snapshot(b["owner_id"],payload["client_message_id"],payload["idempotency_key"]))
        type(self).stop_api()
        type(self).start_api()
        again,_=post(a,payload)
        self.assertEqual(again.status_code,200)
        self.assertEqual(again.json()["disposition"],"replayed")
        self.assertEqual(again.json()["message_id"],original["user_message_id"])
        endpoint="/v1/message-requests/status"
        # The canonical status contract represents the original null conversation
        # by omitting the optional requested_conversation_id parameter.
        query="?"+urlencode({"client_message_id":payload["client_message_id"],
                            "idempotency_key":payload["idempotency_key"]})
        def status(actor):
            token,_=self.signed(actor,"GET",endpoint,query=query[1:].encode())
            return self.request("GET",endpoint,token,query=query)
        observed=status(a)
        self.assertEqual(observed.status_code,200)
        self.assertEqual(observed.json()["attempt_id"],original["attempt_id"])
        self.assertEqual(observed.json()["attempt_request_id"],original["attempt_request_id"])
        self.assertIsNone(observed.json()["answer"])
        self.assertEqual(status(b).status_code,404)
        raw=json.dumps({"operation_id":str(uuid.uuid4())},separators=(",",":")).encode()
        token,_=self.signed(a,"POST",base.REVOKE,raw)
        self.assertEqual(self.request("POST",base.REVOKE,token,body=raw).status_code,200)
        revoked,_=post(a,payload)
        self.assertEqual(revoked.status_code,401)
        self.assertEqual(status(a).status_code,401)
        self.assertEqual(self.list(b).status_code,200)
        self.assertEqual(snap(),original)
        self.callback_witness(original)
        print("F3_M10_A10_REAL_SIGNED_POST_8_CONCURRENT_RESTART_REPLAY_ZERO_T3_PASS",flush=True)

if __name__=="__main__":
    suite=unittest.TestSuite([ReplayPostCI("test_actual_post_retry_parallel_conflict_restart_and_revoke")])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
