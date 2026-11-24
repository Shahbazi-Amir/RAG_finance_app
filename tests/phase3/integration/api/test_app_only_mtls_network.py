"""Real local HTTPS mTLS app-only API request to response; no engine/DB."""
import asyncio
import hashlib
import os
import shutil
import ssl
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import uvicorn
from fastapi import FastAPI

from apps.api.private_app_only_asgi import AppOnlyASGI
from apps.api.private_staging_asgi import _harden_tls_context
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, make_verified_h11_protocol,
)


def openssl(*parts):
    subprocess.run(["openssl", *map(str, parts)], check=True,
                   capture_output=True, timeout=30)


class VerifiedProfile:
    def __init__(self, boundary):
        self.boundary = boundary

    def allowed_peer(self, scope):
        return scope.get("scheme") == "https" and self.boundary.scope_is_verified(scope)


class AppOnlyActualNetwork(unittest.TestCase):
    def test_signed_transport_trusted_bff_real_ready_send_denied(self):
        self.assertEqual(uvicorn.__version__, "0.48.0")
        self.assertTrue(shutil.which("openssl"))
        with tempfile.TemporaryDirectory(prefix="app-only-real-https-") as d:
            root = Path(d)
            openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", root/"ca.key", "-out", root/"ca.pem", "-days", "1",
                    "-subj", "/CN=AppOnlyCA",
                    "-addext", "basicConstraints=critical,CA:TRUE",
                    "-addext", "keyUsage=critical,keyCertSign,cRLSign")
            for name in ("server", "bff", "other"):
                openssl("req", "-newkey", "rsa:2048", "-nodes",
                        "-keyout", root/f"{name}.key", "-out", root/f"{name}.csr",
                        "-subj", f"/CN={name}")
                ext = root/f"{name}.ext"
                ext.write_text(
                    "basicConstraints=critical,CA:FALSE\n"
                    "keyUsage=digitalSignature,keyEncipherment\n"
                    f"extendedKeyUsage={'serverAuth' if name=='server' else 'clientAuth'}\n"
                    + ("subjectAltName=IP:127.0.0.1\n" if name == "server" else "")
                )
                openssl("x509", "-req", "-in", root/f"{name}.csr",
                        "-CA", root/"ca.pem", "-CAkey", root/"ca.key",
                        "-CAcreateserial", "-out", root/f"{name}.pem",
                        "-days", "1", "-extfile", ext)
            fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
                (root/"bff.pem").read_text())).hexdigest()
            boundary = TrustedBFFTLSBoundary(fingerprint)
            inner = FastAPI()
            calls = {"inner_send": 0, "db_check": 0}
            @inner.post("/v1/messages")
            async def unsafe_send():
                calls["inner_send"] += 1
                return {"generated": "FORBIDDEN"}
            @inner.get("/v1/conversations")
            async def protected_history():
                return {"kind": "fixture_only"}
            api = AppOnlyASGI(inner, VerifiedProfile(boundary))
            cfg = uvicorn.Config(
                app=api, host="127.0.0.1", port=0,
                loop="asyncio", http=make_verified_h11_protocol(boundary),
                ws="none", lifespan="off", workers=1, reload=False,
                proxy_headers=False, access_log=False, server_header=False,
                ssl_certfile=str(root/"server.pem"),
                ssl_keyfile=str(root/"server.key"),
                ssl_ca_certs=str(root/"ca.pem"),
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_context_factory=_harden_tls_context,
                log_level="critical",
            )
            server = uvicorn.Server(cfg)

            async def scenario():
                task = asyncio.create_task(server.serve())
                try:
                    for _ in range(150):
                        if server.started and server.servers:
                            break
                        await asyncio.sleep(0.02)
                    self.assertTrue(server.started)
                    port = server.servers[0].sockets[0].getsockname()[1]

                    async def call(method, path, name, body=b""):
                        tls = ssl.create_default_context(
                            ssl.Purpose.SERVER_AUTH, cafile=str(root/"ca.pem"))
                        if name is not None:
                            tls.load_cert_chain(
                                str(root/f"{name}.pem"), str(root/f"{name}.key"))
                        try:
                            reader, writer = await asyncio.wait_for(
                                asyncio.open_connection(
                                    "127.0.0.1", port, ssl=tls,
                                    server_hostname="127.0.0.1"), timeout=3)
                            request = (f"{method} {path} HTTP/1.1\r\n"
                                       "Host: 127.0.0.1\r\n"
                                       "X-SSL-Client-Verify: SUCCESS\r\n"
                                       f"Content-Length: {len(body)}\r\n"
                                       "Connection: close\r\n\r\n").encode()+body
                            writer.write(request)
                            await writer.drain()
                            chunks = []
                            for _ in range(20):
                                try:
                                    part = await asyncio.wait_for(reader.read(4096), timeout=3)
                                except (ssl.SSLError, ConnectionResetError, BrokenPipeError):
                                    break
                                if not part:
                                    break
                                chunks.append(part)
                            writer.close()
                            return b"".join(chunks)
                        except (ssl.SSLError, ConnectionResetError,
                                BrokenPipeError, OSError):
                            return b""

                    ready = await call("GET", "/internal/ready", "bff")
                    self.assertIn(b"HTTP/1.1 200", ready)
                    self.assertIn(b'"generation":"unavailable"', ready)
                    self.assertIn(b'"history_db":"verified"', ready)
                    self.assertIn(b'"bootstrap_idp":"not_probed"', ready)
                    send = await call("POST", "/v1/messages", "bff", b"not JSON, not read")
                    self.assertIn(b"HTTP/1.1 503", send)
                    self.assertIn(b"ENGINE_NOT_AVAILABLE", send)
                    self.assertNotIn(b"FORBIDDEN", send)
                    self.assertIn(b"no-store", send.lower())
                    no_cert = await call("POST", "/v1/messages", None, b"data")
                    wrong = await call("GET", "/internal/ready", "other")
                    self.assertNotIn(b"HTTP/1.1 200", no_cert)
                    self.assertNotIn(b"HTTP/1.1 200", wrong)
                    self.assertEqual(calls["inner_send"], 0)
                finally:
                    server.should_exit = True
                    await asyncio.wait_for(task, timeout=10)

            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                with patch(
                    "apps.api.private_app_only_asgi.verify_staging_database_authority",
                    return_value=None,
                ):
                    asyncio.run(scenario())
            print("F3_APP_ONLY_REAL_MTLS_READY_NO_SEND_NO_ENGINE_PASS", flush=True)


if __name__ == "__main__":
    unittest.main()
