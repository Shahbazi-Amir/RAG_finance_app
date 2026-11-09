"""Real PostgreSQL 17.11 temporary CI: RSA proof + same-session fenced write.

No real IdP, BFF, product API History, production DB or real user. The
synthetic signer lives only in tests/phase3/api/proof_fixture.py.
No dependency override bypasses signature or DB admission.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import unittest
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InsufficientPrivilege
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/phase3/api"))

from proof_fixture import FakeBFFSigner, ISSUER, AUDIENCE, KID
from src.phase3.auth.service_proof import (
    BFFServiceVerifier, TrustRejected, assertion_from_asgi_headers, wire_request,
)
from src.phase3.auth.transactional_admission import (
    PostgresCiReplayStore, protected_operation,
)
from src.phase3.storage.postgres import auth_session as auth


ROLES = {
    "API": "auth_trust_api",
    "MAP": "auth_mapper",
    "SESSION": "auth_sessions",
    "REVOKER": "auth_revoker",
    "REAUTH": "auth_reauth",
    "MIG": "auth_migrator",
}
SIGNER = FakeBFFSigner()
VERIFIER = BFFServiceVerifier(issuer=ISSUER, audience=AUDIENCE,
                              public_keys={KID: SIGNER.public_pem})
STORE = PostgresCiReplayStore()


def db(role="API"):
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("CI_ONLY")
    dsn = os.environ["AUTH_TRUST_" + role + "_DSN"]
    opts = conninfo_to_dict(dsn)
    if (opts.get("host") != "127.0.0.1" or opts.get("port") != "5432"
            or opts.get("dbname") != "history_ci"
            or opts.get("user") != ROLES[role]
            or not set(opts).issubset({
                "host", "port", "dbname", "user", "password", "connect_timeout",
            })):
        raise RuntimeError("CI_ISOLATED_DATABASE_REQUIRED")
    return psycopg.connect(dsn, autocommit=True, row_factory=dict_row)


def new_fixture():
    # Credential creation deliberately separated from API auth_trust_api role.
    ident = ("https://synthetic.invalid/" + uuid.uuid4().hex,
             "synthetic_" + uuid.uuid4().hex)
    with db("MAP") as c:
        owner = auth.map_identity(c, *ident)["owner_id"]
    with db("SESSION") as c:
        session = auth.issue(c, owner, 0, idle_seconds=40, absolute_seconds=400)
    return owner, session


def synthetic_proof(session, *, owner=None, epoch=None, generation=None,
                    method="POST", path=b"/fixture", query=b"", body=b"marker",
                    claims_override=None):
    claim = SIGNER.claims(
        owner_id=session.owner_id if owner is None else owner,
        session_ref=session.opaque,
        epoch=session.epoch if epoch is None else epoch,
        generation=session.generation if generation is None else generation,
        method=method, path=path, query=query, body=body,
    )
    if claims_override:
        claim.update(claims_override)
    return SIGNER.sign(claim)


def inserted(marker: str) -> int:
    with db("MIG") as c:
        return c.execute(
            "SELECT count(*) AS n FROM auth_trust_ci.protected_actions WHERE marker=%s",
            (marker,),
        ).fetchone()["n"]


def action(marker):
    def write(conn, owner):
        conn.execute(
            "INSERT INTO auth_trust_ci.protected_actions(marker,owner_id) VALUES(%s,%s)",
            (marker, owner),
        )
        return True
    return write


def execute(token, marker, *, store=STORE, method="POST",
            path=b"/fixture", query=b"", body=b"marker", action_fn=None):
    with db() as c:
        return protected_operation(
            c, verifier=VERIFIER, replay_store=store, compact_assertion=token,
            method=method, raw_path=path, raw_query=query, body=body,
            action=action(marker) if action_fn is None else action_fn,
        )


app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)


@app.api_route("/fixture", methods=["POST", "GET", "PATCH", "PUT"])
@app.api_route("/other", methods=["POST", "GET", "PATCH", "PUT"])
async def local_only_fixture(request: Request):
    # ONLY a disposable in-process HTTP test, never the product History API.
    try:
        token = assertion_from_asgi_headers(request.scope)
        method, path, query, raw = wire_request(request.scope, await request.body())
        marker = raw.decode("ascii")
        if len(marker) > 64 or not marker.isascii():
            raise TrustRejected()
        execute(token, marker, method=method, path=path, query=query,
                body=raw)
        return {"ok": True}
    except TrustRejected:
        return Response(status_code=401, headers={"Cache-Control": "no-store"})
    except (psycopg.Error, RuntimeError, UnicodeError, ValueError):
        return Response(status_code=503, headers={"Cache-Control": "no-store"})


class BFFTrustPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if "history_ci" not in os.environ.get("AUTH_TRUST_API_DSN", ""):
            raise RuntimeError("CI_ONLY")
        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def marker(self):
        return "trust_" + secrets.token_hex(10)

    def http(self, token, marker, *, path="/fixture", method="POST",
             headers=None):
        value = {} if token is None else {"Authorization": "BFF-Assertion " + token}
        if headers:
            value.update(headers)
        return self.client.request(method, path, content=marker.encode("ascii"),
                                   headers=value)

    def test_TRI01_real_signature_session_and_sql_fixture(self):
        owner, session = new_fixture()
        marker = self.marker()
        jwt_token = synthetic_proof(session, body=marker.encode())
        response = self.http(jwt_token, marker)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertEqual(inserted(marker), 1)
        self.assertNotIn(session.opaque, response.text)

    def test_TRI02_no_assertion_spoofed_owner_and_fake_idp_claim(self):
        owner, session = new_fixture()
        for headers in (None, {"X-Owner-ID": owner},
                        {"X-User-ID": owner}, {"X-Forwarded-User": owner}):
            marker = self.marker()
            resp = self.http(None, marker, headers=headers)
            self.assertEqual(resp.status_code, 401)
            self.assertEqual(inserted(marker), 0)
        marker = self.marker()
        token = synthetic_proof(session, body=marker.encode())
        self.assertEqual(self.http(token, marker, headers={"X-Owner-ID": owner}).status_code, 401)
        self.assertEqual(inserted(marker), 0)
        claimed_idp = synthetic_proof(session, body=marker.encode(),
                                     claims_override={"iss": "https://keycloak.invalid/realms/ci"})
        self.assertEqual(self.http(claimed_idp, marker).status_code, 401)
        self.assertEqual(inserted(marker), 0)

    def test_TRI03_replay_from_independent_connections_and_restart_equivalent(self):
        _, session = new_fixture()
        marker = self.marker()
        proof = synthetic_proof(session, body=marker.encode())
        self.assertEqual(self.http(proof, marker).status_code, 200)
        self.assertEqual(self.http(proof, marker).status_code, 401)
        # New verifier/store instance backed by SAME durable table still denies.
        with self.assertRaises(TrustRejected):
            execute(proof, self.marker(), body=marker.encode(),
                    store=PostgresCiReplayStore())
        self.assertEqual(inserted(marker), 1)

    def test_TRI04_concurrent_replay_exactly_one_commit(self):
        _, session = new_fixture()
        marker = self.marker()
        proof = synthetic_proof(session, body=marker.encode())
        admitted = threading.Event()
        release = threading.Event()
        def first():
            def slow(conn, owner):
                admitted.set()
                if not release.wait(8):
                    raise RuntimeError("BOUNDED_TEST_TIMEOUT")
                return action(marker)(conn, owner)
            return execute(proof, marker, body=marker.encode(), action_fn=slow)
        def second():
            try:
                execute(proof, marker, body=marker.encode())
                return "accepted"
            except TrustRejected:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(first)
            self.assertTrue(admitted.wait(8), "first never admitted")
            f2 = ex.submit(second)
            self.assertFalse(f2.done(), "same JTI must await original TX")
            release.set()
            self.assertTrue(f1.result(timeout=10))
            self.assertEqual(f2.result(timeout=10), "rejected")
        self.assertEqual(inserted(marker), 1)

    def test_TRI05_rebound_method_path_query_raw_body(self):
        _, session = new_fixture()
        marker = self.marker()
        body = marker.encode()
        token = synthetic_proof(session, body=body, query=b"a=1&b=%2f")
        variants = (
            ("PUT", "/fixture?a=1&b=%2f", marker),
            ("POST", "/other?a=1&b=%2f", marker),
            ("POST", "/fixture?b=%2f&a=1", marker),
            ("POST", "/fixture?a=1&b=%2F", marker),
            ("POST", "/fixture?a=1&b=%2f", marker + "x"),
        )
        for method, url, payload in variants:
            with self.subTest(wire="rebound"):
                result = self.http(token, payload, path=url, method=method)
                self.assertEqual(result.status_code, 401)
                self.assertEqual(inserted(payload), 0)
        self.assertEqual(self.http(token, marker, path="/fixture?a=1&b=%2f").status_code, 200)
        self.assertEqual(inserted(marker), 1)

    def test_TRI06_trusted_signed_wrong_owner_epoch_generation(self):
        actual, session = new_fixture()
        other, _ = new_fixture()
        for changes in ({"owner": other}, {"epoch": 1}, {"generation": 1}):
            marker = self.marker()
            token = synthetic_proof(session, body=marker.encode(), **changes)
            self.assertEqual(self.http(token, marker).status_code, 401)
            self.assertEqual(inserted(marker), 0)
        marker = self.marker()
        fresh = synthetic_proof(session, body=marker.encode())
        self.assertEqual(self.http(fresh, marker).status_code, 200)

    def test_TRI07_revoke_one_and_rotation(self):
        owner, first = new_fixture()
        m = self.marker()
        with db("SESSION") as conn:
            self.assertTrue(auth.revoke_one(conn, first.opaque, 0))
        self.assertEqual(self.http(synthetic_proof(first, body=m.encode()), m).status_code, 401)
        self.assertEqual(inserted(m), 0)
        with db("SESSION") as conn:
            fresh = auth.issue(conn, owner, 0, idle_seconds=40, absolute_seconds=400)
            rotated = auth.rotate(conn, fresh.opaque, 0, 0)
        m2 = self.marker()
        self.assertEqual(self.http(synthetic_proof(fresh, body=m2.encode()), m2).status_code, 401)
        self.assertEqual(self.http(synthetic_proof(rotated, body=m2.encode()), m2).status_code, 200)
        self.assertEqual(inserted(m2), 1)

    def test_TRI08_revoke_all_gate_and_suspension(self):
        owner, original = new_fixture()
        with db("REVOKER") as conn:
            self.assertEqual(auth.revoke_all(conn, owner, 0), 1)
        m = self.marker()
        self.assertEqual(self.http(synthetic_proof(original, body=m.encode()), m).status_code, 401)
        with db("REAUTH") as conn:
            self.assertTrue(auth.finish_simulated_reauth(conn, owner, 1))
        # This synthetic reauth is a trusted FIXTURE ONLY, no fresh IdP proof.
        with db("SESSION") as conn:
            new_session = auth.issue(conn, owner, 1, idle_seconds=40, absolute_seconds=400)
        with db("REVOKER") as conn:
            self.assertEqual(auth.suspend_owner(conn, owner, 1), 2)
        m2 = self.marker()
        self.assertEqual(self.http(synthetic_proof(new_session, body=m2.encode()), m2).status_code, 401)
        self.assertEqual(inserted(m2), 0)

    def test_TRI09_idle_and_absolute_expiration(self):
        owner, old = new_fixture()
        with db("MIG") as c:
            import hashlib
            d = hashlib.sha256(old.opaque.encode("ascii")).hexdigest()
            c.execute("""UPDATE auth_l1.sessions
                SET created_at=clock_timestamp()-interval '3 hours',
                    last_activity_at=clock_timestamp()-interval '2 hours',
                    idle_expires_at=clock_timestamp()-interval '1 minute',
                    absolute_expires_at=clock_timestamp()+interval '1 hour'
                WHERE digest_sha256=%s""", (d,))
        marker = self.marker()
        self.assertEqual(self.http(synthetic_proof(old, body=marker.encode()), marker).status_code, 401)
        self.assertEqual(inserted(marker), 0)
        with db("SESSION") as c:
            new = auth.issue(c, owner, 0, idle_seconds=40, absolute_seconds=400)
        with db("MIG") as c:
            import hashlib
            d = hashlib.sha256(new.opaque.encode("ascii")).hexdigest()
            c.execute("""UPDATE auth_l1.sessions
                SET created_at=clock_timestamp()-interval '3 hours',
                    last_activity_at=clock_timestamp()-interval '2 hours',
                    idle_expires_at=clock_timestamp()-interval '1 hour',
                    absolute_expires_at=clock_timestamp()-interval '1 minute'
                WHERE digest_sha256=%s""", (d,))
        marker2 = self.marker()
        self.assertEqual(self.http(synthetic_proof(new, body=marker2.encode()), marker2).status_code, 401)
        self.assertEqual(inserted(marker2), 0)

    def test_TRI10_db_admission_fences_concurrent_revoke(self):
        _, session = new_fixture()
        marker = self.marker()
        token = synthetic_proof(session, body=marker.encode())
        admitted = threading.Event()
        release = threading.Event()
        def admitted_work():
            def slow(conn, owner):
                admitted.set()
                if not release.wait(9):
                    raise RuntimeError("BOUNDED_TEST_TIMEOUT")
                return action(marker)(conn, owner)
            return execute(token, marker, body=marker.encode(), action_fn=slow)
        def revoke():
            with db("SESSION") as conn:
                conn.execute("SELECT set_config('application_name','trust_revoke_wait',false)")
                conn.execute("SET statement_timeout='9000ms'")
                return auth.revoke_one(conn, session.opaque, session.epoch)
        with ThreadPoolExecutor(max_workers=2) as ex:
            first = ex.submit(admitted_work)
            self.assertTrue(admitted.wait(8))
            second = ex.submit(revoke)
            observed = False
            with db("MIG") as observer:
                deadline = time.monotonic() + 7
                while time.monotonic() < deadline:
                    row = observer.execute("""SELECT wait_event_type FROM pg_stat_activity
                        WHERE application_name='trust_revoke_wait'""").fetchone()
                    if row and row["wait_event_type"] == "Lock":
                        observed = True
                        break
                    observer.execute("SELECT pg_sleep(0.03)")
            self.assertTrue(observed, "actual PostgreSQL lock wait required")
            self.assertFalse(second.done())
            release.set()
            self.assertTrue(first.result(timeout=12))
            self.assertTrue(second.result(timeout=12))
        self.assertEqual(inserted(marker), 1)
        next_marker = self.marker()
        self.assertEqual(self.http(synthetic_proof(session, body=next_marker.encode()),
                                   next_marker).status_code, 401)
        self.assertEqual(inserted(next_marker), 0)

    def test_TRI11_rollback_releases_jti_and_protected_write(self):
        _, session = new_fixture()
        marker = self.marker()
        token = synthetic_proof(session, body=marker.encode())
        class SyntheticAbort(Exception):
            pass
        def fail_after_write(c, owner):
            action(marker)(c, owner)
            raise SyntheticAbort("simulated rollback")
        with self.assertRaises(SyntheticAbort):
            execute(token, marker, body=marker.encode(), action_fn=fail_after_write)
        self.assertEqual(inserted(marker), 0)
        self.assertTrue(execute(token, marker, body=marker.encode()))
        self.assertEqual(inserted(marker), 1)
        with self.assertRaises(TrustRejected):
            execute(token, marker, body=marker.encode())

    def test_TRI12_unavailable_replay_table_role_and_denied_grants(self):
        _, session = new_fixture()
        marker = self.marker()
        token = synthetic_proof(session, body=marker.encode())
        with self.assertRaises(TrustRejected):
            execute(token, marker, body=marker.encode(), store=None)
        self.assertEqual(inserted(marker), 0)
        class MissingReplayTable:
            def consume(self, conn, proof):
                conn.execute("INSERT INTO auth_trust_ci.not_installed VALUES (1)")
                return True
        with self.assertRaises(TrustRejected):
            execute(token, marker, body=marker.encode(), store=MissingReplayTable())
        self.assertEqual(inserted(marker), 0)
        with db() as api:
            for q in (
                "SELECT * FROM auth_l1.sessions",
                "SELECT * FROM history_l1.conversations",
                "SELECT * FROM auth_trust_ci.replay_jti",
                "SELECT auth_l1.revoke_all('fake',0)",
                "SELECT auth_l1.issue_session('fake',0,repeat('a',64),40,400)",
                "SELECT auth_l1.finish_simulated_reauth('fake',0)",
            ):
                with self.subTest(role="auth_trust_api"):
                    with self.assertRaises(InsufficientPrivilege):
                        api.execute(q)
        self.assertEqual(self.http(token, marker).status_code, 200)

    def test_TRI13_real_http_missing_db_proof_or_tampering(self):
        _, session = new_fixture()
        marker = self.marker()
        proof = synthetic_proof(session, body=marker.encode())
        response = self.http(proof, marker, headers={"X-Owner-ID": session.owner_id})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(inserted(marker), 0)
        tampered = proof[:-4] + "AAAA"
        self.assertEqual(self.http(tampered, marker).status_code, 401)
        self.assertEqual(self.http(proof, marker).status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
