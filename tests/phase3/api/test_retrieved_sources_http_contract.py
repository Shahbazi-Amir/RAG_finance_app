"""API_F3 Gate3: real FastAPI HTTP routing with simulated signed session/DB.

These tests DO NOT prove a live Mac BFF, PostgreSQL, or C018 execution.
They exercise the production route/error mapper and verify GET has no Runner.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from apps.api import product_session_api as api
from apps.api import history_api as history


PATH = b"/v1/message-requests/retrieved-sources"
URL = ("/v1/message-requests/retrieved-sources"
       "?requested_conversation_id=&client_message_id=msg_fixture"
       "&idempotency_key=abcdefgh12345678")


class RetrievedSourcesHTTPContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.owner = "owner_A"
        self.attempt = "a"*32
        self.trace = "b"*32
        self.doc = {"owner_user_id": self.owner,
                    "attempt_id": self.attempt,
                    "attempt_trace_id": self.trace}
        self.receipt = {
            "kind": "retrieved_sources",
            "contract_version": "api.retrieved_sources.v1",
            "attempt_id": self.attempt,
            "attempt_trace_id": self.trace,
            "retrieval_state": "PARTIAL_UNVERIFIED",
            "engine_sha256": "93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d",
            "chunks_sha256": "3891c4ecad9332ba753cd605bbccd99da9d063f64934a30ee39e495349cffb50",
            "generation_calls": 0,
            "rows": [{"position":1,
                      "chunk_id": "chunk:Fixture:A",
                      "chunk_match": "PASS",
                      "source_id": "program:Fixture:A",
                      "source_validation": "UNVERIFIED",
                      "locator_validation": "PENDING_STRUCTURE",
                      "verified_locators": []}],
        }
        self.handler = Mock()
        self.handler.read_sources.return_value = self.receipt
        self.handler.__call__ = Mock()
        self.handler.reserve = Mock()
        self.ctx = {"owner": self.owner, "conn": object(),
                    "request_id": "c"*32, "trace_id": "d"*32}

    def _signed_route(self, request, body, path, action, *, coherent_read=False):
        self.assertEqual(body, b"")
        self.assertEqual(path, PATH)
        self.assertTrue(coherent_read)
        return (SimpleNamespace(owner_id=self.owner), action(self.ctx))

    def _request(self, *, handler=None, read_status=None, signed=None, method="GET"):
        with (patch.object(api, "_SERVER_NO_DISPATCH_TASK", self.handler if handler is None else handler),
              patch.object(api, "_signed_history",
                           side_effect=self._signed_route if signed is None else signed),
              patch.object(history, "_query", return_value=object()),
              patch.object(history, "read_status",
                           side_effect=read_status if read_status is not None
                           else lambda *args, **kwargs: self.doc)):
            return self.client.request(method, URL)

    def test_get_returns_attempt_bound_unverified_sources_no_runner(self):
        response = self._request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.json(), self.receipt)
        self.handler.read_sources.assert_called_once_with(
            self.owner, self.attempt, self.trace)
        self.handler.reserve.assert_not_called()
        self.handler.__call__.assert_not_called()

    def test_refresh_repeated_get_only_reads_exact_same_receipt(self):
        with (patch.object(api, "_SERVER_NO_DISPATCH_TASK", self.handler),
              patch.object(api, "_signed_history", side_effect=self._signed_route),
              patch.object(history, "_query", return_value=object()),
              patch.object(history, "read_status", return_value=self.doc)):
            first = self.client.get(URL)
            second = self.client.get(URL)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(self.handler.read_sources.call_count, 2)
        self.handler.reserve.assert_not_called()
        self.handler.__call__.assert_not_called()

    def test_unknown_no_receipt_is_not_available_without_runner(self):
        self.handler.read_sources.return_value = None
        response = self._request()
        self.assertEqual(response.status_code, 200)
        obj = response.json()
        self.assertEqual(obj["retrieval_state"], "NOT_AVAILABLE")
        self.assertEqual(obj["rows"], [])
        self.assertIsNone(obj["generation_calls"])
        self.handler.__call__.assert_not_called()

    def test_absent_t2_is_not_available_without_ledger_read(self):
        response = self._request(read_status=lambda *a, **k: {
            "owner_user_id": self.owner, "attempt_id": None,
            "attempt_trace_id": None})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["attempt_id"])
        self.handler.read_sources.assert_not_called()

    def test_foreign_owner_history_not_found_masked_404(self):
        def no_access(*args, **kwargs):
            raise history.NotFound()
        response = self._request(read_status=no_access)
        self.assertEqual(response.status_code, 404)
        self.handler.read_sources.assert_not_called()
        self.handler.__call__.assert_not_called()

    def test_mismatched_owner_never_reads_source_ledger(self):
        response = self._request(read_status=lambda *a, **k: {
            "owner_user_id": "owner_B",
            "attempt_id": self.attempt,
            "attempt_trace_id": self.trace})
        self.assertEqual(response.status_code, 401)
        self.handler.read_sources.assert_not_called()

    def test_bad_signed_service_proof_denied_401(self):
        def invalid_proof(*args, **kwargs):
            raise api.TrustRejected()
        response = self._request(signed=invalid_proof)
        self.assertEqual(response.status_code, 401)
        self.handler.read_sources.assert_not_called()

    def test_post_to_retrieved_sources_not_allowed(self):
        response = self._request(method="POST")
        self.assertEqual(response.status_code, 405)
        self.handler.read_sources.assert_not_called()

    def test_unconfigured_handler_fails_closed(self):
        # sentinel None selects fallback in _request; patch directly.
        with (patch.object(api, "_SERVER_NO_DISPATCH_TASK", None),
              patch.object(api, "_signed_history", side_effect=self._signed_route)):
            response = self.client.get(URL)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
