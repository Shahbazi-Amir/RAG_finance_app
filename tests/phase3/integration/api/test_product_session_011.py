"""Real SQL + mTLS HTTP Product-session API (no override), pinned #48 login."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urljoin, urlsplit, parse_qs
import base64
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
import unittest
import uuid

import httpx
import jwt
import psycopg
from psycopg.rows import dict_row
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(Path(__file__).parent)]
import test_bootstrap_oidc_010 as pinned
from initial_oidc_harness import CallbackHarness, LoginForm, IsolatedOIDCFailure
from src.phase3.storage.postgres import auth_session
from src.phase3.storage.postgres.service_replay import _digest_and_exp
from apps.api import history_api
from repository import start_t2

ISSUER = "urn:rag-finance:synthetic-product-session"
AUDIENCE = "urn:rag-finance:api:history-h1-isolated"
KID = "ci-product-session-kid"
REVOKE = "/internal/auth/session/v1/revoke-one"
LIST = "/v1/conversations"


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RealProductSession011(unittest.TestCase):
    """#48 actual Keycloak issue/ACK -> real 004+005 list / revoke / A-B."""

    @classmethod
    def setUpClass(cls):
        if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
                or "dbname=history_ci" not in os.getenv("AUTH_MIG_DSN", "")):
            raise RuntimeError("HARD_STOP_EPHEMERAL_CI_ONLY")
        cls.base = pinned.InitialBootstrap010
        cls.base.setUpClass()
        cls.children = []
        cls.hcb = None
        try:
            cls.fixture = cls.base.clients["b"]
            cls.temp = Path(cls.base.tmp.name)
            public = cls.fixture.signer.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
            cls.pubkey = cls.temp / "session_signer_public.pem"
            cls.pubkey.write_bytes(public)
            # This is a live permission-denial reproduction, not a production
            # migration. auth_revoker lacks 003 revoke_one and 004/005 grants.
            with psycopg.connect(os.environ["AUTH_REVOKER_DSN"],
                                 autocommit=True, row_factory=dict_row) as c:
                assert c.execute("SELECT has_function_privilege("
                    "current_user,'auth_l1.revoke_one(text,bigint)','EXECUTE') AS ok"
                    ).fetchone()["ok"] is False
                assert c.execute("SELECT has_function_privilege("
                    "current_user,'auth_l1.admit_session_fenced(text,text,bigint,integer)',"
                    "'EXECUTE') AS ok").fetchone()["ok"] is False
                assert c.execute("SELECT has_function_privilege("
                    "current_user,'auth_l1.consume_service_assertion(text,bigint)',"
                    "'EXECUTE') AS ok").fetchone()["ok"] is False
            print("API011_ROLE_GAP_003_004_005_REPRODUCED_PASS", flush=True)
            with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True) as c:
                # TEMPORARY CI grants; no migration or production roles changed.
                c.execute("GRANT USAGE ON SCHEMA auth_l1 TO history_app")
                for name in (
                    "consume_service_assertion(text,bigint)",
                    "admit_session_fenced(text,text,bigint,integer)",
                ):
                    c.execute("GRANT EXECUTE ON FUNCTION auth_l1." + name +
                              " TO history_app, auth_revoker")
                c.execute("GRANT EXECUTE ON FUNCTION "
                          "auth_l1.revoke_one(text,bigint) TO auth_revoker")
            cls.api_port = port()
            env = dict(os.environ)
            env.update(
                API_PRODUCT_PROOF_PUBLIC_KEY_PATH=str(cls.pubkey),
                API_PRODUCT_PROOF_ISSUER=ISSUER,
                API_PRODUCT_PROOF_AUDIENCE=AUDIENCE,
                API_PRODUCT_PROOF_KID=KID,
                API_CURSOR_KEY=secrets.token_urlsafe(48),
                API_CURSOR_TTL_SECONDS="300",
                # The identical AppOnlyASGI guard used in live deployment
                # surrounds original signed Product API on real CI HTTPS/PG.
                API_RUNNER_EXECUTION_MODE="APP_ONLY",
                PHASE3_APP_MODE="APP_ONLY",
                APP_ONLY_CI_API_PORT=str(cls.api_port),
                APP_ONLY_CI_CLIENT_CERT=str(cls.fixture.cert),
                APP_ONLY_CI_SERVER_CERT=str(cls.temp / "server.pem"),
                APP_ONLY_CI_SERVER_KEY=str(cls.temp / "server.key"),
                APP_ONLY_CI_CLIENT_CA=str(cls.fixture.ca),
            )
            command = [
                sys.executable, "-u",
                str(Path(__file__).with_name("app_only_signed_pg_ci_h11.py")),
            ]
            cls.api_worker_log = cls.temp / "app_only_signed_h11_ci.log"
            cls.api_worker_log_file = cls.api_worker_log.open("wb")
            cls.api_worker_env = dict(env)
            cls.api_worker_command = list(command)
            child = subprocess.Popen(command, cwd=ROOT, env=env,
                                     stdout=subprocess.DEVNULL,
                                     stderr=cls.api_worker_log_file)
            cls.children.append(child)
            tls = ssl.create_default_context(cafile=cls.fixture.ca)
            tls.load_cert_chain(cls.fixture.cert, cls.fixture.key)
            cls.tls = tls
            cls.url = "https://127.0.0.1:" + str(cls.api_port)
            for _ in range(80):
                if child.poll() is not None:
                    cls.api_worker_log_file.flush()
                    # The worker emits only a Python traceback, never
                    # a DSN/config dump. Redact sensitive assignments anyway.
                    import re
                    tail = cls.api_worker_log.read_text(
                        encoding="utf-8", errors="replace")[-2500:]
                    tail = re.sub(
                        r"(?i)(password|token|secret|key)=\\S+",
                        r"\\1=<redacted>", tail)
                    print("API_F3_SIGNED_H11_CI_STARTUP_DIAGNOSTIC: " + tail,
                          flush=True)
                    raise AssertionError("REAL_PRODUCT_API_EARLY_EXIT")
                try:
                    with httpx.Client(verify=tls, trust_env=False,
                                      timeout=1) as c:
                        res = c.get(cls.url + LIST)
                    if res.status_code == 401:
                        break
                except httpx.HTTPError:
                    time.sleep(0.1)
            else:
                raise AssertionError("REAL_PRODUCT_API_NOT_READY")
        except BaseException:
            cls._cleanup()
            raise

    @classmethod
    def _cleanup(cls):
        for child in getattr(cls, "children", []):
            child.terminate()
            try: child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.kill();child.wait(timeout=4)
        if getattr(cls, "api_worker_log_file", None):
            cls.api_worker_log_file.close()
            cls.api_worker_log_file = None
        if getattr(cls, "hcb", None):
            cls.hcb.stop()
        if getattr(cls, "base", None):
            cls.base.tearDownClass()
        # Last resort clean of temporary, CI-only privilege bridging.
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True) as c:
            for name in (
                "consume_service_assertion(text,bigint)",
                "admit_session_fenced(text,text,bigint,integer)",
            ):
                c.execute("REVOKE EXECUTE ON FUNCTION auth_l1." + name +
                          " FROM history_app, auth_revoker")
            c.execute("REVOKE EXECUTE ON FUNCTION "
                      "auth_l1.revoke_one(text,bigint) FROM auth_revoker")
            c.execute("REVOKE USAGE ON SCHEMA auth_l1 FROM history_app")

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    def signed(self, pending, method="GET", path=LIST, body=b"", query=b"", *,
               override=None):
        now = int(time.time())
        claims = {
            "iss": ISSUER, "aud": AUDIENCE, "iat": now, "nbf": now,
            "exp": now + 25, "jti": secrets.token_urlsafe(24),
            "method": method,
            "raw_path_sha256": sha256(path.encode("ascii")).hexdigest(),
            "raw_query_sha256": sha256(query).hexdigest(),
            "body_sha256": sha256(body).hexdigest(),
            "body_len": len(body),
            "session_ref": pending["session_verifier"],
            "owner_id": pending["owner_id"],
            "epoch": pending["epoch"],
            "generation": pending["generation"],
        }
        if override:
            claims.update(override)
        return jwt.encode(
            claims, self.fixture.signer, algorithm="RS256",
            headers={"typ": "JWT", "kid": KID}), claims

    def request(self, method, path, token=None, *, body=None, query="",
                headers=None, cert=True):
        h = dict(headers or {})
        if token is not None:
            h["Authorization"] = "BFF-Assertion " + token
        if body is not None:
            h["Content-Type"] = "application/json"
        tls = ssl.create_default_context(cafile=self.fixture.ca)
        if cert:
            tls.load_cert_chain(self.fixture.cert, self.fixture.key)
        try:
            with httpx.Client(verify=tls, trust_env=False,
                              timeout=12, follow_redirects=False) as c:
                return c.request(method, self.url + path + query, content=body,
                                 headers=h)
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError):
            # OpenSSL/uvicorn may abort the mTLS handshake before HTTP,
            # which HTTPX reports as ConnectError OR RemoteProtocolError.
            if not cert:
                return None
            raise

    def login(self, label, ack=True):
        base = self.base("test_PKCEAPI01_cross_process_start_complete_real_Keycloak_ACK")
        ids, start = base.new_start("b")
        callback = base.callback(start, label)
        status, pending = base.complete("c", ids, start, callback)
        self.assertEqual(status, 201)
        self.assertEqual(pending["state"], "ISSUED_PENDING_BINDING")
        if ack:
            self.assertIsNone(base.inspect(pending["session_verifier"]))
            result, _ = base.alias_ack("b", ids, pending)
            self.assertEqual(result[0], 200)
            self.assertEqual(result[1]["state"], "ACTIVE")
            self.assertEqual(base.inspect(pending["session_verifier"])["owner_id"],
                             pending["owner_id"])
        return pending

    def seed(self, pending, title):
        request = {
            "kind": "create_conversation_request", "contract_version": "product.v1",
            "client_conversation_id": history_api.uid(),
            "idempotency_key": "real011_" + uuid.uuid4().hex,
            "title": title,
        }
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as c:
            created = history_api.create_conversation(c, pending["owner_id"], request,
                                            history_api.uid(), history_api.uid())
            return created["conversation"]["conversation_id"]

    def list(self, pending, *, override=None, token=None, query=""):
        t = token or self.signed(pending, query=query.removeprefix("?").encode(), override=override)[0]
        return self.request("GET", LIST, t, query=query)

    def test_API011_01_pending_denied_then_A_B_real_owner_lists_and_005_replay(self):
        a = self.login("A", ack=False)
        before, _ = self.signed(a)
        self.assertEqual(self.list(a, token=before).status_code, 401)
        # Pending denial rolls back 005 JTI, as with 004 admission.
        base = self.base("test_PKCEAPI01_cross_process_start_complete_real_Keycloak_ACK")
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            self.assertIsNone(auth_session.inspect(c, a["session_verifier"]))
        # Pending fixture never ACKs; create a clean active pair.
        a = self.login("A")
        b = self.login("B")
        self.assertNotEqual(a["owner_id"], b["owner_id"])
        self.seed(a, "real-011-private-A")
        self.seed(b, "real-011-private-B")
        for own, expected, foreign in (
            (a, "real-011-private-A", "real-011-private-B"),
            (b, "real-011-private-B", "real-011-private-A"),
        ):
            token, claims = self.signed(own)
            res = self.list(own, token=token)
            self.assertEqual(res.status_code, 200, res.text)
            doc = res.json()
            self.assertEqual(doc["kind"], "conversation_page")
            self.assertEqual(doc["scope_user_id"], own["owner_id"])
            self.assertIn(expected, [x["title"] for x in doc["items"]])
            self.assertNotIn(foreign, [x["title"] for x in doc["items"]])
            self.assertEqual(self.list(own, token=token).status_code, 401)
            bad = self.list(own, override={"owner_id": b["owner_id"] if own is a else a["owner_id"]})
            self.assertEqual(bad.status_code, 401)
        self.assertEqual(self.request("GET", LIST).status_code, 401)
        self.assertEqual(self.request("GET", LIST, headers={"X-Owner-ID": a["owner_id"]}).status_code, 401)
        self.assertIsNone(self.request("GET", LIST, self.signed(a)[0], cert=False))
        print("API011_REAL_HISTORY_PENDING_REPLAY_OWNER_AB_MTLS_PASS", flush=True)

    def test_API011_02_private_revoke_commit_fresh_A_401_B_200(self):
        a, b = self.login("A"), self.login("B")
        self.seed(a, "real-011-revoked-A")
        self.seed(b, "real-011-live-B")
        self.assertEqual(self.list(a).status_code, 200)
        self.assertEqual(self.list(b).status_code, 200)
        op = str(uuid.uuid4())
        raw = json.dumps({"operation_id": op}, separators=(",", ":")).encode("ascii")
        signed, claims = self.signed(a, "POST", REVOKE, raw)
        response = self.request("POST", REVOKE, signed, body=raw)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"state":"REVOKED_COMMITTED","operation_id":op})
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            self.assertIsNone(auth_session.inspect(c, a["session_verifier"]))
            self.assertIsNotNone(auth_session.inspect(c, b["session_verifier"]))
        # No false second success and no false success on replay.
        self.assertEqual(self.request("POST", REVOKE, signed, body=raw).status_code, 401)
        self.assertEqual(self.request("POST", REVOKE, self.signed(
            a, "POST", REVOKE, raw)[0], body=raw).status_code, 401)
        self.assertEqual(self.list(a).status_code, 401)
        again = self.list(b)
        self.assertEqual(again.status_code, 200)
        doc = again.json()
        self.assertEqual(doc["scope_user_id"], b["owner_id"])
        self.assertTrue(all(x["owner_user_id"] == b["owner_id"] for x in doc["items"]))
        self.assertNotIn("real-011-revoked-A", [x["title"] for x in doc["items"]])
        print("API011_COMMITTED_REVOKE_A_401_B_OWNER_ONLY_200_PASS", flush=True)

    def test_API011_03_wrong_session_signature_query_body_and_revoker_roles(self):
        a, b = self.login("A"), self.login("B")
        # Same authenticated service key but wrong owner/epoch are DB denied.
        self.assertEqual(self.list(a, override={"owner_id": b["owner_id"]}).status_code, 401)
        self.assertEqual(self.list(a, override={"epoch": a["epoch"]+1}).status_code, 401)
        t, _ = self.signed(a, query=b"limit=2")
        self.assertEqual(self.list(a, token=t).status_code, 401)
        invalid = self.signed(a)[0]
        self.assertEqual(self.request("GET", LIST, invalid, headers={
            "X-Owner-ID":a["owner_id"]}).status_code, 401)
        op=str(uuid.uuid4())
        body=json.dumps({"operation_id":op}).encode()
        token,_=self.signed(a, "POST", REVOKE, body)
        # Valid differently signed JSON has matching schema, but bytes
        # differ from the RSA-bound body: deny proof, not a schema 422.
        tampered = json.dumps({"operation_id":str(uuid.uuid4())}).encode()
        self.assertEqual(self.request("POST", REVOKE, token,
                                     body=tampered).status_code, 401)
        with psycopg.connect(os.environ["AUTH_REVOKER_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            self.assertFalse(c.execute("SELECT has_table_privilege("
               "current_user,'auth_l1.sessions','SELECT') AS allowed"
            ).fetchone()["allowed"])
            # The restricted revoker lacks even USAGE of history_l1;
            # directly resolving its table name raises InsufficientPrivilege.
            # Test the stronger schema boundary without granting USAGE.
            self.assertFalse(c.execute("SELECT has_schema_privilege("
                "current_user,'history_l1','USAGE') AS allowed"
            ).fetchone()["allowed"])
        print("API011_REVOKE_PROOF_BODY_OWNER_AND_RESTRICTED_ROLE_PASS", flush=True)

    def test_API011_04_real_signed_messages_status_refresh_and_revoke_two_owners(self):
        """Actual HTTPS client cert + RS256 signed BFF + restricted PG17.

        One committed T1/T2, owner-scoped History, read-only refresh,
        cross-owner masking and revoke. No C018 or model dispatch.
        """
        from urllib.parse import urlencode
        a, b = self.login("A"), self.login("B")
        self.assertNotEqual(a["owner_id"], b["owner_id"])
        question = "CI_PRIVATE_A_MESSAGE_NOT_FOR_B"
        req = {
            "kind": "create_conversation_request",
            "contract_version": "product.v1",
            "client_conversation_id": history_api.uid(),
            "idempotency_key": "cihist_" + uuid.uuid4().hex,
            "title": "CI_PRIVATE_A_CONVERSATION",
        }
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as c:
            created = history_api.create_conversation(
                c, a["owner_id"], req, history_api.uid(), history_api.uid())
            cid = created["conversation"]["conversation_id"]
            send = {
                "kind": "send_message_request",
                "contract_version": "product.v1",
                "requested_conversation_id": cid,
                "client_message_id": history_api.uid(),
                "idempotency_key": "cihist_" + uuid.uuid4().hex,
                "question": question,
            }
            persisted = history_api.send_t1(
                c, a["owner_id"], send, history_api.uid(), history_api.uid())
            attempt = start_t2(
                c, a["owner_id"], cid, send["client_message_id"],
                send["idempotency_key"], history_api.uid(), history_api.uid())
        path = "/v1/conversations/" + cid + "/messages"
        status_path = "/v1/message-requests/status"
        query = "?" + urlencode({
            "requested_conversation_id": cid,
            "client_message_id": send["client_message_id"],
            "idempotency_key": send["idempotency_key"],
        })
        def signed_get(actor, endpoint, q=""):
            token, _ = self.signed(
                actor, method="GET", path=endpoint,
                query=q.removeprefix("?").encode("ascii"))
            return self.request("GET", endpoint, token, query=q)

        # A real HTTP response from PostgreSQL, not an in-process history
        # dependency override or forged client-side actor.
        for _ in range(2):
            page = signed_get(a, path)
            self.assertEqual(page.status_code, 200, page.text)
            doc = page.json()
            self.assertEqual(doc["kind"], "conversation_messages_page")
            self.assertEqual(doc["owner_user_id"], a["owner_id"])
            self.assertIn(question, [x["text"] for x in doc["items"]])
            self.assertTrue(all(x["owner_user_id"] == a["owner_id"]
                                for x in doc["items"]))
            status = signed_get(a, status_path, query)
            self.assertEqual(status.status_code, 200, status.text)
            data = status.json()
            self.assertEqual(data["kind"], "message_request_status")
            self.assertEqual(data["status"], "attempt_pending")
            self.assertEqual(data["attempt_id"], attempt["id"])
            self.assertEqual(data["message_id"], persisted["message_id"])
            self.assertIsNone(data["answer"])
        # Owner B has an active valid session but cannot learn the resource.
        for endpoint, q in ((path, ""), (status_path, query)):
            denied = signed_get(b, endpoint, q)
            self.assertEqual(denied.status_code, 404, denied.text)
            self.assertNotIn(question, denied.text)
            self.assertEqual(denied.headers.get("cache-control"), "no-store")
        # Refreshes only read; no additional T1/T2 or synthetic T3.
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            count = admin.execute(
                "SELECT count(*) AS n FROM history_l1.execution_attempts "
                "WHERE owner_id=%s AND send_receipt_id IN "
                "(SELECT id FROM history_l1.send_receipts "
                "WHERE owner_id=%s AND client_message_id=%s)",
                (a["owner_id"], a["owner_id"], send["client_message_id"])
            ).fetchone()["n"]
            self.assertEqual(count, 1)
            # Source-fidelity witness: the *exact* signed HTTP response IDs
            # must be the committed row in PG, with original client request
            # tuple, question and owner. Merely matching row counts is weak.
            witness = admin.execute(
                "SELECT e.id AS attempt_id, e.owner_id, "
                "r.client_message_id, r.idempotency_key, "
                "r.resolved_conversation_id, r.user_message_id, m.text "
                "FROM history_l1.execution_attempts AS e "
                "JOIN history_l1.send_receipts AS r "
                "ON r.owner_id=e.owner_id AND r.id=e.send_receipt_id "
                "JOIN history_l1.messages AS m "
                "ON m.owner_id=r.owner_id "
                "AND m.id=r.user_message_id "
                "AND m.conversation_id=r.resolved_conversation_id "
                "WHERE e.owner_id=%s AND e.id=%s",
                (a["owner_id"], data["attempt_id"]),
            ).fetchall()
            self.assertEqual(len(witness), 1)
            w = witness[0]
            self.assertEqual(
                (w["attempt_id"], w["owner_id"],
                 w["client_message_id"], w["idempotency_key"],
                 w["resolved_conversation_id"], w["user_message_id"],
                 w["text"]),
                (data["attempt_id"], a["owner_id"],
                 send["client_message_id"], send["idempotency_key"],
                 cid, data["message_id"], question),
            )
            # A forged owner cannot resolve this same T2 in SQL either.
            denied_sql = admin.execute(
                "SELECT count(*) AS n FROM history_l1.execution_attempts "
                "WHERE owner_id=%s AND id=%s",
                (b["owner_id"], data["attempt_id"]),
            ).fetchone()["n"]
            self.assertEqual(denied_sql, 0)
            answers = admin.execute(
                "SELECT count(*) AS n FROM history_l1.answers "
                "WHERE owner_id=%s AND attempt_id=%s",
                (a["owner_id"], attempt["id"])
            ).fetchone()["n"]
            self.assertEqual(answers, 0)
        operation_id = str(uuid.uuid4())
        raw = json.dumps({"operation_id": operation_id},
                         separators=(",", ":")).encode("ascii")
        revocation = self.request(
            "POST", REVOKE, self.signed(a, "POST", REVOKE, raw)[0],
            body=raw)
        self.assertEqual(revocation.status_code, 200, revocation.text)
        self.assertEqual(signed_get(a, path).status_code, 401)
        self.assertEqual(signed_get(a, status_path, query).status_code, 401)
        # Independent B remains admitted; A is not made readable by B.
        self.assertEqual(self.list(b).status_code, 200)
        self.assertEqual(signed_get(b, status_path, query).status_code, 404)
        print("API_F3_REAL_SIGNED_PG_T1_T2_HISTORY_REFRESH_AB_REVOKE_PASS",
              flush=True)

    def test_API011_05_app_only_send_503_before_body_no_t1_t2_pg_write(self):
        """Actual pinned-mTLS signed API wrapper must never start Send.

        Unlike a standalone ASGI stub, this runs over real Uvicorn HTTPS and
        the original live Postgres role; only synthetic CI user data exists.
        """
        a = self.login("A")
        body = b"not-json-" + (b"x" * 24576)
        signed, _ = self.signed(a, method="POST", path="/v1/messages", body=body)
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            before = admin.execute(
                "SELECT "
                "(SELECT count(*) FROM history_l1.send_receipts WHERE owner_id=%s) AS t1,"
                "(SELECT count(*) FROM history_l1.execution_attempts WHERE owner_id=%s) AS t2,"
                "(SELECT count(*) FROM history_l1.answers WHERE owner_id=%s) AS t3",
                (a["owner_id"], a["owner_id"], a["owner_id"])
            ).fetchone()
        # The payload is deliberately too large/invalid for Product.v1.
        # If the inner endpoint reads it, it returns validation/413 rather
        # than 503. This proves the app-only wrapper stops it first.
        response = self.request("POST", "/v1/messages", signed, body=body)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertIn("ENGINE_NOT_CONFIGURED", response.text)
        self.assertNotIn("not-json-", response.text)
        # H11/ASGI percent-decodes to /v1/messages; raw_path differs.
        # No route-encoding alias is allowed to bypass the pre-body fence.
        encoded = self.request(
            "POST", "/v1/%6dessages", signed, body=body)
        self.assertEqual(encoded.status_code, 503, encoded.text)
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            after = admin.execute(
                "SELECT "
                "(SELECT count(*) FROM history_l1.send_receipts WHERE owner_id=%s) AS t1,"
                "(SELECT count(*) FROM history_l1.execution_attempts WHERE owner_id=%s) AS t2,"
                "(SELECT count(*) FROM history_l1.answers WHERE owner_id=%s) AS t3",
                (a["owner_id"], a["owner_id"], a["owner_id"])
            ).fetchone()
        self.assertEqual(before, after)
        self.assertEqual(self.list(a).status_code, 200)
        print("API_F3_APP_ONLY_REAL_SIGNED_PG_SEND_ZERO_T1_T2_T3_PASS", flush=True)

    def test_API011_06_signed_readiness_pg_session_and_revoke_fail_closed(self):
        """Real HTTPS pinned BFF and SQL: 200 only for signed live session.

        A malformed signer/subject, missing assertion, replay or revoked
        user never turns signed API readiness green. No synthetic dispatch.
        """
        path = "/health/ready"
        a, b = self.login("A"), self.login("B")
        self.seed(a, "ci-ready-A")
        self.assertEqual(self.request("GET", path).status_code, 503)
        forged_route = self.signed(a, path="/v1/conversations")[0]
        self.assertEqual(self.request("GET", path, forged_route).status_code, 503)
        bad_owner = self.signed(a, path=path,
                                override={"owner_id": b["owner_id"]})[0]
        self.assertEqual(self.request("GET", path, bad_owner).status_code, 503)
        valid = self.signed(a, path=path)[0]
        checked = self.request("GET", path, valid)
        self.assertEqual(checked.status_code, 200, checked.text)
        self.assertEqual(checked.headers.get("cache-control"), "no-store")
        doc = checked.json()
        self.assertEqual(doc["kind"], "api_app_only_readiness")
        self.assertEqual(doc["state"], "ready")
        self.assertEqual(doc["signed_actor_pg"], "verified")
        self.assertEqual(doc["bootstrap_idp"], "not_probed")
        self.assertEqual(doc["generation"], "unavailable")
        self.assertEqual(self.request("GET", path, valid).status_code, 503)
        # A's session revoke is a real committed PG transaction.
        op = str(uuid.uuid4())
        body = json.dumps({"operation_id": op}, separators=(",", ":")).encode()
        revoke = self.request("POST", REVOKE,
                              self.signed(a, "POST", REVOKE, body)[0], body=body)
        self.assertEqual(revoke.status_code, 200, revoke.text)
        self.assertEqual(self.request(
            "GET", path, self.signed(a, path=path)[0]).status_code, 503)
        good_b = self.request("GET", path, self.signed(b, path=path)[0])
        self.assertEqual(good_b.status_code, 200, good_b.text)
        self.assertEqual(self.list(b).status_code, 200)
        print("API_F3_APP_ONLY_SIGNED_PG_READY_200_BAD_REVOKED_503_PASS", flush=True)

    def test_API011_07_signed_ready_real_pg_privilege_failure_and_recovery(self):
        """Isolated PG17: deny required admission function, observe real 503,
        restore only the temporary CI grant, observe fresh signed 200.
        No migrations, owner rows or production roles are modified.
        """
        a = self.login("A")
        path = "/health/ready"
        good = self.request("GET", path, self.signed(a, path=path)[0])
        self.assertEqual(good.status_code, 200, good.text)
        signature = "auth_l1.admit_session_fenced(text,text,bigint,integer)"
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True) as admin:
            admin.execute("REVOKE EXECUTE ON FUNCTION " + signature +
                          " FROM history_app")
            try:
                with psycopg.connect(os.environ["DB_APP_DSN"],
                                    autocommit=True, row_factory=dict_row) as role:
                    allowed = role.execute(
                        "SELECT has_function_privilege(current_user,%s,'EXECUTE') AS ok",
                        (signature,)
                    ).fetchone()["ok"]
                    self.assertFalse(allowed)
                denied = self.request("GET", path, self.signed(a, path=path)[0])
                self.assertEqual(denied.status_code, 503, denied.text)
                self.assertEqual(denied.headers.get("cache-control"), "no-store")
                self.assertNotIn("password=", denied.text.lower())
            finally:
                # CI lab cleanup is mandatory even if an assertion fails.
                admin.execute("GRANT EXECUTE ON FUNCTION " + signature +
                              " TO history_app")
        recovered = self.request("GET", path, self.signed(a, path=path)[0])
        self.assertEqual(recovered.status_code, 200, recovered.text)
        print("API_F3_APP_ONLY_REAL_PG_GRANT_DOWN_503_RESTORED_200_PASS",
              flush=True)

    def test_API011_08_signed_real_pg_pagination_A_B_cursor_and_detail(self):
        """Real 004/005 session and PG rows, page-2 cursor, foreign masking.

        A cursor signed for owner A cannot disclose A's second page to B.
        Refresh is read-only; no send/engine is allowed in this mode.
        """
        a, b = self.login("A"), self.login("B")
        prefix = "CI_PAGE_" + uuid.uuid4().hex[:12]
        ids = [self.seed(a, prefix + "_" + str(i)) for i in range(4)]
        b_id = self.seed(b, prefix + "_B")
        self.assertTrue(all(ids))
        original, cursor, pages, seen = [], None, 0, set()
        while pages < 25:
            query = "?limit=2" + ("&cursor=" + cursor if cursor else "")
            page = self.list(a, query=query)
            self.assertEqual(page.status_code, 200, page.text)
            doc = page.json()
            self.assertEqual(doc["kind"], "conversation_page")
            self.assertEqual(doc["scope_user_id"], a["owner_id"])
            self.assertEqual(doc["page"]["limit"], 2)
            items = doc["items"]
            self.assertLessEqual(len(items), 2)
            for item in items:
                self.assertEqual(item["owner_user_id"], a["owner_id"])
                self.assertNotIn(item["conversation_id"], seen)
                self.assertNotEqual(item["conversation_id"], b_id)
                seen.add(item["conversation_id"])
                if pages == 0:
                    original.append(item["conversation_id"])
            next_cursor = doc["page"]["next_cursor"]
            self.assertEqual(bool(next_cursor), doc["page"]["has_more"])
            if pages == 0:
                self.assertTrue(next_cursor, "Expected a real PG second page")
                foreign = self.list(b, query="?limit=2&cursor=" + next_cursor)
                self.assertEqual(foreign.status_code, 404, foreign.text)
            pages += 1
            if next_cursor is None:
                break
            cursor = next_cursor
        self.assertLess(pages, 25, "Possible pagination loop")
        self.assertTrue(set(ids).issubset(seen))
        refreshed = self.list(a, query="?limit=2")
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertEqual(
            original,
            [x["conversation_id"] for x in refreshed.json()["items"]])
        detail_path = "/v1/conversations/" + ids[0] + "/messages"
        detail_query = "?limit=2"
        token_a, _ = self.signed(
            a, path=detail_path, query=b"limit=2")
        owner_result = self.request(
            "GET", detail_path, token_a, query=detail_query)
        self.assertEqual(owner_result.status_code, 200, owner_result.text)
        self.assertEqual(owner_result.json()["owner_user_id"], a["owner_id"])
        token_b, _ = self.signed(
            b, path=detail_path, query=b"limit=2")
        blocked = self.request("GET", detail_path, token_b, query=detail_query)
        self.assertEqual(blocked.status_code, 404, blocked.text)
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            rows = admin.execute(
                "SELECT id, owner_id FROM history_l1.conversations "
                "WHERE id = ANY(%s)",
                (ids + [b_id],)
            ).fetchall()
        self.assertEqual({r["id"] for r in rows}, set(ids + [b_id]))
        self.assertEqual(
            {r["id"]: r["owner_id"] for r in rows},
            {**{i: a["owner_id"] for i in ids}, b_id: b["owner_id"]})
        print("API_F3_REAL_SIGNED_PG_CURSOR_PAGINATION_AB_DETAIL_PASS",
              flush=True)

    def test_API011_09_replay_persists_after_real_api_process_restart(self):
        """Real HTTPS mTLS, key ID, committed PG replay and History after API restart.

        Fresh GETs must preserve exact owner/rows; reusing a previously
        consumed, still-unexpired assertion must be denied *across workers*.
        This does not claim Send idempotency or provider exactly-once.
        """
        from concurrent.futures import ThreadPoolExecutor
        a, b = self.login("A"), self.login("B")
        cid = self.seed(a, "CI_PERSISTENT_RESTART_" + uuid.uuid4().hex)
        self.seed(b, "CI_RESTART_DISTINCT_B_" + uuid.uuid4().hex)
        fresh, claims = self.signed(a, path=LIST)
        first = self.list(a, token=fresh)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertIn(cid, [x["conversation_id"] for x in first.json()["items"]])
        self.assertEqual(self.list(a, token=fresh).status_code, 401)

        # Independent signed GETs exercise transactional admission without
        # creating a new T1/T2 or accepting a browser-chosen owner.
        def get_fresh(_):
            token, _ = self.signed(a, path=LIST, query=b"limit=20")
            return self.request("GET", LIST, token, query="?limit=20")
        with ThreadPoolExecutor(max_workers=4) as pool:
            replies = list(pool.map(get_fresh, range(6)))
        for reply in replies:
            self.assertEqual(reply.status_code, 200, reply.text)
            self.assertIn(cid, [x["conversation_id"]
                                for x in reply.json()["items"]])
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            def counts():
                return admin.execute(
                    "SELECT "
                    "(SELECT count(*) FROM history_l1.send_receipts "
                    " WHERE owner_id=%s) AS t1,"
                    "(SELECT count(*) FROM history_l1.execution_attempts "
                    " WHERE owner_id=%s) AS t2,"
                    "(SELECT count(*) FROM history_l1.answers "
                    " WHERE owner_id=%s) AS t3",
                    (a["owner_id"], a["owner_id"], a["owner_id"])
                ).fetchone()
            before = counts()

            # Stop the very process serving HTTPS H11: this is NOT
            # an in-process TestClient or a Python mock of restart.
            old_worker = self.__class__.children[0]
            old_worker.terminate()
            old_worker.wait(timeout=6)
            self.__class__.children.pop(0)
            fresh_worker = subprocess.Popen(
                self.__class__.api_worker_command,
                cwd=ROOT, env=self.__class__.api_worker_env,
                stdout=subprocess.DEVNULL,
                stderr=self.__class__.api_worker_log_file,
            )
            self.__class__.children.insert(0, fresh_worker)
            for _ in range(90):
                if fresh_worker.poll() is not None:
                    raise AssertionError("RESTARTED_SIGNED_API_EARLY_EXIT")
                try:
                    probe = self.request("GET", LIST)
                    if probe.status_code == 401:
                        break
                except (httpx.ConnectError, httpx.ReadError,
                        httpx.RemoteProtocolError):
                    pass
                time.sleep(0.05)
            else:
                raise AssertionError("RESTARTED_SIGNED_API_NOT_READY")
            self.assertLess(int(time.time()), claims["exp"],
                            "Replay proof expired during process restart")
            # Single-use RSA proof MUST remain consumed after process restart.
            self.assertEqual(self.list(a, token=fresh).status_code, 401)
            after = self.list(a)
            self.assertEqual(after.status_code, 200, after.text)
            self.assertIn(cid, [x["conversation_id"]
                                for x in after.json()["items"]])
            self.assertEqual(after.json()["scope_user_id"], a["owner_id"])
            self.assertEqual(self.list(b).status_code, 200)
            self.assertEqual(counts(), before)
        print("API_F3_REAL_PG_REPLAY_H11_PROCESS_RESTART_AB_STABLE_PASS",
              flush=True)

    def test_API011_99_pinned_https_callback_real_keycloak_and_redirect_denies(self):
        """Actual verified HTTPS callback, same pinned redirect for Code exchange."""
        from cryptography.hazmat.primitives import serialization
        from src.phase3.auth.bootstrap_oidc import BootstrapOIDC, BootstrapDenied
        keycloak = self.base.keycloak
        # The original HTTP callback is no longer used after earlier tests.
        keycloak.callback.stop()
        callback = CallbackHarness()
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.temp/"server.pem"),str(self.temp/"server.key"))
        callback.server.socket=tls.wrap_socket(callback.server.socket,server_side=True)
        callback.url=("https://127.0.0.1:"+
                      str(callback.server.server_address[1])+"/callback")
        callback.start()
        self.__class__.hcb = callback
        keycloak.callback = callback
        # Test-only Keycloak admin updates EXACT configured client redirect.
        with httpx.Client(trust_env=False, timeout=20) as c:
            token = c.post(keycloak.base+"/realms/master/protocol/openid-connect/token",
                           data={"grant_type":"password","client_id":"admin-cli",
                                 "username":"ci-bootstrap","password":keycloak.password})
            self.assertEqual(token.status_code, 200)
            hdr={"Authorization":"Bearer "+token.json()["access_token"]}
            endpoint=keycloak.base+"/admin/realms/"+keycloak.REALM+"/clients"
            clients=c.get(endpoint,headers=hdr,
                          params={"clientId":keycloak.CLIENT_ID})
            self.assertEqual(clients.status_code,200)
            self.assertEqual(len(clients.json()),1)
            client=clients.json()[0]
            client["redirectUris"]=[callback.url]
            resp=c.put(endpoint+"/"+client["id"],headers=hdr,json=client)
            self.assertEqual(resp.status_code,204)
        # New independent TLS API worker uses pinned HTTPS callback URL.
        template=json.loads((self.temp/"worker_b.json").read_text())
        newport=port()
        template.update(port=newport,worker_id="https",
                        redirect_uri=callback.url)
        path=self.temp/"worker_https.json"
        path.write_text(json.dumps(template));path.chmod(0o600)
        proc=subprocess.Popen(
            [sys.executable,"-u",str(Path(pinned.__file__).with_name(
                "bootstrap_010_worker.py")),str(path)],cwd=ROOT,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.children.append(proc)
        apiurl="https://127.0.0.1:"+str(newport)
        worker=pinned.BFFFixture(apiurl,self.fixture.cert,self.fixture.key,
                                 self.fixture.ca,str(self.temp/"alias.sqlite"),
                                 self.base.alias_key)
        worker.signer=self.fixture.signer
        with httpx.Client(verify=self.tls,trust_env=False,timeout=2) as c:
            for _ in range(70):
                if proc.poll() is not None:raise AssertionError("HTTPS_WORKER_EXIT")
                try:
                    if c.get(apiurl+"/__fixture_health").status_code==200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.1)
            else:raise AssertionError("HTTPS_WORKER_UNAVAILABLE")
        identifiers={
            "attempt_id":str(uuid.uuid4()),
            "initiator_sha256":sha256(secrets.token_bytes(32)).hexdigest(),
            "bff_attempt_id":str(uuid.uuid4()),
            "start_key":secrets.token_urlsafe(22),
        }
        result, start=worker.post("start",identifiers)
        self.assertEqual(result,201)
        parsed=urlsplit(start["authorize_url"])
        self.assertEqual(parse_qs(parsed.query)["redirect_uri"],[callback.url])
        # URI is not an accepted browser/BFF field on START or COMPLETE.
        self.assertEqual(worker.post("start",{**identifiers,
            "redirect_uri":"https://evil.example/callback"})[0],422)
        # Change only the IdP authorization query: unregistered redirect
        # cannot mint a Code, preserving server-pinned challenge.
        from urllib.parse import urlencode
        query=parse_qs(parsed.query)
        query["redirect_uri"]=["https://127.0.0.1:1/callback"]
        with httpx.Client(trust_env=False,timeout=8,follow_redirects=False) as c:
            invalid=c.get(keycloak.oidc["authorization_endpoint"],
                          params={k:v[0] for k,v in query.items()})
            self.assertIn(invalid.status_code,(400,403))
        # Genuine IdP login followed by a CA-verified TLS callback GET.
        with httpx.Client(verify=self.fixture.ca,trust_env=False,
                          timeout=20,follow_redirects=False) as browser:
            response=keycloak.same_origin_local_request(
                browser,"GET",keycloak.oidc["authorization_endpoint"],
                params={k:v[0] for k,v in parse_qs(parsed.query).items()})
            submitted=False
            captured=None
            for _ in range(24):
                if response.status_code in (301,302,303,307,308):
                    dest=urljoin(str(response.url),response.headers.get("location",""))
                    if dest.startswith(callback.url+"?"):
                        received=browser.get(dest)
                        self.assertEqual(received.status_code,200)
                        captured=callback.next()
                        break
                    if not dest.startswith(keycloak.base+"/realms/"+keycloak.REALM+"/"):
                        raise IsolatedOIDCFailure()
                    response=keycloak.same_origin_local_request(browser,"GET",dest)
                elif response.status_code==200 and not submitted:
                    form=LoginForm();form.feed(response.text)
                    if not form.action:raise IsolatedOIDCFailure()
                    data=dict(form.hidden)
                    data.update(username=keycloak.accounts["A"]["email"],
                                password=keycloak.accounts["A"]["password"])
                    submitted=True
                    response=keycloak.same_origin_local_request(
                        browser,"POST",urljoin(str(response.url),form.action),
                        data=data)
                else:
                    raise IsolatedOIDCFailure()
        self.assertIsNotNone(captured)
        payload={"attempt_id":identifiers["attempt_id"],
                 "initiator_sha256":identifiers["initiator_sha256"],
                 "bff_attempt_id":identifiers["bff_attempt_id"],
                 "state":captured["state"][0],"code":captured["code"][0]}
        status,pending=worker.post("complete",payload)
        self.assertEqual(status,201,{"status":status})
        # This verifies same configured HTTPS redirect used by token exchange.
        alias=worker.create_alias(pending)
        ack={k:identifiers[k] for k in ("attempt_id","initiator_sha256")}
        ack.update(receipt_id=pending["receipt_id"],owner_id=pending["owner_id"],
                   epoch=pending["epoch"],alias_sha256=alias)
        self.assertEqual(worker.post("ack",ack)[0],200)
        print("API011_PINNED_CA_VERIFIED_HTTPS_CALLBACK_CODE_ACK_PASS",flush=True)
