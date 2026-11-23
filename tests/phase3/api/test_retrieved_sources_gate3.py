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
    pinned_chunk_ids, unavailable_receipt, validate_public_receipt,
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

    def test_duplicate_ranked_chunk_denied_before_evidence_persist(self):
        # Two distinct ranks with the same chunk inflate apparent top-k.
        duplicates = [dict(self.rows[0]), dict(self.rows[0])]
        duplicates[1]["position"] = 2
        with self.assertRaises(EvidenceDenied):
            self._convert(self._stdout(rows=duplicates))

    def test_duplicate_chunk_denied_even_if_receipt_schema_is_valid(self):
        receipt = self._convert()
        receipt["rows"][1]["chunk_id"] = receipt["rows"][0]["chunk_id"]
        with self.assertRaises(EvidenceDenied):
            validate_public_receipt(receipt)

    def test_recomputed_sqlite_digest_cannot_accept_duplicate_rank(self):
        ledger = NoDispatchLedger(self.root / "ranked-ledger.sqlite")
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        self.assertTrue(ledger.succeed(
            "owner_A", self.binding, {"top10_count": 2}, self._convert()))
        with sqlite3.connect(ledger.filepath) as conn:
            (raw,) = conn.execute(
                "SELECT receipt_json FROM retrieval_receipts").fetchone()
            tampered = json.loads(raw)
            tampered["rows"][1]["chunk_id"] = tampered["rows"][0]["chunk_id"]
            canonical = json.dumps(tampered, sort_keys=True,
                                   separators=(",", ":"), ensure_ascii=False)
            conn.execute("""UPDATE retrieval_receipts
                SET receipt_json=?,receipt_sha256=?""",
                (canonical, hashlib.sha256(canonical.encode()).hexdigest()))
        with self.assertRaises(PreflightDenied):
            ledger.read_sources(
                "owner_A", self.binding.engine_request_id, self.binding.trace_id)

    def test_same_source_with_two_different_chunks_is_allowed(self):
        # Same book/program may contribute multiple distinct chunks.
        rows = [dict(item) for item in self.rows]
        rows[1]["source_id"] = rows[0]["source_id"]
        receipt = self._convert(self._stdout(rows=rows))
        self.assertEqual(len(receipt["rows"]), 2)
        self.assertEqual(len({x["chunk_id"] for x in receipt["rows"]}), 2)
        self.assertEqual(receipt["rows"][0]["source_id"],
                         receipt["rows"][1]["source_id"])
        self.assertTrue(all(x["source_validation"] == "UNVERIFIED"
                            for x in receipt["rows"]))

    def test_pinned_chunk_bytes_mutated_before_ingest_fail_closed(self):
        # A changed C011 artifact must not be accepted even when its chunk
        # labels still appear to match the Rank list.
        original_sha = self.chunks_digest
        with self.chunks.open("ab") as file:
            file.write(b"\n")
        with self.assertRaises(EvidenceDenied):
            self._convert(sha=original_sha)

    def test_pinned_chunks_symlink_refused_even_with_identical_bytes(self):
        content = self.chunks.read_bytes()
        target = self.root / "other_pinned_copy.jsonl"
        target.write_bytes(content)
        self.chunks.unlink()
        self.chunks.symlink_to(target)
        with self.assertRaises(EvidenceDenied):
            self._convert()

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

    def test_ledger_rejects_positive_count_mismatch_without_commit(self):
        ledger = NoDispatchLedger(self.root / "mismatch-ledger.sqlite")
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        with self.assertRaises(PreflightDenied):
            ledger.succeed("owner_A", self.binding,
                           {"top10_count": 10}, self._convert())
        self.assertEqual(
            ledger.read("owner_A", self.binding.engine_request_id)["state"],
            "RUNNING")
        self.assertIsNone(ledger.read_sources(
            "owner_A", self.binding.engine_request_id, self.binding.trace_id))

    def test_ledger_rejects_boolean_count_and_invalid_receipt_shape(self):
        ledger = NoDispatchLedger(self.root / "bad-count-ledger.sqlite")
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        for count in (True, -1, 11, None, "2"):
            with self.subTest(count=count), self.assertRaises(PreflightDenied):
                ledger.succeed("owner_A", self.binding,
                               {"top10_count": count}, self._convert())
        receipt = self._convert()
        receipt["rows"] = None
        with self.assertRaises(PreflightDenied):
            ledger.succeed("owner_A", self.binding,
                           {"top10_count": 2}, receipt)
        self.assertEqual(ledger.read(
            "owner_A", self.binding.engine_request_id)["state"], "RUNNING")

    def test_unavailable_sources_legitimately_keep_original_observed_count(self):
        # CONTEXT_READY may be true while its source member structure is
        # UNVERIFIED. Do not replace unverified sources with fake valid rows.
        ledger = NoDispatchLedger(self.root / "unavailable-ledger.sqlite")
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        self.assertTrue(ledger.succeed(
            "owner_A", self.binding, {"top10_count": 2},
            unavailable_receipt(self.binding)))
        state = ledger.read("owner_A", self.binding.engine_request_id)
        self.assertEqual(state["state"], "CONTEXT_READY")
        self.assertEqual(state["top10_count"], 2)
        receipt = ledger.read_sources(
            "owner_A", self.binding.engine_request_id, self.binding.trace_id)
        self.assertEqual(receipt["rows"], [])
        self.assertEqual(receipt["retrieval_state"], "EVIDENCE_INVALID")

    def test_tampered_outcome_count_blocked_on_signed_owner_receipt_read(self):
        ledger = NoDispatchLedger(self.root / "outcome-count-ledger.sqlite")
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        receipt = self._convert()
        self.assertTrue(ledger.succeed(
            "owner_A", self.binding, {"top10_count": 2}, receipt))
        with sqlite3.connect(ledger.filepath) as conn:
            conn.execute(
                "UPDATE outcomes SET top10_count=9 WHERE attempt_id=?",
                (self.binding.engine_request_id,))
        with self.assertRaises(PreflightDenied):
            ledger.read_sources(
                "owner_A", self.binding.engine_request_id,
                self.binding.trace_id)

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

    def _canonical_receipt_ledger(self, name):
        ledger = NoDispatchLedger(self.root / name)
        self.assertTrue(ledger.reserve("owner_A", self.binding))
        self.assertTrue(ledger.start("owner_A", self.binding))
        self.assertTrue(ledger.succeed(
            "owner_A", self.binding, {"top10_count": 2}, self._convert()))
        with sqlite3.connect(ledger.filepath) as conn:
            (raw,) = conn.execute(
                "SELECT receipt_json FROM retrieval_receipts").fetchone()
        return ledger, raw

    def _rehashed_raw_receipt(self, ledger, raw):
        # Only an untrusted direct ledger mutation for this isolated negative
        # test. The production path has no direct client SQLite write.
        with sqlite3.connect(ledger.filepath) as conn:
            conn.execute("""UPDATE retrieval_receipts
                SET receipt_json=?,receipt_sha256=?""",
                (raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()))

    def _assert_replay_denied_without_leak(self, ledger):
        with self.assertRaises(PreflightDenied) as caught:
            ledger.read_sources(
                "owner_A", self.binding.engine_request_id,
                self.binding.trace_id)
        self.assertNotIn("PRIVATE_QUESTION_MARKER", str(caught.exception))
        self.assertNotIn("PRIVATE_QUESTION_MARKER", repr(caught.exception))

    def test_rehashed_duplicate_json_property_cannot_be_replayed(self):
        ledger, raw = self._canonical_receipt_ledger("duplicate-key.sqlite")
        # The kind property is present a second time, with a matching value;
        # ordinary json.loads would silently accept this modified document.
        raw = '{"kind":"retrieved_sources",' + raw[1:]
        self.assertEqual(json.loads(raw)["kind"], "retrieved_sources")
        self._rehashed_raw_receipt(ledger, raw)
        self._assert_replay_denied_without_leak(ledger)

    def test_rehashed_whitespace_encoding_cannot_be_replayed(self):
        ledger, raw = self._canonical_receipt_ledger("whitespace.sqlite")
        self._rehashed_raw_receipt(ledger, raw + " \n")
        self._assert_replay_denied_without_leak(ledger)

    def test_rehashed_oversized_ledger_document_cannot_be_replayed(self):
        ledger, raw = self._canonical_receipt_ledger("oversize.sqlite")
        self._rehashed_raw_receipt(ledger, raw + " " * 66000)
        self._assert_replay_denied_without_leak(ledger)

    def test_rehashed_sensitive_question_field_is_never_returned(self):
        ledger, raw = self._canonical_receipt_ledger("private-field.sqlite")
        secret = "PRIVATE_QUESTION_MARKER"
        # This field is not in the existing public retrieved_sources v1 DTO.
        raw = '{"question":' + json.dumps(secret) + "," + raw[1:]
        self._rehashed_raw_receipt(ledger, raw)
        self._assert_replay_denied_without_leak(ledger)

    def test_rehashed_nonstandard_number_denied_on_ledger_read(self):
        ledger, raw = self._canonical_receipt_ledger("nonstandard.sqlite")
        raw = '{"nonfinite":NaN,' + raw[1:]
        self._rehashed_raw_receipt(ledger, raw)
        self._assert_replay_denied_without_leak(ledger)

    def test_ledger_forged_verified_link_with_recomputed_digest_denied(self):
        """Even someone tampering with SQLite cannot grant a verified locator."""
        ledger = NoDispatchLedger(self.root / "source-ledger.sqlite")
        ledger.reserve("owner_A", self.binding)
        ledger.start("owner_A", self.binding)
        ledger.succeed("owner_A", self.binding,
                       {"top10_count": 2}, self._convert())
        with sqlite3.connect(ledger.filepath) as conn:
            raw, = conn.execute(
                "SELECT receipt_json FROM retrieval_receipts").fetchone()
            tampered = json.loads(raw)
            tampered["rows"][0]["verified_locators"] = [
                {"kind": "url", "url": "https://fixture.invalid"}]
            rewritten = json.dumps(tampered, sort_keys=True,
                                   separators=(",", ":"), ensure_ascii=False)
            digest = hashlib.sha256(rewritten.encode()).hexdigest()
            conn.execute("""UPDATE retrieval_receipts
                SET receipt_json=?, receipt_sha256=?""", (rewritten, digest))
        with self.assertRaises(PreflightDenied):
            ledger.read_sources("owner_A", self.binding.engine_request_id,
                                self.binding.trace_id)

    def test_ledger_forged_extra_source_claim_with_recomputed_digest_denied(self):
        ledger = NoDispatchLedger(self.root / "source-ledger.sqlite")
        ledger.reserve("owner_A", self.binding)
        ledger.start("owner_A", self.binding)
        ledger.succeed("owner_A", self.binding,
                       {"top10_count": 2}, self._convert())
        with sqlite3.connect(ledger.filepath) as conn:
            raw, = conn.execute(
                "SELECT receipt_json FROM retrieval_receipts").fetchone()
            tampered = json.loads(raw)
            tampered["rows"][0]["source_verified"] = True
            rewritten = json.dumps(tampered, sort_keys=True,
                                   separators=(",", ":"), ensure_ascii=False)
            conn.execute("""UPDATE retrieval_receipts
                SET receipt_json=?, receipt_sha256=?""",
                (rewritten, hashlib.sha256(rewritten.encode()).hexdigest()))
        with self.assertRaises(PreflightDenied):
            ledger.read_sources("owner_A", self.binding.engine_request_id,
                                self.binding.trace_id)


if __name__ == "__main__":
    unittest.main()
