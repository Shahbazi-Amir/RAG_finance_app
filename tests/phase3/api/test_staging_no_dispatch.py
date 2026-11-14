"""Synthetic offline bridge test; NOT actual NB23(2) CLI or staging proof."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.phase3.rag_runtime.staging_no_dispatch import (
    ApprovedNoDispatchCLI, invoke_pinned_no_dispatch,
    prepare_post_commit_no_dispatch,
)
from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied, RunnerLayout,
)


class NoDispatchBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="no-dispatch-synthetic-")
        root = Path(self.tmp.name)
        self.runner = root/"artifacts"/"synthetic"/"rag_engine.py"
        self.runner.parent.mkdir(parents=True, exist_ok=True)
        self.repo = root/"source"
        self.repo.mkdir()
        self.cache = root/"hf"
        self.cache.mkdir()
        self.binding = AttemptBinding("a"*32,"b"*32,"c"*32)
        self.runner.write_text(
            "import sys,json,os\n"
            "if '--dispatch' in sys.argv: raise SystemExit(17)\n"
            "if 'ARVAN_GATEWAY_API_KEY' in os.environ: raise SystemExit(18)\n"
            "if '--request-id' not in sys.argv: raise SystemExit(19)\n"
            "i=sys.argv.index('--request-id')\n"
            "request_id=sys.argv[i+1]\n"
            "assert sys.stdin.read() == 'test-only question'\n"
            "print(json.dumps({'phase':'CONTEXT_READY','request_id':request_id}))\n",
            encoding="utf-8",
        )
        self.layout = RunnerLayout(Path(sys.executable), self.repo,
                                   root/"artifacts",
                                   "synthetic/rag_engine.py", self.cache)
        self.profile = ApprovedNoDispatchCLI(
            hashlib.sha256(self.runner.read_bytes()).hexdigest(),
            ("--request-id", self.binding.engine_request_id), 10)
        self.environment = {
            "HF_HUB_CACHE":str(self.cache), "HF_HUB_OFFLINE":"1",
            "TRANSFORMERS_OFFLINE":"1",
            "ARVAN_GATEWAY_API_KEY":"SECRET_MUST_NOT_REACH_SUBPROCESS",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_synthetic_runner_executed_once_no_dispatch_no_key(self):
        raw=invoke_pinned_no_dispatch(
            layout=self.layout,profile=self.profile,binding=self.binding,
            input_bytes=b"test-only question",environment=self.environment)
        self.assertEqual(json.loads(raw)["phase"],"CONTEXT_READY")
        self.assertEqual(json.loads(raw)["request_id"],self.binding.engine_request_id)
        self.assertNotIn(b"SECRET_MUST_NOT_REACH_SUBPROCESS",raw)

    def test_wrong_hash_denies_before_process(self):
        bad=ApprovedNoDispatchCLI("0"*64,self.profile.argv_tokens,10)
        with self.assertRaises(PreflightDenied):
            invoke_pinned_no_dispatch(
                layout=self.layout,profile=bad,binding=self.binding,
                input_bytes=b"test-only question",environment=self.environment)

    def test_dispatch_flag_always_denied(self):
        bad=ApprovedNoDispatchCLI(
            self.profile.runner_file_sha256,
            self.profile.argv_tokens+("--dispatch",),10)
        with self.assertRaises(PreflightDenied):
            invoke_pinned_no_dispatch(
                layout=self.layout,profile=bad,binding=self.binding,
                input_bytes=b"test-only question",environment=self.environment)

    def test_foreign_request_id_denied(self):
        bad=ApprovedNoDispatchCLI(self.profile.runner_file_sha256,
                                  ("--request-id","f"*32),10)
        with self.assertRaises(PreflightDenied):
            invoke_pinned_no_dispatch(
                layout=self.layout,profile=bad,binding=self.binding,
                input_bytes=b"test-only question",environment=self.environment)

    def test_unset_offline_env_denied(self):
        bad=dict(self.environment,HF_HUB_OFFLINE="0")
        with self.assertRaises(PreflightDenied):
            invoke_pinned_no_dispatch(
                layout=self.layout,profile=self.profile,binding=self.binding,
                input_bytes=b"test-only question",environment=bad)

    def test_replay_receipt_never_schedules_second_runner(self):
        task=Mock()
        operation=Mock(return_value=(
            {"disposition":"replayed","kind":"send_message_receipt"},None))
        receipt,evidence=prepare_post_commit_no_dispatch(
            operation,task,"test-only question")
        self.assertEqual(receipt["disposition"],"replayed")
        self.assertFalse(evidence.enqueue_performed)
        self.assertTrue(evidence.is_replay)
        task.assert_not_called()
        operation.assert_called_once()

    def test_created_receipt_queues_only_after_confirmed_commit(self):
        committed=[False]
        enqueued=[]
        def committed_t1_t2():
            committed[0]=True
            return {"disposition":"created","kind":"send_message_receipt"},{
                "id":self.binding.engine_request_id,
                "attempt_request_id":self.binding.product_request_id,
                "attempt_trace_id":self.binding.trace_id,
                "state":"attempt_pending",
            }
        def enqueue(binding,question):
            self.assertTrue(committed[0])
            enqueued.append((binding,question))
        _,result=prepare_post_commit_no_dispatch(
            committed_t1_t2,enqueue,"test-only question")
        self.assertEqual(len(enqueued),1)
        self.assertEqual(result.engine_request_id,self.binding.engine_request_id)
        self.assertEqual(result.trace_id,self.binding.trace_id)
        self.assertTrue(result.enqueue_performed)

    def test_unknown_commit_never_queues_any_runner(self):
        task=Mock()
        def unknown_commit():
            raise RuntimeError("TEST_ONLY_UNCERTAIN_COMMIT")
        with self.assertRaises(RuntimeError):
            prepare_post_commit_no_dispatch(
                unknown_commit,task,"test-only question")
        task.assert_not_called()

    def test_status_poll_not_a_dispatch_function(self):
        task=Mock()
        owner_status={"kind":"message_request_status",
                      "status":"attempt_pending","answer":None}
        self.assertEqual(owner_status["status"],"attempt_pending")
        self.assertIsNone(owner_status["answer"])
        task.assert_not_called()


if __name__=="__main__":
    unittest.main(verbosity=2)
