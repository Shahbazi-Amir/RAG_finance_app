"""Pure local real subprocess / private SQLite tests. NOT staging smoke."""
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from src.phase3.rag_runtime.staging_no_dispatch import (
    ApprovedNoDispatchCLI, invoke_pinned_no_dispatch,
    prepare_post_commit_no_dispatch,
)
from src.phase3.rag_runtime.no_dispatch_handler import (
    NoDispatchHandler, NoDispatchLedger,
)
from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied, RunnerLayout,
)


class NoDispatchBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="no-dispatch-c018-")
        root=Path(self.tmp.name)
        self.runner=root/"artifacts"/"synthetic"/"rag_engine.py"
        self.runner.parent.mkdir(parents=True)
        self.repo=root/"source"
        self.repo.mkdir()
        self.cache=root/"hf"
        self.cache.mkdir()
        self.binding=AttemptBinding("a"*32,"b"*32,"c"*32)
        self.question="test-only question"
        self.runner.write_text(
            "import hashlib,json,os,sys,time\n"
            "a=sys.argv[1:]\n"
            "assert len(a)==8\n"
            "v=dict(zip(a[::2],a[1::2]))\n"
            "assert set(v)=={'--repo-root','--artifacts-root','--request-id','--question'}\n"
            "assert v['--request-id']=='a'*32\n"
            "assert os.environ['HF_HUB_OFFLINE']=='1'\n"
            "assert 'ARVAN_GATEWAY_API_KEY' not in os.environ\n"
            "assert sys.stdin.read()==''\n"
            "q=v['--question']\n"
            "if q=='synthetic-fail':raise SystemExit(2)\n"
            "if q=='synthetic-timeout':time.sleep(2)\n"
            "print(json.dumps({'status':'CONTEXT_READY',"
            "'question_sha256':hashlib.sha256(q.encode()).hexdigest(),"
            "'context_sha256':hashlib.sha256(b'synthetic').hexdigest(),"
            "'top10':10,'generation_calls':0}))\n",
            encoding="utf-8")
        self.layout=RunnerLayout(Path(sys.executable),self.repo,
                                 root/"artifacts","synthetic/rag_engine.py",self.cache)
        self.digest=hashlib.sha256(self.runner.read_bytes()).hexdigest()
        self.profile=ApprovedNoDispatchCLI(self.digest,10)
        self.env={"HF_HUB_CACHE":str(self.cache),
                  "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1",
                  "ARVAN_GATEWAY_API_KEY":"SECRET_NEVER_LEAK"}
        self.ledger=NoDispatchLedger(root/"outcome.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def run_direct(self,question=None,profile=None,environment=None):
        return invoke_pinned_no_dispatch(
            layout=self.layout,profile=profile or self.profile,
            binding=self.binding,question=self.question if question is None else question,
            environment=environment or self.env)

    def test_exact_four_cli_flags_no_stdin_no_secret(self):
        d=json.loads(self.run_direct())
        self.assertEqual(set(d),{
            "status","question_sha256","context_sha256","top10","generation_calls"})
        self.assertEqual(d["status"],"CONTEXT_READY")
        self.assertNotIn("request_id",d)
        self.assertNotIn("trace_id",d)
        self.assertNotIn("SECRET_NEVER_LEAK",json.dumps(d))

    def test_wrong_sha_denied(self):
        with self.assertRaises(PreflightDenied):
            self.run_direct(profile=ApprovedNoDispatchCLI("0"*64,10))

    def test_question_id_not_browser_override(self):
        foreign=AttemptBinding("f"*32,self.binding.product_request_id,
                               self.binding.trace_id)
        with self.assertRaises(PreflightDenied):
            invoke_pinned_no_dispatch(
                layout=self.layout,profile=self.profile,binding=foreign,
                question=self.question,environment=self.env)

    def test_offline_flag_required(self):
        bad=dict(self.env,HF_HUB_OFFLINE="0")
        with self.assertRaises(PreflightDenied):
            self.run_direct(environment=bad)

    def test_symlink_outside_root_denied(self):
        self.runner.unlink()
        outside=Path(self.tmp.name)/"outside.py"
        outside.write_text("print('oops')")
        self.runner.symlink_to(outside)
        with self.assertRaises(PreflightDenied):
            self.run_direct()

    def test_ledger_unique_and_owner_scope(self):
        self.assertTrue(self.ledger.reserve("owner_A",self.binding))
        self.assertFalse(self.ledger.reserve("owner_A",self.binding))
        self.assertEqual(self.ledger.read("owner_A",self.binding.engine_request_id)["state"],"QUEUED")
        self.assertEqual(self.ledger.read("owner_B",self.binding.engine_request_id)["state"],"NOT_RECORDED")

    def test_handler_success_context_only_not_history(self):
        handler=NoDispatchHandler(self.layout,runner_sha256=self.digest,ledger=self.ledger)
        self.assertTrue(handler.reserve("owner_A",self.binding))
        with patch.dict(os.environ,self.env,clear=False):
            handler("owner_A",self.binding,self.question)
        d=handler.read("owner_A",self.binding.engine_request_id)
        self.assertEqual(d["state"],"CONTEXT_READY")
        self.assertEqual(d["top10_count"],10)
        self.assertEqual(d["generation_calls"],0)
        self.assertTrue(d["question_hash_match"])
        self.assertNotIn("answer",d)
        self.assertNotIn("question",d)
        self.assertNotIn("context_sha256",d)

    def test_handler_no_second_execution_after_completed(self):
        handler=NoDispatchHandler(self.layout,runner_sha256=self.digest,ledger=self.ledger)
        handler.reserve("owner_A",self.binding)
        with patch.dict(os.environ,self.env,clear=False):
            handler("owner_A",self.binding,self.question)
        original=handler.read("owner_A",self.binding.engine_request_id)
        with patch("src.phase3.rag_runtime.no_dispatch_handler.invoke_pinned_no_dispatch",
                   side_effect=AssertionError("DOUBLE_EXECUTION")):
            handler("owner_A",self.binding,self.question)
        self.assertEqual(handler.read("owner_A",self.binding.engine_request_id),original)
        self.assertFalse(handler.reserve("owner_A",self.binding))

    def test_handler_nonzero_exit_marked_failed(self):
        handler=NoDispatchHandler(self.layout,runner_sha256=self.digest,ledger=self.ledger)
        handler.reserve("owner_A",self.binding)
        with patch.dict(os.environ,self.env,clear=False):
            handler("owner_A",self.binding,"synthetic-fail")
        self.assertEqual(handler.read("owner_A",self.binding.engine_request_id)["state"],"FAILED")

    def test_timeout_unknown_without_second_dispatch(self):
        handler=NoDispatchHandler(self.layout,runner_sha256=self.digest,
                                  ledger=self.ledger,max_seconds=1)
        handler.reserve("owner_A",self.binding)
        with patch.dict(os.environ,self.env,clear=False):
            handler("owner_A",self.binding,"synthetic-timeout")
        self.assertEqual(handler.read("owner_A",self.binding.engine_request_id)["state"],"UNKNOWN")
        self.assertFalse(handler.reserve("owner_A",self.binding))

    def test_old_running_observed_unknown_not_requeued(self):
        self.ledger.reserve("owner_A",self.binding)
        self.ledger.start("owner_A",self.binding)
        with self.ledger._connect() as c:
            c.execute("UPDATE outcomes SET updated_at=? WHERE attempt_id=?",
                      (int(time.time())-600,self.binding.engine_request_id))
        self.assertEqual(self.ledger.read("owner_A",self.binding.engine_request_id)["state"],"UNKNOWN")
        self.assertFalse(self.ledger.reserve("owner_A",self.binding))

    def test_only_created_receipt_queues_after_commit(self):
        events=[]
        def commit():
            events.append("COMMIT_ACK")
            return {"disposition":"created"},{
                "id":self.binding.engine_request_id,
                "attempt_request_id":self.binding.product_request_id,
                "attempt_trace_id":self.binding.trace_id,
                "state":"attempt_pending"}
        def queue(binding,question):
            self.assertEqual(events,["COMMIT_ACK"])
            events.append("QUEUED")
        _,result=prepare_post_commit_no_dispatch(commit,queue,self.question)
        self.assertEqual(events,["COMMIT_ACK","QUEUED"])
        self.assertTrue(result.enqueue_performed)
        self.assertEqual(result.trace_id,self.binding.trace_id)

    def test_replayed_receipt_and_unknown_commit_no_enqueue(self):
        task=Mock()
        receipt,stage=prepare_post_commit_no_dispatch(
            lambda:({"disposition":"replayed"},None),task,self.question)
        self.assertTrue(stage.is_replay)
        self.assertFalse(stage.enqueue_performed)
        task.assert_not_called()
        def unknown():
            raise RuntimeError("synthetic_commit_unknown")
        with self.assertRaises(RuntimeError):
            prepare_post_commit_no_dispatch(unknown,task,self.question)
        task.assert_not_called()

    def test_ledger_rejects_unrestricted_directory(self):
        path=Path(self.tmp.name)/"world"
        path.mkdir(mode=0o777)
        path.chmod(0o755)
        with self.assertRaises(PreflightDenied):
            NoDispatchLedger(path/"bad.sqlite")

    def test_poll_only_reads_durable_state(self):
        self.ledger.reserve("owner_A",self.binding)
        for _ in range(3):
            d=self.ledger.read("owner_A",self.binding.engine_request_id)
            self.assertEqual(d["state"],"QUEUED")
        self.assertFalse(self.ledger.reserve("owner_A",self.binding))


if __name__=="__main__":
    unittest.main(verbosity=2)
