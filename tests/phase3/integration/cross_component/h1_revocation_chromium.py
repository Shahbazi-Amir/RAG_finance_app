"""H1-X01: real Chromium -> Next History -> CI signer -> real FastAPI GET -> PG 005/004.

Only GET /v1/conversations is signed. Chromium's test-only second list
callback forces a stale overlap while the Refresh button is disabled; both
200 and 401 come from the actual API. No production code or migration edits.
No real OIDC/BFF integration, browser owner header or real user identity.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import Event, Lock, Thread
import time
from urllib.parse import urlsplit
import uuid

import httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row
from fastapi import Request
from playwright.async_api import async_playwright, expect
import uvicorn

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/phase3/api"))

from proof_fixture import FakeBFFSigner, ISSUER, AUDIENCE, KID  # noqa: E402
from apps.api import history_api as history  # noqa: E402
from src.phase3.auth.service_proof import (  # noqa: E402
    BFFServiceVerifier, TrustRejected, assertion_from_asgi_headers, wire_request,
)
from src.phase3.auth.transactional_admission import protected_transaction  # noqa: E402
from src.phase3.storage.postgres import auth_session  # noqa: E402
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore  # noqa: E402

DSNS = {
    "APP": ("H1_APP_DSN", "history_app"),
    "MIG": ("H1_AUTH_MIG_DSN", "auth_migrator"),
    "MAP": ("H1_MAP_DSN", "auth_mapper"),
    "SESSION": ("H1_SESSION_DSN", "auth_sessions"),
}
API_PORT = 8120
A_PORT, B_PORT = 8111, 8112
A_NEXT, B_NEXT = 3000, 3001


def guard() -> None:
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("GITHUB_EPHEMERAL_CI_ONLY")
    for env, role in DSNS.values():
        spec = conninfo_to_dict(os.environ[env])
        if (spec.get("host") != "127.0.0.1"
                or spec.get("port") != "5432"
                or spec.get("dbname") != "history_ci"
                or spec.get("user") != role
                or not set(spec).issubset({
                    "host", "port", "dbname", "user", "password", "connect_timeout",
                })):
            raise RuntimeError("UNSAFE_H1_TEST_DATABASE:" + env)


def db(which: str):
    return psycopg.connect(os.environ[DSNS[which][0]], autocommit=True,
                           row_factory=dict_row, connect_timeout=5)


class Witness:
    def __init__(self):
        self.lock = Lock()
        self.signer = FakeBFFSigner()
        self.verifier = BFFServiceVerifier(
            issuer=ISSUER, audience=AUDIENCE,
            public_keys={KID: self.signer.public_pem},
        )
        self.store = PostgresDurableReplayStore()
        self.sessions = {}
        self.rows = []
        self.sql_owners = []
        self.failures = []
        self.hold_next_a_list = False
        self.held_ready = Event()
        self.release_held = Event()
        self.held_sent = Event()

    def record(self, slot, path, status, claims):
        with self.lock:
            self.rows.append((slot, path, status, claims["jti"]))


STATE = Witness()
REAL_LIST = history.list_conversations


def checked_real_history_list(conn, owner, **kwargs):
    # Observe the actual route's repository connection WHILE the signed
    # 005 replay and 004 admission outer transaction still holds the locks.
    if conn.info.transaction_status != TransactionStatus.INTRANS:
        raise AssertionError("H1_HISTORY_NOT_IN_005_004_TRANSACTION")
    check = conn.execute(
        """SELECT current_user AS role, current_setting('app.owner_id',true) AS owner,
                  r.rolsuper, r.rolbypassrls
           FROM pg_roles r WHERE r.rolname=current_user"""
    ).fetchone()
    if (check["role"] != "history_app" or check["rolsuper"]
            or check["rolbypassrls"]):
        raise AssertionError("H1_INSECURE_HISTORY_SQL_ROLE")
    page = REAL_LIST(conn, owner, **kwargs)
    scoped_owner = conn.execute(
        "SELECT current_setting('app.owner_id',true) AS owner"
    ).fetchone()["owner"]
    if scoped_owner != owner or any(
            item["owner_user_id"] != owner for item in page["items"]):
        raise AssertionError("H1_SQL_OWNER_OR_RLS_MISMATCH")
    with STATE.lock:
        STATE.sql_owners.append(owner)
    return page


def signed_session(request: Request):
    # Test-only injection of the *entire* History dependency. No production
    # get_trusted_actor override, HTTP owner selector, or forged API response.
    try:
        token = assertion_from_asgi_headers(request.scope)
        method, path, query, body = wire_request(request.scope, b"")
        with db("APP") as conn:
            with protected_transaction(
                conn, verifier=STATE.verifier, replay_store=STATE.store,
                compact_assertion=token, method=method, raw_path=path,
                raw_query=query, body=body,
            ) as owner:
                yield {
                    "owner": owner, "conn": conn,
                    "request_id": history.uid(), "trace_id": history.uid(),
                }
    except TrustRejected:
        raise history.ApiFailure(401, "AUTH_REQUIRED", "authorization") from None
    except psycopg.Error:
        raise history.ApiFailure(503, "TEMPORARILY_UNAVAILABLE") from None


def gateway_class(slot):
    class Gateway(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            # No assertion, session handle, private body or URL logging.
            return

        def do_GET(self):
            parsed = urlsplit(self.path)
            # No other History path is signed or exercised here.
            allowed = parsed.path == "/v1/conversations"
            if not allowed or parsed.scheme or parsed.netloc:
                self.send_error(404)
                return
            session = STATE.sessions[slot]
            raw_query = self.path.split("?", 1)[1].encode("ascii") if "?" in self.path else b""
            claims = STATE.signer.claims(
                owner_id=session.owner_id, session_ref=session.opaque,
                epoch=session.epoch, generation=session.generation,
                method="GET", path=parsed.path.encode("ascii"),
                query=raw_query, body=b"",
            )
            proof = STATE.signer.sign(claims)
            try:
                upstream = httpx.get(
                    "http://127.0.0.1:" + str(API_PORT) + self.path,
                    headers={"Authorization": "BFF-Assertion " + proof},
                    timeout=8.0,
                )
                status, content = upstream.status_code, upstream.content
                STATE.record(slot, parsed.path, status, claims)
                if slot == "A" and parsed.path == "/v1/conversations" and status == 200:
                    with STATE.lock:
                        hold = STATE.hold_next_a_list
                        if hold:
                            STATE.hold_next_a_list = False
                    if hold:
                        # The API completed and committed 005/004 before
                        # the old 200 is held at this test-only gateway.
                        STATE.held_ready.set()
                        if not STATE.release_held.wait(25):
                            raise TimeoutError("H1_HELD_200_RELEASE_TIMEOUT")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(content)
                self.wfile.flush()
                if slot == "A" and parsed.path == "/v1/conversations" and status == 200:
                    if STATE.held_ready.is_set():
                        STATE.held_sent.set()
            except Exception as exc:
                with STATE.lock:
                    STATE.failures.append(type(exc).__name__)
                try:
                    self.send_error(502)
                except OSError:
                    pass
            finally:
                self.close_connection = True

    return Gateway


def create_fixtures():
    for slot in ("A", "B"):
        with db("MAP") as conn:
            owner = auth_session.map_identity(
                conn, "https://synthetic.invalid/foundation-h1",
                "foundation-h1-" + slot + "-" + uuid.uuid4().hex,
            )["owner_id"]
        with db("SESSION") as conn:
            session = auth_session.issue(
                conn, owner, 0, idle_seconds=180, absolute_seconds=900,
            )
        STATE.sessions[slot] = session
    ids = {}
    for slot in ("A", "B"):
        owner = STATE.sessions[slot].owner_id
        title = "H1-private-" + slot + "-" + uuid.uuid4().hex[:10]
        request = {
            "kind": "create_conversation_request",
            "contract_version": "product.v1",
            "client_conversation_id": history.uid(),
            "idempotency_key": "h1_" + uuid.uuid4().hex,
            "title": title,
        }
        with db("APP") as conn:
            receipt = history.create_conversation(
                conn, owner, request, history.uid(), history.uid())
        ids[slot] = (receipt["conversation"]["conversation_id"], title)
    return ids


def revoked_in_database(session) -> bool:
    digest = sha256(session.opaque.encode("ascii")).hexdigest()
    with db("MIG") as conn:
        row = conn.execute(
            "SELECT status FROM auth_l1.sessions WHERE digest_sha256=%s",
            (digest,),
        ).fetchone()
    return row is not None and row["status"] == "revoked"


def assert_denied_list_jti_not_consumed() -> int:
    with STATE.lock:
        denials = [jti for slot, path, status, jti in STATE.rows
                   if slot == "A" and path == "/v1/conversations" and status == 401]
    if not denials:
        raise AssertionError("NO_REAL_GET_CONVERSATIONS_API_401")
    digest = sha256((ISSUER + "\x00" + denials[-1]).encode("utf8")).hexdigest()
    with db("MIG") as conn:
        row = conn.execute(
            "SELECT count(*) AS n FROM auth_l1.service_assertion_replays "
            "WHERE issuer_jti_sha256=%s", (digest,),
        ).fetchone()
    if row["n"] != 0:
        raise AssertionError("REVOKED_GET_401_CONSUMED_DURABLE_JTI")
    return len(denials)


def wait_http(url, deadline=35):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            with httpx.Client(timeout=2) as client:
                if client.get(url).status_code == 200:
                    return
        except (httpx.HTTPError, OSError):
            pass
        time.sleep(0.3)
    raise RuntimeError("H1_LOOPBACK_SERVER_UNAVAILABLE")


async def assert_cleared(page, a_title, b_title):
    await expect(page.get_by_test_id("history-login-required")).to_be_visible()
    await expect(page.get_by_test_id("history-state")).to_contain_text("ورود معتبر لازم")
    await expect(page.locator('[data-testid^="conversation-"]')).to_have_count(0)
    await expect(page.locator('[data-testid^="history-message-"]')).to_have_count(0)
    await expect(page.locator('[data-testid^="pending-"]')).to_have_count(0)
    await expect(page.get_by_test_id("history-question")).to_have_value("")
    await expect(page.get_by_test_id("history-question")).to_be_disabled()
    await expect(page.get_by_test_id("refresh-history")).to_be_disabled()
    await expect(page.get_by_test_id("new-draft")).to_be_disabled()
    await expect(page.get_by_text(a_title, exact=True)).to_have_count(0)
    await expect(page.get_by_text(b_title, exact=True)).to_have_count(0)


async def browser_scenario(ids):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ca = await browser.new_context(viewport={"width": 1280, "height": 800})
        cb = await browser.new_context(viewport={"width": 1280, "height": 800})
        try:
            a = await ca.new_page()
            b = await cb.new_page()
            aid, atitle = ids["A"]
            bid, btitle = ids["B"]
            await a.goto("http://127.0.0.1:3000/history", wait_until="domcontentloaded")
            await b.goto("http://127.0.0.1:3001/history", wait_until="domcontentloaded")
            await expect(a.get_by_test_id("conversation-" + aid)).to_be_visible(timeout=20000)
            await expect(b.get_by_test_id("conversation-" + bid)).to_be_visible(timeout=20000)
            await expect(a.get_by_text(atitle, exact=True)).to_be_visible()
            await expect(b.get_by_text(btitle, exact=True)).to_be_visible()
            await expect(a.get_by_text(btitle, exact=True)).to_have_count(0)
            await expect(b.get_by_text(atitle, exact=True)).to_have_count(0)
            print("H1X01_A_AND_B_INITIAL_REAL_GET_200_OWNER_ISOLATED_PASS", flush=True)

            # The old A LIST 200 has truly completed at the API but its
            # DELIVERY is held by the network fixture, not manufactured.
            with STATE.lock:
                STATE.hold_next_a_list = True
            await a.get_by_test_id("refresh-history").click()
            assert await asyncio.to_thread(STATE.held_ready.wait, 12), (
                "A previous successful GET /v1/conversations was not held")
            assert not STATE.release_held.is_set()
            print("H1X02_PRIOR_REAL_A_LIST_200_HELD_BEFORE_REVOKE_PASS", flush=True)

            # Genuine 003 revoke_one COMMIT on separate privileged SQL connection.
            def revoke():
                with db("SESSION") as conn:
                    return auth_session.revoke_one(
                        conn, STATE.sessions["A"].opaque, STATE.sessions["A"].epoch)
            assert await asyncio.to_thread(revoke) is True
            assert await asyncio.to_thread(revoked_in_database, STATE.sessions["A"])
            print("H1X03_REAL_POSTGRES_EXPLICIT_A_REVOKE_COMMITTED_PASS", flush=True)

            # Fresh, distinct server-signed BFF proof for the SAME old A
            # session. The actual FastAPI GET returns 401; Playwright does
            # NOT fabricate 401 nor tamper with the API response.
            denied = await ca.request.get(
                "http://127.0.0.1:8111/v1/conversations?limit=2", timeout=12000)
            assert denied.status == 401, "fresh proof must fail at real API"
            denied_doc = await denied.json()
            assert denied_doc["error"]["code"] == "AUTH_REQUIRED"
            assert await asyncio.to_thread(assert_denied_list_jti_not_consumed) >= 1
            print("H1X04_FRESH_SIGNED_SAME_SESSION_REAL_API_LIST_401_NO_JTI_COMMIT_PASS", flush=True)

            # Disabled Refresh prevents user overlap. Chromium's test-only
            # adversarial scheduling calls the SAME React onClick once more,
            # while the old API 200 remains undelivered. No mocked response.
            async with a.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and r.status == 401, timeout=15000
            ) as denied_ui:
                await a.get_by_test_id("refresh-history").evaluate(
                    """element => {
                      const name = Object.keys(element).find(
                        key => key.startsWith('__reactProps$'));
                      const handler = name && element[name].onClick;
                      if (typeof handler !== 'function')
                        throw new Error('H1_REACT_OVERLAP_HARNESS_UNAVAILABLE');
                      handler();
                    }"""
                )
            denied_response = await denied_ui.value
            await denied_response.finished()
            api_error = await denied_response.json()
            assert api_error["error"]["code"] == "AUTH_REQUIRED"
            await assert_cleared(a, atitle, btitle)
            assert not STATE.release_held.is_set()
            print("H1X05_REAL_API_LIST_401_PURGES_A_UI_WHILE_OLD_LIST_HELD_PASS",
                  flush=True)

            # The previously admitted successful 200 is delivered LATER.
            async with a.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and r.status == 200, timeout=15000
            ) as late:
                STATE.release_held.set()
            await (await late.value).finished()
            assert await asyncio.to_thread(STATE.held_sent.wait, 10)
            await a.evaluate(
                "() => new Promise(resolve => requestAnimationFrame("
                "() => requestAnimationFrame(resolve)))")
            await assert_cleared(a, atitle, btitle)
            print("H1X06_OLD_REAL_API_200_DELIVERED_AFTER_401_NO_UI_REHYDRATION_PASS",
                  flush=True)

            # Independent session B is not revoked: real refresh and owner-only
            # DB-backed List through a NEW B proof must remain valid.
            async with b.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and r.status == 200, timeout=15000
            ) as fresh_b:
                await b.get_by_test_id("refresh-history").click()
            await (await fresh_b.value).finished()
            await expect(b.get_by_test_id("conversation-" + bid)).to_be_visible()
            await expect(b.get_by_text(atitle, exact=True)).to_have_count(0)
            await expect(b.get_by_text(btitle, exact=True)).to_be_visible()
            assert not STATE.failures, "Gateway returned a transport/error fallback"
            with STATE.lock:
                observed = Counter((slot, path, status)
                                   for slot, path, status, _ in STATE.rows)
                sql_owners = list(STATE.sql_owners)
            assert STATE.sessions["A"].owner_id in sql_owners
            assert STATE.sessions["B"].owner_id in sql_owners
            assert observed[("A", "/v1/conversations", 200)] >= 2
            assert observed[("A", "/v1/conversations", 401)] >= 1
            assert observed[("B", "/v1/conversations", 200)] >= 2
            print("H1X07_B_NEW_SIGNED_API_200_OWNER_B_ONLY_AFTER_A_REVOKE_PASS",
                  flush=True)
            print("H1_CROSS_COMPONENT_CHROMIUM_REAL_API_PG_PASS", flush=True)
        finally:
            STATE.release_held.set()
            await ca.close()
            await cb.close()
            await browser.close()


def main():
    guard()
    ids = create_fixtures()
    history.app.dependency_overrides[history._session] = signed_session
    history.list_conversations = checked_real_history_list
    api = uvicorn.Server(uvicorn.Config(
        history.app, host="127.0.0.1", port=API_PORT,
        access_log=False, log_level="error", lifespan="off"))
    api_thread = Thread(target=api.run, daemon=True)
    api_thread.start()
    servers = []
    processes = []
    try:
        wait_http("http://127.0.0.1:8120/openapi.json")
        # Missing proof is still a real API 401. No browser/client owner header.
        anonymous = httpx.get("http://127.0.0.1:8120/v1/conversations?limit=2")
        assert anonymous.status_code == 401
        for slot, port in (("A", A_PORT), ("B", B_PORT)):
            server = ThreadingHTTPServer(("127.0.0.1", port), gateway_class(slot))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append((server, thread))
        for port, upstream in ((A_NEXT, A_PORT), (B_NEXT, B_PORT)):
            env = dict(os.environ)
            env["HISTORY_UPSTREAM_ORIGIN"] = "http://127.0.0.1:" + str(upstream)
            proc = subprocess.Popen(
                ["./node_modules/.bin/next", "start", "-H", "127.0.0.1",
                 "-p", str(port)], cwd=ROOT / "apps/web", env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )
            processes.append(proc)
        wait_http("http://127.0.0.1:3000/history")
        wait_http("http://127.0.0.1:3001/history")
        asyncio.run(browser_scenario(ids))
    finally:
        STATE.release_held.set()
        for proc in processes:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        for server, thread in servers:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        api.should_exit = True
        api_thread.join(timeout=5)
        history.app.dependency_overrides.clear()
        history.list_conversations = REAL_LIST


if __name__ == "__main__":
    main()
