"""Offline synthetic bridge tests; real PostgreSQL/HTTP test is separate."""
import unittest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.phase3.rag_runtime.dispatch_claim_bridge import (
    CommittedDispatchPermit, DispatchClaimDenied, after_definitive_commit,
    claim_within_signed_t2, owner_scoped_claim_status, flag_reporter_unknown,
)
from src.phase3.rag_runtime.dispatch_claim_test_stub import CountOnlyGatewayStub
from src.phase3.rag_runtime.staging_preflight import AttemptBinding


class FakeConn:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, query, args):
        self.calls.append((query, args))
        return self

    def fetchone(self):
        return self.row


class TestClaimPostCommitBoundary(unittest.TestCase):
    def setUp(self):
        self.owner = "synthetic_owner_A"
        self.attempt = {
            "id": "a" * 32, "attempt_request_id": "b" * 32,
            "attempt_trace_id": "c" * 32, "owner_id": self.owner,
            "state": "attempt_pending",
        }
        self.row = {
            "claim_won": True, "claim_id": uuid4(),
            "claimed_at": datetime.now(timezone.utc),
        }

    def permit(self):
        return claim_within_signed_t2(FakeConn(self.row), self.owner, self.attempt)

    def test_claim_sql_signature_and_trusted_attempt_owner_trace(self):
        conn = FakeConn(self.row)
        permit = claim_within_signed_t2(conn, self.owner, self.attempt)
        self.assertEqual(permit.binding.engine_request_id, "a" * 32)
        self.assertEqual(permit.binding.trace_id, "c" * 32)
        self.assertEqual(permit.claim_id, self.row["claim_id"])
        self.assertEqual(conn.calls[0][1], (self.owner, "a" * 32, "c" * 32))
        self.assertIn("history_l1.claim_external_dispatch(%s,%s,%s)", conn.calls[0][0])
        self.assertNotIn(str(permit.claim_id), repr(permit))

    def test_loser_missing_claim_or_foreign_owner_rejects_without_send(self):
        for row in (
            {"claim_won": False, "claim_id": None, "claimed_at": None},
            {"claim_won": True, "claim_id": None, "claimed_at": datetime.now(timezone.utc)},
            {"claim_won": True, "claim_id": uuid4(), "claimed_at": None},
            None,
        ):
            with self.subTest(row=row), self.assertRaises(DispatchClaimDenied):
                claim_within_signed_t2(FakeConn(row), self.owner, self.attempt)
        with self.assertRaises(DispatchClaimDenied):
            claim_within_signed_t2(FakeConn(self.row), "owner_B", self.attempt)

    def test_only_definitively_committed_created_claim_queues_once(self):
        events = []
        permit = self.permit()
        def commit():
            events.append("COMMIT_ACK")
            return {"disposition": "created"}, permit
        def enqueue(p, question):
            self.assertEqual(events, ["COMMIT_ACK"])
            self.assertIs(p, permit)
            events.append("COUNTED_GATEWAY_BOUNDARY")
        receipt, created = after_definitive_commit(commit, enqueue, "synthetic question")
        self.assertTrue(created)
        self.assertEqual(events, ["COMMIT_ACK", "COUNTED_GATEWAY_BOUNDARY"])

    def test_replay_and_uncertain_commit_never_send(self):
        sends = []
        receipt, created = after_definitive_commit(
            lambda: ({"disposition": "replayed"}, None),
            lambda *_: sends.append(1), "synthetic")
        self.assertFalse(created)
        def unknown_commit():
            raise OSError("INJECTED_COMMIT_ACK_LOSS")
        with self.assertRaises(OSError):
            after_definitive_commit(unknown_commit, lambda *_: sends.append(1),
                                    "synthetic")
        with self.assertRaises(DispatchClaimDenied):
            after_definitive_commit(
                lambda: ({"disposition":"created"}, None),
                lambda *_: sends.append(1), "synthetic")
        self.assertEqual(sends, [])

    def test_counted_gateway_boundary_timeout_after_one_no_retry(self):
        stub = CountOnlyGatewayStub()
        permit = self.permit()
        stub.inject_outcome(permit.binding.engine_request_id, "TIMEOUT")
        with self.assertRaises(TimeoutError):
            stub(permit, "synthetic")
        self.assertEqual(stub.count(permit.binding.engine_request_id), 1)
        self.assertEqual(stub.count(), 1)

    def test_status_select_scoped_and_read_only(self):
        doc = {
            "owner_user_id": self.owner,
            "attempt_id": "a" * 32, "attempt_trace_id": "c" * 32,
        }
        c = FakeConn({"dispatch_state": "UNKNOWN", "claimed_at": None,
                      "unknown_at": None, "reconciled_at": None})
        status = owner_scoped_claim_status(c, self.owner, doc)
        self.assertEqual(status, {"dispatch_state": "UNKNOWN"})
        self.assertEqual(c.calls[0][1], (self.owner, "a" * 32, "c" * 32))
        self.assertIn("status_external_dispatch(%s,%s,%s)", c.calls[0][0])
        with self.assertRaises(DispatchClaimDenied):
            owner_scoped_claim_status(c, "synthetic_owner_B", doc)

    def test_unknown_reporter_only_claim_id_and_enum(self):
        permit = self.permit()
        c = FakeConn({"ok": True})
        self.assertTrue(flag_reporter_unknown(c, permit, "TIMEOUT"))
        self.assertEqual(c.calls[0][1],
                         (self.owner, "a" * 32, "c" * 32, permit.claim_id, "TIMEOUT"))
        with self.assertRaises(DispatchClaimDenied):
            flag_reporter_unknown(c, permit, "RETRY_SEND")
        self.assertEqual(len(c.calls), 1)


if __name__ == "__main__":
    unittest.main()
