"""Real signed ASGI HTTP + disposable PostgreSQL DB011 + fixed counted Gateway.

Must be run by Foundation-owned isolated PG17 workflow. NEVER real Gateway,
staging credentials, .env, Arvan SSH, Phase2 runner or product.v1 T3.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

import test_product_message_fixture_012 as fixture

from apps.api import product_session_api as api
from src.phase3.rag_runtime.staging_invited_result_fixture import (
    FixedInvitedGatewayStub, PrivateFixtureResultLedger, FIXTURE_ANSWER, VERSION,
)

RESULT_ROUTE = "/v1/message-requests/invited-live-result"


class SignedInvitedResult015HTTP(unittest.TestCase):
    def setUp(self):
        if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
                or "dbname=history_ci" not in os.getenv("DB_APP_DSN", "")):
            self.fail("REAL_PG_DISPOSABLE_CI_ONLY")
        self.enterContext(patch.dict(os.environ, {
            "API_RUNNER_EXECUTION_MODE": "INVITED_RESULT_STUB_CI_ONLY"}))
        for name in ("_CI_CLAIM_STUB", "_CI_DISPATCH_REPORTER_DSN",
                     "_CI_INVITED_RESULT_STORE"):
            self.enterContext(patch.object(api, name, None))
        self.helper = fixture.SignedFixtureTest(
            "test_registered_answer_and_access_are_owner_scoped")
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.a, self.b = self.helper.a, self.helper.b
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        folder.chmod(0o700)
        self.file = folder / "result.sqlite3"
        self.store = PrivateFixtureResultLedger(self.file)
        self.gateway = FixedInvitedGatewayStub()
        api.install_ci_invited_result_fixture(
            self.store, self.gateway, os.environ["DISPATCH_REPORTER_DSN"])

    def query(self, msg):
        return urlencode({k: msg[k] for k in (
            "requested_conversation_id", "client_message_id", "idempotency_key")
            if msg[k] is not None})

    def send(self, session, msg):
        return self.helper.call(session, "POST", "/v1/messages", body=msg)

    def result(self, session, msg):
        return self.helper.call(session, "GET", RESULT_ROUTE,
                                query=self.query(msg))

    def test_LR01_A_202_stable_attempt_and_exact_synthetic_answer_citation(self):
        msg = self.helper.message()
        first = self.send(self.a, msg)
        self.assertEqual(first.status_code, 202, first.text)
        receipt = first.json()
        ready = self.result(self.a, msg)
        self.assertEqual(ready.status_code, 200, ready.text)
        result = ready.json()
        self.assertEqual(result["contract_version"], VERSION)
        self.assertEqual(result["result_status"], "READY")
        self.assertEqual(result["owner_user_id"], self.a.owner_id)
        self.assertEqual(result["resolved_conversation_id"],
                         receipt["resolved_conversation_id"])
        self.assertEqual(result["requested_conversation_id"], None)
        self.assertEqual(result["client_message_id"], msg["client_message_id"])
        self.assertEqual(result["idempotency_key"], msg["idempotency_key"])
        self.assertEqual(result["answer"], FIXTURE_ANSWER)
        self.assertEqual(result["provenance"]["state"], "UNVERIFIED_STAGING")
        self.assertFalse(result["provenance"]["product_live_verified"])
        self.assertEqual(self.gateway.count(result["attempt_id"]), 1)
        product = self.helper.status(self.a, msg).json()
        self.assertEqual(product["attempt_id"], result["attempt_id"])
        self.assertEqual(product["attempt_request_id"], result["attempt_request_id"])
        self.assertEqual(product["attempt_trace_id"], result["attempt_trace_id"])
        self.assertEqual(product["status"], "attempt_pending")
        self.assertIsNone(product["answer"])
        thread = self.helper.call(self.a, "GET",
            "/v1/conversations/" + receipt["resolved_conversation_id"] + "/messages")
        self.assertEqual(thread.status_code, 200)
        self.assertEqual(thread.json()["answers"], [])
        self.assertEqual([m["role"] for m in thread.json()["items"]], ["user"])
        print("LR01_SIGNED_A_202_SAME_T2_READY_CITATION_GATEWAY_STUB=1", flush=True)

    def test_LR02_refresh_poll_replay_and_new_ledger_handle_zero_additional_send(self):
        msg = self.helper.message()
        self.assertEqual(self.send(self.a, msg).status_code, 202)
        first = self.result(self.a, msg).json()
        for _ in range(6):
            later = self.result(self.a, msg).json()
            self.assertEqual(later["attempt_id"], first["attempt_id"])
            self.assertEqual(later["attempt_trace_id"], first["attempt_trace_id"])
            self.assertEqual(later["answer"], first["answer"])
        with patch.object(api, "_CI_INVITED_RESULT_STORE",
                          PrivateFixtureResultLedger(self.file)):
            same = self.result(self.a, msg)
        self.assertEqual(same.status_code, 200)
        self.assertEqual(same.json()["answer"], first["answer"])
        self.assertEqual(self.send(self.a, msg).status_code, 200)
        self.assertEqual(self.gateway.count(), 1)
        print("LR02_REFRESH_POLL_REPLAY_PERSISTENT_RESULT_EXTRA_SEND=0", flush=True)

    def test_LR03_B_404_and_revocation_A_401_no_result_or_send(self):
        msg = self.helper.message()
        self.assertEqual(self.send(self.a, msg).status_code, 202)
        self.assertEqual(self.result(self.b, msg).status_code, 404)
        self.assertEqual(self.helper.status(self.b, msg).status_code, 404)
        self.assertEqual(self.gateway.count(), 1)
        self.helper.revoke(self.a)
        self.assertEqual(self.result(self.a, msg).status_code, 401)
        self.assertEqual(self.gateway.count(), 1)
        print("LR03_B404_REVOKED_A401_GATEWAY_EXTRA_SEND=0", flush=True)

    def test_LR04_commit_ack_unknown_zero_stub_and_replay_remains_same_attempt(self):
        msg = self.helper.message()
        original = api._signed_history
        def lose_commit_ack(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("synthetic lost commit acknowledgment")
        with patch.object(api, "_signed_history", side_effect=lose_commit_ack):
            first = self.send(self.a, msg)
        self.assertEqual(first.status_code, 503)
        self.assertEqual(self.gateway.count(), 0)
        self.assertEqual(self.send(self.a, msg).status_code, 200)
        self.assertEqual(self.gateway.count(), 0)
        view = self.result(self.a, msg)
        self.assertEqual(view.status_code, 200)
        self.assertEqual(view.json()["result_status"], "UNKNOWN")
        self.assertIsNone(view.json()["answer"])
        print("LR04_LOST_COMMIT_ACK_STUB_SEND=0_NO_RECLAIM", flush=True)

    def test_LR05_gateway_timeout_unknown_no_answer_and_no_second_send(self):
        msg = self.helper.message()
        self.gateway.set_default_outcome("TIMEOUT")
        self.assertEqual(self.send(self.a, msg).status_code, 202)
        first = self.result(self.a, msg)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["result_status"], "UNKNOWN")
        self.assertIsNone(first.json()["answer"])
        for _ in range(3):
            self.assertEqual(self.result(self.a, msg).json()["result_status"], "UNKNOWN")
        self.assertEqual(self.send(self.a, msg).status_code, 200)
        self.assertEqual(self.gateway.count(), 1)
        print("LR05_GATEWAY_TIMEOUT_AFTER_ONE_STUB_UNKNOWN_NO_RETRY", flush=True)

    def test_LR06_uninstalled_fixture_fail_closed_before_T1(self):
        msg = self.helper.message()
        with patch.object(api, "_CI_INVITED_RESULT_STORE", None):
            self.assertEqual(self.send(self.a, msg).status_code, 503)
            self.assertEqual(self.result(self.a, msg).status_code, 503)
        self.assertEqual(self.helper.status(self.a, msg).status_code, 404)
        self.assertEqual(self.gateway.count(), 0)
        print("LR06_NOT_INSTALLED_STUB_ZERO_POST_GATEWAY", flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
