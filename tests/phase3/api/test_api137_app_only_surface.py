"""API-only boundary regression, no real DB claim in these unit tests."""
import asyncio
import json
import os
import unittest
from unittest.mock import patch
from apps.api.private_app_only_asgi import AppOnlyASGI

class Peer:
    def allowed_peer(self, scope):return True

class Scope(unittest.TestCase):
    def call(self, path, method="GET", raw=None, status=200):
        events=[];calls=[]
        async def inner(scope,receive,send):
            calls.append(True)
            await send({"type":"http.response.start","status":status,"headers":[(b"cache-control",b"public")]})
            await send({"type":"http.response.body","body":b"{}"})
        async def run():
            async def recv():raise AssertionError("unexpected body read")
            async def emit(event):events.append(event)
            with patch.dict(os.environ,{"API_RUNNER_EXECUTION_MODE":"APP_ONLY","PHASE3_APP_MODE":"APP_ONLY"}):
                await AppOnlyASGI(inner,Peer())({"type":"http","scheme":"https","path":path,
                    "raw_path":path.encode() if raw is None else raw,"method":method,
                    "query_string":b"","headers":[]},recv,emit)
        asyncio.run(run())
        first=events[0]
        self.assertEqual(dict(first["headers"])[b"cache-control"],b"no-store")
        return first["status"],len(calls),b"".join(e.get("body",b"") for e in events[1:])
    def test_only_existing_history_read_surface(self):
        for path in ("/v1/conversations","/v1/conversations/c1/messages","/v1/message-requests/status",
                     "/v1/message-requests/engine-status","/v1/message-requests/retrieved-sources"):
            self.assertEqual(self.call(path)[:2],(200,1))
    def test_only_revoke_mutation_reaches_inner(self):
        self.assertEqual(self.call("/internal/auth/session/v1/revoke-one","POST")[:2],(200,1))
        for path in ("/v1/conversations","/v1/message-requests/status","/internal/auth/session/v1/revoke-all"):
            self.assertEqual(self.call(path,"POST")[:2],(404,0))
    def test_invited_fixture_never_routes(self):
        for path in ("/v1/message-requests/claim-test-status","/v1/message-requests/invited-live-result",
                     "/openapi.json","/docs","/v1/new-engine-endpoint"):
            code,calls,body=self.call(path)
            self.assertEqual((code,calls),(404,0));self.assertEqual(json.loads(body)["error"]["code"],"NOT_FOUND")
    def test_encoded_read_not_normalized(self):
        self.assertEqual(self.call("/v1/conversations",raw=b"/v1/%63onversations")[:2],(404,0))
        self.assertEqual(self.call("/v1/conversations/c1/messages/")[:2],(404,0))
    def test_head_put_and_options_not_forwarded(self):
        for method in ("HEAD","PUT","OPTIONS","DELETE","PATCH"):
            self.assertEqual(self.call("/v1/conversations",method)[:2],(404,0))
    def test_security_log_fixed_vocabulary(self):
        with self.assertLogs("phase3.api.security",level="WARNING") as log:
            self.assertEqual(self.call("/v1/conversations/PRIVATE_CANARY/messages",status=401)[:2],(401,1))
        self.assertEqual(len(log.records),1)
        self.assertEqual(json.loads(log.records[0].getMessage()),{"event":"private_request_denied","status":401})
        self.assertNotIn("PRIVATE_CANARY",log.output[0])
