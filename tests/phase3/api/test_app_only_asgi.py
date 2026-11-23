import asyncio
import json
import unittest
from unittest.mock import patch
from apps.api.app_only_asgi import AppOnly

async def request(surface,path,method="GET",raw=None,body=b""):
    events=[];reads=0
    async def receive():
        nonlocal reads
        reads+=1
        return {"type":"http.request","body":body,"more_body":False}
    async def send(msg):events.append(msg)
    await surface({"type":"http","path":path,"raw_path":raw or path.encode(),
                   "scheme":"http","method":method,"headers":[]},receive,send)
    return events[0]["status"],json.loads(events[1]["body"]),reads

class AppOnlyBoundary(unittest.TestCase):
    def run_request(self,*args,**kw):return asyncio.run(request(*args,**kw))
    def test_liveness_not_fake_readiness(self):
        self.assertEqual(self.run_request(AppOnly(),"/health/live")[0],200)
        self.assertEqual(self.run_request(AppOnly(),"/health/ready")[0],503)
    def test_only_live_preverified_pg_ready(self):
        class Protected:
            async def __call__(self,*args):raise AssertionError("Not reached")
        x=AppOnly(Protected(),ready=True,readiness_probe=lambda: True)
        self.assertEqual(self.run_request(x,"/health/ready")[0],200)
        self.assertEqual(self.run_request(AppOnly(ready=True),"/health/ready")[0],503)
    def test_db_outage_health_fails_closed(self):
        class Protected:
            async def __call__(self,*args):raise AssertionError("Not reached")
        def offline():raise OSError("private PG unavailable")
        x=AppOnly(Protected(),ready=True,readiness_probe=offline)
        status,doc,reads=self.run_request(x,"/health/ready")
        self.assertEqual((status,doc["ready"],reads),(503,False,0))
    def test_no_engine_capability(self):
        code,doc,reads=self.run_request(AppOnly(),"/v1/capabilities")
        self.assertEqual((code,doc["retrieval"],doc["generation"],reads),
                         (200,"unavailable","unavailable",0))
        self.assertFalse(doc["send_enabled"])
    def test_send_zero_body_reads_no_sql_no_os_spawn(self):
        class Forbidden:
            async def __call__(self,*args):raise AssertionError("Product invoked")
        with patch("subprocess.Popen",side_effect=AssertionError("spawn")):
            guard=AppOnly(Forbidden(),ready=True)
            code,doc,reads=self.run_request(guard,"/v1/messages","POST",
                                            body=b"secret"*200000)
        self.assertEqual((code,doc["error"],reads),(503,"ENGINE_UNAVAILABLE",0))
        self.assertNotIn("answer",doc)
        self.assertNotIn("citations",doc)
    def test_no_engine_status_or_sources(self):
        for p in ("/v1/message-requests/engine-status",
                  "/v1/message-requests/retrieved-sources",
                  "/v1/message-requests/claim-test-status"):
            code,doc,reads=self.run_request(AppOnly(),p)
            self.assertEqual((code,doc["error"],reads),(503,"ENGINE_UNAVAILABLE",0))
    def test_history_fails_closed_without_ops_proof(self):
        code,doc,reads=self.run_request(AppOnly(),"/v1/conversations")
        self.assertEqual((code,doc["error"],reads),(503,"APP_DEPENDENCIES_NOT_READY",0))
    def test_encoded_path_not_accepted(self):
        self.assertEqual(self.run_request(AppOnly(),"/v1/messages",
                         "POST",raw=b"/v1/%6dessages")[0],404)
