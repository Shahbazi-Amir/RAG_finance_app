"""Real in-process HTTP / temporary PostgreSQL History L1 tests; synthetic only.

No external HTTP service, real Auth, provider, model, or production DB.
A lost response is simulated by discarding the completed in-process result;
it is NOT a network outage, process kill, or externally verified delivery loss.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src/phase3/storage/postgres"))
sys.path.insert(0, str(ROOT / "tests/phase3/contracts"))

from apps.api.history_api import app, get_trusted_actor
from repository import (VALIDATOR, check_wire, uid, start_t2, mark_attempt,
                        finalize_t3, scoped)
from history_semantics import (check_conversation_page, check_messages_page,
                               check_status_query, canonical_create_fingerprint,
                               check_create_receipt)
from repository import SCHEMA

FIXTURE_FILE = ROOT / "packages/contracts/fixtures/product.v1.cases.json"
FIXTURES = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))["cases"]


def synthetic_answer(attempt, receipt):
    ans = copy.deepcopy(next(c["document"] for c in FIXTURES
                             if c["case_id"] == "valid_confidence_calibrated_example"))
    ans.update(answer_id=attempt["reserved_answer_id"],
               conversation_id=receipt["resolved_conversation_id"],
               message_id=uid(), request_id=attempt["attempt_request_id"],
               trace_id=attempt["attempt_trace_id"])
    check_wire(ans, "answer")
    return ans


def new_owner():
    return "synthetic_api_" + uuid.uuid4().hex[:20]


def actor(owner):
    return {
        "kind": "trusted_actor_context", "contract_version": "product.v1",
        "owner_user_id": owner, "principal_source": "server_auth_context",
        "authenticated_at": datetime.now(timezone.utc).isoformat(),
        "request_id": uid(), "trace_id": uid(),
    }


def request_create(title="Synthetic first", client_id=None, key="create_key_123456"):
    return {
        "kind": "create_conversation_request", "contract_version": "product.v1",
        "client_conversation_id": client_id or uid(),
        "idempotency_key": key, "title": title,
    }


def request_send(cid=None, question="Synthetic question", client_id=None,
                 key="send_key_123456"):
    return {
        "kind": "send_message_request", "contract_version": "product.v1",
        "requested_conversation_id": cid, "client_message_id": client_id or uid(),
        "question": question, "idempotency_key": key,
    }


def status_params(req):
    return {
        "requested_conversation_id": req["requested_conversation_id"] or "",
        "client_message_id": req["client_message_id"],
        "idempotency_key": req["idempotency_key"],
    }


def make_testclient(owner=None):
    if owner is not None:
        app.dependency_overrides[get_trusted_actor] = lambda: actor(owner)
    else:
        app.dependency_overrides.clear()
    return TestClient(app, raise_server_exceptions=False)


def real_conn():
    return psycopg.connect(os.environ["API_HISTORY_DSN"], autocommit=True,
                           row_factory=dict_row)


class HttpPostgreSQLHistoryL1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getenv("CI") != "true" or
                "dbname=history_api_ci" not in os.getenv("API_HISTORY_DSN", "") or
                "host=127.0.0.1" not in os.getenv("API_HISTORY_DSN", "") or
                "user=history_app" not in os.getenv("API_HISTORY_DSN", "") or
                "dbname=history_api_ci" not in os.getenv("API_MIG_DSN", "") or
                "user=history_migrator" not in os.getenv("API_MIG_DSN", "")):
            raise RuntimeError("CI_ONLY: ephemeral loopback history_api_ci required")
        cls.migrator_dsn = os.environ["API_MIG_DSN"]

    def setUp(self):
        self.owner = new_owner()
        self.client = make_testclient(self.owner)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def check_response(self, response, kind, status=None):
        if status is not None:
            self.assertEqual(response.status_code, status, response.text)
        document = response.json()
        self.assertEqual(document["kind"], kind, response.text)
        VALIDATOR.validate(document)
        return document

    def create(self, title="Synthetic first"):
        payload = request_create(title=title)
        res = self.client.post("/v1/conversations", json=payload)
        return payload, self.check_response(res, "create_conversation_receipt", 201)

    def send(self, cid=None, question="Synthetic question"):
        payload = request_send(cid=cid, question=question)
        res = self.client.post("/v1/messages", json=payload)
        return payload, self.check_response(res, "send_message_receipt", 202)

    def seed_t2(self, request, state="attempt_pending"):
        with real_conn() as conn:
            t2 = start_t2(conn, self.owner, request["requested_conversation_id"],
                          request["client_message_id"], request["idempotency_key"],
                          uid(), uid())
            if state in ("failed", "cancelled", "attempt_unknown"):
                mark_attempt(conn, self.owner, t2["id"], state)
            return t2

    def test_01_default_denies_without_identity_and_no_owner_override_endpoint(self):
        app.dependency_overrides.clear()
        unauthorized = TestClient(app, raise_server_exceptions=False)
        for method, path, body in (
            ("post", "/v1/conversations", request_create()),
            ("get", "/v1/conversations", None),
            ("get", "/v1/conversations/any_id/messages", None),
            ("post", "/v1/messages", request_send()),
            ("get", "/v1/message-requests/status", None),
        ):
            with self.subTest(path=path):
                response = getattr(unauthorized, method)(path, json=body) if body else unauthorized.get(path)
                doc = self.check_response(response, "error_response", 401)
                self.assertEqual(doc["error"]["code"], "AUTH_REQUIRED")
        unauthorized.close()
        self.client = make_testclient(self.owner)
        forged = {**request_create(), "owner_user_id": self.owner}
        result = self.client.post("/v1/conversations", json=forged)
        self.assertEqual(self.check_response(result, "error_response", 422)["error"]["code"], "INVALID_REQUEST")
        for params in ({"owner_user_id": self.owner}, {"owner": self.owner},
                       {"actor": self.owner}):
            response = self.client.get("/v1/conversations", params=params)
            self.check_response(response, "error_response", 422)

    def test_02_create_replay_conflict_and_original_creation_snapshot(self):
        req, first = self.create()
        replay = self.client.post("/v1/conversations", json=req)
        replayed = self.check_response(replay, "create_conversation_receipt", 200)
        self.assertEqual(first["conversation"], replayed["conversation"])
        self.assertEqual(first["conversation"]["conversation_id"],
                         replayed["conversation"]["conversation_id"])
        self.assertNotEqual(first["request_id"], replayed["request_id"])
        self.assertNotEqual(first["trace_id"], replayed["trace_id"])
        self.assertEqual(first["payload_sha256"], canonical_create_fingerprint(req))
        actor_one = actor(self.owner)
        actor_one.update(request_id=first["request_id"], trace_id=first["trace_id"])
        self.assertEqual(check_create_receipt(req, first, actor_one), [])
        edited = {**req, "title": "Conflicting title"}
        resp = self.client.post("/v1/conversations", json=edited)
        self.assertEqual(self.check_response(resp, "error_response", 409)["error"]["code"],
                         "IDEMPOTENCY_CONFLICT")
        with real_conn() as conn:
            with conn.transaction():
                scoped(conn, self.owner)
                count = conn.execute("""SELECT count(*) AS n FROM history_l1.create_receipts
                    WHERE owner_id=%s AND client_conversation_id=%s""",
                    (self.owner, req["client_conversation_id"])).fetchone()["n"]
                self.assertEqual(count, 1)
        with psycopg.connect(self.migrator_dsn, autocommit=True) as mig:
            with mig.transaction():
                mig.execute("""UPDATE history_l1.conversations SET title=%s
                    WHERE owner_id=%s AND id=%s""",
                    ("Changed after create", self.owner, first["conversation"]["conversation_id"]))
        snap = self.client.post("/v1/conversations", json=req)
        self.assertEqual(self.check_response(snap, "create_conversation_receipt", 200)["conversation"]["title"],
                         req["title"])
        with psycopg.connect(self.migrator_dsn, autocommit=True) as mig:
            with mig.transaction():
                mig.execute("""UPDATE history_l1.conversations SET state='deletion_requested'
                    WHERE owner_id=%s AND id=%s""",
                    (self.owner, first["conversation"]["conversation_id"]))
        self.check_response(self.client.post("/v1/conversations", json=req), "error_response", 404)

    def test_03_send_null_replay_conflict_and_distinct_operation_namespaces(self):
        create, first = self.create()
        request, receipt = self.send()
        self.assertIsNone(receipt["requested_conversation_id"])
        self.assertTrue(receipt["resolved_conversation_id"])
        self.assertEqual(receipt["disposition"], "created")
        self.assertEqual(receipt["idempotency_scope"], "trusted_user+send_message+conversation")
        retry = self.check_response(self.client.post("/v1/messages", json=request),
                                    "send_message_receipt", 200)
        self.assertEqual(retry["requested_conversation_id"], None)
        self.assertEqual(retry["resolved_conversation_id"], receipt["resolved_conversation_id"])
        self.assertEqual(retry["message_id"], receipt["message_id"])
        self.assertNotEqual(retry["request_id"], receipt["request_id"])
        conflict = self.client.post("/v1/messages", json={**request, "question": "Other question"})
        self.check_response(conflict, "error_response", 409)
        with real_conn() as conn:
            with conn.transaction():
                scoped(conn, self.owner)
                n = conn.execute("""SELECT count(*) AS n FROM history_l1.send_receipts
                    WHERE owner_id=%s AND client_message_id=%s""",
                    (self.owner, request["client_message_id"])).fetchone()["n"]
                self.assertEqual(n, 1)
                n = conn.execute("""SELECT count(*) AS n FROM history_l1.execution_attempts
                    WHERE owner_id=%s""", (self.owner,)).fetchone()["n"]
                self.assertEqual(n, 0)
        self.assertNotEqual(first["conversation"]["conversation_id"],
                            receipt["resolved_conversation_id"])
        self.assertNotEqual(create["client_conversation_id"], request["client_message_id"])

    def test_04_simulated_response_discard_after_commit_then_replay(self):
        payload = request_send()
        # Deliberately DISCARD the completed in-process HTTP response.
        # Not a real socket disconnect, process crash or delivery failure.
        self.client.post("/v1/messages", json=payload)
        recovered = self.check_response(self.client.post("/v1/messages", json=payload),
                                        "send_message_receipt", 200)
        status = self.check_response(self.client.get("/v1/message-requests/status",
                                                     params=status_params(payload)),
                                     "message_request_status", 200)
        self.assertEqual(status["status"], "persisted")
        self.assertEqual(status["message_id"], recovered["message_id"])
        self.assertEqual(status["resolved_conversation_id"], recovered["resolved_conversation_id"])
        self.assertIsNone(status["attempt_id"])
        self.assertIsNone(status["answer"])
        self.assertNotEqual(status["request_id"], recovered["request_id"])

    def test_05_concurrent_send_null_and_create_are_single_write(self):
        create = request_create()
        send = request_send()
        def do_create(_):
            client = TestClient(app, raise_server_exceptions=False)
            return client.post("/v1/conversations", json=create)
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(do_create, range(6)))
        create_docs = [self.check_response(r, "create_conversation_receipt") for r in results]
        self.assertEqual({r.status_code for r in results}, {200, 201})
        self.assertEqual(len({doc["conversation"]["conversation_id"] for doc in create_docs}), 1)
        def do_send(_):
            client = TestClient(app, raise_server_exceptions=False)
            return client.post("/v1/messages", json=send)
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(do_send, range(8)))
        send_docs = [self.check_response(r, "send_message_receipt") for r in results]
        self.assertEqual({r.status_code for r in results}, {200, 202})
        self.assertEqual(len({d["message_id"] for d in send_docs}), 1)
        self.assertEqual(len({d["resolved_conversation_id"] for d in send_docs}), 1)
        with real_conn() as conn:
            with conn.transaction():
                scoped(conn, self.owner)
                self.assertEqual(conn.execute(
                    "SELECT count(*) AS n FROM history_l1.send_receipts WHERE owner_id=%s",
                    (self.owner,)).fetchone()["n"], 1)
                self.assertEqual(conn.execute(
                    "SELECT count(*) AS n FROM history_l1.execution_attempts WHERE owner_id=%s",
                    (self.owner,)).fetchone()["n"], 0)

    def test_06_status_states_with_internal_fixture_t2_t3_and_historical_trace(self):
        req, rec = self.send()
        pending = self.seed_t2(req)
        first = self.check_response(self.client.get("/v1/message-requests/status",
                      params=status_params(req)), "message_request_status", 200)
        self.assertEqual(first["status"], "attempt_pending")
        self.assertEqual(first["attempt_id"], pending["id"])
        self.assertEqual(first["attempt_trace_id"], pending["attempt_trace_id"])
        self.assertEqual(first["attempt_request_id"], pending["attempt_request_id"])
        second = self.check_response(self.client.get("/v1/message-requests/status",
                       params=status_params(req)), "message_request_status", 200)
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertNotEqual(first["trace_id"], second["trace_id"])
        self.assertEqual(first["attempt_trace_id"], second["attempt_trace_id"])
        actor_ctx = actor(self.owner)
        actor_ctx.update(request_id=second["request_id"], trace_id=second["trace_id"])
        query = {"kind": "message_request_status_query", "contract_version": "product.v1", **{
            "requested_conversation_id": req["requested_conversation_id"],
            "client_message_id": req["client_message_id"],
            "idempotency_key": req["idempotency_key"]}}
        self.assertEqual(check_status_query(query, second, actor_ctx), [])
        answer = synthetic_answer(pending, rec)
        with real_conn() as conn:
            finalized = finalize_t3(conn, self.owner, pending["id"], answer, "Synthetic assistant message")
        self.assertEqual(finalized["answer_id"], pending["reserved_answer_id"])
        done = self.check_response(self.client.get("/v1/message-requests/status",
                       params=status_params(req)), "message_request_status", 200)
        self.assertEqual(done["status"], "answer_committed")
        self.assertEqual(done["answer"], answer)
        self.assertEqual(done["attempt_trace_id"], pending["attempt_trace_id"])
        self.assertEqual(done["answer_id"], pending["reserved_answer_id"])
        self.assertNotEqual(done["answer"]["message_id"], done["message_id"])
        self.assertNotEqual(done["request_id"], first["request_id"])
        again = self.check_response(self.client.post("/v1/messages", json=req),
                                    "send_message_receipt", 200)
        self.assertEqual(again["message_id"], rec["message_id"])
        with real_conn() as conn:
            with conn.transaction():
                scoped(conn, self.owner)
                self.assertEqual(conn.execute(
                    "SELECT count(*) AS n FROM history_l1.execution_attempts WHERE owner_id=%s",
                    (self.owner,)).fetchone()["n"], 1)
                self.assertEqual(conn.execute(
                    "SELECT count(*) AS n FROM history_l1.answers WHERE owner_id=%s",
                    (self.owner,)).fetchone()["n"], 1)

    def test_07_unknown_failed_cancelled_are_read_only(self):
        for state in ("attempt_unknown", "failed", "cancelled"):
            req, rec = self.send(question="Synthetic " + state)
            att = self.seed_t2(req, state)
            status = self.check_response(self.client.get("/v1/message-requests/status",
                         params=status_params(req)), "message_request_status", 200)
            self.assertEqual(status["status"], state)
            self.assertEqual(status["attempt_id"], att["id"])
            self.assertIsNone(status["answer"])
            self.assertIsNone(status["answer_id"])
            self.check_response(self.client.post("/v1/messages", json=req),
                                "send_message_receipt", 200)
            recheck = self.check_response(self.client.get("/v1/message-requests/status",
                        params=status_params(req)), "message_request_status", 200)
            self.assertEqual(recheck["attempt_id"], att["id"])
            self.assertEqual(recheck["attempt_trace_id"], att["attempt_trace_id"])
        with real_conn() as conn:
            with conn.transaction():
                scoped(conn, self.owner)
                self.assertEqual(conn.execute(
                    "SELECT count(*) AS n FROM history_l1.execution_attempts WHERE owner_id=%s",
                    (self.owner,)).fetchone()["n"], 3)
                self.assertEqual(conn.execute(
                    "SELECT count(*) AS n FROM history_l1.answers WHERE owner_id=%s",
                    (self.owner,)).fetchone()["n"], 0)

    def test_08_cross_user_and_missing_indistinguishable_errors(self):
        req, receipt = self.create()
        msg_req, msg_receipt = self.send(receipt["conversation"]["conversation_id"])
        foreign_cid = receipt["conversation"]["conversation_id"]
        app.dependency_overrides[get_trusted_actor] = lambda: actor(new_owner())
        alt = TestClient(app, raise_server_exceptions=False)
        foreign = alt.get(f"/v1/conversations/{foreign_cid}/messages")
        missing = alt.get("/v1/conversations/missing_contract_id/messages")
        foreign_doc = self.check_response(foreign, "error_response", 404)
        missing_doc = self.check_response(missing, "error_response", 404)
        self.assertEqual(foreign_doc["error"], missing_doc["error"])
        wrong_status = alt.get("/v1/message-requests/status", params=status_params(msg_req))
        absent_status = alt.get("/v1/message-requests/status", params={
            **status_params(msg_req), "client_message_id": "missing_id"})
        self.assertEqual(self.check_response(wrong_status, "error_response", 404)["error"],
                         self.check_response(absent_status, "error_response", 404)["error"])
        alt.close()
        self.client = make_testclient(self.owner)
        for path in ("/v1/conversations/unknown_id/messages",):
            self.check_response(self.client.get(path), "error_response", 404)

    def test_09_conversation_cursor_multi_page_owner_scope_limit_tamper_expiry(self):
        docs = [self.create("Conversation " + str(i))[1] for i in range(7)]
        first = self.check_response(self.client.get("/v1/conversations",
                                   params={"limit": 2}), "conversation_page", 200)
        actor_ctx = actor(self.owner)
        self.assertEqual(check_conversation_page(
            {"kind": "conversation_list_request", "contract_version": "product.v1",
             "limit": 2, "cursor": None}, first, actor_ctx), [])
        self.assertTrue(first["page"]["has_more"])
        token = first["page"]["next_cursor"]
        self.assertTrue(token)
        seen = [v["conversation_id"] for v in first["items"]]
        late = self.create("Inserted after anchor")[1]["conversation"]["conversation_id"]
        current = token
        while current:
            response = self.client.get("/v1/conversations", params={"limit": 2, "cursor": current})
            page = self.check_response(response, "conversation_page", 200)
            seen.extend(v["conversation_id"] for v in page["items"])
            current = page["page"]["next_cursor"]
        self.assertEqual(len(seen), 7)
        self.assertEqual(len(set(seen)), 7)
        self.assertNotIn(late, seen)
        self.check_response(self.client.get("/v1/conversations",
                params={"limit": 3, "cursor": token}), "error_response", 422)
        self.check_response(self.client.get("/v1/conversations",
                params={"limit": 2, "cursor": token[:-2] + "AB"}), "error_response", 422)
        with patch.dict(os.environ, {"API_CURSOR_KEY": "different-synthetic-key-1234567890abcdef"}):
            self.check_response(self.client.get("/v1/conversations",
                    params={"limit": 2, "cursor": token}), "error_response", 422)
        now = time.time()
        with patch("apps.api.history_api.time.time", return_value=now + 100000):
            expired = self.client.get("/v1/conversations", params={"limit": 2, "cursor": token})
        self.assertEqual(self.check_response(expired, "error_response", 422)["error"]["code"],
                         "CURSOR_EXPIRED")
        app.dependency_overrides[get_trusted_actor] = lambda: actor(new_owner())
        other = TestClient(app, raise_server_exceptions=False)
        self.check_response(other.get("/v1/conversations",
                            params={"limit": 2, "cursor": token}), "error_response", 404)
        other.close()
        self.client = make_testclient(self.owner)

    def test_10_message_pagination_tied_timestamp_and_linked_answer(self):
        _, created = self.create()
        cid = created["conversation"]["conversation_id"]
        reqs = [self.send(cid=cid, question="Question " + str(i)) for i in range(4)]
        with real_conn() as conn:
            for req, receipt in reqs[:3]:
                att = start_t2(conn, self.owner, cid, req["client_message_id"],
                               req["idempotency_key"], uid(), uid())
                answer = synthetic_answer(att, receipt)
                finalize_t3(conn, self.owner, att["id"], answer, "Assistant reply")
        with psycopg.connect(self.migrator_dsn, autocommit=True) as migrator:
            with migrator.transaction():
                migrator.execute("""UPDATE history_l1.messages SET created_at=%s
                    WHERE owner_id=%s AND conversation_id=%s""",
                    (datetime(2026,1,1,tzinfo=timezone.utc), self.owner, cid))
        seen = []
        answers = set()
        params = {"limit": 2}
        late_ids = None
        while True:
            response = self.client.get(f"/v1/conversations/{cid}/messages", params=params)
            page = self.check_response(response, "conversation_messages_page", 200)
            actor_ctx = actor(self.owner)
            expected_query = {
                "kind": "conversation_messages_request", "contract_version": "product.v1",
                "conversation_id": cid, "limit": 2,
                "cursor": params.get("cursor"),
            }
            self.assertEqual(check_messages_page(expected_query, page, actor_ctx), [])
            seen.extend(m["message_id"] for m in page["items"])
            ids = {m["message_id"] for m in page["items"]}
            for ans in page["answers"]:
                self.assertIn(ans["message_id"], ids)
                self.assertNotIn(ans["answer_id"], answers)
                answers.add(ans["answer_id"])
            if late_ids is None:
                late_req, late_receipt = self.send(cid=cid, question="Later after anchor")
                late_ids = {late_receipt["message_id"]}
            if not page["page"]["has_more"]:
                break
            params = {"limit": 2, "cursor": page["page"]["next_cursor"]}
        self.assertEqual(len(seen), 7)
        self.assertEqual(len(set(seen)), 7)
        self.assertTrue(late_ids.isdisjoint(seen))
        self.assertEqual(len(answers), 3)
        page = self.client.get(f"/v1/conversations/{cid}/messages",
                               params={"limit": 1})
        cursor = self.check_response(page, "conversation_messages_page", 200)["page"]["next_cursor"]
        self.assertIsNotNone(cursor)
        self.check_response(self.client.get("/v1/conversations",
                            params={"limit": 1, "cursor": cursor}), "error_response", 422)
        self.check_response(self.client.get(f"/v1/conversations/other_cid/messages",
                            params={"limit": 1, "cursor": cursor}), "error_response", 422)
        self.check_response(self.client.get(f"/v1/conversations/{cid}/messages",
                            params={"limit": 2, "cursor": cursor}), "error_response", 422)

    def test_11_validation_size_error_redaction_and_cursor_configuration(self):
        bad = [
            ({**request_create(), "extra": "unwanted"}, 422),
            ({**request_create(), "client_conversation_id": "*bad"}, 422),
            ({**request_create(), "idempotency_key": "short"}, 422),
        ]
        for data, code in bad:
            self.check_response(self.client.post("/v1/conversations", json=data),
                                "error_response", code)
        self.check_response(self.client.post("/v1/messages",
                            json=request_send(question="é" * 5000)), "error_response", 413)
        self.check_response(self.client.post("/v1/messages", json={
            **request_send(), "owner_user_id": self.owner}), "error_response", 422)
        self.check_response(self.client.post("/v1/messages",
                            content='{"kind":', headers={"content-type":"application/json"}),
                            "error_response", 422)
        self.check_response(self.client.post("/v1/messages",
                            content='{"kind":1,"kind":2}',
                            headers={"content-type":"application/json"}), "error_response", 422)
        self.check_response(self.client.get("/v1/conversations", params={"limit": 0}),
                            "error_response", 422)
        self.check_response(self.client.get("/v1/conversations", params={"limit": 101}),
                            "error_response", 422)
        self.check_response(self.client.get("/v1/conversations", params={"limit": 2, "owner": self.owner}),
                            "error_response", 422)
        self.check_response(self.client.get("/v1/message-requests/status",
                    params={"owner_user_id": self.owner}), "error_response", 422)
        self.check_response(self.client.post("/v1/messages", json={
            **request_send(), "server_commit_evidence": {"verified": True}}),
            "error_response", 422)
        for n in range(3):
            self.create("Cursor config " + str(n))
        with patch.dict(os.environ, {"API_CURSOR_KEY": ""}):
            no_key = self.client.get("/v1/conversations", params={"limit": 1})
            self.assertEqual(self.check_response(no_key, "error_response", 503)
                             ["error"]["code"], "CURSOR_CONFIGURATION")
        missing = self.client.get("/v1/conversations/unowned_123/messages")
        self.check_response(missing, "error_response", 404)
        self.assertNotIn("psycopg", missing.text.lower())
        self.assertNotIn("password", missing.text.lower())
        self.assertNotIn("traceback", missing.text.lower())
        self.assertNotIn("SELECT ", missing.text)

    def test_12_openapi_maps_existing_product_contract_and_actual_http_codes(self):
        document = app.openapi()
        self.assertEqual(document["openapi"], "3.1.0")
        paths = document["paths"]
        self.assertEqual(set(paths), {
            "/v1/conversations", "/v1/conversations/{conversation_id}/messages",
            "/v1/messages", "/v1/message-requests/status",
        })
        target = document["components"]["schemas"]["ProductContract"]
        self.assertEqual(set(target["$defs"]), set(SCHEMA["$defs"]))
        self.assertEqual(target["$defs"]["send_message_request"]["required"],
                         SCHEMA["$defs"]["send_message_request"]["required"])
        self.assertIn("201", paths["/v1/conversations"]["post"]["responses"])
        self.assertIn("200", paths["/v1/conversations"]["post"]["responses"])
        self.assertIn("202", paths["/v1/messages"]["post"]["responses"])
        self.assertIn("200", paths["/v1/messages"]["post"]["responses"])
        for path, methods in paths.items():
            for method, operation in methods.items():
                self.assertIn("x-product-contract-version", operation)
                for code, entry in operation["responses"].items():
                    self.assertTrue(code.isdigit())
                    schema = entry.get("content", {}).get("application/json", {}).get("schema", {})
                    if schema:
                        self.assertTrue(schema["$ref"].startswith("#/components/schemas/ProductContract/$defs/"))
        self.assertNotIn("/v1/attempts", paths)
        self.assertNotIn("/v1/answer", paths)
        with real_conn() as conn:
            info = conn.execute("""SELECT rolname,rolsuper,rolbypassrls FROM pg_roles
                                   WHERE rolname=current_user""").fetchone()
            self.assertEqual(info["rolname"], "history_app")
            self.assertFalse(info["rolsuper"])
            self.assertFalse(info["rolbypassrls"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
