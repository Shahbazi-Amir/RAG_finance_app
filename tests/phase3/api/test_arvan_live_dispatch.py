"""Offline coverage of the Arvan overlay, queue and release-candidate boundary."""
from dataclasses import replace
import hashlib
import inspect
from pathlib import Path
import sys
from threading import Event
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.phase3.rag_runtime.arvan_live_dispatch import ArvanLiveDispatch, public_result
from src.phase3.rag_runtime.dispatch_claim_bridge import CommittedDispatchPermit
from src.phase3.rag_runtime.staging_invited_result_fixture import InvitedBinding
from src.phase3.rag_runtime.staging_preflight import AttemptBinding

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "infra/nb23-v4"))
try:
    from arvan_gateway import metadata_issues, overlay_generation
    from worker import ENGINE_SHA
finally:
    sys.path.pop(0)

PROFILE = {"model": "DeepSeek-V4-Flash", "thinking": {"type": "disabled"}}
ALIAS = {"model": "deepseek/deepseek-v4-flash"}
REASONING = "REASONING_MISSING_OR_NONZERO"


class ArvanGatewayTests(unittest.TestCase):
    def test_exact_alias_with_explicit_zero(self):
        usage = {"completion_tokens_details": {"reasoning_tokens": 0}}
        self.assertEqual(metadata_issues(ALIAS, {}, usage, PROFILE), [])
        self.assertEqual(metadata_issues(
            {"model": "other/deepseek-v4-flash"}, {}, usage, PROFILE),
            ["RETURNED_MODEL_REVIEW"])

    def test_missing_reasoning_requires_approved_model_and_disabled_thinking(self):
        for usage in ({}, {"completion_tokens_details": {}}):
            self.assertEqual(metadata_issues(ALIAS, {}, usage, PROFILE), [])
        self.assertEqual(metadata_issues(ALIAS, {}, {}, {
            **PROFILE, "thinking": {"type": "enabled"}}), [REASONING])
        self.assertEqual(metadata_issues({"model": PROFILE["model"]}, {}, {}, PROFILE), [])
        self.assertEqual(metadata_issues({"model": "other"}, {}, {}, PROFILE),
                         ["RETURNED_MODEL_REVIEW", REASONING])

    def test_explicit_bad_reasoning_is_held(self):
        for usage in ({"reasoning_tokens": None}, {"reasoning_tokens": False},
                      {"reasoning_tokens": 1}, {"completion_tokens_details": None},
                      {"completion_tokens_details": {"reasoning_tokens": 0}, "reasoning_tokens": 1}):
            with self.subTest(usage=usage):
                self.assertEqual(metadata_issues(ALIAS, {}, usage, PROFILE), [REASONING])
        self.assertEqual(metadata_issues(
            ALIAS, {"reasoning_content": "unexpected"}, {}, PROFILE), [REASONING])

    def test_overlay_applies_to_actual_pin_when_bundle_is_available(self):
        file = ROOT / "artifacts/nb23-v4-bundle/engine.py"
        if not file.is_file():
            self.skipTest("local pinned upstream artifact absent")
        source = file.read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), ENGINE_SHA)
        ns = {"__name__": "arvan_engine_test", "metadata_issues": metadata_issues}
        exec(compile(overlay_generation(source.decode()), str(file), "exec"), ns)
        self.assertIn("diagnostic_root", inspect.signature(ns["generate"]).parameters)
        with self.assertRaisesRegex(ValueError, "ANCHOR_MISMATCH"):
            overlay_generation(source.decode().replace("RETURNED_MODEL_REVIEW", "CHANGED"))


class ArvanQueueTests(unittest.TestCase):
    def test_generation_does_not_block_retrieval_and_results_are_session_bound(self):
        generation_entered = Event()
        release_generation = Event()
        second_retrieved = Event()
        first = InvitedBinding("owner", "3" * 64, 0, 1, None, "conversation",
                               "client", "key12345", "a" * 32, "b" * 32, "c" * 32)
        second = replace(first, attempt_id="d" * 32, client_message_id="another")

        def retrieve(req, timeout):
            if req["attempt_id"] == second.attempt_id:
                second_retrieved.set()
            return {"attempt_id": req["attempt_id"], "source": {"question": req["question"]}}

        def generate(source, attempt):
            if attempt == first.attempt_id:
                generation_entered.set()
                self.assertTrue(release_generation.wait(5))
                return {"outcome": "ANSWER", "issues": [], "claims": [
                    {"text": "پاسخ", "citation": {"chunk_id": "c1", "quote": "نقل‌قول"}}]}
            return {"outcome": "NO_ANSWER", "issues": [], "claims": []}

        service = ArvanLiveDispatch(Path("/unused"), generate)
        with patch.object(service, "_exchange", side_effect=retrieve):
            try:
                for binding in (first, second):
                    self.assertTrue(service.slots.acquire(blocking=False))
                    permit = CommittedDispatchPermit("owner", AttemptBinding(
                        binding.attempt_id, binding.attempt_request_id, binding.attempt_trace_id,
                    ), uuid4())
                    service.enqueue(permit, binding, "سؤال")
                    if binding == first:
                        self.assertTrue(generation_entered.wait(5))
                self.assertTrue(second_retrieved.wait(5))
                self.assertEqual(service.read(first)["state"], "PENDING")
                self.assertEqual(service.read(replace(first, session_generation=2))["state"], "UNKNOWN")
                self.assertEqual(service.read(replace(first, owner_user_id="other"))["state"], "UNKNOWN")
            finally:
                release_generation.set()
                service.retrieval.shutdown()
                service.generation.shutdown()
        self.assertEqual(service.read(first), {"state": "READY", "outcome": "ANSWER",
            "claims": [{"text": "پاسخ", "quote": "نقل‌قول", "chunk_id": "c1"}]})
        self.assertEqual(service.read(second)["outcome"], "NO_ANSWER")
        service.close()

    def test_review_output_exposes_no_raw_provider_data(self):
        self.assertEqual(public_result({
            "issues": ["untrusted"], "claims": [{"raw": "private"}], "outcome": "ANSWER",
        }), {"state": "REVIEW_REQUIRED", "claims": [], "outcome": None})
