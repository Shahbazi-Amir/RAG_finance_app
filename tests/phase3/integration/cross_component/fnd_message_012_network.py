"""Foundation cross-component network proof for the unmodified #52 Fixture.

Never deploy: only on an ephemeral CI PostgreSQL 17.11 / real Keycloak 26.8.2,
and real mTLS uvicorn from #50's already tested test harness. No paid engine.
"""
import json
import os
import secrets
import unittest
import uuid
from urllib.parse import urlencode

from test_product_session_011 import RealProductSession011, REVOKE

SEND = "/v1/messages"
STATUS = "/v1/message-requests/status"


class FoundationFixtureNetwork012(RealProductSession011):
    """Only the explicitly named network method is executed by this workflow.

    Reuse the exact #50 CA/client cert, actual HTTPS uvicorn and Keycloak login.
    Do not use browser-generated identities, TestClient, route.fulfill or mocks.
    """

    def test_FND_NET012_real_mtls_fixture_send_owner_revocation(self):
        self.assertEqual(os.environ.get("CI"), "true")
        self.assertEqual(os.environ.get("GITHUB_ACTIONS"), "true")
        a, b = self.login("A"), self.login("B")
        self.assertNotEqual(a["owner_id"], b["owner_id"])
        payload = {
            "kind": "send_message_request",
            "contract_version": "product.v1",
            "requested_conversation_id": None,
            "question": "نمونهٔ پرسش آزمایشیِ ایزوله چیست؟",
            "client_message_id": secrets.token_hex(16),
            "idempotency_key": secrets.token_hex(16),
        }
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        token, _ = self.signed(a, "POST", SEND, raw)
        first = self.request("POST", SEND, token, body=raw)
        self.assertEqual(first.status_code, 202, first.text)
        receipt = first.json()
        self.assertTrue(receipt["resolved_conversation_id"])
        # A new valid signed JTI on the identical operation must NOT run T2 again.
        replay = self.request("POST", SEND, self.signed(a, "POST", SEND, raw)[0], body=raw)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["message_id"], receipt["message_id"])
        changed = {**payload, "question": "سؤال متفاوت"}
        changed_raw = json.dumps(changed, ensure_ascii=False, separators=(",", ":")).encode()
        conflict = self.request("POST", SEND, self.signed(a, "POST", SEND, changed_raw)[0],
                                body=changed_raw)
        self.assertEqual(conflict.status_code, 409, conflict.text)

        query = urlencode({k: payload[k] for k in
                           ("requested_conversation_id", "client_message_id", "idempotency_key")
                           if payload[k] is not None})
        status_token, _ = self.signed(a, "GET", STATUS, query=query.encode())
        status_res = self.request("GET", STATUS, status_token, query="?" + query)
        self.assertEqual(status_res.status_code, 200, status_res.text)
        result = status_res.json()
        self.assertEqual(result["status"], "answer_committed")
        answer = result["answer"]
        self.assertEqual(answer["provenance"]["origin"], "SYNTHETIC")
        self.assertEqual(answer["provenance"]["rag_binding"]["status"], "provisional")
        self.assertIsNone(answer["provenance"]["rag_binding"]["release_id"])
        self.assertIsNone(answer["provenance"]["source_fingerprint"])
        self.assertEqual(answer["citations"][0]["source"]["resolution_status"], "unresolved")
        path = "/v1/conversations/" + receipt["resolved_conversation_id"] + "/messages"
        page = self.request("GET", path, self.signed(a, "GET", path)[0])
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual([m["role"] for m in page.json()["items"]], ["user", "assistant"])
        self.assertEqual(page.json()["answers"][0]["provenance"]["origin"], "SYNTHETIC")
        self.assertEqual(self.request("GET", path, self.signed(b, "GET", path)[0]).status_code, 404)

        # Genuine network-level mTLS denial; a valid signed bearer is insufficient.
        self.assertIsNone(self.request("POST", SEND, self.signed(a, "POST", SEND, raw)[0],
                                       body=raw, cert=False))
        self.assertEqual(self.request("POST", SEND,
                         self.signed(a, "POST", SEND, b"{}")[0], body=raw).status_code, 401)
        self.assertEqual(self.request("GET", STATUS,
                         self.signed(b, "GET", STATUS, query=query.encode())[0],
                         query="?" + query).status_code, 404)

        op = json.dumps({"operation_id": str(uuid.uuid4())}, separators=(",", ":")).encode()
        revoked = self.request("POST", REVOKE, self.signed(a, "POST", REVOKE, op)[0], body=op)
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(revoked.json()["state"], "REVOKED_COMMITTED")
        self.assertEqual(self.request("GET", path, self.signed(a, "GET", path)[0]).status_code, 401)
        self.assertEqual(self.request("GET", "/v1/conversations",
                         self.signed(b)[0]).status_code, 200)
        print("FND_NET012_REAL_KEYCLOAK_MTLS_PG_FIXTURE_AB_REVOKE_PASS", flush=True)
        print("FND_NET012_SYNTHETIC_UNRESOLVED_NOT_LIVE_VERIFIED_PASS", flush=True)


if __name__ == "__main__":
    raise SystemExit("CI runner must select the single FND_NET012 method explicitly")
