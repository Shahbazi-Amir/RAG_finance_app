"""Real signed ASGI HTTP + disposable PG 001-011 + DB Claim + counted stub.

Foundation-owned CI MUST install DB #56 exact SHA b0ba6dbf6100109cb58f8cb49da808839d68c5f0
onto ephemeral PG17, plus existing signed 003/004/005 function-only grants.
This test never creates roles, runs Migration, contacts a Gateway, or writes staging.
Real CA-verified mTLS NETWORK test remains a separate Foundation obligation.
"""
from __future__ import annotations

import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row
import test_product_message_fixture_012 as fixture

from apps.api import product_session_api as api
from src.phase3.rag_runtime.dispatch_claim_test_stub import CountOnlyGatewayStub

CLAIM_STATUS = "/v1/message-requests/claim-test-status"


class SignedClaimDispatchHttp011(unittest.TestCase):
    def setUp(self):
        if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
            self.fail("DISPOSABLE_POSTGRES_GITHUB_ACTIONS_ONLY")
        if os.getenv("DB_APP_DSN", "").find("dbname=history_ci") < 0:
            self.fail("ONLY_HISTORY_CI_ALLOWED")
        if not os.getenv("DISPATCH_REPORTER_DSN", "").endswith("connect_timeout=5"):
            # Harness must supply explicit strict synthetic role DSN.
            self.fail("MISSING_CI_ONLY_REPORTER_DSN")
        self.mode = self.enterContext(patch.dict(
            os.environ, {"API_RUNNER_EXECUTION_MODE": "CLAIM_STUB_CI_ONLY"}))
        self.enterContext(patch.object(api, "_CI_CLAIM_STUB", None))
        self.enterContext(patch.object(api, "_CI_DISPATCH_REPORTER_DSN", None))
        self.helper = fixture.SignedFixtureTest(
            "test_registered_answer_and_access_are_owner_scoped")
        self.helper.setUp()  # genuinely signed RS256 proof, real 003/004/005 PG
        self.addCleanup(self.helper.doCleanups)
        self.a, self.b = self.helper.a, self.helper.b
        self.client = self.helper.client
        self.stub = CountOnlyGatewayStub()
        api.install_ci_count_only_dispatch(
            self.stub, os.environ["DISPATCH_REPORTER_DSN"])

    def msg(self):
        return self.helper.message()

    def send(self, session, msg):
        return self.helper.call(session, "POST", "/v1/messages", body=msg)

    def status(self, session, msg):
        q = urlencode({k: msg[k] for k in (
            "requested_conversation_id", "client_message_id", "idempotency_key")
            if msg[k] is not None})
        return self.helper.call(session, "GET", CLAIM_STATUS, query=q)

    def check_pg011(self):
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as conn:
            row = conn.execute(
                "SELECT to_regprocedure("
                "'history_l1.claim_external_dispatch(text,text,text)') IS NOT NULL "
                "AS present").fetchone()
            self.assertTrue(row["present"], "exact DB #56 011 not applied")
            row = conn.execute(
                "SELECT has_function_privilege(current_user,"
                "'history_l1.claim_external_dispatch(text,text,text)',"
                "'EXECUTE') AS can").fetchone()
            self.assertTrue(row["can"])

    def test_HTTP01_concurrent_signed_post_one_committed_claim_one_send(self):
        self.check_pg011()
        msg = self.msg()
        with ThreadPoolExecutor(max_workers=2) as executor:
            fs = [executor.submit(self.send, self.a, msg) for _ in range(2)]
            responses = [f.result(timeout=30) for f in fs]
        self.assertEqual(sorted(r.status_code for r in responses), [200, 202],
                         [r.text for r in responses])
        self.assertEqual(responses[0].json()["message_id"],
                         responses[1].json()["message_id"])
        status = self.status(self.a, msg)
        self.assertEqual(status.status_code, 200, status.text)
        document = status.json()
        self.assertEqual(document["dispatch_state"], "CLAIMED")
        self.assertEqual(document["product_status"], "attempt_pending")
        self.assertIsNone(document["answer"])
        attempt = document["attempt_id"]
        self.assertEqual(self.stub.count(attempt), 1)
        for _ in range(4):
            same = self.status(self.a, msg)
            self.assertEqual(same.status_code, 200)
        self.assertEqual(self.stub.count(attempt), 1)
        print("API53_HTTP011_CONCURRENT_A_202_200_GATEWAY_BOUNDARY_COUNT=1", flush=True)

    def test_HTTP02_replay_poll_refresh_only_signed_get_and_B_hidden(self):
        msg = self.msg()
        self.assertEqual(self.send(self.a, msg).status_code, 202)
        result = self.status(self.a, msg)
        self.assertEqual(result.status_code, 200)
        id1 = result.json()["attempt_id"]
        for _ in range(3):
            self.assertEqual(self.status(self.a, msg).status_code, 200)
        self.assertEqual(self.send(self.a, msg).status_code, 200)
        self.assertEqual(self.stub.count(id1), 1)
        self.assertEqual(self.status(self.b, msg).status_code, 404)
        self.assertEqual(self.helper.status(self.b, msg).status_code, 404)
        self.assertEqual(self.stub.count(), 1)
        print("API53_HTTP011_REPLAY_COUNT=0_POLL_COUNT=0_B_READ=404", flush=True)

    def test_HTTP03_commit_ack_unknown_zero_send_and_replay_no_reclaim(self):
        original = api._signed_history
        msg = self.msg()
        def lost_ack(*args, **kwargs):
            original(*args, **kwargs)  # actual PostgreSQL COMMIT before ACK lost
            raise OSError("SYNTHETIC_COMMIT_ACK_LOSS")
        with patch.object(api, "_signed_history", side_effect=lost_ack):
            unknown = self.send(self.a, msg)
        self.assertNotEqual(unknown.status_code, 202)
        self.assertEqual(self.stub.count(), 0)
        replay = self.send(self.a, msg)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(self.stub.count(), 0)
        read = self.status(self.a, msg)
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["dispatch_state"], "CLAIMED")
        print("API53_HTTP011_UNKNOWN_COMMIT_GATEWAY_BOUNDARY_COUNT=0", flush=True)

    def test_HTTP04_timeout_after_count_persists_UNKNOWN_never_retry(self):
        msg = self.msg()
        self.stub.set_default_outcome("TIMEOUT")
        response = self.send(self.a, msg)
        self.assertEqual(response.status_code, 202, response.text)
        status = self.status(self.a, msg)
        self.assertEqual(status.status_code, 200, status.text)
        self.assertEqual(status.json()["dispatch_state"], "UNKNOWN")
        self.assertEqual(self.stub.count(status.json()["attempt_id"]), 1)
        self.assertEqual(self.send(self.a, msg).status_code, 200)
        for _ in range(3):
            self.assertEqual(self.status(self.a, msg).json()["dispatch_state"], "UNKNOWN")
        self.assertEqual(self.stub.count(), 1)
        print("API53_HTTP011_TIMEOUT_AFTER_SEND_COUNT=1_UNKNOWN_NO_RETRY", flush=True)

    def test_HTTP05_lost_response_after_count_unknown_no_retry(self):
        msg = self.msg()
        self.stub.set_default_outcome("LOST_RESPONSE")
        first = self.send(self.a, msg)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(self.status(self.a, msg).json()["dispatch_state"], "UNKNOWN")
        self.assertEqual(self.stub.count(), 1)
        self.assertEqual(self.send(self.a, msg).status_code, 200)
        self.assertEqual(self.stub.count(), 1)
        print("API53_HTTP011_LOST_RESPONSE_SEND_COUNT=1_UNKNOWN_NO_RETRY", flush=True)

    def test_HTTP06_unconfigured_stub_503_before_any_claim(self):
        msg = self.msg()
        with patch.object(api, "_CI_CLAIM_STUB", None):
            refused = self.send(self.a, msg)
            self.assertEqual(refused.status_code, 503)
        self.assertEqual(self.helper.status(self.a, msg).status_code, 404)
        self.assertEqual(self.stub.count(), 0)
        print("API53_HTTP011_UNCONFIGURED_GATEWAY_BOUNDARY_COUNT=0", flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
