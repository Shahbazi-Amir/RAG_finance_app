"""Signed Product API requests over ASGI and real disposable PostgreSQL."""
import json
import os
import secrets
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Event
from unittest.mock import patch
from urllib.parse import urlencode

import jwt
import psycopg
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from apps.api import product_session_api as api
from src.phase3.auth.service_proof import BFFServiceVerifier
from src.phase3.storage.postgres import auth_session

ISSUER = "urn:rag-finance:synthetic-fixture"
AUDIENCE = "urn:rag-finance:api:fixture"
SEND = "/v1/messages"
STATUS = "/v1/message-requests/status"
REVOKE = "/internal/auth/session/v1/revoke-one"


class SignedFixtureTest(unittest.TestCase):
    def setUp(self):
        if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
            self.fail("Only run against a disposable CI-compatible database.")
        self.signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = self.signer.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        verifier = BFFServiceVerifier(issuer=ISSUER, audience=AUDIENCE,
                                      public_keys={"fixture": public})
        # Only key provisioning is replaced. Use real JWT validation, durable
        # replay, session fence, repository, migrations and PostgreSQL roles.
        self.enterContext(patch.object(api, "_config", return_value=verifier))
        self.client = self.enterContext(TestClient(api.app))
        self.a = self.issue_session()
        self.b = self.issue_session()

    def issue_session(self):
        def provision(role, key, action):
            dsn = os.environ[key]
            options = conninfo_to_dict(dsn)
            self.assertEqual(
                tuple(options.get(k) for k in ("host", "port", "dbname", "user")),
                ("127.0.0.1", "5432", "history_ci", role),
            )
            with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
                return action(conn)

        identity = provision("auth_mapper", "AUTH_MAP_DSN",
                             lambda c: auth_session.map_identity(
                                 c, "https://synthetic.invalid/fixture", secrets.token_hex(16)))
        return provision("auth_sessions", "AUTH_SESSION_DSN",
                         lambda c: auth_session.issue(c, identity["owner_id"], identity["epoch"],
                                                      idle_seconds=900, absolute_seconds=3600))

    def call(self, session, method, path, *, body=None, query="", signed_body=None,
             jti=None):
        raw = json.dumps(body, ensure_ascii=False).encode() if body is not None else b""
        bound = signed_body if signed_body is not None else raw
        now = int(time.time())
        claims = {
            "iss": ISSUER, "aud": AUDIENCE, "iat": now, "nbf": now, "exp": now + 25,
            "jti": jti if jti is not None else secrets.token_urlsafe(24),
            "method": method,
            "raw_path_sha256": sha256(path.encode()).hexdigest(),
            "raw_query_sha256": sha256(query.encode()).hexdigest(),
            "body_sha256": sha256(bound).hexdigest(), "body_len": len(bound),
            "session_ref": session.opaque, "owner_id": session.owner_id,
            "epoch": session.epoch, "generation": session.generation,
        }
        assertion = jwt.encode(claims, self.signer, algorithm="RS256",
                               headers={"typ": "JWT", "kid": "fixture"})
        return self.client.request(
            method, path + ("?" + query if query else ""), content=raw,
            headers={"Authorization": "BFF-Assertion " + assertion,
                     "Content-Type": "application/json"},
        )

    def message(self, conversation=None):
        return dict(kind="send_message_request", contract_version="product.v1",
                    requested_conversation_id=conversation, question="بودجه چیست؟",
                    client_message_id=secrets.token_hex(16),
                    idempotency_key=secrets.token_hex(16))

    def status(self, session, message):
        query = {key: message[key] for key in
                 ("requested_conversation_id", "client_message_id", "idempotency_key")
                 if message[key] is not None}
        return self.call(session, "GET", STATUS, query=urlencode(query))

    def revoke(self, session):
        response = self.call(session, "POST", REVOKE,
                             body={"operation_id": "82b99755-a92d-4ba6-9c32-42bb12f0fb0b"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "REVOKED_COMMITTED")

    def test_registered_answer_and_access_are_owner_scoped(self):
        message = self.message()
        with patch.object(api, "answer_from_fixture", wraps=api.answer_from_fixture) as engine:
            first = self.call(self.a, "POST", SEND, body=message)
            self.assertEqual(first.status_code, 202, first.text)
            duplicate = self.call(self.a, "POST", SEND, body=message)
            self.assertEqual(duplicate.status_code, 200, duplicate.text)
            self.assertEqual(duplicate.json()["message_id"], first.json()["message_id"])
            conflict = self.call(self.a, "POST", SEND, body={**message, "question": "پرسش دیگر"})
            self.assertEqual(conflict.status_code, 409, conflict.text)
            engine.assert_called_once_with(message["question"])

        status = self.status(self.a, message).json()
        self.assertEqual(status["status"], "answer_committed")
        answer = status["answer"]
        self.assertEqual(answer["provenance"]["origin"], "SYNTHETIC")
        self.assertIsNone(answer["provenance"]["rag_binding"]["release_id"])
        self.assertEqual(answer["citations"][0]["source"]["resolution_status"], "unresolved")
        conversation = first.json()["resolved_conversation_id"]
        path = f"/v1/conversations/{conversation}/messages"
        page = self.call(self.a, "GET", path)
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual([m["role"] for m in page.json()["items"]], ["user", "assistant"])
        self.assertEqual(page.json()["answers"], [answer])
        self.assertEqual(self.call(self.b, "GET", path).status_code, 404)
        self.assertEqual(self.status(self.b, message).status_code, 404)
        self.assertEqual(self.call(self.b, "POST", SEND,
                                   body=self.message(conversation)).status_code, 404)
        self.assertEqual(self.call(self.b, "POST", SEND, body=self.message()).status_code, 202)

        self.revoke(self.a)
        self.assertEqual(self.call(self.a, "GET", path).status_code, 401)
        self.assertEqual(self.call(self.a, "POST", SEND, body=self.message()).status_code, 401)
        self.assertEqual(self.call(self.b, "GET", "/v1/conversations").status_code, 200)

    def test_provider_failure_and_timeout_are_distinct_and_never_finalize(self):
        for error, http, code in (
            (OSError("internal-only"), 502, "PROVIDER_REQUEST_FAILED"),
            (TimeoutError("internal-only"), 504, "PROVIDER_TIMEOUT"),
        ):
            with self.subTest(code=code):
                message = self.message()
                with patch.object(api, "answer_from_fixture", side_effect=error) as engine:
                    response = self.call(self.a, "POST", SEND, body=message)
                    self.assertEqual(response.status_code, http, response.text)
                    self.assertEqual(response.json()["error"]["code"], code)
                    self.assertNotIn("internal-only", response.text)
                    self.assertEqual(self.call(self.a, "POST", SEND, body=message).status_code, 200)
                    engine.assert_called_once()
                status = self.status(self.a, message).json()
                self.assertEqual(status["status"], "failed")
                self.assertIsNone(status["answer"])
                self.assertEqual(status["attempt_request_id"], response.json()["request_id"])
                self.assertEqual(status["attempt_trace_id"], response.json()["trace_id"])
                path = f"/v1/conversations/{status['resolved_conversation_id']}/messages"
                page = self.call(self.a, "GET", path).json()
                self.assertEqual(page["answers"], [])
                self.assertEqual([m["role"] for m in page["items"]], ["user"])

    def test_revoke_and_duplicate_finish_while_fixture_waits(self):
        message = self.message()
        entered, release = Event(), Event()
        original = api.answer_from_fixture

        def delayed(question):
            entered.set()
            if not release.wait(10):
                raise TimeoutError()
            return original(question)

        with patch.object(api, "answer_from_fixture", side_effect=delayed) as engine:
            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(self.call, self.a, "POST", SEND, body=message)
                try:
                    self.assertTrue(entered.wait(5))
                    duplicate = self.call(self.a, "POST", SEND, body=message)
                    self.assertEqual(duplicate.status_code, 200, duplicate.text)
                    self.assertEqual(self.status(self.a, message).json()["status"], "attempt_pending")
                    self.revoke(self.a)
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=5).status_code, 401)
            engine.assert_called_once()
        # Reissue for the same synthetic owner to inspect persistent History.
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"], autocommit=True,
                             row_factory=dict_row) as conn:
            fresh = auth_session.issue(conn, self.a.owner_id, self.a.epoch,
                                       idle_seconds=900, absolute_seconds=3600)
        status = self.status(fresh, message).json()
        self.assertEqual(status["status"], "attempt_pending")
        self.assertIsNone(status["answer"])

    def test_valid_body_with_mismatched_signature_has_no_side_effect(self):
        message = self.message()
        with patch.object(api, "answer_from_fixture") as engine:
            response = self.call(self.a, "POST", SEND, body=message, signed_body=b"{}")
            self.assertEqual(response.status_code, 401, response.text)
            engine.assert_not_called()
        self.assertEqual(self.status(self.a, message).status_code, 404)


    def test_real_signed_rr_40001_maps_503_rolls_back_jti_then_revoked_401(self):
        """Real PG 17 RR conflict via independent committed revoke, not a fake SQL exception."""
        seed = self.call(self.a, "POST", SEND, body=self.message())
        self.assertEqual(seed.status_code, 202, seed.status_code)
        conversation = seed.json()["resolved_conversation_id"]
        private_path = f"/v1/conversations/{conversation}/messages"
        raced_jti = secrets.token_urlsafe(24)
        original_fence = api.auth_session.admit_session_fenced
        original_consume = api._REPLAY.consume
        witnessed = {"jti_committed_to_open_tx": 0, "revoke_committed": 0,
                     "real_sqlstates": []}

        def observe_real_005(conn, verified):
            self.assertEqual(verified.jti, raced_jti)
            self.assertEqual(conn.isolation_level, psycopg.IsolationLevel.REPEATABLE_READ)
            self.assertTrue(original_consume(conn, verified))
            self.assertEqual(conn.info.transaction_status,
                             psycopg.pq.TransactionStatus.INTRANS)
            witnessed["jti_committed_to_open_tx"] += 1
            return True

        def revoke_between_005_snapshot_and_004_lock(conn, ref, owner, epoch, generation):
            self.assertEqual(ref, self.a.opaque)
            self.assertEqual(owner, self.a.owner_id)
            self.assertEqual(epoch, self.a.epoch)
            self.assertEqual(generation, self.a.generation)
            self.assertEqual(witnessed["jti_committed_to_open_tx"], 1)
            # The independent physical auth_sessions connection actually commits
            # a real 003 revoke_one AFTER 005 fixed the reader's RR snapshot.
            # 004 then takes FOR SHARE of the modified PG row and raises 40001.
            with psycopg.connect(os.environ["AUTH_SESSION_DSN"], autocommit=True,
                                 row_factory=dict_row) as revoker:
                self.assertTrue(auth_session.revoke_one(
                    revoker, self.a.opaque, self.a.epoch))
            witnessed["revoke_committed"] += 1
            try:
                return original_fence(conn, ref, owner, epoch, generation)
            except psycopg.errors.SerializationFailure as exc:
                witnessed["real_sqlstates"].append(exc.sqlstate)
                raise

        with patch.object(api._REPLAY, "consume", side_effect=observe_real_005), \
             patch.object(api.auth_session, "admit_session_fenced",
                          side_effect=revoke_between_005_snapshot_and_004_lock):
            conflicted = self.call(
                self.a, "GET", private_path, jti=raced_jti)
        self.assertEqual(conflicted.status_code, 503, conflicted.status_code)
        payload = conflicted.json()
        self.assertEqual(payload["kind"], "error_response")
        self.assertEqual(payload["error"]["code"], "TEMPORARILY_UNAVAILABLE")
        self.assertEqual(payload["error"]["category"], "technical")
        self.assertEqual(payload["error"]["message"], "History unavailable.")
        self.assertTrue(conflicted.headers["Cache-Control"] == "no-store")
        self.assertFalse(set(payload).intersection({"items", "answers", "owner_user_id"}))
        self.assertNotIn(self.a.owner_id, conflicted.text)
        self.assertNotIn(self.a.opaque, conflicted.text)
        self.assertNotIn(raced_jti, conflicted.text)
        self.assertNotIn("40001", conflicted.text)
        self.assertNotIn("SerializationFailure", conflicted.text)
        self.assertNotIn(conversation, conflicted.text)
        self.assertEqual(witnessed["jti_committed_to_open_tx"], 1)
        self.assertEqual(witnessed["revoke_committed"], 1)
        self.assertEqual(witnessed["real_sqlstates"], ["40001"])
        issuer_jti_digest = sha256((ISSUER + "\x00" + raced_jti).encode()).hexdigest()
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as admin:
            row = admin.execute(
                "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
                "WHERE issuer_jti_sha256=%s", (issuer_jti_digest,)).fetchone()
        self.assertEqual(row["n"], 0, "failed outer TX must rollback 005 JTI")
        # A fresh, independently signed JWT for the REVOKED session is a
        # genuine 401, NOT a technical 503 or a replay rejection.
        revoked = self.call(self.a, "GET", private_path)
        self.assertEqual(revoked.status_code, 401, revoked.status_code)
        self.assertEqual(revoked.json()["error"]["code"], "AUTH_REQUIRED")
        # B remains authenticated and can read only its own data.
        b_seed = self.call(self.b, "POST", SEND, body=self.message())
        self.assertEqual(b_seed.status_code, 202, b_seed.status_code)
        b_page = self.call(self.b, "GET", "/v1/conversations")
        self.assertEqual(b_page.status_code, 200, b_page.status_code)
        self.assertEqual(b_page.json()["scope_user_id"], self.b.owner_id)
        self.assertNotIn(conversation, b_page.text)
        print("API52_REAL_SIGNED_RR_PG40001_HTTP503_JTI_ROLLBACK_REVOKED401", flush=True)

    def test_real_committed_005_jti_replay_stays_401_not_503(self):
        jti = secrets.token_urlsafe(24)
        first = self.call(self.b, "GET", "/v1/conversations", jti=jti)
        self.assertEqual(first.status_code, 200, first.status_code)
        # Freshly signed proof but identical durable issuer+JTI cannot pass 005.
        second = self.call(self.b, "GET", "/v1/conversations", jti=jti)
        self.assertEqual(second.status_code, 401, second.status_code)
        self.assertEqual(second.json()["error"]["code"], "AUTH_REQUIRED")
        print("API52_COMMITTED_005_JTI_REPLAY_AUTH401_PRESERVED", flush=True)
