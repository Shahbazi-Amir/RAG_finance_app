"""Real localhost Uvicorn0.48.0/H11 HTTPS/mTLS + five signed Bootstrap RPCs.

Uses a fake 005/009/010 DB backend and *never* a live IdP or Arvan host.
Run only with Foundation's explicit integration-deps job.
"""
import asyncio
from contextlib import ExitStack
import ssl
import unittest
from unittest.mock import patch

import uvicorn

from apps.api.private_staging_asgi import _harden_tls_context
from apps.api.private_staging_bootstrap_asgi import create_bootstrap_app
from src.phase3.auth.staging_transport_mtls import make_verified_h11_protocol


class BootstrapHTTPSNetwork(unittest.TestCase):
    def test_five_real_network_mtls_signed_post_and_negative_peers(self):
        from test_staging_bootstrap_asgi import StagingBootstrapASGITests, FakeConnection
        fixture=StagingBootstrapASGITests
        fixture.setUpClass()
        try:
            h=fixture("test_01_https_real_idp_and_exact_public_callback")
            h.setUp()
            calls=[]
            with ExitStack() as stack:
                stack.enter_context(patch.object(
                    h.service,"_conn",return_value=FakeConnection()))
                stack.enter_context(patch(
                    "src.phase3.auth.bootstrap_oidc.PostgresDurableReplayStore.consume",
                    return_value=True))
                for op in ("start","complete","status","ack","abort"):
                    stack.enter_context(patch.object(
                        h.service,"_"+op,
                        side_effect=lambda payload, proof, name=op: (
                            (201 if name in ("start","complete") else 200),
                            {"kind":"synthetic_"+name, "state":"FIXTURE_"+name})))
                app=create_bootstrap_app(h.service,h.boundary)
                server=uvicorn.Server(uvicorn.Config(
                    app=app,host="127.0.0.1",port=0,loop="asyncio",
                    http=make_verified_h11_protocol(h.boundary),
                    ws="none",lifespan="off",workers=1,reload=False,
                    proxy_headers=False,access_log=False,server_header=False,
                    ssl_certfile=str(h.root/"server.pem"),
                    ssl_keyfile=str(h.root/"server.key"),
                    ssl_ca_certs=str(h.root/"ca.pem"),
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    ssl_context_factory=_harden_tls_context,
                    log_level="critical"))

                async def exercise():
                    task=asyncio.create_task(server.serve())
                    try:
                        for _ in range(200):
                            if server.started and server.servers:
                                break
                            await asyncio.sleep(0.02)
                        self.assertTrue(server.started)
                        port=server.servers[0].sockets[0].getsockname()[1]

                        async def request(path,body,auth,client="bff"):
                            tls=ssl.create_default_context(
                                cafile=str(h.root/"ca.pem"))
                            if client is not None:
                                tls.load_cert_chain(str(h.root/f"{client}.pem"),
                                                    str(h.root/f"{client}.key"))
                            try:
                                reader,writer=await asyncio.wait_for(
                                    asyncio.open_connection(
                                        "127.0.0.1",port,ssl=tls,
                                        server_hostname="127.0.0.1"),timeout=5)
                                req=(b"POST "+path.encode()+
                                     b" HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                                     b"Content-Type: application/json\r\n"
                                     b"Authorization: "+auth.encode()+
                                     b"\r\nX-Forwarded-Client-Cert: forged\r\n"
                                     b"X-SSL-Client-Verify: SUCCESS\r\n"
                                     b"Content-Length: "+str(len(body)).encode()+
                                     b"\r\nConnection: close\r\n\r\n"+body)
                                writer.write(req);await writer.drain()
                                try:
                                    out=await asyncio.wait_for(reader.read(),timeout=5)
                                except (ConnectionResetError,ssl.SSLError):
                                    out=b""
                                writer.close()
                                return out
                            except (ssl.SSLError,ConnectionResetError,
                                    BrokenPipeError):
                                return b""

                        for op in ("start","complete","status","ack","abort"):
                            path="/internal/auth/oidc/v1/"+op
                            msg=h.example(op)
                            raw,proof=h.proof(path,msg)
                            response=await request(path,raw,proof)
                            code=b"201" if op in ("start","complete") else b"200"
                            self.assertIn(b"HTTP/1.1 "+code,response,response[:500])
                            self.assertIn(("FIXTURE_"+op).encode(),response)
                            calls.append(op)
                        path="/internal/auth/oidc/v1/start"
                        raw,proof=h.proof(path,h.example("start"))
                        no_cert=await request(path,raw,proof,client=None)
                        other=await request(path,raw,proof,client="other")
                        self.assertNotIn(b"HTTP/1.1 201",no_cert)
                        self.assertNotIn(b"HTTP/1.1 201",other)
                    finally:
                        server.should_exit=True
                        await asyncio.wait_for(task,timeout=10)

                asyncio.run(exercise())
            self.assertEqual(calls,["start","complete","status","ack","abort"])
            print("BOOTSTRAP_STAGING_REAL_LOCAL_HTTPS_MTLS_RS256_FIVE_ROUTES_PASS",
                  flush=True)
        finally:
            fixture.tearDownClass()


if __name__=="__main__":
    unittest.main(verbosity=2)
