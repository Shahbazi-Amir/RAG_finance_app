"""Offline Product v1 streamed-event integrity, no provider or fake T3."""
from __future__ import annotations

import copy
import unittest

from src.phase3.rag_runtime.stream_event_integrity import (
    ServerStreamBinding, StreamIntegrityDenied, inspect_stream_session,
)


class StreamIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.binding = ServerStreamBinding("s01", "a01", "r01", "t01")
        self.base = {
            "kind": "stream_session", "contract_version": "product.v1",
            "stream_id": "s01", "answer_id": "a01",
            "request_id": "r01", "trace_id": "t01",
            "delivery_state": "terminal", "events": [],
        }

    def event(self, kind, index, **data):
        return {
            "kind": "stream_event", "contract_version": "product.v1",
            "stream_id": "s01", "answer_id": "a01",
            "request_id": "r01", "trace_id": "t01",
            "seq": index, "event_type": kind, "data": data,
        }

    def audit(self, events, *, delivery="terminal", no_dispatch=True):
        session = {**self.base, "delivery_state": delivery,
                   "events": events}
        return inspect_stream_session(
            session, binding=self.binding, no_dispatch_only=no_dispatch)

    def deny(self, events, *, delivery="terminal", no_dispatch=True):
        with self.assertRaises(StreamIntegrityDenied) as ctx:
            self.audit(events, delivery=delivery, no_dispatch=no_dispatch)
        self.assertEqual(str(ctx.exception), "STREAM_INTEGRITY_DENIED")

    def test_context_only_unknown_has_no_answer_or_t3_authority(self):
        result = self.audit([
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
            self.event("unknown", 2, reason="RESULT_UNAVAILABLE"),
        ])
        self.assertEqual(result.final_event, "unknown")
        self.assertEqual(result.event_count, 3)
        self.assertFalse(result.live_verified)
        self.assertFalse(result.authorizes_product_t3)
        self.assertTrue(result.structural_only)
        self.assertNotIn("trace", repr(result))

    def test_transport_disconnected_never_implies_server_cancelled(self):
        result = self.audit([
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
        ], delivery="disconnected")
        self.assertEqual(result.delivery_state, "disconnected")
        self.assertNotEqual(result.final_event, "server_cancelled")

    def test_display_only_cancel_does_not_claim_backend_stop(self):
        result = self.audit([
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
            self.event("display_cancelled", 2, effect="display_only"),
        ], delivery="display_cancelled")
        self.assertEqual(result.final_event, "display_cancelled")
        self.assertFalse(result.authorizes_product_t3)

    def test_server_confirmed_cancel_requires_prior_request(self):
        self.deny([
            self.event("connected", 0),
            self.event("server_cancelled", 1,
                       server_stopped=True, confirmation_ref="ref123"),
        ])
        result = self.audit([
            self.event("connected", 0),
            self.event("cancel_requested", 1, effect="server_requested"),
            self.event("server_cancelled", 2,
                       server_stopped=True, confirmation_ref="ref123"),
        ])
        self.assertEqual(result.final_event, "server_cancelled")

    def test_future_live_shape_only_never_authorizes_real_answer(self):
        events = [
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
            self.event("generating", 2, reported_by="backend"),
            self.event("delta", 3, text="sample generated text"),
            self.event("completed", 4, final_answer_id="a01",
                       final_state="completed"),
        ]
        self.deny(events)  # no-dispatch cannot emit an answer
        result = self.audit(events, no_dispatch=False)
        self.assertEqual(result.final_event, "completed")
        self.assertFalse(result.live_verified)
        self.assertFalse(result.authorizes_product_t3)

    def test_no_dispatch_rejects_generating_delta_and_completed(self):
        self.deny([
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
            self.event("generating", 2, reported_by="backend"),
        ], delivery="open")
        self.deny([
            self.event("connected", 0), self.event("delta", 1, text="x"),
        ])

    def test_first_event_must_be_connected_and_sequence_contiguous(self):
        self.deny([self.event("retrieving", 0, reported_by="backend")],
                  delivery="open")
        self.deny([
            self.event("connected", 0),
            self.event("retrieving", 2, reported_by="backend"),
        ], delivery="open")
        self.deny([
            self.event("connected", 0),
            self.event("retrieving", 0, reported_by="backend"),
        ], delivery="open")
        self.deny([
            self.event("connected", True),
        ], delivery="open")
        self.deny([
            self.event("connected", 0.0),
        ], delivery="open")

    def test_wrong_owner_immutable_correlation_denied(self):
        for field in ("stream_id", "answer_id", "request_id", "trace_id"):
            with self.subTest(field=field):
                events = [self.event("connected", 0)]
                events[0][field] = "owner_B"
                self.deny(events, delivery="open")
                session = {**self.base, field: "owner_B",
                           "delivery_state": "open",
                           "events": [self.event("connected", 0)]}
                with self.assertRaises(StreamIntegrityDenied):
                    inspect_stream_session(session, binding=self.binding)

    def test_no_events_after_terminal_unknown_failed_or_display_cancelled(self):
        unknown = [
            self.event("connected", 0),
            self.event("unknown", 1, reason="COMMIT_UNCERTAIN"),
        ]
        self.deny(unknown + [self.event("retrieving", 2, reported_by="backend")])
        self.deny([
            self.event("connected", 0),
            self.event("failed", 1, error={
                "category": "technical", "code": "FAILED",
                "message": "Service unavailable",
            }),
            self.event("connected", 2),
        ])
        self.deny([
            self.event("connected", 0),
            self.event("display_cancelled", 1, effect="display_only"),
            self.event("retrieving", 2, reported_by="backend"),
        ])

    def test_reject_mismatched_terminal_state(self):
        self.deny([
            self.event("connected", 0),
            self.event("unknown", 1, reason="UNKNOWN"),
        ], delivery="open")
        self.deny([self.event("connected", 0)], delivery="terminal")
        self.deny([self.event("connected", 0)], delivery="display_cancelled")
        self.deny([
            self.event("connected", 0),
            self.event("display_cancelled", 1, effect="display_only"),
        ], delivery="terminal")

    def test_untrusted_answer_id_not_equal_to_same_stream_rejected(self):
        self.deny([
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
            self.event("generating", 2, reported_by="backend"),
            self.event("completed", 3, final_answer_id="other",
                       final_state="completed"),
        ], no_dispatch=False)

    def test_schema_rejects_unknown_fields_pii_and_invalid_data(self):
        tests = [
            self.event("connected", 0, secret="should not exist"),
            self.event("retrieving", 0, reported_by="browser"),
            self.event("unknown", 0, reason=""),
            self.event("delta", 0, text=""),
        ]
        for event in tests:
            with self.subTest(event=event["event_type"]):
                if event["event_type"] == "connected":
                    self.deny([event], delivery="open")
                else:
                    event["seq"] = 1
                    self.deny([self.event("connected", 0), event],
                              delivery="open")
        bad = {**self.base, "delivery_state": "open",
               "events": [self.event("connected", 0)],
               "owner_user_id": "B"}
        with self.assertRaises(StreamIntegrityDenied):
            inspect_stream_session(bad, binding=self.binding)

    def test_live_invalid_order_delta_before_generating_denied(self):
        self.deny([
            self.event("connected", 0),
            self.event("retrieving", 1, reported_by="backend"),
            self.event("delta", 2, text="x"),
        ], delivery="open", no_dispatch=False)

    def test_invalid_session_and_binding_types_denied(self):
        for session in (None, [], "raw", {"kind": "stream_session"}):
            with self.subTest(session_type=str(type(session))):
                with self.assertRaises(StreamIntegrityDenied):
                    inspect_stream_session(session, binding=self.binding)
        with self.assertRaises(StreamIntegrityDenied):
            inspect_stream_session(self.base, binding="B")
        with self.assertRaises(StreamIntegrityDenied):
            inspect_stream_session(self.base, binding=self.binding,
                                   no_dispatch_only="false")

    def test_repeated_connected_or_fake_cancel_confirmation_denied(self):
        self.deny([
            self.event("connected", 0), self.event("connected", 1),
        ], delivery="open")
        self.deny([
            self.event("connected", 0),
            self.event("cancel_requested", 1, effect="display_only"),
        ], delivery="open")
        self.deny([
            self.event("connected", 0),
            self.event("cancel_requested", 1, effect="server_requested"),
            self.event("server_cancelled", 2,
                       server_stopped=False, confirmation_ref="ref123"),
        ])


if __name__ == "__main__":
    unittest.main()
