"""Gate3 source evidence isolated tests: Fixtures only; no model, DB or Gateway."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.phase3.rag_runtime.no_dispatch_handler import NoDispatchLedger
from src.phase3.rag_runtime.retrieved_sources import (
    CHUNKS_RELATIVE, CONTRACT, EvidenceDenied, from_c018_stdout,
    pinned_chunk_ids, unavailable_receipt,
)
from src.phase3.rag_runtime.staging_preflight import AttemptBinding, PreflightDenied


class C018RetrievedSourcesOfflineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="Fixture-C018-sources-")
        self.root = Path(self._tmp.name)
        self.chunks = self.root / CHUNKS_RELATIVE
        self.chunks.parent.mkdir(parents=True)
        self._set_chunks([{"chunk_id": "chunk:Fixture:A"},
                          {"chunk_id": "chunk:Fixture:B"}])
        self.question = "Fixture private question"
        self.binding = AttemptBinding("a" * 32, "c" * 32, "b" * 32)
        self.rows = [
            {"position": 1, "chunk_id": "chunk:Fixture:A",
             "source_id": "program:Fixture:A",
             "member_locators": [{"opaque_fixture": "NOT_A_VERIFIED_LINK"}]},
            {"position": 2, "chunk_id": "chunk:Fixture:B",
             "source_id": None, "member_locators": []},
        ]

    def tearDown(self):
        self._tmp.cleanup()

    def _set_chunks(self, records):
        self.chunks.write_bytes(
            "".join(json.dumps(x, separators=(",", ":")) + "\n" for x in records).encode())
        self.chunks_digest = hashlib.sha256(self.chunks.read_bytes()).hexdigest()

    def _stdout(self, rows=None, **override):
        value = {"status": "CONTEXT_READY",
                 "question_sha256": hashlib.sha256(self.question.encode()).hexdigest(),
                 "context_sha256": "d" * 64,
                 "top10": self.rows if rows is None else rows,
                 "generation_calls": 0}
        value.update(override)
        return json.dumps(value, separators=(",", ":")).encode()

    def _convert(self, raw=None, *, sha=None):
        return from_c018_stdout(self._stdout() if raw is None else raw,
                                binding=self.binding, question=self.question,
                                repo_root=self.root,
                                chunks_sha256=self.chunks_digest if sha is None else sha)

    def test_fixture_order_and_attempt_binding(self):
        out = self._convert()
        self.assertEqual(out["contract_version"], CONTRACT)
        self.assertEqual(out["attempt_id"], self.binding.engine_request_id)
        self.assertEqual(out["attempt_trace_id"], self.binding.trace_id)
        self.assertEqual([r["position"] for r in out["rows"]], [1, 2])
        self.assertEqual([r["chunk_id"] for r in out["rows"]],
                         ["chunk:Fixture:A", "chunk:Fixture:B"])

    def test_fixture_no_verified_locator_from_untyped_members(self):
        out = self._convert()
        self.assertEqual([r["verified_locators"] for r in out["rows"]], [[], []])
        self.assertNotIn("NOT_A_VERIFIED_LINK", json.dumps(out))
        self.assertEqual(out["rows"][0]["source_validation"], "UNVERIFIED")

    def test_fixture_null_source_and_empty_locator(self):
        self.assertIsNone(self._convert()["rows"][1]["source_id"])

    def test_fixture_malformed_position_denied(self):
        self.rows[0]["position"] = 2
        with self.assertRaises(EvidenceDenied): self._convert()

    def test_fixture_missing_member_locators_key_denied(self):
        del self.rows[0]["member_locators"]
        with self.assertRaises(EvidenceDenied): self._convert()

    def test_fixture_wrong_chunk_denied(self):
        self.rows[0]["chunk_id"] = "chunk:Fixture:unknown"
        with self.assertRaises(EvidenceDenied): self._convert()

    def test_fixture_wrong_sha_denied(self):
        with self.assertRaises(EvidenceDenied): self._convert(sha="0" * 64)

    def test_fixture_duplicate_chunk_index_denied(self):
        self._set_chunks([{"chunk_id":"chunk:Fixture:A"}, {"chunk_id":"chunk:Fixture:A"}])
        with self.assertRaises(EvidenceDenied): self._convert()

    def test_fixture_missing_chunk_key_denied(self):
        self._set_chunks([{"other_id": "chunk:Fixture:A"}])
        with self.assertRaises(EvidenceDenied): self._convert()

    def test_fixture_non_list_top10_denied(self):
        with self.assertRaises(EvidenceDenied): self._convert(self._stdout(rows=2))

    def test_fixture_generation_denied(self):
        with self.assertRaises(EvidenceDenied):
            self._convert(self._stdout(generation_calls=1))

    def test_fixture_question_hash_denied(self):
        with self.assertRaises(EvidenceDenied):
            self._convert(self._stdout(question_sha256="0"*64))

    def test_fixture_nonobject_row_denied(self):
        with self.assertRaises(EvidenceDenied): self._convert(self._stdout(rows=["bad"]))

    def test_fixture_duplicate_json_key_denied(self):
        raw = b'{"status":"CONTEXT_READY","status":"CONTEXT_READY"}'
        with self.assertRaises(EvidenceDenied): self._convert(raw)

    def test_fixture_pinned_index(self):
        self.assertEqual(pinned_chunk_ids(self.root, self.chunks_digest),
                         {"chunk:Fixture:A", "chunk:Fixture:B"})

    def test_fixture_unavailable_fail_closed(self):
        r = unavailable_receipt(self.binding)
        self.assertEqual(r["rows"], [])
        self.assertEqual(r["retrieval_state"], "EVIDENCE_INVALID")

    def test_ledger_owner_trace_and_persistent_get(self):
        ledger = NoDispatchLedger(self.root / "source-ledger.sqlite")
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        receipt = self._convert()
        self.assertTrue(ledger.succeed("owner_A", self.binding,
                                       {"top10_count": 2}, receipt))
        self.assertEqual(ledger.read_sources(
            "owner_A", self.binding.engine_request_id,
            self.binding.trace_id), receipt)
        self.assertIsNone(ledger.read_sources(
            "owner_B", self.binding.engine_request_id, self.binding.trace_id))
        self.assertIsNone(ledger.read_sources(
            "owner_A", self.binding.engine_request_id, "f"*32))
        self.assertFalse(ledger.reserve("owner_A", self.binding))
        reopened = NoDispatchLedger(self.root / "source-ledger.sqlite")
        self.assertEqual(reopened.read_sources(
            "owner_A", self.binding.engine_request_id, self.binding.trace_id), receipt)

    def test_ledger_rejects_mismatched_attempt_without_state_mutation(self):
        ledger = NoDispatchLedger(self.root / "source-ledger.sqlite")
        ledger.reserve("owner_A", self.binding)
        ledger.start("owner_A", self.binding)
        receipt = self._convert()
        receipt["attempt_id"] = "f"*32
        with self.assertRaises(PreflightDenied):
            ledger.succeed("owner_A", self.binding, {"top10_count": 2}, receipt)
        self.assertEqual(ledger.read("owner_A", self.binding.engine_request_id)["state"], "RUNNING")

    def test_ledger_tamper_hash_denied(self):
        ledger = NoDispatchLedger(self.root / "source-ledger.sqlite")
        ledger.reserve("owner_A", self.binding)
        ledger.start("owner_A", self.binding)
        ledger.succeed("owner_A", self.binding,
                       {"top10_count": 2}, self._convert())
        with sqlite3.connect(ledger.filepath) as conn:
            conn.execute("UPDATE retrieval_receipts SET receipt_sha256='0'")
        with self.assertRaises(PreflightDenied):
            ledger.read_sources("owner_A", self.binding.engine_request_id,
                                self.binding.trace_id)


if __name__ == "__main__":
    unittest.main()
