"""Strict CI-only synthetic invited result: no PG, no real Gateway."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from src.phase3.rag_runtime.dispatch_claim_bridge import CommittedDispatchPermit
from src.phase3.rag_runtime.staging_preflight import AttemptBinding, PreflightDenied
from src.phase3.rag_runtime import staging_invited_result_fixture as fixture


class InvitedResultFixtureTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {
            "CI": "true", "GITHUB_ACTIONS": "true"}))
        temp = self.enterContext(tempfile.TemporaryDirectory())
        folder = Path(temp)
        folder.chmod(0o700)
        self.path = folder / "invited_results.sqlite3"
        self.store = fixture.PrivateFixtureResultLedger(self.path)
        self.a = self.binding()
        self.gateway = fixture.FixedInvitedGatewayStub()
        self.permit = CommittedDispatchPermit(
            self.a.owner_user_id,
            AttemptBinding(self.a.attempt_id, self.a.attempt_request_id,
                           self.a.attempt_trace_id),
            uuid4())

    def binding(self, **replace):
        x = {
            "owner_user_id": "owner_A",
            "session_ref_sha256": hashlib.sha256(b"synthetic-session-A").hexdigest(),
            "session_epoch": 0, "session_generation": 0,
            "requested_conversation_id": None,
            "resolved_conversation_id": "c" * 32,
            "client_message_id": "m" * 32,
            "idempotency_key": "key_synthetic_A_123456",
            "attempt_id": "a" * 32,
            "attempt_request_id": "b" * 32,
            "attempt_trace_id": "d" * 32,
        }
        x.update(replace)
        return fixture.InvitedBinding(**x)

    def test_01_fixed_gateway_one_count_and_recovery_after_new_store_instance(self):
        self.assertTrue(self.store.reserve(self.a))
        self.assertEqual(self.store.read(self.a)["result_status"], "PENDING")
        generated = self.gateway(self.permit, "synthetic Persian question")
        self.assertEqual(self.gateway.count(), 1)
        self.assertTrue(self.store.ready(self.a, generated))
        self.assertEqual(self.store.read(self.a)["result_status"], "READY")
        self.assertEqual(self.store.read(self.a)["answer"], fixture.FIXTURE_ANSWER)
        new_process_like_store = fixture.PrivateFixtureResultLedger(self.path)
        for _ in range(5):
            self.assertEqual(new_process_like_store.read(self.a)["answer"], generated)
        self.assertFalse(new_process_like_store.reserve(self.a))
        self.assertEqual(self.gateway.count(), 1)

    def test_02_owner_B_denied_even_when_attempt_id_known(self):
        self.store.reserve(self.a)
        self.store.ready(self.a, fixture.FIXTURE_ANSWER)
        with self.assertRaises(PreflightDenied):
            self.store.read(self.binding(owner_user_id="owner_B"))
        self.assertEqual(self.gateway.count(), 0)

    def test_03_conversation_and_attempt_trace_cannot_be_swapped(self):
        self.store.reserve(self.a)
        for foreign in (
            self.binding(resolved_conversation_id="e" * 32),
            self.binding(attempt_trace_id="e" * 32),
            self.binding(attempt_request_id="e" * 32),
            self.binding(idempotency_key="wrong-same-attempt"),
            self.binding(client_message_id="f" * 32),
            self.binding(requested_conversation_id="g" * 32),
        ):
            with self.subTest(foreign=repr(foreign)), self.assertRaises(PreflightDenied):
                self.store.read(foreign)

    def test_04_session_verifier_epoch_and_generation_all_bound(self):
        self.store.reserve(self.a)
        for change in (
            {"session_ref_sha256": hashlib.sha256(b"new-session").hexdigest()},
            {"session_epoch": 1},
            {"session_generation": 1},
        ):
            with self.assertRaises(PreflightDenied):
                self.store.read(self.binding(**change))

    def test_05_no_reinsert_or_rewrite_after_ready_or_unknown(self):
        self.store.reserve(self.a)
        self.assertTrue(self.store.ready(self.a, fixture.FIXTURE_ANSWER))
        self.assertFalse(self.store.ready(self.a, fixture.FIXTURE_ANSWER))
        self.assertFalse(self.store.unknown(self.a))
        self.assertFalse(self.store.reserve(self.a))
        self.assertEqual(self.store.read(self.a)["result_status"], "READY")
        other = self.binding(attempt_id="e" * 32)
        self.store.reserve(other)
        self.assertTrue(self.store.unknown(other))
        self.assertFalse(self.store.ready(other, fixture.FIXTURE_ANSWER))
        self.assertEqual(self.store.read(other)["answer"], None)

    def test_06_reject_arbitrary_answer_or_forged_locator(self):
        self.store.reserve(self.a)
        untrusted = {"text": "FAKE LIVE VERIFIED",
                     "citations": [{"locator": "https://arbitrary.example"}]}
        with self.assertRaises(PreflightDenied):
            self.store.ready(self.a, untrusted)
        self.assertEqual(self.store.read(self.a)["result_status"], "PENDING")
        self.assertIsNone(fixture.FIXTURE_ANSWER["citations"][0]["locator"])
        self.assertIsNone(fixture.FIXTURE_ANSWER["citations"][0]["excerpt"])

    def test_07_fail_closed_when_ttl_expires_no_refresh_resend(self):
        start = 1000000000
        with patch.object(fixture.time, "time", return_value=start):
            self.assertTrue(self.store.reserve(self.a))
            self.assertTrue(self.store.ready(self.a, fixture.FIXTURE_ANSWER))
        with patch.object(fixture.time, "time", return_value=start + 901):
            got = self.store.read(self.a)
            self.assertEqual(got["result_status"], "UNKNOWN")
            self.assertIsNone(got["answer"])
            self.assertFalse(self.store.reserve(self.a))
            self.assertEqual(self.store.purge_expired(), 1)
        self.assertEqual(self.gateway.count(), 0)

    def test_08_permission_owner_and_symlink_fail_closed(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(PreflightDenied):
            fixture.PrivateFixtureResultLedger(self.path, ttl_seconds=86400)
        self.path.chmod(0o644)
        with self.assertRaises(PreflightDenied):
            fixture.PrivateFixtureResultLedger(self.path)
        self.path.chmod(0o600)
        other = self.path.parent / "link"
        other.symlink_to(self.path)
        with self.assertRaises(PreflightDenied):
            fixture.PrivateFixtureResultLedger(other)

    def test_09_no_ci_flags_no_result_storage_or_gateway_import(self):
        with patch.dict(os.environ, {"CI": "false", "GITHUB_ACTIONS": "false"}):
            with self.assertRaises(PreflightDenied):
                fixture.PrivateFixtureResultLedger(self.path)
            with self.assertRaises(PreflightDenied):
                self.store.read(self.a)
        from inspect import getsource
        source = getsource(fixture.FixedInvitedGatewayStub)
        self.assertIn("CountOnlyGatewayStub", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("httpx.", source)

    def test_10_original_no_dispatch_mode_is_still_independent(self):
        root = Path(__file__).resolve().parents[3]
        api = (root / "apps/api/product_session_api.py").read_text()
        self.assertIn('API_RUNNER_EXECUTION_MODE") == "NO_DISPATCH_ONLY"', api)
        self.assertIn("install_private_staging_no_dispatch(", api)
        self.assertIn('api.no_dispatch_status.v1', api)
        self.assertIn("INVITED_RESULT_STUB_CI_ONLY", api)

    def test_11_fixture_exact_citation_and_warning_shape(self):
        got = fixture.FIXTURE_ANSWER
        self.assertEqual(got["citations"][0]["source_id"],
                         "fixture:budget-example-001")
        self.assertEqual(got["citations"][0]["evidence_status"],
                         "SYNTHETIC_TEST_ONLY")
        self.assertEqual(fixture.VERSION, "staging.invited_live_result.v1")
        self.assertIn("آزمایشی", fixture.WARNING)
        self.assertNotIn("LIVE_VERIFIED", fixture.WARNING)


if __name__ == "__main__":
    unittest.main()
