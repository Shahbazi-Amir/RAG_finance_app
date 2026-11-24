"""Actual Chromium/Next/BFF/Keycloak -> app-only H11 mTLS -> PG CI witness.

Reuse the original real login harness. No route interception, cookie creation,
owner header, fake response or engine. This is a single-runner integration
witness, not Foundation's Docker/fresh-volume or destination acceptance.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import sys
import uuid
from hashlib import sha256

import httpx
import psycopg
from psycopg.rows import dict_row
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tests/phase3/integration/ui")]
from phase3_auth_demo import Demo, ORIGIN, TITLE
from apps.api import history_api


class AppOnlyBrowserDemo(Demo):
    def add(self, cmd, env=None, cwd=ROOT):
        # Replace only the old test harness's API process, not application
        # source. Production-path TLS protocol and app-only guard are shared
        # with the actual listener; CI DB profile remains explicitly isolated.
        if cmd[:4] == [sys.executable, "-m", "uvicorn", "apps.api.product_session_api:app"]:
            self.api_env = dict(env)
            self.api_env.update(
                PHASE3_APP_MODE="APP_ONLY",
                API_RUNNER_EXECUTION_MODE="APP_ONLY",
                API_CURSOR_KEY=secrets.token_urlsafe(48),
                API_CURSOR_TTL_SECONDS="300",
                APP_ONLY_CI_API_PORT=cmd[cmd.index("--port") + 1],
                APP_ONLY_CI_CLIENT_CERT=str(self.client[0]),
                APP_ONLY_CI_SERVER_CERT=cmd[cmd.index("--ssl-certfile") + 1],
                APP_ONLY_CI_SERVER_KEY=cmd[cmd.index("--ssl-keyfile") + 1],
                APP_ONLY_CI_CLIENT_CA=cmd[cmd.index("--ssl-ca-certs") + 1],
            )
            self.api_command = [sys.executable, "-u", str(ROOT /
                "tests/phase3/integration/api/app_only_signed_pg_ci_h11.py")]
            self.api_process = super().add(self.api_command, self.api_env)
            return self.api_process
        if env is not None and "AUTH_CI_LOGIN_MODE" in env:
            env = {**env, "PHASE3_APP_MODE": "APP_ONLY"}
            env.pop("AUTH_CI_PRODUCT_CHAT_MODE", None)
        return super().add(cmd, env, cwd)

    def counts(self):
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            return db.execute(
                "SELECT (SELECT count(*) FROM history_l1.conversations) AS conv,"
                "(SELECT count(*) FROM history_l1.messages) AS msg,"
                "(SELECT count(*) FROM history_l1.send_receipts) AS t1,"
                "(SELECT count(*) FROM history_l1.execution_attempts) AS t2,"
                "(SELECT count(*) FROM history_l1.answers) AS t3").fetchone()

    def seed_extra(self, label):
        owner = self.owners[label]
        title = "CI restored browser page two " + label
        request = {"kind": "create_conversation_request", "contract_version": "product.v1",
                   "client_conversation_id": history_api.uid(),
                   "idempotency_key": "browser_" + uuid.uuid4().hex, "title": title}
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            receipt = history_api.create_conversation(
                db, owner, request, history_api.uid(), history_api.uid())
        cid = receipt["conversation"]["conversation_id"]
        mid = history_api.uid()
        message = "متن آزمایشی خصوصی " + label + " " + uuid.uuid4().hex[:12]
        # Pre-existing synthetic fixture data, not a Send endpoint or engine.
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True) as db:
            db.execute("INSERT INTO history_l1.messages "
                       "(owner_id,id,conversation_id,role,body) VALUES (%s,%s,%s,'user',%s)",
                       (owner, mid, cid, message))
        return cid, mid, message

    def sql_history(self, label):
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            return db.execute(
                "SELECT id,title FROM history_l1.conversations WHERE owner_id=%s "
                "AND state='active' ORDER BY created_at DESC,id DESC",
                (self.owners[label],)).fetchall()

    async def journey(self, browser, output):
        contexts = []
        try:
            ca, a, _, raw_a = await self.browser_login(browser, "A", False, output)
            contexts.append(ca)
            cb, b, _, raw_b = await self.browser_login(browser, "B", False, output)
            contexts.append(cb)
            assert raw_a["owner_id"] != raw_b["owner_id"]
            print("API_F3_BROWSER_REAL_OIDC_COOKIE_AB_PASS", flush=True)
            aid, mid, message = self.seed_extra("A")
            bid, _, _ = self.seed_extra("B")
            expected = {label: self.sql_history(label) for label in ("A", "B")}
            assert all(len(rows) == 3 for rows in expected.values())
            before = self.counts()
            for label, page in (("A", a), ("B", b)):
                foreign = "B" if label == "A" else "A"
                async with page.expect_response(
                    lambda r: "/api/history/conversations?limit=2" in r.url
                    and "cursor=" not in r.url and r.request.method == "GET") as wait:
                    await page.get_by_test_id("refresh-history").click()
                response = await wait.value
                assert response.status == 200
                doc = await response.json()
                assert [x["conversation_id"] for x in doc["items"]] == [
                    x["id"] for x in expected[label][:2]]
                assert doc["scope_user_id"] == self.owners[label]
                cursor = doc["page"]["next_cursor"]
                assert cursor
                async with page.expect_response(
                    lambda r: "/api/history/conversations?" in r.url and
                    "cursor=" in r.url and r.request.method == "GET") as wait:
                    await page.get_by_role("button", name="نمایش گفت‌وگوهای بیشتر").click()
                second = await wait.value
                assert second.status == 200
                second_doc = await second.json()
                assert [x["conversation_id"] for x in second_doc["items"]] == [
                    x["id"] for x in expected[label][2:]]
                for row in expected[label]:
                    await expect(page.get_by_test_id("conversation-" + row["id"])).to_be_visible()
                for row in expected[foreign]:
                    assert await page.get_by_test_id("conversation-" + row["id"]).count() == 0
                # Foreign cursor with the other real browser's session.
                foreign_page = b if label == "A" else a
                status = await foreign_page.evaluate(
                    """async cursor => (await fetch('/api/history/conversations?limit=2&cursor='+
                        encodeURIComponent(cursor), {cache:'no-store'})).status""", cursor)
                assert status == 404
            print("API_F3_BROWSER_PG_HTTP_DOM_PAGE2_AB_PASS", flush=True)
            async with a.expect_response(
                lambda r: "/api/history/conversations/" + aid + "/messages?" in r.url
                and r.request.method == "GET") as wait:
                await a.get_by_test_id("conversation-" + aid).click()
            detail = await wait.value
            assert detail.status == 200
            doc = await detail.json()
            assert doc["owner_user_id"] == self.owners["A"]
            assert any(x["message_id"] == mid and x["text"] == message for x in doc["items"])
            await expect(a.get_by_test_id("history-message-" + mid)).to_contain_text(message)
            denial = await b.evaluate("""async id => {
                const r=await fetch('/api/history/conversations/'+id+'/messages?limit=2',
                    {cache:'no-store'}); return {status:r.status,body:await r.text()};
                }""", aid)
            assert denial["status"] == 404 and message not in denial["body"]
            await expect(a.get_by_test_id("app-runtime-capability")).to_contain_text(
                "برنامه در حالت بدون موتور")
            await expect(a.get_by_test_id("create-conversation")).to_be_disabled()
            await expect(a.get_by_test_id("history-question")).to_be_disabled()
            await expect(a.get_by_test_id("history-send")).to_be_disabled()
            result = await a.evaluate("""async () => {
                const r=await fetch('/api/history/messages',{method:'POST',
                    headers:{'Content-Type':'application/json'},body:'{}'});
                return {status:r.status, body:await r.text()};
                }""")
            assert result["status"] == 503 and "ENGINE_NOT_AVAILABLE" in result["body"]
            tls = ssl.create_default_context(cafile=self.ca)
            tls.load_cert_chain(self.client[0], self.client[1])
            with httpx.Client(verify=tls, trust_env=False, timeout=8) as client:
                direct = client.post(self.product_origin + "/v1/messages", content=b"{}")
                assert direct.status_code == 503 and "ENGINE_NOT_CONFIGURED" in direct.text
            await a.reload(wait_until="domcontentloaded")
            await expect(a.get_by_test_id("conversation-" + aid)).to_be_visible()
            assert self.counts() == before
            print("API_F3_BROWSER_DETAIL_REFRESH_SEND_ZERO_SQL_PASS", flush=True)

            # Existing live ordinary browser logout; no cookie injected.
            logout = await ca.new_page()
            await logout.goto(ORIGIN + "/login")
            async with logout.expect_response(
                lambda r: r.url.endswith("/api/auth/logout") and r.request.method == "POST"
            ) as wait:
                await logout.get_by_test_id("logout-submit").click()
            assert (await wait.value).status == 303
            await expect(logout.get_by_test_id("logout-success")).to_be_visible()
            assert self.signed_private(raw_a).status_code == 401
            assert self.signed_private(raw_b).status_code == 200
            await a.get_by_test_id("refresh-history").click()
            await expect(a.get_by_test_id("history-login-required")).to_be_visible()
            assert await a.locator('[data-testid^="conversation-"]').count() == 0
            await b.get_by_test_id("refresh-history").click()
            await expect(b.get_by_test_id("conversation-" + bid)).to_be_visible()
            assert self.counts() == before
            print("API_F3_BROWSER_COMMITTED_REVOKE_AB_PASS", flush=True)
        finally:
            for context in contexts:
                await context.close()


async def main():
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("BROWSER_JOURNEY_CI_ONLY")
    demo = AppOnlyBrowserDemo()
    try:
        demo.start()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                # Private temporary directory, never upload session material.
                await demo.journey(browser, demo.root / "browser-output")
            finally:
                await browser.close()
        print("API_F3_REAL_NEXT_BROWSER_SIGNED_APP_ONLY_PG_JOURNEY_PASS", flush=True)
    finally:
        demo.stop()


if __name__ == "__main__":
    asyncio.run(main())
