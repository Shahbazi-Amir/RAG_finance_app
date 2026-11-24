"""Offline process-transport tests with a synthetic worker."""
import sys
import unittest

from src.phase3.rag_runtime.persistent_v4_pipe import PersistentV4Pipe, WorkerUnavailable
from src.phase3.rag_runtime.staging_preflight import AttemptBinding

FIXTURE = """
import hashlib, json, sys, time
print(json.dumps(dict(event="ready", constructions=dict(E5=1,TOKENIZER=1,ONNX_SESSION=1))), flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if req["question"] == "slow":
        time.sleep(30)
    result = dict(status="CONTEXT_READY", generation_calls=0, top10=10,
                  question_sha256=hashlib.sha256(req["question"].encode()).hexdigest(),
                  context_sha256="a"*64)
    attempt = req["attempt_id"] if req["question"] != "wrong" else "other"
    print(json.dumps(dict(event="result", attempt_id=attempt, result=result)), flush=True)
"""


class TestPersistentV4Pipe(unittest.TestCase):
    def setUp(self):
        self.worker = PersistentV4Pipe(
            [sys.executable, "-u", "-c", FIXTURE],
            {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
            request_timeout=0.3,
        )
        self.addCleanup(self.worker.close)

    def test_two_requests_use_same_process_and_contract(self):
        pid = self.worker._process.pid
        for attempt in ("attempt-a", "attempt-b"):
            result = self.worker.request(AttemptBinding(attempt, "request", "trace"), "بودجه")
            self.assertEqual(result["top10_count"], 10)
            self.assertEqual(result["engine_request_id"], attempt)
            self.assertEqual(self.worker._process.pid, pid)

    def test_timeout_closes_stream_without_replaying(self):
        with self.assertRaises(TimeoutError):
            self.worker.request(AttemptBinding("attempt", "request", "trace"), "slow")
        with self.assertRaisesRegex(WorkerUnavailable, "V4_NOT_RUNNING"):
            self.worker.request(AttemptBinding("attempt", "request", "trace"), "slow")

    def test_mismatched_attempt_fails_closed(self):
        with self.assertRaisesRegex(WorkerUnavailable, "V4_RESULT_BINDING_MISMATCH"):
            self.worker.request(AttemptBinding("attempt", "request", "trace"), "wrong")
