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
                "r.resolved_conversation_id, r.user_message_id, m.body AS text "
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
        self.seed(a, "CI_RESTART_PAGE2_" + uuid.uuid4().hex)
        self.seed(a, "CI_RESTART_PAGE3_" + uuid.uuid4().hex)
        self.seed(b, "CI_RESTART_DISTINCT_B_" + uuid.uuid4().hex)
        before_page = self.list(a, query="?limit=1")
        self.assertEqual(before_page.status_code, 200, before_page.text)
        before_first = before_page.json()["items"][0]["conversation_id"]
        cursor = before_page.json()["page"]["next_cursor"]
        self.assertIsNotNone(cursor)
        cursor_query = "?limit=1&cursor=" + cursor
        before_page2 = self.list(a, query=cursor_query)
        self.assertEqual(before_page2.status_code, 200, before_page2.text)
        before_second = before_page2.json()["items"][0]["conversation_id"]
        self.assertNotEqual(before_first, before_second)
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
            page1_after = self.list(a, query="?limit=1")
            page2_after = self.list(a, query=cursor_query)
            self.assertEqual(page1_after.status_code, 200, page1_after.text)
            self.assertEqual(page2_after.status_code, 200, page2_after.text)
            self.assertEqual(page1_after.json()["items"][0]["conversation_id"],
                             before_first)
            self.assertEqual(page2_after.json()["items"][0]["conversation_id"],
                             before_second)
            self.assertEqual(page2_after.json()["scope_user_id"], a["owner_id"])
            # Cursor issued before a real Uvicorn restart remains bound to A.
            self.assertEqual(self.list(b, query=cursor_query).status_code, 404)
            self.assertEqual(self.list(b).status_code, 200)
            self.assertEqual(counts(), before)
        print("API_F3_REAL_PG_REPLAY_H11_PROCESS_RESTART_AB_STABLE_PASS",
              flush=True)

    def test_API011_10_unknown_cancel_status_is_durable_and_never_retried(self):
        """Real PG17 + BFF RS256 mTLS: UNKNOWN and CANCELLED keep original T2.

        APP_ONLY sends no new message; this validates *pre-existing*
        synthetic T1/T2 state read over original Product.v1 signed History,
        not engine/provider completion or a new Send endpoint.
        """
        from repository import mark_attempt
        from urllib.parse import urlencode
        a, b = self.login("A"), self.login("B")
        cid = self.seed(a, "CI_UNKNOWN_CANCELLATION_" + uuid.uuid4().hex)
        sent = {
            "kind": "send_message_request",
            "contract_version": "product.v1",
            "requested_conversation_id": cid,
            "client_message_id": history_api.uid(),
            "idempotency_key": "ciunknown_" + uuid.uuid4().hex,
            "question": "CI_T2_PREVIOUSLY_COMMITTED_NOT_FOR_MODEL",
        }
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as conn:
            t1 = history_api.send_t1(
                conn, a["owner_id"], sent, history_api.uid(), history_api.uid())
            t2 = start_t2(
                conn, a["owner_id"], cid, sent["client_message_id"],
                sent["idempotency_key"], history_api.uid(), history_api.uid())
            # Real crash/timeout ambiguity is represented by the repository
            # state only; never reinterpret UNKNOWN as permission to Send.
            mark_attempt(conn, a["owner_id"], t2["id"], "attempt_unknown")
        path = "/v1/message-requests/status"
        q = "?" + urlencode({
            "requested_conversation_id": cid,
            "client_message_id": sent["client_message_id"],
            "idempotency_key": sent["idempotency_key"],
        })
        def read(actor, query=q):
            token, _ = self.signed(
                actor, path=path, query=query.removeprefix("?").encode("ascii"))
            return self.request("GET", path, token, query=query)
        for expected in ("attempt_unknown", "cancelled"):
            for _ in range(3):
                reply = read(a)
                self.assertEqual(reply.status_code, 200, reply.text)
                doc = reply.json()
                self.assertEqual(doc["status"], expected)
                self.assertEqual(doc["attempt_id"], t2["id"])
                self.assertEqual(doc["message_id"], t1["message_id"])
                self.assertEqual(doc["owner_user_id"], a["owner_id"])
                self.assertIsNone(doc["answer"])
                self.assertIsNone(doc["answer_id"])
            denied = read(b)
            self.assertEqual(denied.status_code, 404, denied.text)
            wrong = read(a, query=q.replace(
                sent["idempotency_key"],
                "ciunknown_nonexistent_" + uuid.uuid4().hex))
            self.assertEqual(wrong.status_code, 404, wrong.text)
            with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                                 row_factory=dict_row) as conn:
                same = start_t2(
                    conn, a["owner_id"], cid, sent["client_message_id"],
                    sent["idempotency_key"], history_api.uid(), history_api.uid())
                self.assertEqual(same["id"], t2["id"])
                if expected == "attempt_unknown":
                    mark_attempt(conn, a["owner_id"], t2["id"], "cancelled")
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            actual = admin.execute(
                "SELECT e.id,e.state,count(ans.id) AS answers "
                "FROM history_l1.execution_attempts AS e "
                "LEFT JOIN history_l1.answers AS ans "
                "ON ans.owner_id=e.owner_id AND ans.attempt_id=e.id "
                "WHERE e.owner_id=%s AND e.id=%s "
                "GROUP BY e.id,e.state",
                (a["owner_id"], t2["id"])
            ).fetchone()
            self.assertIsNotNone(actual)
            self.assertEqual(actual["id"], t2["id"])
            self.assertEqual(actual["state"], "cancelled")
            self.assertEqual(actual["answers"], 0)
            attempts = admin.execute(
                "SELECT count(*) AS n FROM history_l1.execution_attempts "
                "WHERE owner_id=%s AND send_receipt_id IN "
                "(SELECT id FROM history_l1.send_receipts "
                "WHERE owner_id=%s AND client_message_id=%s)",
                (a["owner_id"], a["owner_id"], sent["client_message_id"])
            ).fetchone()["n"]
            self.assertEqual(attempts, 1)
        print("API_F3_REAL_SIGNED_PG_UNKNOWN_CANCELLED_ONE_T2_NO_T3_PASS",
              flush=True)

    def test_API011_11_real_isolated_pg_container_loss_readiness_503_recovery(self):
        """Actual PG network outage, no mocks: exact CI-owned service only.

        This test may stop ONLY the GitHub Actions postgres:17.11 service
        bound to synthetic history_ci, never a user or Mac database.
        """
        import re
        cid = os.environ.get("API_F3_ISOLATED_PG_CID", "")
        if (os.environ.get("CI") != "true"
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or not re.fullmatch(r"[a-f0-9]{12,64}", cid)
                or "dbname=history_ci" not in os.environ.get("DB_APP_DSN", "")
                or os.environ.get("PGHOST") != "127.0.0.1"
                or os.environ.get("PGPORT") != "5432"):
            raise AssertionError("ISOLATED_PG_STOP_FENCE_DENIED")
        inspect = subprocess.run(
            ["docker", "inspect", "--format",
             "{{.Config.Image}} {{.State.Running}}", cid],
            capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(inspect.stdout.strip(), "postgres:17.11 true")
        a = self.login("A")
        cid_a = self.seed(a, "CI_REAL_PG_OUTAGE_" + uuid.uuid4().hex)
        self.assertEqual(self.list(a).status_code, 200)
        before_token, _ = self.signed(a, path="/health/ready")
        self.assertEqual(self.request(
            "GET", "/health/ready", before_token).status_code, 200)
        stopped = False
        try:
            subprocess.run(
                ["docker", "stop", "--time", "2", cid],
                capture_output=True, text=True, timeout=20, check=True)
            stopped = True
            # A valid, fresh RSA proof/owner cannot compensate for an
            # unreachable PG: the signed endpoint must fail closed.
            token, _ = self.signed(a, path="/health/ready")
            outage = self.request("GET", "/health/ready", token)
            self.assertEqual(outage.status_code, 503, outage.text)
            self.assertEqual(outage.headers.get("cache-control"), "no-store")
            self.assertEqual(outage.json()["state"], "unavailable")
            self.assertNotIn("postgres", outage.text.lower())
            self.assertNotIn("password", outage.text.lower())
        finally:
            if stopped:
                subprocess.run(
                    ["docker", "start", cid],
                    capture_output=True, text=True, timeout=20, check=True)
        for _ in range(50):
            probe = subprocess.run(
                ["pg_isready", "-h", "127.0.0.1", "-p", "5432"],
                capture_output=True, timeout=3, check=False)
            if probe.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise AssertionError("ISOLATED_PG_DID_NOT_RECOVER")
        token, _ = self.signed(a, path="/health/ready")
        restored = self.request("GET", "/health/ready", token)
        self.assertEqual(restored.status_code, 200, restored.text)
        history = self.list(a)
        self.assertEqual(history.status_code, 200, history.text)
        self.assertIn(cid_a, [r["conversation_id"]
                              for r in history.json()["items"]])
        print("API_F3_ACTUAL_PG_CONTAINER_STOP_READY_503_RESTART_200_PASS",
              flush=True)

    def test_API011_12_parallel_same_assertion_one_durable_pg_replay(self):
        """Race six distinct mTLS HTTP sockets with one *identical* RS256 JTI.

        Only one may obtain a signed History result. The PostgreSQL replay
        primary key must contain exactly one digest, with no T1/T2/T3 write.
        This tests durable admission race, NOT client Send idempotency.
        """
        from concurrent.futures import ThreadPoolExecutor
        a = self.login("A")
        cid = self.seed(a, "CI_REPLAY_RACE_" + uuid.uuid4().hex)
        token, claims = self.signed(a)
        key = sha256((claims["iss"] + "\x00" + claims["jti"]).encode(
            "utf-8")).hexdigest()
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as auth_admin:
            self.assertEqual(auth_admin.execute(
                "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                "WHERE issuer_jti_sha256=%s", (key,)).fetchone()["n"], 0)
            with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                                 row_factory=dict_row) as db_admin:
                def counts():
                    return db_admin.execute(
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
                with ThreadPoolExecutor(max_workers=6) as pool:
                    result = list(pool.map(
                        lambda _: self.list(a, token=token), range(6)))
                successes = [r for r in result if r.status_code == 200]
                rejected = [r for r in result if r.status_code != 200]
                self.assertEqual(len(successes), 1,
                                 [(r.status_code, r.text[:180]) for r in result])
                self.assertEqual(len(rejected), 5)
                self.assertTrue(all(r.status_code in (401, 503)
                                    for r in rejected))
                for denied in rejected:
                    self.assertEqual(denied.headers.get("cache-control"),
                                     "no-store")
                    self.assertNotIn(cid, denied.text)
                    self.assertNotIn(claims["jti"], denied.text)
                got = successes[0].json()
                self.assertEqual(got["scope_user_id"], a["owner_id"])
                self.assertIn(cid, [x["conversation_id"]
                                    for x in got["items"]])
                self.assertEqual(auth_admin.execute(
                    "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                    "WHERE issuer_jti_sha256=%s", (key,)
                ).fetchone()["n"], 1)
                self.assertEqual(counts(), before)
                self.assertEqual(self.list(a, token=token).status_code, 401)
                self.assertEqual(self.list(a).status_code, 200)
        print("API_F3_REAL_SIGNED_PG_PARALLEL_REPLAY_ONLY_ONE_ADMISSION_PASS",
              flush=True)

    def test_API011_13_invalid_signed_bff_claims_never_consume_pg_replay(self):
        """Real mTLS HTTPS/RS256 negative issuer/expiry/path/method matrix.

        These INVALID claims must fail BEFORE the PG durable JTI insert.
        Same active A remains readable with a completely fresh signed token.
        """
        a = self.login("A")
        cid = self.seed(a, "CI_NEGATIVE_PROOF_" + uuid.uuid4().hex)
        now = int(time.time())
        negative = (
            {"aud": "urn:wrong-signed-history-audience"},
            {"iss": "urn:wrong-signed-history-issuer"},
            {"exp": now - 10},
            {"nbf": now + 60},
            {"method": "POST"},
            {"raw_path_sha256": sha256(b"/v1/conversations/fake").hexdigest()},
            {"raw_query_sha256": sha256(b"limit=7").hexdigest()},
            {"body_sha256": sha256(b"not-empty").hexdigest()},
            {"body_len": 3},
        )
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            for claims_changed in negative:
                token, proof = self.signed(a, override=claims_changed)
                rejected = self.list(a, token=token)
                self.assertEqual(rejected.status_code, 401,
                                 (claims_changed, rejected.text))
                self.assertEqual(rejected.headers.get("cache-control"),
                                 "no-store")
                self.assertNotIn(cid, rejected.text)
                key = sha256((proof["iss"] + "\x00" + proof["jti"]).encode(
                    "utf-8")).hexdigest()
                self.assertEqual(admin.execute(
                    "SELECT count(*) AS n "
                    "FROM auth_l1.service_assertion_replays "
                    "WHERE issuer_jti_sha256=%s",
                    (key,)).fetchone()["n"], 0)
        fresh = self.list(a)
        self.assertEqual(fresh.status_code, 200, fresh.text)
        self.assertIn(cid, [x["conversation_id"]
                            for x in fresh.json()["items"]])
        print("API_F3_REAL_HTTPS_INVALID_BFF_PROOF_DENIED_BEFORE_PG_REPLAY_PASS",
              flush=True)

    def test_API011_14_body_bearing_get_denied_before_durable_signed_replay(self):
        """Real mTLS/PG: an empty-body signature cannot authorize a nonempty GET."""
        a = self.login("A")
        cid = self.seed(a, "CI_GET_BODY_BINDING_" + uuid.uuid4().hex)
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            for path, denied_status in (
                (LIST, 401),
                ("/v1/conversations/" + cid + "/messages", 401),
                ("/health/ready", 503),
            ):
                with self.subTest(path=path):
                    token, claims = self.signed(a, path=path)
                    key = sha256((claims["iss"] + "\x00" + claims["jti"]).encode(
                        "utf-8")).hexdigest()
                    def count():
                        return admin.execute(
                            "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                            "WHERE issuer_jti_sha256=%s", (key,)).fetchone()["n"]
                    self.assertEqual(count(), 0)
                    denied = self.request("GET", path, token, body=b"{}")
                    self.assertEqual(denied.status_code, denied_status, denied.text)
                    self.assertEqual(denied.headers.get("cache-control"), "no-store")
                    self.assertNotIn(cid, denied.text)
                    self.assertEqual(count(), 0)
                    good = self.request("GET", path, token)
                    self.assertEqual(good.status_code, 200, good.text)
                    self.assertEqual(count(), 1)
            self.assertEqual(self.request(
                "GET", "/internal/ready", body=b"{}").status_code, 503)
        print("API_F3_REAL_SIGNED_GET_BODY_FENCE_BEFORE_PG_REPLAY_PASS", flush=True)

    def test_API011_15_signed_ready_requires_actual_history_read_privilege(self):
        """A live session/005 grant is insufficient if the History table is unreadable."""
        a = self.login("A")
        cid = self.seed(a, "CI_READY_PRIVATE_TITLE_" + uuid.uuid4().hex)
        path = "/health/ready"
        before = self.request("GET", path, self.signed(a, path=path)[0])
        self.assertEqual(before.status_code, 200, before.text)
        self.assertNotIn(cid, before.text)
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True) as admin:
            admin.execute("REVOKE SELECT ON history_l1.conversations FROM history_app")
            try:
                with psycopg.connect(os.environ["DB_APP_DSN"],
                                    autocommit=True, row_factory=dict_row) as role:
                    self.assertFalse(role.execute(
                        "SELECT has_table_privilege(current_user,"
                        "'history_l1.conversations','SELECT') AS ok"
                    ).fetchone()["ok"])
                token, claims = self.signed(a, path=path)
                denied = self.request("GET", path, token)
                self.assertEqual(denied.status_code, 503, denied.text)
                self.assertEqual(denied.headers.get("cache-control"), "no-store")
                self.assertNotIn(cid, denied.text)
                key = sha256((claims["iss"] + "\x00" + claims["jti"]).encode(
                    "utf-8")).hexdigest()
                with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                                     row_factory=dict_row) as auth_admin:
                    self.assertEqual(auth_admin.execute(
                        "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                        "WHERE issuer_jti_sha256=%s", (key,)).fetchone()["n"], 0)
                self.assertNotEqual(self.list(a).status_code, 200)
            finally:
                admin.execute("GRANT SELECT ON history_l1.conversations TO history_app")
        recovered = self.request("GET", path, self.signed(a, path=path)[0])
        self.assertEqual(recovered.status_code, 200, recovered.text)
        self.assertNotIn(cid, recovered.text)
        history = self.list(a)
        self.assertEqual(history.status_code, 200, history.text)
        self.assertIn(cid, [row["conversation_id"] for row in history.json()["items"]])
        print("API_F3_REAL_SIGNED_READY_HISTORY_GRANT_DOWN_503_RECOVERY_PASS", flush=True)

    def test_API011_16_real_pg_revocation_lock_does_not_stall_other_owner_or_send(self):
        """Real PG row lock + HTTPS: A waits for revoke; B still reads History."""
        from concurrent.futures import ThreadPoolExecutor
        a, b = self.login("A"), self.login("B")
        self.assertNotEqual(a["owner_id"], b["owner_id"])
        bid = self.seed(b, "CI_UNBLOCKED_HISTORY_" + uuid.uuid4().hex)
        body = json.dumps({"operation_id": str(uuid.uuid4())}).encode()
        with ThreadPoolExecutor(max_workers=2) as pool:
            with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                                 row_factory=dict_row) as holder:
                with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                                     row_factory=dict_row) as observer:
                    with holder.transaction():
                        locked = holder.execute(
                            "SELECT owner_id FROM auth_l1.owners "
                            "WHERE owner_id=%s FOR UPDATE", (a["owner_id"],)
                        ).fetchone()
                        self.assertEqual(locked["owner_id"], a["owner_id"])
                        blocker = holder.info.backend_pid
                        token = self.signed(a, "POST", REVOKE, body)[0]
                        pending = pool.submit(self.request, "POST", REVOKE,
                                              token, body=body)
                        deadline = time.monotonic() + 4
                        observed_lock = False
                        while time.monotonic() < deadline:
                            self.assertFalse(pending.done(), "Revoke did not wait")
                            observed_lock = observer.execute(
                                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE usename='auth_revoker' AND wait_event_type='Lock' "
                                "AND %s=ANY(pg_blocking_pids(pid))) AS blocked",
                                (blocker,)
                            ).fetchone()["blocked"]
                            if observed_lock:
                                break
                            time.sleep(0.05)
                        self.assertTrue(observed_lock, "No actual PG lock observed")
                        # Independent B must succeed before A's lock is released.
                        other = pool.submit(self.list, b).result(timeout=4)
                        self.assertEqual(other.status_code, 200, other.text)
                        self.assertIn(bid, [row["conversation_id"]
                                            for row in other.json()["items"]])
                        send_body = b"invalid-app-only-body"
                        signed_send = self.signed(
                            b, "POST", "/v1/messages", send_body)[0]
                        denied = pool.submit(
                            self.request, "POST", "/v1/messages", signed_send,
                            body=send_body).result(timeout=3)
                        self.assertEqual(denied.status_code, 503, denied.text)
                        self.assertIn("ENGINE_NOT_CONFIGURED", denied.text)
                        self.assertFalse(pending.done())
                    # The temporary blocker COMMITs here even on exceptions.
                    revoked = pending.result(timeout=10)
                    self.assertEqual(revoked.status_code, 200, revoked.text)
                    self.assertEqual(revoked.json()["state"], "REVOKED_COMMITTED")
        self.assertEqual(self.list(a).status_code, 401)
        self.assertEqual(self.list(b).status_code, 200)
        print("API_F3_REAL_PG_REVOKE_LOCK_OTHER_OWNER_HISTORY_AND_SEND_PASS", flush=True)

    def test_API011_17_rejected_revoke_body_leaves_assertion_unused(self):
        """Real signed HTTPS: invalid revoke input never consumes the durable JTI."""
        a, b = self.login("A"), self.login("B")
        op = str(uuid.uuid4())
        body = json.dumps({"operation_id": op}).encode()
        token, claims = self.signed(a, "POST", REVOKE, body)
        key = sha256((claims["iss"] + "\x00" + claims["jti"]).encode("utf-8")).hexdigest()
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            def count():
                return admin.execute(
                    "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                    "WHERE issuer_jti_sha256=%s", (key,)).fetchone()["n"]
            self.assertEqual(count(), 0)
            tls = ssl.create_default_context(cafile=self.fixture.ca)
            tls.load_cert_chain(self.fixture.cert, self.fixture.key)
            with httpx.Client(verify=tls, trust_env=False, timeout=12,
                              follow_redirects=False) as client:
                invalid = client.post(self.url + REVOKE, content=body, headers=[
                    ("Authorization", "BFF-Assertion " + token),
                    ("Content-Type", "application/json"),
                    ("Content-Type", "text/plain"),
                ])
            self.assertEqual(invalid.status_code, 422, invalid.text)
            self.assertEqual(invalid.headers.get("cache-control"), "no-store")
            self.assertEqual(count(), 0)
            invalid = self.request("POST", REVOKE, token, body=b"x" * 513)
            self.assertEqual(invalid.status_code, 413, invalid.text)
            self.assertEqual(invalid.headers.get("cache-control"), "no-store")
            self.assertEqual(count(), 0)
            duplicate_json = ('{"operation_id":"%s","operation_id":"%s"}' % (op, op)).encode()
            invalid = self.request("POST", REVOKE, token, body=duplicate_json)
            self.assertEqual(invalid.status_code, 422, invalid.text)
            self.assertEqual(count(), 0)
            # The exact same assertion is still usable for the original
            # correctly framed body. This revokes A in the real 003/005 TX.
            revoked = self.request("POST", REVOKE, token, body=body)
            self.assertEqual(revoked.status_code, 200, revoked.text)
            self.assertEqual(revoked.json(), {"state": "REVOKED_COMMITTED", "operation_id": op})
            self.assertEqual(count(), 1)
        self.assertEqual(self.list(a).status_code, 401)
        self.assertEqual(self.list(b).status_code, 200)
        print("API_F3_REVOKE_BAD_BODY_ZERO_REPLAY_THEN_VALID_COMMIT_PASS", flush=True)

    def test_API011_18_parallel_app_only_send_retries_never_write_or_consume_jti(self):
        """Test disabled Send retries; NOT successful write idempotency or T3."""
        from concurrent.futures import ThreadPoolExecutor
        a = self.login("A")
        body = b"not-json-app-only-retry"
        shared_token, shared = self.signed(a, "POST", "/v1/messages", body)
        fresh = [self.signed(a, "POST", "/v1/messages", body) for _ in range(4)]
        tokens = [shared_token] * 4 + [token for token, _ in fresh]
        claims = [shared] + [proof for _, proof in fresh]
        keys = [sha256((proof["iss"] + "\x00" + proof["jti"]).encode("utf-8")).hexdigest()
                for proof in claims]
        self.assertEqual(len(set(keys)), 5)
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                                 row_factory=dict_row) as auth:
                def counts():
                    return db.execute(
                        "SELECT "
                        "(SELECT count(*) FROM history_l1.send_receipts WHERE owner_id=%s) AS t1,"
                        "(SELECT count(*) FROM history_l1.execution_attempts WHERE owner_id=%s) AS t2,"
                        "(SELECT count(*) FROM history_l1.answers WHERE owner_id=%s) AS t3",
                        (a["owner_id"], a["owner_id"], a["owner_id"])).fetchone()
                def replay_count():
                    return auth.execute(
                        "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                        "WHERE issuer_jti_sha256=ANY(%s)", (keys,)).fetchone()["n"]
                before = counts()
                self.assertEqual(replay_count(), 0)
                with ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(pool.map(lambda token: self.request(
                        "POST", "/v1/messages", token, body=body), tokens))
                for response in responses:
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertIn("ENGINE_NOT_CONFIGURED", response.text)
                    self.assertEqual(response.headers.get("cache-control"), "no-store")
                    self.assertNotIn(body.decode(), response.text)
                self.assertEqual(counts(), before)
                self.assertEqual(replay_count(), 0)
        self.assertEqual(self.list(a).status_code, 200)
        print("API_F3_APP_ONLY_PARALLEL_SEND_RETRIES_ZERO_T1_T2_T3_REPLAY_PASS", flush=True)

    def test_API011_19_actual_web_bff_signer_to_real_pg_history_revoke(self):
        """Use the real Web TypeScript signer, not the Python signing helper.

        CI-only OIDC sessions and disposable PG; no Next browser or cookie
        proof, no private-staging deployment, no Send or engine.
        """
        a, b = self.login("A"), self.login("B")
        ids = [self.seed(a, "CI_BFF_A_" + uuid.uuid4().hex) for _ in range(3)]
        bid = self.seed(b, "CI_BFF_B_" + uuid.uuid4().hex)
        signer_path = self.temp / ("bff_signer_" + uuid.uuid4().hex + ".pem")
        key_bytes = self.fixture.signer.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption())
        fd = os.open(signer_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as keyfile:
                keyfile.write(key_bytes)
            env = dict(os.environ)
            for name in ("AUTH_RUNTIME_PROFILE", "AUTH_CI_PRODUCT_CHAT_MODE"):
                env.pop(name, None)
            env.update(
                AUTH_CI_DEMO_MODE="true",
                AUTH_CI_PRODUCT_ORIGIN=self.url,
                AUTH_CI_PRODUCT_SIGN_KEY=str(signer_path),
                AUTH_CI_BOOTSTRAP_CA=str(self.fixture.ca),
                AUTH_CI_BOOTSTRAP_CERT=str(self.fixture.cert),
                AUTH_CI_BOOTSTRAP_KEY=str(self.fixture.key),
                AUTH_CI_PRODUCT_ISSUER=ISSUER,
                AUTH_CI_PRODUCT_AUDIENCE=AUDIENCE,
                AUTH_CI_PRODUCT_KID=KID,
            )
            script = """
import {readFileSync} from 'node:fs';
import {productRequest} from './apps/web/src/auth/server/product-session.ts';
const {operation, active, query, operationId} = JSON.parse(readFileSync(0, 'utf8'));
try {
    const result = await productRequest(operation, active, query, operationId);
    process.stdout.write(JSON.stringify(result));
} catch {
    process.exitCode = 1;
}
"""
            def call(pending, operation, query="", operation_id=""):
                # Synthetic trusted session values from the real CI OIDC ACK.
                # Pass through stdin, never CLI args, stdout logs, or repo.
                payload = {"operation": operation, "query": query,
                           "operationId": operation_id,
                           "active": {"ownerId": pending["owner_id"],
                                      "epoch": pending["epoch"],
                                      "generation": pending["generation"],
                                      "sessionVerifier": pending["session_verifier"]}}
                proc = subprocess.run(
                    ["node", "--experimental-strip-types", "--input-type=module",
                     "-e", script],
                    input=json.dumps(payload), text=True, capture_output=True,
                    cwd=ROOT, env=env, timeout=18)
                self.assertEqual(proc.returncode, 0, "ACTUAL_BFF_SIGNER_FAILED")
                response = json.loads(proc.stdout)
                return response["status"], json.loads(response["body"])

            status, first = call(a, "history", "?limit=1")
            self.assertEqual(status, 200)
            self.assertEqual(first["scope_user_id"], a["owner_id"])
            self.assertEqual(len(first["items"]), 1)
            aid = first["items"][0]["conversation_id"]
            self.assertIn(aid, ids)
            cursor = first["page"]["next_cursor"]
            self.assertTrue(cursor)
            status, second = call(a, "history", "?limit=1&cursor=" + cursor)
            self.assertEqual(status, 200)
            self.assertEqual(second["scope_user_id"], a["owner_id"])
            self.assertEqual(len(second["items"]), 1)
            sid = second["items"][0]["conversation_id"]
            self.assertIn(sid, ids)
            self.assertNotEqual(sid, aid)
            status, detail = call(a, "messages", "?limit=2", aid)
            self.assertEqual(status, 200)
            self.assertEqual(detail["conversation_id"], aid)
            self.assertEqual(detail["owner_user_id"], a["owner_id"])
            self.assertEqual(call(b, "messages", "?limit=2", aid)[0], 404)
            self.assertEqual(call(b, "history", "?limit=1&cursor=" + cursor)[0], 404)
            status, refreshed = call(a, "history", "?limit=1")
            self.assertEqual(status, 200)
            self.assertEqual(refreshed["items"][0]["conversation_id"], aid)
            status, other = call(b, "history", "?limit=1")
            self.assertEqual(status, 200)
            self.assertEqual(other["items"][0]["conversation_id"], bid)
            with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                                 row_factory=dict_row) as admin:
                rows = admin.execute(
                    "SELECT id, owner_id FROM history_l1.conversations "
                    "WHERE id = ANY(%s)", ([aid, sid, bid],)
                ).fetchall()
            self.assertEqual({r["id"]: r["owner_id"] for r in rows},
                             {aid: a["owner_id"], sid: a["owner_id"], bid: b["owner_id"]})
            op = str(uuid.uuid4())
            status, receipt = call(a, "revoke", operation_id=op)
            self.assertEqual(status, 200)
            self.assertEqual(receipt, {"state": "REVOKED_COMMITTED", "operation_id": op})
            self.assertEqual(call(a, "history", "?limit=1")[0], 401)
            self.assertEqual(call(b, "history", "?limit=1")[0], 200)
        finally:
            signer_path.unlink(missing_ok=True)
        print("API_F3_ACTUAL_WEB_BFF_SIGNER_PG_AB_PAGINATION_REVOKE_PASS", flush=True)

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
