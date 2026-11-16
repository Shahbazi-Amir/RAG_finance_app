"""Real localhost HTTPS/Uvicorn0.48.0 client-cert boundary; NO PG or Gateway.

Must be run in Foundation isolated network CI with pinned Uvicorn0.48.0,
FastAPI/cryptography/jsonschema installed. Never target the Arvan IP/host.
"""
import asyncio
import hashlib
import shutil
import ssl
import subprocess
import tempfile
import unittest
from pathlib import Path

import uvicorn

from apps.api.private_staging_asgi import _harden_tls_context
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, make_verified_h11_protocol,
)


def cmd(*parts):
    subprocess.run(["openssl", *map(str, parts)], check=True,
                   capture_output=True, timeout=30)


class RealLocalMTLSH11Test(unittest.TestCase):
    def test_real_https_bff_ca_and_leaf_transport_and_header_spoofing(self):
        self.assertEqual(uvicorn.__version__, "0.48.0")
        self.assertIsNotNone(shutil.which("openssl"))
        with tempfile.TemporaryDirectory(prefix="real-mtls-h11-") as root:
            base = Path(root)
            cmd("req","-x509","-newkey","rsa:2048","-nodes",
                "-keyout",base/"ca.key","-out",base/"ca.pem","-days","1",
                "-subj","/CN=TestCA",
                "-addext","basicConstraints=critical,CA:TRUE",
                "-addext","keyUsage=critical,keyCertSign,cRLSign")
            for name in ("server", "bff", "other"):
                cmd("req","-newkey","rsa:2048","-nodes",
                    "-keyout",base/f"{name}.key",
                    "-out",base/f"{name}.csr","-subj",f"/CN={name}")
                ext = base/f"{name}.ext"
                ext.write_text("basicConstraints=critical,CA:FALSE\n"
                    "keyUsage=digitalSignature,keyEncipherment\n"
                    f"extendedKeyUsage={'serverAuth' if name=='server' else 'clientAuth'}\n"
                    + ("subjectAltName=IP:127.0.0.1\n" if name=="server" else ""))
                cmd("x509","-req","-in",base/f"{name}.csr",
                    "-CA",base/"ca.pem","-CAkey",base/"ca.key",
                    "-CAcreateserial","-out",base/f"{name}.pem","-days","1",
                    "-extfile",ext)
            der = ssl.PEM_cert_to_DER_cert((base/"bff.pem").read_text())
            bff_sha = hashlib.sha256(der).hexdigest()
            boundary = TrustedBFFTLSBoundary(bff_sha)
            calls = []

            async def asgi(scope, receive, send):
                # Identity is process-local TLS capability, NOT HTTP header.
                valid = boundary.scope_is_verified(scope)
                calls.append(valid)
                body = b"VERIFIED_BFF" if valid else b"DENIED"
                await send({"type":"http.response.start",
                            "status":200 if valid else 403,
                            "headers":[(b"content-length",str(len(body)).encode())]})
                await send({"type":"http.response.body","body":body})

            config = uvicorn.Config(
                app=asgi,host="127.0.0.1",port=0,
                loop="asyncio",http=make_verified_h11_protocol(boundary),
                ws="none",lifespan="off",workers=1,reload=False,
                proxy_headers=False,access_log=False,server_header=False,
                ssl_certfile=str(base/"server.pem"),
                ssl_keyfile=str(base/"server.key"),
                ssl_ca_certs=str(base/"ca.pem"),
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_context_factory=_harden_tls_context,
                log_level="critical")
            server = uvicorn.Server(config)

            async def scenario():
                task=asyncio.create_task(server.serve())
                try:
                    for _ in range(200):
                        if server.started and server.servers:
                            break
                        await asyncio.sleep(0.02)
                    self.assertTrue(server.started)
                    port=server.servers[0].sockets[0].getsockname()[1]

                    async def call(name=None):
                        context=ssl.create_default_context(
                            ssl.Purpose.SERVER_AUTH,cafile=str(base/"ca.pem"))
                        if name:
                            context.load_cert_chain(
                                str(base/f"{name}.pem"),str(base/f"{name}.key"))
                        try:
                            reader, writer=await asyncio.wait_for(
                                asyncio.open_connection(
                                    "127.0.0.1",port,ssl=context,
                                    server_hostname="127.0.0.1"),timeout=3)
                            writer.write(
                                b"GET /v1/messages HTTP/1.1\r\n"
                                b"Host: 127.0.0.1\r\n"
                                b"X-Forwarded-Client-Cert: fake\r\n"
                                b"X-SSL-Client-Verify: SUCCESS\r\n"
                                b"Connection: close\r\n\r\n")
                            await writer.drain()
                            try:
                                reply=await asyncio.wait_for(reader.read(),timeout=3)
                            except (ConnectionResetError, BrokenPipeError, ssl.SSLError):
                                reply=b""
                            writer.close()
                            return reply
                        except (ssl.SSLError, ConnectionResetError, BrokenPipeError):
                            return b""

                    positive=await call("bff")
                    self.assertIn(b"HTTP/1.1 200",positive)
                    self.assertIn(b"VERIFIED_BFF",positive)
                    no_cert=await call(None)
                    self.assertNotIn(b"HTTP/1.1 200",no_cert)
                    same_ca_wrong_leaf=await call("other")
                    self.assertNotIn(b"HTTP/1.1 200",same_ca_wrong_leaf)
                    self.assertEqual(calls,[True])
                finally:
                    server.should_exit=True
                    await asyncio.wait_for(task,timeout=10)

            asyncio.run(scenario())
            print("API_F3_REAL_LOCAL_MTLS_UVICORN_BFF200_NO_CERT_DENIED_OTHER_CERT_DENIED_PASS",
                  flush=True)


if __name__ == "__main__":
    unittest.main()
