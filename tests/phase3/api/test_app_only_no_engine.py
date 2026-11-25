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
            "history_dsn": f"host=127.0.0.1 port=5432 dbname=stage user=history_app sslmode=verify-full sslrootcert={self.root / 'ca.pem'}",
            "revoke_dsn": f"host=127.0.0.1 port=5432 dbname=stage user=auth_revoker sslmode=verify-full sslrootcert={self.root / 'ca.pem'}",
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


    def test_signed_get_rejects_ambiguous_body_before_history_or_pg(self):
        """ASGI framing fence is independent of the signed session/DB."""
        calls = []
        async def downstream(scope, receive, send):
            calls.append(scope["path"])
            raise AssertionError("BODY_BEARING_GET_MUST_NOT_REACH_PRODUCT")
        wrapper = AppOnlyASGI(downstream, FakeProfile())

        async def scenario():
            for path, expected in (
                ("/v1/conversations", 401),
                ("/v1/conversations/example/messages", 401),
                ("/v1/message-requests/status", 401),
                ("/health/ready", 503),
                ("/internal/ready", 503),
            ):
                for headers in (
                    [(b"content-length", b"1")],
                    [(b"content-length", b"0"), (b"content-length", b"0")],
                    [(b"content-length", b"00")],
                    [(b"transfer-encoding", b"chunked")],
                    [(b"content-length", b"0"), (b"transfer-encoding", b"chunked")],
                ):
                    with self.subTest(path=path, headers=headers):
                        events = []
                        async def receive():
                            raise AssertionError("REJECT_BEFORE_READING_BODY")
                        async def send(event):
                            events.append(event)
                        await wrapper({
                            "type": "http", "scheme": "https",
                            "trusted_transport_test": True, "path": path,
                            "raw_path": path.encode(), "method": "GET",
                            "query_string": b"", "headers": headers,
                            "http_version": "1.1",
                        }, receive, send)
                        start = next(e for e in events
                                     if e["type"] == "http.response.start")
                        self.assertEqual(start["status"], expected)
                        self.assertEqual(dict(start["headers"])[b"cache-control"],
                                         b"no-store")
            self.assertEqual(calls, [])

        with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
            asyncio.run(scenario())

    def test_slow_revoke_does_not_block_prebody_send(self):
        """Mock SQL worker delay only; exercise the actual revoke route."""
        from threading import Event
        from starlette.responses import JSONResponse
        from apps.api import product_session_api
        started, release = Event(), Event()
        wrapper = AppOnlyASGI(product_session_api.app, FakeProfile())
        op = "f88ef6e2-12c0-41ca-9117-2ad283ec71e2"

        async def trusted(scope, receive, send):
            scope["scheme"] = "https"
            scope["trusted_transport_test"] = True
            return await wrapper(scope, receive, send)

        def delayed_commit(scope, raw, operation_id):
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError("TEST_REVOKE_COMMIT_TIMED_OUT")
            return JSONResponse({"state": "REVOKED_COMMITTED",
                                 "operation_id": operation_id})

        async def scenario():
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                with patch.object(product_session_api, "_PRIVATE_STAGING_PROFILE", None):
                    with patch.object(product_session_api, "_revoke_committed",
                                      side_effect=delayed_commit) as commit:
                        async with AsyncClient(
                            transport=ASGITransport(app=trusted),
                            base_url="https://test.invalid",
                        ) as client:
                            pending = asyncio.create_task(client.post(
                                "/internal/auth/session/v1/revoke-one",
                                json={"operation_id": op}))
                            try:
                                self.assertTrue(await asyncio.wait_for(
                                    asyncio.to_thread(started.wait, 2), timeout=3))
                                denied = await asyncio.wait_for(
                                    client.post("/v1/messages", content=b"invalid"),
                                    timeout=1.5)
                                self.assertEqual(denied.status_code, 503)
                                self.assertIn("ENGINE_NOT_CONFIGURED", denied.text)
                                self.assertFalse(pending.done())
                            finally:
                                release.set()
                            revoked = await asyncio.wait_for(pending, timeout=3)
                            self.assertEqual(revoked.status_code, 200)
                            self.assertEqual(revoked.json()["operation_id"], op)
                            self.assertEqual(commit.call_count, 1)

        asyncio.run(scenario())


    def test_signed_readiness_checks_actual_history_action_without_leaking_page(self):
        from starlette.responses import JSONResponse
        from apps.api import history_api, product_session_api
        wrapper = AppOnlyASGI(FastAPI(), FakeProfile())
        context = {"owner": "test_owner_only", "conn": object()}

        async def trusted(scope, receive, send):
            scope["scheme"] = "https"
            scope["trusted_transport_test"] = True
            return await wrapper(scope, receive, send)

        def invoke_action(request, body, path, action):
            self.assertEqual(body, b"")
            self.assertEqual(path, b"/health/ready")
            return None, action(context)

        async def scenario():
            with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
                with patch.object(product_session_api, "_signed_history",
                                  side_effect=invoke_action):
                    with patch.object(history_api, "_cursor_config",
                                      return_value=(b"x" * 32, 300)):
                        async with AsyncClient(
                            transport=ASGITransport(app=trusted),
                            base_url="https://test.invalid",
                        ) as client:
                            with patch.object(history_api, "conversations",
                                              return_value=JSONResponse({
                                                  "title": "PRIVATE_TEST_HISTORY"
                                              })) as read:
                                ready = await client.get("/health/ready")
                                self.assertEqual(ready.status_code, 200)
                                self.assertNotIn("PRIVATE_TEST_HISTORY", ready.text)
                                self.assertNotIn("test_owner_only", ready.text)
                                self.assertIs(read.call_args.args[1], context)
                            with patch.object(history_api, "conversations",
                                              side_effect=RuntimeError(
                                                  "PRIVATE_DB_FAILURE")):
                                denied = await client.get("/health/ready")
                                self.assertEqual(denied.status_code, 503)
                                self.assertNotIn("PRIVATE_DB_FAILURE", denied.text)

        asyncio.run(scenario())


    def test_revoke_declared_size_and_disconnect_never_reach_commit(self):
        """Reject oversized/ambiguous headers early and truncated bodies safely."""
        from apps.api import product_session_api
        wrapper = AppOnlyASGI(product_session_api.app, FakeProfile())
        path = "/internal/auth/session/v1/revoke-one"

        async def invoke(headers, input_events, status):
            received, events = [], []
            async def receive():
                received.append(True)
                if not input_events:
                    raise AssertionError("HEADER_DENIAL_MUST_NOT_READ")
                return input_events.pop(0)
            async def send(event):
                events.append(event)
            scope = {
                "type": "http", "scheme": "https", "trusted_transport_test": True,
                "path": path, "raw_path": path.encode(), "root_path": "",
                "method": "POST", "query_string": b"", "http_version": "1.1",
                "headers": [(b"content-type", b"application/json"), *headers],
                "client": ("127.0.0.1", 12345), "server": ("test.invalid", 443),
            }
            await wrapper(scope, receive, send)
            start = next(e for e in events if e["type"] == "http.response.start")
            self.assertEqual(start["status"], status)
            self.assertEqual(dict(start["headers"])[b"cache-control"], b"no-store")
            return received

        async def scenario():
            self.assertEqual(await invoke([(b"content-length", b"513")], [], 413), [])
            self.assertEqual(await invoke([(b"content-length", b"invalid")], [], 422), [])
            self.assertEqual(await invoke(
                [(b"content-length", b"1"), (b"content-length", b"1")],
                [], 422), [])
            self.assertEqual(len(await invoke([(b"content-length", b"42")], [
                {"type": "http.request", "body": b"{", "more_body": True},
                {"type": "http.disconnect"},
            ], 422)), 2)
            self.assertEqual(len(await invoke([(b"content-length", b"42")], [
                {"type": "http.request", "body": b"{}", "more_body": False},
            ], 422)), 1)

        with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
            with patch.object(product_session_api, "_PRIVATE_STAGING_PROFILE", None):
                with patch.object(product_session_api, "_revoke_committed",
                                  side_effect=AssertionError("NO_DB_ADMISSION")) as commit:
                    asyncio.run(scenario())
                    commit.assert_not_called()


    def test_revoke_ambiguous_headers_reject_before_body_or_admission(self):
        from apps.api import product_session_api
        wrapper = AppOnlyASGI(product_session_api.app, FakeProfile())
        path = "/internal/auth/session/v1/revoke-one"

        async def scenario():
            ct = (b"content-type", b"application/json")
            for headers in (
                [],
                [ct, ct],
                [ct, (b"content-type", b"text/plain")],
                [ct, (b"content-length", b"1"), (b"transfer-encoding", b"chunked")],
                [ct, (b"transfer-encoding", b"chunked"), (b"transfer-encoding", b"chunked")],
                [ct, (b"transfer-encoding", b"gzip")],
            ):
                with self.subTest(headers=headers):
                    events = []
                    async def receive():
                        raise AssertionError("AMBIGUOUS_HEADERS_MUST_NOT_READ_BODY")
                    async def send(event):
                        events.append(event)
                    await wrapper({
                        "type": "http", "scheme": "https", "trusted_transport_test": True,
                        "path": path, "raw_path": path.encode(), "root_path": "",
                        "method": "POST", "query_string": b"", "http_version": "1.1",
                        "headers": headers, "client": ("127.0.0.1", 12345),
                        "server": ("test.invalid", 443),
                    }, receive, send)
                    start = next(e for e in events if e["type"] == "http.response.start")
                    self.assertEqual(start["status"], 422)
                    self.assertEqual(dict(start["headers"])[b"cache-control"], b"no-store")
                    body = b"".join(e.get("body", b"") for e in events
                                    if e["type"] == "http.response.body")
                    self.assertEqual(json.loads(body), {"error": "INVALID_REQUEST"})

        with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}):
            with patch.object(product_session_api, "_PRIVATE_STAGING_PROFILE", None):
                with patch.object(product_session_api, "_revoke_committed",
                                  side_effect=AssertionError("NO_DB_ADMISSION")) as commit:
                    asyncio.run(scenario())
                    commit.assert_not_called()


    def test_private_db_destination_cannot_be_overridden(self):
        from src.phase3.auth.staging_service_profile import (
            private_db_connection_options,
        )
        for operation, role in (("history", "history_app"), ("revoke", "auth_revoker")):
            local = "host=127.0.0.1 dbname=stage user=" + role
            remote = ("host=pg-restore dbname=stage user=" + role
                      + " sslmode=verify-full sslrootcert=/run/secrets/pg-ca.pem")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(private_db_connection_options(local, operation),
                                 {"gssencmode": "disable"})
                self.assertEqual(private_db_connection_options(remote, operation),
                                 {"gssencmode": "disable"})
                for invalid in (
                    local + " hostaddr=192.0.2.10",
                    local + " service=other",
                    local + " port=5432,5433",
                    local.replace("127.0.0.1", "127.0.0.1,pg-restore"),
                    remote + " hostaddr=192.0.2.10",
                    remote + " gssencmode=prefer",
                    remote + " gssencmode=require",
                    local + " invalid_option=private_test_secret",
                    local + " password='private_test_secret",
                ):
                    with self.subTest(operation=operation), self.assertRaises(StagingConfigDenied) as caught:
                        private_db_connection_options(invalid, operation)
                    self.assertEqual(str(caught.exception), "PRIVATE_STAGING_CONFIG_DENIED")
                for override in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"):
                    with patch.dict(os.environ, {override:"private_test_secret"}):
                        with self.assertRaises(StagingConfigDenied):
                            private_db_connection_options(local, operation)
                with patch.dict(os.environ, {"PGGSSENCMODE":"require"}):
                    self.assertEqual(private_db_connection_options(remote, operation),
                                     {"gssencmode": "disable"})

    def test_private_db_bad_dsn_is_rejected_before_connect_or_startup(self):
        from src.phase3.auth.staging_service_profile import PrivateStagingProfile
        from apps.api.private_staging_asgi import verify_staging_database_authority
        from apps.api import product_session_api
        profile = PrivateStagingProfile(
            issuer="urn:test:issuer", audience="urn:test:api", kid="test-key",
            public_key_path=self.root / "pub.pem",
            history_dsn="host=127.0.0.1 dbname=stage user=history_app hostaddr=192.0.2.10",
            revoke_dsn=self.doc["revoke_dsn"], peer_verifier=lambda _: False)
        with patch("psycopg.connect", side_effect=AssertionError("MUST_NOT_CONNECT")) as connect:
            with self.assertRaises(StagingConfigDenied):
                verify_staging_database_authority(profile)
            with patch.object(product_session_api, "_PRIVATE_STAGING_PROFILE", profile):
                with self.assertRaisesRegex(RuntimeError, "^PRIVATE_STAGING_DB_DENIED$"):
                    product_session_api._conn("history")
            connect.assert_not_called()


    def test_app_only_startup_refuses_inherited_execution_capability(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from apps.api.private_app_only_asgi import prepare_app_only
        from apps.api import product_session_api
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        (self.root / "pub.pem").write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        cfg = load_app_only_config(self.config_file)
        with patch.dict(os.environ, {"PHASE3_APP_MODE":"APP_ONLY",
                "API_RUNNER_EXECUTION_MODE":"APP_ONLY", "API_CURSOR_KEY":"x"*48,
                "API_CURSOR_TTL_SECONDS":"300", "CI":"false", "GITHUB_ACTIONS":"false"}):
            with patch("apps.api.private_app_only_asgi._test_tls_material"), patch(
                    "apps.api.private_app_only_asgi.verify_staging_database_authority"), patch.object(
                    product_session_api, "install_private_staging_auth") as install:
                for name in ("_SERVER_NO_DISPATCH_TASK", "_CI_CLAIM_STUB",
                             "_CI_DISPATCH_REPORTER_DSN", "_CI_INVITED_RESULT_STORE"):
                    with self.subTest(name=name), patch.object(product_session_api, name, object()):
                        with self.assertRaises(StagingConfigDenied):
                            prepare_app_only(cfg)
                install.assert_not_called()

    def test_actual_app_only_send_never_invokes_spawn_gateway_or_persistence(self):
        from contextlib import ExitStack
        from apps.api import product_session_api
        wrapper = AppOnlyASGI(product_session_api.app, FakeProfile())
        async def invoke():
            async def trusted(scope, receive, send):
                scope["trusted_transport_test"] = True
                return await wrapper(scope, receive, send)
            async with AsyncClient(transport=ASGITransport(app=trusted),
                                   base_url="https://test.invalid") as client:
                for path in ("/v1/messages", "/v1/%6dessages"):
                    response = await client.post(path, content=b"not-json")
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.headers["cache-control"], "no-store")
                    self.assertIn("ENGINE_NOT_CONFIGURED", response.text)
        with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE":"APP_ONLY"}):
            with ExitStack() as stack:
                forbidden = [
                    "subprocess.Popen", "httpx.Client.request",
                    "psycopg.connect", "apps.api.product_session_api.answer_from_fixture",
                    "apps.api.product_session_api.start_t2",
                    "apps.api.product_session_api.finalize_t3",
                    "apps.api.product_session_api.after_definitive_commit",
                    "apps.api.product_session_api._run_ci_claim_send",
                ]
                spies = [stack.enter_context(patch(name, side_effect=AssertionError(
                         "FORBIDDEN_APP_ONLY_EFFECT"))) for name in forbidden]
                asyncio.run(invoke())
                for spy in spies:
                    spy.assert_not_called()


    def test_runtime_signer_drift_denies_before_pg_or_handler_and_recovers(self):
        from apps.api.app_only_signer_pin import SignerPin
        from apps.api import product_session_api
        profile = FakeProfile()
        profile.load_public_key = lambda: b"original"
        downstream = FastAPI()
        calls = []
        @downstream.get("/v1/conversations")
        async def history():
            calls.append("history")
            return {"ok": True}
        wrapper = AppOnlyASGI(downstream, profile, signer_pin=SignerPin.capture(b"original"))

        async def invoke():
            async def trusted(scope, receive, send):
                scope["trusted_transport_test"] = True
                return await wrapper(scope, receive, send)
            async with AsyncClient(transport=ASGITransport(app=trusted),
                                   base_url="https://test.invalid") as client:
                self.assertEqual((await client.get("/v1/conversations")).status_code, 200)
                profile.load_public_key = lambda: b"replacement"
                for path in ("/v1/conversations", "/health/ready", "/internal/ready"):
                    response = await client.get(path)
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.headers["cache-control"], "no-store")
                    self.assertNotIn("replacement", response.text)
                response = await client.post("/internal/auth/session/v1/revoke-one", content=b"bad")
                self.assertEqual(response.status_code, 503)
                self.assertEqual((await client.post("/v1/%6dessages", content=b"bad")).status_code, 503)
                profile.load_public_key = lambda: b"original"
                self.assertEqual((await client.get("/v1/conversations")).status_code, 200)
        with patch.dict(os.environ, {"API_RUNNER_EXECUTION_MODE": "APP_ONLY"}), \
                patch("apps.api.private_app_only_asgi.verify_staging_database_authority",
                      side_effect=AssertionError("MUST_NOT_PROBE_PG")) as pg, \
                patch.object(product_session_api, "_signed_history",
                             side_effect=AssertionError("MUST_NOT_ADMIT")) as admit:
            asyncio.run(invoke())
            pg.assert_not_called()
            admit.assert_not_called()
        self.assertEqual(calls, ["history", "history"])


    def test_startup_key_replacement_denied_before_verifier_install(self):
        # Exercise the actual installation function, not a mocked verifier.
        # DSN parsing only is mocked; no database is contacted in this L1 test.
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from apps.api import product_session_api as api
        from src.phase3.auth.staging_service_profile import PrivateStagingProfile
        def public_key():
            return rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        original, replacement = public_key(), public_key()
        path = self.root / "pub.pem"
        profile = PrivateStagingProfile(
            issuer="urn:test:bff", audience="urn:test:api", kid="test-kid",
            public_key_path=path, history_dsn="unused-history", revoke_dsn="unused-revoke",
            peer_verifier=lambda scope: True)
        path.write_bytes(original)
        inspected = profile.load_public_key()
        path.write_bytes(replacement)
        with patch.dict(os.environ, {"CI": "false", "GITHUB_ACTIONS": "false"}), \
                patch.object(api, "_PRIVATE_STAGING_PROFILE", None), \
                patch.object(api, "_PRIVATE_STAGING_VERIFIER", None), \
                patch.object(api, "_SERVER_NO_DISPATCH_TASK", None), \
                patch.object(api, "private_db_connection_options", return_value={}):
            with self.assertRaises(StagingConfigDenied):
                api.install_private_staging_auth(profile, expected_public_key=inspected)
            self.assertIsNone(api._PRIVATE_STAGING_PROFILE)
            self.assertIsNone(api._PRIVATE_STAGING_VERIFIER)
            path.write_bytes(original)
            api.install_private_staging_auth(profile, expected_public_key=inspected)
            self.assertIs(api._PRIVATE_STAGING_PROFILE, profile)
            self.assertIsNotNone(api._PRIVATE_STAGING_VERIFIER)



    def test_app_only_explicit_route_fence_never_admits_disabled_routes(self):
        calls = []
        async def downstream(scope, receive, send):
            calls.append((scope["method"], scope["raw_path"]))
            from starlette.responses import JSONResponse
            await JSONResponse({"kind":"allowed-test"})(scope, receive, send)
        app = AppOnlyASGI(downstream, FakeProfile())
        async def invoke(method, raw, path=None, query=b""):
            events = []
            async def recv():
                raise AssertionError("ROUTE_FENCE_MUST_NOT_READ_BODY")
            async def emit(event):
                events.append(event)
            await app({"type":"http", "scheme":"https",
                       "trusted_transport_test":True, "method":method,
                       "path":path or raw.decode(), "raw_path":raw,
                       "query_string":query, "headers":[], "http_version":"1.1"},
                      recv, emit)
            start = next(e for e in events if e["type"]=="http.response.start")
            headers = dict(start["headers"])
            body = json.loads(b"".join(e.get("body",b"") for e in events if e["type"]=="http.response.body"))
            self.assertEqual(headers[b"cache-control"],b"no-store")
            self.assertEqual(headers[b"x-content-type-options"],b"nosniff")
            self.assertNotIn(b"location",headers)
            return start["status"],body
        async def run():
            for method,raw,path in (
                ("GET",b"/v1/conversations",None),
                ("GET",b"/v1/conversations/A-1/messages",None),
                ("GET",b"/v1/message-requests/status",None),
                ("POST",b"/internal/auth/session/v1/revoke-one",None)):
                self.assertEqual((await invoke(method,raw,path))[0],200)
            for raw in (b"/v1/message-requests/engine-status",b"/v1/message-requests/retrieved-sources"):
                status,body=await invoke("GET",raw)
                self.assertEqual((status,body["error"]["code"]),(503,"ENGINE_STATUS_UNAVAILABLE"))
            for method,raw,path in (
                ("GET",b"/v1/message-requests/claim-test-status",None),
                ("GET",b"/v1/message-requests/invited-live-result",None),
                ("GET",b"/docs",None),("GET",b"/openapi.json",None),
                ("GET",b"/v1/conversations/",None),
                ("GET",b"/v1/%63onversations","/v1/conversations"),
                ("GET",b"/v1/conversations/A-1/messages/",None),
                ("POST",b"/internal/auth/session/v1/revoke-one/",None),
                ("HEAD",b"/v1/conversations",None),
                ("DELETE",b"/v1/conversations/A-1/messages",None),
                ("GET",b"/v1/future-unknown",None)):
                status,body=await invoke(method,raw,path)
                self.assertEqual((status,body["error"]["code"]),(404,"NOT_FOUND"))
            for raw in (b"/v1/messages",b"/v1/messages/",b"/v1/%6dessages/"):
                status,body=await invoke("POST",raw,"/v1/messages/" if raw.endswith(b"/") else None)
                self.assertEqual((status,body["error"]["code"]),(503,"ENGINE_NOT_CONFIGURED"))
            status,body=await invoke("GET",b"/health/live")
            self.assertEqual(status,200)
            self.assertTrue(body["process_alive"])
            self.assertFalse(body["application_ready"])
            status,body=await invoke("GET",b"/v1/capabilities")
            self.assertEqual(status,200)
            self.assertEqual(body["send_mode"],"DISABLED")
            self.assertFalse(body["background_dispatch_available"])
            self.assertEqual((await invoke("GET",b"/v1/capabilities",query=b"x=1"))[0],404)
        with patch.dict(os.environ,{"API_RUNNER_EXECUTION_MODE":"APP_ONLY","PHASE3_APP_MODE":"APP_ONLY"}):
            asyncio.run(run())
        self.assertEqual(len(calls),4)


    def test_app_only_pg_transport_is_verified_before_any_db_authority_probe(self):
        from dataclasses import replace
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from apps.api.private_app_only_asgi import prepare_app_only, _require_app_only_pg_tls
        cfg = load_app_only_config(self.config_file)
        for dsn in (cfg.history_dsn,cfg.revoke_dsn):
            verified = conninfo_to_dict(_require_app_only_pg_tls(dsn))
            self.assertEqual(verified["sslmode"],"verify-full")
            self.assertEqual(verified["gssencmode"],"disable")
        for field in ("history_dsn","revoke_dsn"):
            dsn=getattr(cfg,field)
            for changes in ({"sslmode":"disable"}, {"sslmode":"require"},
                            {"sslmode":"verify-ca"}, {"hostaddr":"127.0.0.1"},
                            {"sslrootcert":"relative.pem"}, {"port":""},
                            {"sslrootcert":str(self.root/"missing-ca.pem")}):
                with self.subTest(field=field,case=list(changes)):
                    bad=replace(cfg,**{field:make_conninfo(dsn,**changes)})
                    with patch.dict(os.environ,{"PHASE3_APP_MODE":"APP_ONLY",
                                                 "API_RUNNER_EXECUTION_MODE":"APP_ONLY",
                                                 "CI":"false","GITHUB_ACTIONS":"false"}), \
                            patch("apps.api.private_app_only_asgi._test_tls_material"), \
                            patch("apps.api.private_app_only_asgi.verify_staging_database_authority") as probe:
                        with self.assertRaises(StagingConfigDenied):
                            prepare_app_only(bad)
                        probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
