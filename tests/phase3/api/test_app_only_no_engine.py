"""App-only API L1: no runner, durable Send, fake Answer or owner bypass."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.api.private_app_only_asgi import (
    APP_ONLY_VERSION, AppOnlyASGI, AppOnlyConfig,
    assert_app_only_environment, load_app_only_config,
)
from src.phase3.auth.staging_service_profile import StagingConfigDenied


class FakeProfile:
    def allowed_peer(self, scope):
        return (scope.get("scheme") == "https"
                and scope.get("trusted_transport_test") is True)


class AppOnlyNoEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="app-only-l1-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = {}
        for name in ("server.pem", "server.key", "ca.pem", "pub.pem"):
            p = self.root / name
            p.write_text("synthetic-test-only-not-a-certificate")
            p.chmod(0o600)
        self.config_file = self.root / "config.json"
        self.doc = {
            "contract_version": APP_ONLY_VERSION,
            "listen_host": "127.0.0.1", "listen_port": 18443,
            "server_tls_cert_file": str(self.root / "server.pem"),
            "server_tls_key_file": str(self.root / "server.key"),
            "trusted_bff_ca_file": str(self.root / "ca.pem"),
            "bff_leaf_cert_sha256": "a" * 64,
            "bff_issuer": "urn:test:bff",
            "bff_audience": "urn:test:api",
            "bff_kid": "test-kid",
            "bff_rs256_public_key_file": str(self.root / "pub.pem"),
            "history_dsn": "host=127.0.0.1 dbname=stage user=history_app",
            "revoke_dsn": "host=127.0.0.1 dbname=stage user=auth_revoker",
        }
        self.save()

    def save(self):
        self.config_file.write_text(json.dumps(self.doc))
        self.config_file.chmod(0o600)

    def test_prepare_real_product_app_without_runner_mount_or_ledger(self):
        """Composition of actual Product ASGI is independent of engine files.

        PG and TLS preflight are mocked ONLY in this source unit test; this
        is NOT a signed Mac or real PostgreSQL readiness attestation.
        """
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from apps.api.private_app_only_asgi import prepare_app_only, AppOnlyASGI
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)
        (self.root / "pub.pem").write_bytes(public_key)
        cfg = load_app_only_config(self.config_file)
        with patch.dict(os.environ, {
            "CI": "false", "GITHUB_ACTIONS": "false",
            "API_RUNNER_EXECUTION_MODE": "APP_ONLY",
            "PHASE3_APP_MODE": "APP_ONLY",
            "API_CURSOR_KEY": "p" * 48,
            "API_CURSOR_TTL_SECONDS": "300",
        }):
            with patch("apps.api.private_app_only_asgi._test_tls_material"):
                with patch("apps.api.private_app_only_asgi.verify_staging_database_authority"):
                    with patch(
                        "src.phase3.rag_runtime.staging_preflight.RunnerLayout.pinned",
                        side_effect=AssertionError("ENGINE_LOCK_MUST_NOT_BE_LOADED"),
                    ):
                        from apps.api import product_session_api
                        with patch.object(
                            product_session_api, "install_private_staging_auth"
                        ) as install:
                            app, boundary = prepare_app_only(cfg)
        self.assertIsInstance(app, AppOnlyASGI)
        self.assertIsNotNone(boundary)
        self.assertEqual(install.call_count, 1)
        self.assertIs(app._app, product_session_api.app)
        self.assertIsNone(product_session_api._SERVER_NO_DISPATCH_TASK)

    def test_missing_cursor_signing_secret_fails_before_signed_service_exposed(self):
        """Original History page 2 requires a stable Ops HMAC+TTL."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from apps.api.private_app_only_asgi import prepare_app_only
        from apps.api import product_session_api
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        (self.root / "pub.pem").write_bytes(
            key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo))
        cfg = load_app_only_config(self.config_file)
        with patch.dict(os.environ, {
            "CI": "false", "GITHUB_ACTIONS": "false",
            "PHASE3_APP_MODE": "APP_ONLY",
            "API_RUNNER_EXECUTION_MODE": "APP_ONLY",
            "API_CURSOR_KEY": "",
            "API_CURSOR_TTL_SECONDS": "300",
        }):
            with patch("apps.api.private_app_only_asgi._test_tls_material"):
                with patch("apps.api.private_app_only_asgi.verify_staging_database_authority"):
                    with patch.object(product_session_api, "install_private_staging_auth") as install:
                        with self.assertRaises(StagingConfigDenied):
                            prepare_app_only(cfg)
                        install.assert_not_called()

    def test_invalid_bff_public_key_denied_without_traceback_or_socket(self):
        """Malformed RS256 key must exit 78, not expose internals or run."""
        from contextlib import redirect_stderr
        from io import StringIO
        from apps.api.private_app_only_asgi import main
        sink = StringIO()
        with patch.dict(os.environ, {
            "CI": "false", "GITHUB_ACTIONS": "false",
            "PHASE3_APP_MODE": "APP_ONLY",
            "API_RUNNER_EXECUTION_MODE": "APP_ONLY",
        }):
            with patch("apps.api.private_app_only_asgi._test_tls_material"):
                with patch("apps.api.private_app_only_asgi.verify_staging_database_authority"):
                    with redirect_stderr(sink):
                        code = main(["--config", str(self.config_file)])
        self.assertEqual(code, 78)
        self.assertEqual(sink.getvalue().strip(), "APP_ONLY_STARTUP_DENIED")

    def test_config_exact_and_redacted_no_runner_no_ledger(self):
        cfg = load_app_only_config(self.config_file)
        self.assertIsInstance(cfg, AppOnlyConfig)
        self.assertEqual(cfg.port, 18443)
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertNotIn("history_app", repr(cfg))
        self.assertNotIn("runner", repr(cfg).lower())
        self.assertFalse("engine_version" in self.doc)

    def test_refuses_engine_or_fixture_config_fields(self):
        for extra in ("engine_version", "ledger_file",
                      "runner_sha256", "gateway_api_key"):
            with self.subTest(extra=extra):
                self.doc[extra] = "malicious"
                self.save()
                with self.assertRaises(StagingConfigDenied):
                    load_app_only_config(self.config_file)
                self.doc.pop(extra)
        self.save()

    def test_world_readable_config_and_symlink_denied(self):
        self.config_file.chmod(0o644)
        with self.assertRaises(StagingConfigDenied):
            load_app_only_config(self.config_file)
        self.config_file.chmod(0o600)
        link = self.root / "symlink.json"
        link.symlink_to(self.config_file)
        with self.assertRaises(StagingConfigDenied):
            load_app_only_config(link)

    def test_ambiguous_duplicate_or_non_json_ops_config_denied(self):
        valid = json.dumps(self.doc)
        doubled = valid.replace(
            '"bff_kid": "test-kid"',
            '"bff_kid": "test-kid", "bff_kid": "forged"')
        self.config_file.write_text(doubled)
        with self.assertRaises(StagingConfigDenied):
            load_app_only_config(self.config_file)
        self.config_file.write_text(valid.replace('18443', 'NaN'))
        with self.assertRaises(StagingConfigDenied):
            load_app_only_config(self.config_file)
        self.save()

    def test_non_loopback_port_type_and_missing_tls_file_denied(self):
        for update in ({"listen_host": "evil.example"},
                       {"listen_port": True},
                       {"listen_port": 0},
                       {"server_tls_key_file": "/tmp/does-not-exist-private-app-only.key"}):
            with self.subTest(update=update):
                old = dict(self.doc)
                self.doc.update(update)
                self.save()
                with self.assertRaises(StagingConfigDenied):
                    load_app_only_config(self.config_file)
                self.doc = old
        self.save()

    def test_production_only_mode_fails_closed_for_dispatch_and_ci(self):
        env = {"API_RUNNER_EXECUTION_MODE": "APP_ONLY",
               "PHASE3_APP_MODE": "APP_ONLY"}
        assert_app_only_environment(env)
        for update in ({"API_RUNNER_EXECUTION_MODE": "NO_DISPATCH_ONLY"},
                       {"API_RUNNER_EXECUTION_MODE": "CLAIM_STUB_CI_ONLY"},
                       {"PHASE3_APP_MODE": "ENGINE_ENABLED"},
                       {"CI": "true"}, {"GITHUB_ACTIONS": "true"},
                       {"MODEL_GATEWAY_URL": "https://invalid.example"},
                       {"C018_RUNNER_PATH": "/tmp/runner"}):
            with self.subTest(update=update):
                with self.assertRaises(StagingConfigDenied):
                    assert_app_only_environment({**env, **update})

    def test_private_app_only_http_guard_denies_before_body_and_db(self):
        app = FastAPI()
        calls = {"app": 0}
        @app.post("/v1/messages")
        async def unsafe_send():
            calls["app"] += 1
            return {"unsafe": True}
        @app.get("/v1/conversations")
        async def history_get():
            calls["app"] += 1
            return {"kind": "fixture_history"}
        wrapper = AppOnlyASGI(app, FakeProfile())

        async def invoke(path, method, trusted, mode="APP_ONLY", raw_path=None):
            receive_reads = []
            emitted = []
            async def recv():
                receive_reads.append(True)
                raise AssertionError("NO_REQUEST_BODY_ALLOWED")
            async def sent(event):
                emitted.append(event)
            scope = {
                "type": "http", "scheme": "https" if trusted else "http",
                "trusted_transport_test": trusted,
                "path": path, "raw_path": (raw_path or path).encode(),
                "method": method, "query_string": b"", "headers": [],
                "http_version": "1.1",
            }
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": mode}):
                await wrapper(scope, recv, sent)
            status = next(v["status"] for v in emitted
                          if v["type"] == "http.response.start")
            headers = dict(next(v["headers"] for v in emitted
                                if v["type"] == "http.response.start"))
            body = b"".join(v.get("body", b"") for v in emitted
                            if v["type"] == "http.response.body")
            return status, headers, body, receive_reads

        for trusted, mode, expected in ((True, "APP_ONLY", 503),
                                        (False, "APP_ONLY", 401),
                                        (True, "NO_DISPATCH_ONLY", 503)):
            status, headers, body, reads = asyncio.run(
                invoke("/v1/messages", "POST", trusted, mode))
            self.assertEqual(status, expected)
            self.assertEqual({k.lower(): v for k, v in headers.items()}[b"cache-control"], b"no-store")
            self.assertFalse(reads)
            self.assertNotIn(b"unsafe", body)
        # Raw encoded URI resolves to the same FastAPI route. It must not
        # bypass the engine fence or cause a request body read.
        status, headers, body, reads = asyncio.run(
            invoke("/v1/messages", "POST", True,
                   raw_path="/v1/%6dessages"))
        self.assertEqual(status, 503)
        self.assertEqual(reads, [])
        self.assertEqual(calls["app"], 0)

    def test_bff_only_history_is_routed_but_not_created_here(self):
        app = FastAPI()
        @app.get("/v1/conversations")
        async def history_get():
            return {"kind": "existing_history"}
        wrapper = AppOnlyASGI(app, FakeProfile())

        async def run():
            # Actual ASGITransport cannot spoof mTLS; this is ONLY a boundary
            # unit test. Real TLS proof lives in test_staging_mtls_h11_network.
            async def with_trusted(scope, receive, send):
                scope["scheme"] = "https"
                scope["trusted_transport_test"] = True
                return await wrapper(scope, receive, send)
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                async with AsyncClient(
                    transport=ASGITransport(app=with_trusted),
                    base_url="https://test.invalid",
                ) as c:
                    resp = await c.get("/v1/conversations")
                    self.assertEqual(resp.status_code, 200)
                    self.assertEqual(resp.json()["kind"], "existing_history")
        asyncio.run(run())

    def test_health_refuses_unknown_pg_never_claims_generation(self):
        app = FastAPI()
        wrapper = AppOnlyASGI(app, FakeProfile())

        async def run():
            async def trusted(scope, receive, send):
                scope["scheme"] = "https"
                scope["trusted_transport_test"] = True
                return await wrapper(scope, receive, send)
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                with patch(
                    "apps.api.private_app_only_asgi.verify_staging_database_authority",
                    side_effect=StagingConfigDenied(),
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=trusted),
                        base_url="https://test.invalid",
                    ) as c:
                        response = await c.get("/internal/ready")
                        alias = await c.get("/health/ready")
                        # /health/ready is stricter than the mTLS-only
                        # metadata probe: it needs signed session+PG.
                        self.assertEqual(alias.status_code, 503)
                        self.assertEqual(response.status_code, 503)
                        self.assertEqual(response.json()["generation"], "unavailable")
                        self.assertEqual(response.headers["cache-control"], "no-store")
                with patch(
                    "apps.api.private_app_only_asgi.verify_staging_database_authority",
                    return_value=None,
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=trusted),
                        base_url="https://test.invalid",
                    ) as c:
                        response = await c.get("/internal/ready")
                        alias = await c.get("/health/ready")
                        # /health/ready is stricter than the mTLS-only
                        # metadata probe: it needs signed session+PG.
                        self.assertEqual(alias.status_code, 503)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["history_db"], "verified")
                        self.assertEqual(response.json()["retrieval"], "unavailable")
                        self.assertEqual(response.json()["generation"], "unavailable")
                        self.assertEqual(response.json()["bootstrap_idp"], "not_probed")
        asyncio.run(run())


    def test_health_ready_requires_real_bff_signed_session_pg_transaction(self):
        """Only the original signed admission may issue a 200 readiness.

        _signed_history is mocked here to inspect composition; actual
        cryptographic and PG behavior is exercised by CI signed PG E2E.
        """
        app = AppOnlyASGI(FastAPI(), FakeProfile())

        async def trusted(scope, receive, send):
            scope["scheme"] = "https"
            scope["trusted_transport_test"] = True
            return await app(scope, receive, send)

        async def scenario():
            with patch.dict(os.environ, {
                "API_RUNNER_EXECUTION_MODE": "APP_ONLY",
            }):
                with patch("apps.api.product_session_api._signed_history",
                           side_effect=ValueError("invalid signed actor")) as proof:
                    async with AsyncClient(
                        transport=ASGITransport(app=trusted),
                        base_url="https://test.invalid",
                    ) as client:
                        denied = await client.get("/health/ready")
                        self.assertEqual(denied.status_code, 503)
                        self.assertEqual(denied.headers["cache-control"], "no-store")
                        self.assertNotIn("invalid", denied.text)
                    self.assertEqual(proof.call_count, 1)
                with patch("apps.api.product_session_api._signed_history",
                           return_value=(None, None)) as proof:
                    async with AsyncClient(
                        transport=ASGITransport(app=trusted),
                        base_url="https://test.invalid",
                    ) as client:
                        ready = await client.get("/health/ready")
                        self.assertEqual(ready.status_code, 200)
                        self.assertEqual(ready.json()["signed_actor_pg"], "verified")
                        self.assertEqual(ready.json()["bootstrap_idp"], "not_probed")
                        self.assertEqual(ready.json()["generation"], "unavailable")
                    self.assertEqual(proof.call_count, 1)

        asyncio.run(scenario())


    def test_slow_pg_readiness_does_not_block_app_only_send_fence(self):
        """A slow signed DB admission must not monopolize the ASGI loop.

        The signed DB call is mocked *only* for deterministic unit control;
        the real PG and signer acceptance stays in API-SESSION-011 Actions.
        """
        from threading import Event
        started, release = Event(), Event()
        wrapper = AppOnlyASGI(FastAPI(), FakeProfile())

        async def trusted(scope, receive, send):
            scope["scheme"] = "https"
            scope["trusted_transport_test"] = True
            return await wrapper(scope, receive, send)

        def slow_pg(*args, **kwargs):
            started.set()
            if not release.wait(timeout=3):
                raise RuntimeError("TEST_SLOW_PG_TIMED_OUT")
            return None, None

        async def scenario():
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                with patch("apps.api.product_session_api._signed_history",
                           side_effect=slow_pg) as proof:
                    async with AsyncClient(
                        transport=ASGITransport(app=trusted),
                        base_url="https://test.invalid",
                    ) as client:
                        readiness = asyncio.create_task(client.get("/health/ready"))
                        try:
                            began = await asyncio.wait_for(
                                asyncio.to_thread(started.wait, 2), timeout=2.5)
                            self.assertTrue(began)
                            # Send remains disabled and cannot read/dispatch,
                            # *while* the other worker is blocked in SQL.
                            denied = await asyncio.wait_for(
                                client.post("/v1/messages",
                                            content=b"malformed-large-" + b"x"*9000),
                                timeout=1.2)
                            self.assertEqual(denied.status_code, 503)
                            self.assertIn("ENGINE_NOT_CONFIGURED", denied.text)
                            self.assertFalse(release.is_set())
                        finally:
                            release.set()
                        ready = await asyncio.wait_for(readiness, timeout=3)
                        self.assertEqual(ready.status_code, 200)
                        self.assertEqual(ready.json()["signed_actor_pg"], "verified")
                        self.assertEqual(proof.call_count, 1)

        asyncio.run(scenario())


    def test_slow_pg_role_metadata_does_not_stall_no_engine_http(self):
        """Even mTLS-only /internal/ready is isolated from the event loop.

        This is a deterministic unit control, not a real PG timeout;
        the separate Actions outage test exercises stopped PG17.
        """
        from threading import Event
        started, release = Event(), Event()
        wrapper = AppOnlyASGI(FastAPI(), FakeProfile())

        async def trusted(scope, receive, send):
            scope["scheme"] = "https"
            scope["trusted_transport_test"] = True
            return await wrapper(scope, receive, send)

        def slow_metadata(_profile):
            started.set()
            if not release.wait(timeout=3):
                raise RuntimeError("TEST_SLOW_DB_METADATA_TIMED_OUT")

        async def scenario():
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                with patch(
                    "apps.api.private_app_only_asgi.verify_staging_database_authority",
                    side_effect=slow_metadata,
                ) as verifier:
                    async with AsyncClient(
                        transport=ASGITransport(app=trusted),
                        base_url="https://test.invalid",
                    ) as client:
                        pending = asyncio.create_task(client.get("/internal/ready"))
                        try:
                            seen = await asyncio.wait_for(
                                asyncio.to_thread(started.wait, 2), timeout=2.5)
                            self.assertTrue(seen)
                            denied = await asyncio.wait_for(
                                client.post("/v1/messages",
                                            content=b"invalid-body-unguarded"),
                                timeout=1.2)
                            self.assertEqual(denied.status_code, 503)
                            self.assertIn("ENGINE_NOT_CONFIGURED", denied.text)
                            self.assertFalse(release.is_set())
                        finally:
                            release.set()
                        ready = await asyncio.wait_for(pending, timeout=3)
                        self.assertEqual(ready.status_code, 200)
                        self.assertEqual(ready.json()["history_db"], "verified")
                        self.assertEqual(verifier.call_count, 1)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
