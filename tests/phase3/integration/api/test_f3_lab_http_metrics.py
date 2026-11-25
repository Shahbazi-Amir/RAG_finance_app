"""Pure unit tests and deterministic response doubles, NOT actual HTTP evidence."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from f3_lab_http_metrics import percentiles, measure_read_baseline

class Response:
    def __init__(self, status, body, cache="no-store"):
        self.status, self.body = status, body
        self.headers = {"cache-control": cache}
        self.disposed = False
    def json(self):
        return self.body
    def text(self):
        return json.dumps(self.body)
    def dispose(self):
        self.disposed = True

class Request:
    def __init__(self, owner, bad_cache=False, leak=False, wrong_owner=False):
        self.owner, self.bad_cache, self.leak, self.wrong_owner = owner, bad_cache, leak, wrong_owner
        self.responses = []
    def get(self, url, timeout):
        a = self.owner == "synthetic-owner-a"
        if "browser-a-1/messages" in url:
            body = {"owner_user_id": self.owner, "items": [{"message_id": "browser-msg-a", "text": "lab browser A"}]} if a else {"error": "lab browser A" if self.leak else "NOT_FOUND"}
            status = 200 if a else 404
        else:
            ids = ["browser-a-3", "browser-a-2"] if a else ["browser-b-1"]
            body = {"scope_user_id": "unexpected" if self.wrong_owner else self.owner, "items": [{"conversation_id": i} for i in ids]}
            status = 200
        body.update(request_id="synthetic-request-" + str(len(self.responses)), trace_id="synthetic-trace-" + str(len(self.responses)))
        r = Response(status, body, "public" if self.bad_cache else "no-store")
        self.responses.append(r)
        return r

class Actor:
    def __init__(self, owner, **kw):
        self.request = Request(owner, **kw)

class Tests(unittest.TestCase):
    def test_nearest_rank(self):
        self.assertEqual(percentiles([i * 1000000 for i in range(1, 101)])['p95_ms'], 95)
        self.assertEqual(percentiles([i * 1000000 for i in range(1, 101)])['p99_ms'], 99)
        self.assertEqual(percentiles([i * 1000000 for i in range(1, 101)])['p50_ms'], 50)
    def test_small_sample(self):
        self.assertEqual(percentiles([1000000, 5000000])['p99_ms'], 5)
    def test_bad_samples(self):
        for x in ([], [-1], [1.5], [True]):
            with self.assertRaises(ValueError): percentiles(x)
    def measure(self, a=None, b=None, rounds=2, stage="source"):
        a = a or Actor("synthetic-owner-a")
        b = b or Actor("synthetic-owner-b")
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            r = measure_read_baseline(a,b,"https://invalid.example/api/history/conversations","synthetic-owner-a","synthetic-owner-b",stage,rounds)
        return r, printed.getvalue(), a, b
    def test_measure_counts_and_redaction(self):
        r, log, a, b = self.measure()
        self.assertEqual(r['requests'], 8)
        self.assertEqual(r['routes']['owner_a_list']['samples'], 2)
        self.assertEqual(r['correlation_fields']['request_id']['present_valid'], 6)
        for secret in ('synthetic-owner-a','synthetic-owner-b','synthetic-request-','lab browser A','invalid.example'):
            self.assertNotIn(secret, log)
        self.assertTrue(all(x.disposed for x in a.request.responses + b.request.responses))
    def test_bad_cache_rejected(self):
        with self.assertRaises(AssertionError): self.measure(a=Actor("synthetic-owner-a",bad_cache=True))
    def test_failed_response_is_disposed(self):
        a=Actor("synthetic-owner-a",bad_cache=True)
        with self.assertRaises(AssertionError): self.measure(a=a)
        self.assertEqual(len(a.request.responses),1)
        self.assertTrue(a.request.responses[0].disposed)
    def test_foreign_body_rejected(self):
        with self.assertRaises(AssertionError): self.measure(b=Actor("synthetic-owner-b",leak=True))
    def test_wrong_owner_rejected(self):
        with self.assertRaises(AssertionError): self.measure(a=Actor("synthetic-owner-a",wrong_owner=True))
    def test_bounded_stage_and_rounds(self):
        for rounds in (0,13):
            with self.assertRaises(ValueError): self.measure(rounds=rounds)
        with self.assertRaises(ValueError): self.measure(stage="production")
    def test_restore_measurement(self):
        self.assertEqual(self.measure(stage="restore")[0]['stage'],'restore')

if __name__ == '__main__': unittest.main()
