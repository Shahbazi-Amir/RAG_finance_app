"""Offline L1; protects the full DB T2 Attempt identity, not a PG/E2E grant."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.phase3.rag_runtime.no_dispatch_handler import NoDispatchLedger
from src.phase3.rag_runtime.retrieved_sources import unavailable_receipt
from src.phase3.rag_runtime.staging_preflight import AttemptBinding, PreflightDenied


class FullAttemptBindingFenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="api-f3-binding-")
        self.addCleanup(self.tmp.cleanup)
        self.ledger = NoDispatchLedger(Path(self.tmp.name) / "private-ledger.sqlite")
        self.owner = "owner_A"
        self.original = AttemptBinding("a" * 32, "b" * 32, "c" * 32)
        self.forged = AttemptBinding("a" * 32, "d" * 32, "c" * 32)
        self.assertTrue(self.ledger.reserve(self.owner, self.original))

    def test_exact_replay_never_requeues(self):
        self.assertFalse(self.ledger.reserve(self.owner, self.original))
        self.assertEqual(self.ledger.read(
            self.owner, self.original.engine_request_id)["state"], "QUEUED")

    def test_changed_product_request_denied_at_replay(self):
        with self.assertRaises(PreflightDenied):
            self.ledger.reserve(self.owner, self.forged)
        self.assertEqual(self.ledger.read(
            self.owner, self.original.engine_request_id)["state"], "QUEUED")

    def test_changed_product_request_cannot_start_fail_or_reconcile(self):
        self.assertFalse(self.ledger.start(self.owner, self.forged))
        self.assertFalse(self.ledger.fail(self.owner, self.forged, unknown=True))
        self.assertTrue(self.ledger.start(self.owner, self.original))
        self.assertFalse(self.ledger.fail(self.owner, self.forged, unknown=True))
        self.assertEqual(self.ledger.read(
            self.owner, self.original.engine_request_id)["state"], "RUNNING")

    def test_changed_product_request_cannot_finalize_c018(self):
        self.assertTrue(self.ledger.start(self.owner, self.original))
        self.assertFalse(self.ledger.succeed(
            self.owner, self.forged, {"top10_count": 0},
            unavailable_receipt(self.forged)))
        self.assertEqual(self.ledger.read(
            self.owner, self.original.engine_request_id)["state"], "RUNNING")
        self.assertIsNone(self.ledger.read_sources(
            self.owner, self.original.engine_request_id, self.original.trace_id))
        self.assertTrue(self.ledger.succeed(
            self.owner, self.original, {"top10_count": 0},
            unavailable_receipt(self.original)))
        self.assertEqual(self.ledger.read(
            self.owner, self.original.engine_request_id)["state"], "CONTEXT_READY")

    def test_foreign_owner_or_trace_cannot_share_attempt(self):
        with self.assertRaises(PreflightDenied):
            self.ledger.reserve("owner_B", self.original)
        with self.assertRaises(PreflightDenied):
            self.ledger.reserve(self.owner, AttemptBinding(
                self.original.engine_request_id,
                self.original.product_request_id, "f" * 32))


if __name__ == "__main__":
    unittest.main()
