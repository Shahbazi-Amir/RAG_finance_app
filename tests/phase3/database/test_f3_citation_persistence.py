"""Actual synthetic L1 SQL persistence only, never a product Answer or engine."""
import copy
import json
import os
from pathlib import Path
import unittest
from jsonschema import ValidationError
from test_history_l1 import db, actor_id, send_req, status_q, synthetic_answer
from repository import (uid, scoped, send_t1, start_t2, finalize_t3, read_status,
                        list_messages, NotFound, InjectedRollback, Conflict)

class F3CitationPersistence(unittest.TestCase):
    def test_jsonb_claim_source_unknown_provenance_atomic_and_immutable(self):
        self.assertEqual(os.environ.get("GITHUB_ACTIONS"),"true")
        a,b=actor_id("citation_a"),actor_id("citation_b")
        req=send_req()
        with db() as c:
            receipt=send_t1(c,a,req,uid(),uid())
            att=start_t2(c,a,None,req["client_message_id"],req["idempotency_key"],uid(),uid())
            answer=synthetic_answer(att,receipt)
            answer["claims"].append({"claim_id":"claim_2","text":"ادعای دوم صرفاً آزمایشی","citation_ids":["cite_2"]})
            second=copy.deepcopy(answer["citations"][0])
            second.update(citation_id="cite_2",claim_ids=["claim_2"])
            answer["citations"].append(second)
            forged=copy.deepcopy(answer)
            forged["provenance"]["rag_binding"]["release_id"]="invented_release"
            with self.assertRaises((ValidationError,ValueError)):
                finalize_t3(c,a,att["id"],forged,"forged provenance")
            with self.assertRaises(InjectedRollback):
                finalize_t3(c,a,att["id"],answer,"synthetic L1",rollback=True)
            self.assertIsNone(read_status(c,a,status_q(req),uid(),uid())["answer"])
            with self.assertRaises(NotFound):
                finalize_t3(c,b,att["id"],answer,"foreign")
            finalize_t3(c,a,att["id"],answer,"synthetic L1")
            self.assertEqual(finalize_t3(c,a,att["id"],answer,"synthetic L1"),answer)
            changed=copy.deepcopy(answer);changed["claims"][0]["text"]="changed"
            with self.assertRaises(Conflict):
                finalize_t3(c,a,att["id"],changed,"changed")
            with db() as fresh:
                loaded=read_status(fresh,a,status_q(req),uid(),uid())
                self.assertEqual(loaded["answer"],answer)
                self.assertEqual(loaded["attempt_request_id"],att["attempt_request_id"])
                self.assertEqual(loaded["attempt_trace_id"],att["attempt_trace_id"])
                self.assertEqual(loaded["answer"]["provenance"]["rag_binding"],
                    {"status":"provisional","blocked_by":"NB23","release_id":None,"adapter_verified":False})
                page=list_messages(fresh,a,receipt["resolved_conversation_id"],limit=20)
                self.assertEqual(page["answers"],[answer])
                self.assertEqual(len(page["items"]),2)
                with self.assertRaises(NotFound):
                    list_messages(fresh,b,receipt["resolved_conversation_id"])
            with db("DB_MIG_DSN") as mig:
                row=mig.execute("""SELECT jsonb_array_length(payload->'claims') AS claims,
                    jsonb_array_length(payload->'citations') AS cites,
                    payload->'provenance' AS provenance FROM history_l1.answers
                    WHERE owner_id=%s AND attempt_id=%s""",(a,att["id"])).fetchone()
                self.assertEqual((row["claims"],row["cites"]),(2,2))
                self.assertEqual(row["provenance"],answer["provenance"])
                self.assertEqual(mig.execute("SELECT count(*) AS n FROM history_l1.answers WHERE owner_id=%s AND attempt_id=%s",(a,att["id"])).fetchone()["n"],1)
        out=Path(__file__).resolve().parents[3]/"ci_receipts/f3_synthetic_citation_persistence.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
          "scope":"REAL_PG_HISTORY_L1_SYNTHETIC_FIXTURE_NOT_APP_ONLY_SEND",
          "claims":2,"citations":2,"exact_jsonb_after_reconnect":True,"t3_rollback_denied_partial":True,
          "foreign_read_write_denied":True,"immutable_replay":True,"invented_release_rejected":True,
          "source_locator_verified":False,"model_policy_versions_available":False,"engine_calls":0,"accepted":False},indent=2)+"\n")
        print("F3_CITATION_JSONB_ATOMIC_ROLLBACK_RECONNECT_IMMUTABLE_SYNTHETIC_PASS")
