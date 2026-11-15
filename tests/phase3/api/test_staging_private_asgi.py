"""Offline real OpenSSL TLS CA+client handshake and ASGI bootstrap checks.

No Arvan, Gateway, model, network to third parties, PostgreSQL writes or app
startup. An isolated Foundation CI must additionally test the actual
Uvicorn0.48.0 listener and signed PG/Keycloak API with genuine BFF identity.
"""
import asyncio
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.api.private_staging_asgi import (
    CONFIG_VERSION, _assert_no_dispatch_environment, _test_tls_material,
    load_private_config,
)
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, VerifiedPeerUnavailable,
)


def openssl(*args):
    subprocess.run(
        ["openssl", *map(str, args)], check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)


def handshake(client_ctx, server_ctx):
    """TLS over in-memory BIO, actual OpenSSL cert-chain verification."""
    client_in, client_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    server_in, server_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = client_ctx.wrap_bio(
        client_in, client_out, server_side=False, server_hostname="server")
    server = server_ctx.wrap_bio(server_in, server_out, server_side=True)
    completed = [False, False]
    for _ in range(30):
        try:
            client.do_handshake()
            completed[0] = True
        except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
            pass
        outgoing = client_out.read()
        if outgoing:
            server_in.write(outgoing)
        try:
            server.do_handshake()
            completed[1] = True
        except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
            pass
        outgoing = server_out.read()
        if outgoing:
            client_in.write(outgoing)
        if all(completed):
            return server
    raise AssertionError("TLS_HANDSHAKE_DID_NOT_COMPLETE")


class PrivateASGITransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("openssl"):
            raise AssertionError("OpenSSL required for real TLS CI tests")
        cls.temp = tempfile.TemporaryDirectory(prefix="api53-mtls-")
        cls.root = Path(cls.temp.name)
        openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", cls.root/"ca.key", "-out", cls.root/"ca.pem",
                "-subj", "/CN=RagTestCA", "-days", "1",
                "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign")
        (cls.root/"ext.cnf").write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth,clientAuth\n")
        for name in ("server", "bff", "other_bff"):
            openssl("req", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", cls.root/f"{name}.key",
                    "-out", cls.root/f"{name}.csr",
                    "-subj", f"/CN={name}")
            openssl("x509", "-req", "-in", cls.root/f"{name}.csr",
                    "-CA", cls.root/"ca.pem", "-CAkey", cls.root/"ca.key",
                    "-CAcreateserial", "-out", cls.root/f"{name}.pem",
                    "-days", "1", "-extfile", cls.root/"ext.cnf")
        for name in ("server", "bff", "other_bff", "ca"):
            (cls.root/f"{name}.key").chmod(0o600)
        cls.cert_der = ssl.PEM_cert_to_DER_cert(
            (cls.root/"bff.pem").read_text())
        cls.cert_fingerprint = hashlib.sha256(cls.cert_der).hexdigest()
        cls.server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cls.server_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        cls.server_ctx.load_cert_chain(
            str(cls.root/"server.pem"), str(cls.root/"server.key"))
        cls.server_ctx.load_verify_locations(cafile=str(cls.root/"ca.pem"))
        cls.server_ctx.verify_mode = ssl.CERT_REQUIRED

        cls.config_file = cls.root/"api-private.json"
        cls.doc = {
            "contract_version": CONFIG_VERSION,
            "listen_host": "127.0.0.1", "listen_port": 18443,
            "server_tls_cert_file": str(cls.root/"server.pem"),
            "server_tls_key_file": str(cls.root/"server.key"),
            "trusted_bff_ca_file": str(cls.root/"ca.pem"),
            "bff_leaf_cert_sha256": cls.cert_fingerprint,
            "bff_issuer": "urn:rag-finance:bff",
            "bff_audience": "urn:rag-finance:api",
            "bff_kid": "test_01",
            "bff_rs256_public_key_file": str(cls.root/"bff.pem"),
            "history_dsn": "host=127.0.0.1 dbname=stage user=history_app",
            "revoke_dsn": "host=127.0.0.1 dbname=stage user=auth_revoker",
            "engine_version": "NB23.C018",
            "ledger_file": str(cls.root/"ledger.sqlite3"),
        }
        cls.config_file.write_text(json.dumps(cls.doc))
        cls.config_file.chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def client_context(cls, name="bff", *, with_cert=True):
        ctx = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH, cafile=str(cls.root/"ca.pem"))
        ctx.check_hostname = False
        if with_cert:
            ctx.load_cert_chain(
                str(cls.root/f"{name}.pem"), str(cls.root/f"{name}.key"))
        return ctx

    def test_01_real_ca_verified_bff_leaf_pin_and_scope_capability(self):
        server_tls = handshake(self.client_context(), self.server_ctx)
        boundary = TrustedBFFTLSBoundary(self.cert_fingerprint)
        self.assertTrue(boundary.approved_tls_peer(server_tls))
        scope = {"type": "http", "scheme": "https", "headers": [
            (b"x-forwarded-client-cert", b"INJECTED"),
            (b"x-ssl-client-verify", b"SUCCESS"),
        ]}
        self.assertFalse(boundary.scope_is_verified(scope))
        recorded = []
        async def inner(request_scope, receive, send):
            recorded.append(request_scope)
        wrapper = boundary.wrap_real_verified_connection(inner, server_tls)
        asyncio.run(wrapper(scope, None, None))
        self.assertEqual(len(recorded), 1)
        self.assertTrue(boundary.scope_is_verified(recorded[0]))
        self.assertFalse(boundary.scope_is_verified(scope))
        self.assertNotIn("private_staging", str(recorded[0].get("headers")))

    def test_02_same_ca_wrong_BFF_leaf_rejected(self):
        foreign = handshake(self.client_context("other_bff"), self.server_ctx)
        boundary = TrustedBFFTLSBoundary(self.cert_fingerprint)
        self.assertFalse(boundary.approved_tls_peer(foreign))
        with self.assertRaises(VerifiedPeerUnavailable):
            boundary.wrap_real_verified_connection(lambda *_: None, foreign)

    def test_03_missing_client_cert_fails_real_server_tls_handshake(self):
        with self.assertRaises(ssl.SSLError):
            handshake(self.client_context(with_cert=False), self.server_ctx)

    def test_04_without_tls_and_with_forged_http_headers_denied(self):
        boundary = TrustedBFFTLSBoundary(self.cert_fingerprint)
        self.assertFalse(boundary.approved_tls_peer(None))
        self.assertFalse(boundary.scope_is_verified({
            "type": "http", "scheme": "https",
            "headers": [(b"x-ssl-client-cert", b"fake"),
                        (b"x-forwarded-proto", b"https")]}))
        with self.assertRaises(VerifiedPeerUnavailable):
            boundary.wrap_real_verified_connection(lambda *_: None, None)

    def test_05_http_scope_or_bad_fingerprint_fail_closed(self):
        server_tls = handshake(self.client_context(), self.server_ctx)
        boundary = TrustedBFFTLSBoundary(self.cert_fingerprint)
        async def inner(*_):
            self.fail("HTTP_SCOPE_MUST_NOT_RUN")
        protected = boundary.wrap_real_verified_connection(inner, server_tls)
        with self.assertRaises(VerifiedPeerUnavailable):
            asyncio.run(protected({"type": "http", "scheme": "http"}, None, None))
        self.assertFalse(TrustedBFFTLSBoundary("0"*64).approved_tls_peer(server_tls))
        for sha in ("", "z"*64, "0"*63, "0"*65):
            with self.assertRaises(VerifiedPeerUnavailable):
                TrustedBFFTLSBoundary(sha)

    def test_06_tls_context_without_cert_required_denied(self):
        server_tls = handshake(self.client_context(), self.server_ctx)
        boundary = TrustedBFFTLSBoundary(self.cert_fingerprint)
        with patch.object(boundary, "_expected_fingerprint", "0"*64):
            self.assertFalse(boundary.approved_tls_peer(server_tls))

    def test_07_server_only_config_loads_exact_keys_and_checks_tls(self):
        cfg = load_private_config(self.config_file)
        self.assertEqual(cfg.listen_port, 18443)
        self.assertNotIn("history_app", repr(cfg))
        _test_tls_material(cfg)

    def test_08_no_world_readable_config_or_server_private_key(self):
        self.config_file.chmod(0o644)
        try:
            with self.assertRaises(Exception):
                load_private_config(self.config_file)
        finally:
            self.config_file.chmod(0o600)
        key = self.root/"server.key"
        key.chmod(0o644)
        try:
            with self.assertRaises(Exception):
                load_private_config(self.config_file)
        finally:
            key.chmod(0o600)

    def test_09_symlink_config_and_injected_fields_refused(self):
        link = self.root/"config-link"
        link.symlink_to(self.config_file)
        with self.assertRaises(Exception):
            load_private_config(link)
        link.unlink()
        p = self.root/"bad.json"
        altered = dict(self.doc, injected_admin=True)
        p.write_text(json.dumps(altered))
        p.chmod(0o600)
        with self.assertRaises(Exception):
            load_private_config(p)

    def test_10_nonloopback_invalid_port_and_ci_modes_rejected(self):
        for changes in (
            {"listen_host": "0.0.0.0"},
            {"listen_host": "::"},
            {"listen_port": -1},
            {"listen_port": True},
        ):
            p = self.root/"bad.json"
            p.write_text(json.dumps({**self.doc, **changes}))
            p.chmod(0o600)
            with self.assertRaises(Exception):
                load_private_config(p)
        for mode in ("CLAIM_STUB_CI_ONLY", "INVITED_RESULT_STUB_CI_ONLY", ""):
            with self.assertRaises(Exception):
                _assert_no_dispatch_environment({"API_RUNNER_EXECUTION_MODE": mode})
        with self.assertRaises(Exception):
            _assert_no_dispatch_environment({
                "API_RUNNER_EXECUTION_MODE": "NO_DISPATCH_ONLY", "CI": "true"})

    def test_11_valid_no_dispatch_config_preflight_is_read_only(self):
        preflight = {
            "filesystem": {"runner": True, "python": True},
            "offline_environment": {"HF_HUB_CACHE": True, "HF_HUB_OFFLINE": True},
        }
        with patch("apps.api.private_staging_asgi.inspect_no_dispatch",
                   return_value=preflight), patch(
                   "apps.api.private_staging_asgi._matches_exact_file_sha",
                   return_value=True):
            _assert_no_dispatch_environment({
                "API_RUNNER_EXECUTION_MODE": "NO_DISPATCH_ONLY"})
        # Tests never create the operational staging ledger.
        self.assertFalse((self.root/"ledger.sqlite3").exists())

    def test_12_no_plain_uvicorn_and_legacy_no_dispatch_preserved(self):
        source = (Path(__file__).resolve().parents[3] /
                  "apps/api/private_staging_asgi.py").read_text()
        compile(source, "private_staging_asgi.py", "exec")
        self.assertIn("install_private_staging_no_dispatch(profile, engine)", source)
        self.assertIn("ssl_cert_reqs=ssl.CERT_REQUIRED", source)
        self.assertIn("proxy_headers=False", source)
        self.assertIn("workers=1", source)
        self.assertIn("uvicorn.__version__ != \"0.48.0\"", source)
        self.assertIn("verify_staging_database_authority(profile)", source)
        self.assertNotIn("GatewayStub(", source)
        self.assertNotIn("--dispatch", source.replace("no --dispatch", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
