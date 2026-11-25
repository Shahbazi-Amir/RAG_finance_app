"""TEST-ONLY independent API process: real mutual TLS, 010 Claim and Keycloak.

Each launch is a separate CPython interpreter, no in-memory Login material or
counters shared with other workers. Keyring/config files and durable PostgreSQL
are the only permitted cross-process inputs. Never log codes or certificates.
"""
from __future__ import annotations

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
import sqlite3
import ssl
import sys

import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.phase3.auth.bootstrap_oidc import BootstrapOIDC, BootstrapDenied


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/__fixture_health":
            self.send_error(404)
            return
        payload = json.dumps({"pid": os.getpid()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = self.headers.get("Content-Length", "")
        if not length.isdecimal() or int(length) > 8192:
            self.send_error(413)
            return
        body = self.rfile.read(int(length))
        try:
            status, payload = self.server.app.handle(
                peer_der=self.connection.getpeercert(binary_form=True),
                authorization=self.headers.get("Authorization", ""),
                method="POST", path=urlsplit(self.path).path, raw_body=body)
        except BootstrapDenied as exc:
            status, payload = exc.status, {"error": "BOOTSTRAP_DENIED"}
        except Exception:
            status, payload = 503, {"error": "TEMPORARILY_UNAVAILABLE"}
        raw = json.dumps(payload, sort_keys=True, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


def serve(config_path):
    config = json.loads(Path(config_path).read_text())
    app = BootstrapOIDC(
        service_issuer=config["service_issuer"], audience=config["audience"],
        service_keys={k: v.encode() for k, v in config["service_keys"].items()},
        cert_fingerprints=config["fingerprints"],
        seal_keys={k: v.encode() for k, v in config["material_keys"].items()},
        active_seal_kid=config["active_kid"], db_dsn=config["db_dsn"],
        oidc=config["oidc"], client_id=config["client_id"],
        redirect_uri=config["redirect_uri"])

    original_redeem = app._redeem
    def instrumented_exchange(code, verifier):
        # Durable CI counter across independent API processes; never store Code.
        with sqlite3.connect(config["audit_path"], timeout=20) as c:
            c.execute("INSERT INTO token_exchanges(worker, code_sha256) VALUES (?,?)",
                      (config["worker_id"], sha256(code.encode()).hexdigest()))
            c.commit()
        reply = original_redeem(code, verifier)  # actual Keycloak token HTTP
        if config.get("fault") == "timeout_after_exchange":
            # Real IdP HTTP response was lost to the caller AFTER redemption.
            raise httpx.ReadTimeout("synthetic post-exchange transport outcome unknown")
        return reply
    app.exchange = instrumented_exchange

    if config.get("fault") == "claim_commit_uncertain":
        real_claim = app._claim_material
        def lost_ack(payload, proof):
            real_claim(payload, proof)  # actual 010 PostgreSQL COMMIT completes
            raise psycopg.OperationalError(
                "synthetic post-commit acknowledgement lost before IdP")
        app._claim_material = lost_ack

    server = ThreadingHTTPServer(("127.0.0.1", config["port"]), Handler)
    server.app = app
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(config["server_cert"], config["server_key"])
    tls.load_verify_locations(cafile=config["ca"])
    tls.verify_mode = ssl.CERT_REQUIRED
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("CI_WORKER_CONFIG_REQUIRED")
    serve(sys.argv[1])
