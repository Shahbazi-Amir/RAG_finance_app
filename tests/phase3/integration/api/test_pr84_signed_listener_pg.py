"""Separate real signed-listener PG TLS lab; does not edit pinned API011 suite.

Only the disposable CI service and synthetic OIDC identities are used.
No production grants, engine, existing volumes, or SQL011.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
import json
import os
import secrets
import ssl
import subprocess
import sys
import time
import uuid
import unittest

import httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo

import test_product_session_011 as original
from loopback_pg_relay import LoopbackPGRelay


class PR84SignedHistory(original.RealProductSession011):
    # Reuse the exact pinned ephemeral setup and teardown, not its test cases.
    test_API011_01_pending_denied_then_A_B_real_owner_lists_and_005_replay = None
    test_API011_02_private_revoke_commit_fresh_A_401_B_200 = None
    test_API011_03_wrong_session_signature_query_body_and_revoker_roles = None
    test_API011_04_real_signed_messages_status_refresh_and_revoke_two_owners = None
    test_API011_99_pinned_https_callback_real_keycloak_and_redirect_denies = None

    def test_signed_history_on_fresh_lab_database(self):
        self.assertEqual(os.getenv("CI"), "true")
        self.assertEqual(os.getenv("GITHUB_ACTIONS"), "true")
        ca = Path(os.environ["F3_SIGNED_LISTENER_PG_CA"])
        self.assertTrue(ca.is_file())
        options = conninfo_to_dict(os.environ["DB_APP_DSN"])
        self.assertEqual((options.get("host"), options.get("port"), options.get("dbname")),
                         ("127.0.0.1", "5432", "history_ci"))
        a, b = self.login("A"), self.login("B")
        self.assertNotEqual(a["owner_id"], b["owner_id"])
        title = "PR84_" + uuid.uuid4().hex
        self.seed(a, title + "_A")
        self.seed(a, title + "_A2")
        self.seed(b, title + "_B")

        from apps.api import history_api
        from repository import start_t2
        from psycopg.rows import dict_row
        question = "synthetic PR84 historical message"
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True, row_factory=dict_row) as c:
            created = history_api.create_conversation(c, a["owner_id"], {
                "kind": "create_conversation_request", "contract_version": "product.v1",
                "client_conversation_id": history_api.uid(), "idempotency_key": "pr84_" + uuid.uuid4().hex,
                "title": title + "_detail",
            }, history_api.uid(), history_api.uid())
            cid = created["conversation"]["conversation_id"]
            send = {"kind": "send_message_request", "contract_version": "product.v1",
                    "requested_conversation_id": cid, "client_message_id": history_api.uid(),
                    "idempotency_key": "pr84_" + uuid.uuid4().hex, "question": question}
            persisted = history_api.send_t1(c, a["owner_id"], send, history_api.uid(), history_api.uid())
            attempt = start_t2(c, a["owner_id"], cid, send["client_message_id"],
                               send["idempotency_key"], history_api.uid(), history_api.uid())

        # Fresh CI-only database copied from seeded synthetic data. Never
        # remove or modify another database; CI destroys its service afterward.
        labdb = "history_pr84_signed_lab"
        admin_dsn = make_conninfo(os.environ["DB_APP_DSN"], user="postgres",
                                 password=os.environ["PGPASSWORD"], dbname="postgres",
                                 sslmode="verify-full", sslrootcert=str(ca))
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute("CREATE DATABASE history_pr84_signed_lab TEMPLATE history_ci")

        def dsn(envkey):
            return make_conninfo(os.environ[envkey], dbname=labdb,
                                 sslmode="verify-full", sslrootcert=str(ca))
        def counts():
            with psycopg.connect(dsn("DB_MIG_DSN"), autocommit=True) as conn:
                return tuple(conn.execute("SELECT count(*) FROM history_l1." + table).fetchone()[0]
                             for table in ("conversations", "messages", "send_receipts",
                                           "execution_attempts", "answers"))
        for key in ("DB_APP_DSN", "AUTH_REVOKER_DSN"):
            with psycopg.connect(dsn(key)) as conn:
                self.assertTrue(conn.execute(
                    "SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0])

        relay = LoopbackPGRelay(5432)
        self.addCleanup(relay.close)
        old_url = self.url
        child = None
        try:
            with TemporaryDirectory(prefix="pr84-signed-lab-") as directory:
                root = Path(directory)
                config, cursor = root / "config.json", root / "cursor.key"
                key_file, public_file = root / "server.key", root / "bff-public.pem"
                cursor.write_text(secrets.token_urlsafe(48))
                key_file.write_bytes((self.temp / "server.key").read_bytes())
                public_file.write_bytes(self.pubkey.read_bytes())
                for file in (cursor, key_file, public_file):
                    file.chmod(0o600)
                port = original.port()
                config.write_text(json.dumps({
                    "contract_version": "api.private_app_only_asgi.v2",
                    "listen_host": "127.0.0.1", "listen_port": port,
                    "server_tls_cert_file": str(self.temp / "server.pem"),
                    "server_tls_key_file": str(key_file),
                    "trusted_bff_ca_file": str(self.fixture.ca),
                    "bff_leaf_cert_sha256": sha256(ssl.PEM_cert_to_DER_cert(
                        Path(self.fixture.cert).read_text())).hexdigest(),
                    "bff_issuer": original.ISSUER, "bff_audience": original.AUDIENCE,
                    "bff_kid": original.KID, "bff_rs256_public_key_file": str(public_file),
                    "history_dsn": make_conninfo(dsn("DB_APP_DSN"), port=relay.port),
                    "revoke_dsn": make_conninfo(dsn("AUTH_REVOKER_DSN"), port=relay.port),
                    "cursor_key_file": str(cursor), "cursor_ttl_seconds": 300,
                }))
                config.chmod(0o600)
                # Separate private runtime process receives only its explicit
                # normal configuration, not harness switches or engine keys.
                runtime_env = {"PATH": os.environ["PATH"], "HOME": str(root),
                               "PHASE3_APP_MODE": "APP_ONLY",
                               "API_RUNNER_EXECUTION_MODE": "APP_ONLY"}
                child = subprocess.Popen([sys.executable, "-m",
                    "apps.api.private_app_only_asgi", "--config", str(config)],
                    cwd=original.ROOT, env=runtime_env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.url = "https://127.0.0.1:" + str(port)
                for _ in range(100):
                    self.assertIsNone(child.poll(), "SIGNED_LISTENER_STARTUP_FAILED")
                    try:
                        if self.request("GET", "/internal/ready").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    self.fail("SIGNED_LISTENER_NOT_READY")
                self.assertEqual(self.request("GET", "/health/ready").status_code, 503)
                before = counts()

                def get(actor, path=original.LIST, params=None):
                    raw = urlencode(params or {})
                    proof, _ = self.signed(actor, path=path, query=raw.encode("ascii"))
                    return self.request("GET", path, proof, query=("?" + raw if raw else ""))

                page = get(a, params={"limit": 100})
                self.assertEqual(page.status_code, 200)
                titles = {row["title"] for row in page.json()["items"]}
                self.assertIn(title + "_A", titles)
                self.assertIn(title + "_A2", titles)
                self.assertNotIn(title + "_B", titles)
                self.assertEqual(get(b).status_code, 200)
                path = "/v1/conversations/" + cid + "/messages"
                status_path = "/v1/message-requests/status"
                params = {key: send[key] for key in
                          ("requested_conversation_id", "client_message_id", "idempotency_key")}
                for _ in range(2):
                    detail = get(a, path)
                    self.assertEqual(detail.status_code, 200)
                    self.assertIn(question, [item["text"] for item in detail.json()["items"]])
                    status = get(a, status_path, params)
                    self.assertEqual(status.status_code, 200)
                    self.assertEqual(status.json()["attempt_id"], attempt["id"])
                    self.assertEqual(status.json()["message_id"], persisted["message_id"])
                    self.assertIsNone(status.json()["answer"])
                self.assertEqual(get(b, path).status_code, 404)
                self.assertEqual(get(b, status_path, params).status_code, 404)

                first = get(a, params={"limit": 1})
                self.assertEqual(first.status_code, 200)
                next_cursor = first.json()["page"]["next_cursor"]
                self.assertTrue(next_cursor)
                second = get(a, params={"limit": 1, "cursor": next_cursor})
                self.assertEqual(second.status_code, 200)
                self.assertNotEqual(first.json()["items"][0]["conversation_id"],
                                    second.json()["items"][0]["conversation_id"])
                self.assertEqual(get(b, params={"limit": 1, "cursor": next_cursor}).status_code, 422)
                self.assertEqual(self.request("GET", original.LIST).status_code, 401)
                replay, _ = self.signed(a)
                self.assertEqual(self.request("GET", original.LIST, replay).status_code, 200)
                self.assertEqual(self.request("GET", original.LIST, replay).status_code, 401)
                self.assertIsNone(self.request("GET", original.LIST, self.signed(a)[0], cert=False))

                blocked = self.request("POST", "/v1/messages", body=b"not JSON")
                self.assertEqual(blocked.status_code, 503)
                self.assertEqual(blocked.json(), {"error": "ENGINE_NOT_AVAILABLE"})
                self.assertEqual(counts(), before)

                relay.pause()
                try:
                    self.assertEqual(self.request("GET", "/internal/ready").status_code, 503)
                    self.assertEqual(get(a).status_code, 503)
                finally:
                    relay.resume()
                self.assertEqual(self.request("GET", "/internal/ready").status_code, 200)
                self.assertEqual(get(a).status_code, 200)
                public_bytes = public_file.read_bytes()
                public_file.write_bytes(b"invalid")
                self.assertEqual(self.request("GET", "/internal/ready").status_code, 503)
                self.assertEqual(get(a).status_code, 503)
                public_file.write_bytes(public_bytes)
                self.assertEqual(self.request("GET", "/internal/ready").status_code, 200)
                raw = json.dumps({"operation_id": str(uuid.uuid4())}, separators=(",", ":")).encode()
                proof, _ = self.signed(a, "POST", original.REVOKE, raw)
                self.assertEqual(self.request("POST", original.REVOKE, proof, body=raw).status_code, 200)
                self.assertEqual(get(a).status_code, 401)
                self.assertEqual(get(b).status_code, 200)
                self.assertEqual(counts(), before)
                print("PR84_SIGNED_LISTENER_PG_TLS_AB_PAGINATION_REPLAY_REVOKE_ZERO_SEND_PASS", flush=True)
        finally:
            self.url = old_url
            if child is not None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
