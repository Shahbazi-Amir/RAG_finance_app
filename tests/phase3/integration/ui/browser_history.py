"""Real Chromium CI-only E2E for API History L1 with disposable PostgreSQL.

No external service, user-owned cookies, real identity or product Auth.
Two synthetic owners run in independent fixed loopback server processes.
Answer seed is a direct test fixture DB operation; no public seed endpoint.
"""
from __future__ import annotations
import asyncio
import copy
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src/phase3/storage/postgres"))
from repository import start_t2, finalize_t3, check_wire, uid, scoped  # noqa: E402

OWNER_A = "synthetic_ui_history_actor_a"
OWNER_B = "synthetic_ui_history_actor_b"
QUESTIONS = {
    "one": "آزمون تاریخچه یک: بودجه‌بندی",
    "two": "آزمون تاریخچه دو: پس‌انداز",
    "replay": "آزمون بازیابی پاسخ قطع‌شده",
    "status": "آزمون استعلام بعد از قطع شبکه",
    "seed": "آزمون پاسخ فقط از Fixture پایگاه داده",
}


def assert_ci():
    dsn = os.getenv("API_HISTORY_DSN", "")
    if (os.getenv("CI") != "true" or "dbname=history_ui_ci" not in dsn
            or "host=127.0.0.1" not in dsn or "user=history_app" not in dsn):
        raise SystemExit("CI_ONLY: temporary loopback DB")
    if not os.getenv("UI_HISTORY_SCREENSHOTS"):
        raise SystemExit("CI_ONLY: screenshot output required")


def receipt_count(client_id: str, owner: str = OWNER_A) -> int:
    with psycopg.connect(os.environ["API_HISTORY_DSN"], autocommit=True,
                         row_factory=dict_row) as conn:
        with conn.transaction():
            scoped(conn, owner)
            return conn.execute(
                """SELECT count(*) AS n FROM history_l1.send_receipts
                   WHERE owner_id=%s AND client_message_id=%s""",
                (owner, client_id)).fetchone()["n"]


def seed_answer(request: dict):
    fixtures = json.loads((ROOT / "packages/contracts/fixtures/product.v1.cases.json").read_text())["cases"]
    source = next(item["document"] for item in fixtures
                  if item["case_id"] == "valid_confidence_calibrated_example")
    with psycopg.connect(os.environ["API_HISTORY_DSN"], autocommit=True,
                         row_factory=dict_row) as conn:
        attempt = start_t2(
            conn, OWNER_A, request["requested_conversation_id"],
            request["client_message_id"], request["idempotency_key"], uid(), uid())
        with conn.transaction():
            scoped(conn, OWNER_A)
            receipt = conn.execute(
                """SELECT resolved_conversation_id FROM history_l1.send_receipts
                   WHERE owner_id=%s AND client_message_id=%s AND idempotency_key=%s""",
                (OWNER_A, request["client_message_id"], request["idempotency_key"])).fetchone()
        answer = copy.deepcopy(source)
        answer.update(
            answer_id=attempt["reserved_answer_id"],
            conversation_id=receipt["resolved_conversation_id"],
            message_id=uid(),
            request_id=attempt["attempt_request_id"],
            trace_id=attempt["attempt_trace_id"],
        )
        check_wire(answer, "answer")
        finalize_t3(conn, OWNER_A, attempt["id"], answer, "Synthetic assistant message")
    return answer


async def wait_conversations(page, n: int):
    await expect(page.locator('[data-testid^="conversation-"]')).to_have_count(n, timeout=10000)


async def send_ui(page, question: str):
    await page.get_by_test_id("history-question").fill(question)
    await page.get_by_test_id("history-send").click()
    await expect(page.get_by_text(question, exact=True).first).to_be_visible(timeout=10000)


async def load_until(page, conversation_id: str):
    # On refresh, the React effect fetches the first page asynchronously.
    # Absence of a 'more' button BEFORE the first page is loaded proves nothing.
    await expect(page.locator('[data-testid^="conversation-"]').first).to_be_visible(timeout=15000)
    for _ in range(16):
        if await page.get_by_test_id("conversation-" + conversation_id).count():
            return
        more = page.get_by_test_id("more-conversations")
        if not await more.count():
            raise AssertionError("Conversation not found after last owner-scoped page")
        await expect(more).to_be_enabled(timeout=10000)
        before = await page.locator('[data-testid^="conversation-"]').count()
        await more.click()
        await page.wait_for_function(
            "n => document.querySelectorAll('[data-testid^=conversation-]').length > n",
            arg=before, timeout=10000)
    raise AssertionError("Conversation pagination exceeded fixture bound")

async def run():
    assert_ci()
    folder = Path(os.environ["UI_HISTORY_SCREENSHOTS"])
    folder.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        a = await context.new_page()
        await a.goto("http://127.0.0.1:3000/history")
        await expect(a.get_by_test_id("history-state")).to_contain_text("هنوز مکالمه", timeout=15000)

        # Create two actual DB conversations, send, switch, then reload from DB.
        await a.get_by_test_id("create-conversation").click()
        await wait_conversations(a, 1)
        c1 = (await a.locator('[data-testid^="conversation-"]').first.get_attribute("data-testid")).split("conversation-", 1)[1]
        await send_ui(a, QUESTIONS["one"])
        await expect(a.get_by_text("پیام ثبت شد؛ پاسخ‌گویی موتور هنوز فعال نیست.").first).to_be_visible()

        await a.get_by_test_id("create-conversation").click()
        await wait_conversations(a, 2)
        ids = [x.split("conversation-", 1)[1] for x in
               await a.locator('[data-testid^="conversation-"]').evaluate_all(
                   "(nodes) => nodes.map(n => n.getAttribute('data-testid'))")]
        c2 = next(id for id in ids if id != c1)
        await send_ui(a, QUESTIONS["two"])
        await a.get_by_test_id("conversation-" + c1).click()
        await expect(a.get_by_text(QUESTIONS["one"], exact=True)).to_be_visible()
        await a.reload()
        await expect(a.get_by_test_id("conversation-" + c2)).to_be_visible(timeout=12000)
        await expect(a.get_by_text(QUESTIONS["two"], exact=True)).to_be_visible()
        await a.get_by_test_id("conversation-" + c1).click()
        await expect(a.get_by_text(QUESTIONS["one"], exact=True)).to_be_visible()
        print("E2E: two conversations, navigation and DB-backed refresh PASS")

        # Cursor pagination (server uses limit 2) and no duplicated UI rows.
        await a.get_by_test_id("create-conversation").click()
        await wait_conversations(a, 2)
        for _ in range(2):
            await a.get_by_test_id("create-conversation").click()
            await wait_conversations(a, 2)
        await load_until(a, c1)
        ids_all = await a.locator('[data-testid^="conversation-"]').evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('data-testid'))")
        assert len(ids_all) == len(set(ids_all)) == 5, "duplicate/list pagination"
        await a.get_by_test_id("conversation-" + c1).click()
        for i in range(4):
            await send_ui(a, f"پیام صفحه‌بندی {i}")
        await load_until(a, c1)
        await a.get_by_test_id("conversation-" + c1).click()
        for _ in range(8):
            more = a.get_by_test_id("more-messages")
            if not await more.count():
                break
            await expect(more).to_be_enabled(timeout=10000)
            before = await a.locator('[data-testid^="history-message-"]').count()
            await more.click()
            await a.wait_for_function(
                "n => document.querySelectorAll('[data-testid^=history-message-]').length > n",
                arg=before, timeout=10000)
        rendered = await a.locator('[data-testid^="history-message-"]').evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('data-testid'))")
        assert len(rendered) == len(set(rendered)) >= 5, "message pagination and dedupe"
        print("E2E: conversations/messages pagination and deduplication PASS")

        # Deliver a successfully committed POST to API, then discard only the
        # browser-visible response: a controlled *unknown* network result.
        captured = []
        drop_first = True

        async def drop_response(route):
            nonlocal drop_first
            captured.append(route.request.post_data_json)
            if drop_first:
                drop_first = False
                upstream = await route.fetch()
                assert upstream.status == 202
                await route.abort("failed")
            else:
                await route.continue_()

        await a.route("**/api/history/messages", drop_response)
        await send_ui(a, QUESTIONS["replay"])
        await expect(a.get_by_text("نتیجهٔ شبکه نامعلوم است؛ ثبت پیام تأیید نشده.")).to_be_visible()
        assert receipt_count(captured[0]["client_message_id"]) == 1
        await a.get_by_test_id("retry-send").click()
        await expect(a.get_by_text("پیام ثبت شد؛ پاسخ‌گویی موتور هنوز فعال نیست.").first).to_be_visible()
        assert len(captured) == 2 and captured[0] == captured[1], "replay payload changed"
        assert receipt_count(captured[0]["client_message_id"]) == 1, "duplicate DB receipt"
        await a.unroute("**/api/history/messages", drop_response)

        drop_first = True
        captured.clear()
        await a.route("**/api/history/messages", drop_response)
        await send_ui(a, QUESTIONS["status"])
        await expect(a.get_by_text("نتیجهٔ شبکه نامعلوم است؛ ثبت پیام تأیید نشده.")).to_be_visible()
        await a.get_by_test_id("recover-status").click()
        await expect(a.get_by_text("پیام ثبت شد؛ پاسخ‌گویی موتور هنوز فعال نیست.").first).to_be_visible()
        assert len(captured) == 1 and receipt_count(captured[0]["client_message_id"]) == 1
        await a.unroute("**/api/history/messages", drop_response)
        print("E2E: lost response, immutable replay, status recovery/no duplicate PASS")

        # A delayed request is assigned to its origin, never to currently
        # selected conversation B. Controlled asyncio Events, not a sleep race.
        await load_until(a, c2)
        await load_until(a, c1)  # older cursor page must exist before selecting A
        entered = asyncio.Event()
        released = asyncio.Event()
        hold_once = True

        async def hold_a(route):
            nonlocal hold_once
            if hold_once and "/conversations/" + c1 + "/messages" in route.request.url:
                hold_once = False
                entered.set()
                await released.wait()
            await route.continue_()

        await a.route("**/api/history/conversations/*/messages?**", hold_a)
        await a.get_by_test_id("conversation-" + c2).click()
        await a.get_by_test_id("conversation-" + c1).click()
        await asyncio.wait_for(entered.wait(), timeout=5)
        await a.get_by_test_id("conversation-" + c2).click()
        await expect(a.get_by_text(QUESTIONS["two"], exact=True)).to_be_visible()
        released.set()
        await a.get_by_test_id("history-question").fill("پرسش در گفتگوی دوم")
        await expect(a.get_by_text(QUESTIONS["one"], exact=True)).to_have_count(0)
        await a.unroute("**/api/history/conversations/*/messages?**", hold_a)
        print("E2E: delayed response scoped to originating chat PASS")

        # Fixture T2/T3 ONLY inside test code: API never exposes seed routes.
        captured.clear()
        seed_committed = asyncio.Event()

        async def capture_seed(route):
            captured.append(route.request.post_data_json)
            # A browser-visible optimistic bubble is NOT proof of a DB commit.
            # Fetch and deliver the real HTTP response before fixture T2 starts.
            response = await route.fetch()
            assert response.status == 202, "seed T1 must really commit first"
            await route.fulfill(response=response)
            seed_committed.set()

        await a.route("**/api/history/messages", capture_seed)
        await send_ui(a, QUESTIONS["seed"])
        await asyncio.wait_for(seed_committed.wait(), timeout=10)
        await a.unroute("**/api/history/messages", capture_seed)
        assert len(captured) == 1
        assert receipt_count(captured[0]["client_message_id"]) == 1
        seed_answer(captured[0])
        await a.reload()
        await load_until(a, c2)
        await a.get_by_test_id("conversation-" + c2).click()
        for _ in range(20):
            if await a.get_by_text("پاسخ از تاریخچهٔ معتبر API دریافت شده است.").count():
                break
            more = a.get_by_test_id("more-messages")
            if not await more.count():
                break
            await expect(more).to_be_enabled(timeout=10000)
            before = await a.locator('[data-testid^="history-message-"]').count()
            await more.click()
            await a.wait_for_function(
                "n => document.querySelectorAll('[data-testid^=history-message-]').length > n",
                arg=before, timeout=10000)
        await expect(a.get_by_text("پاسخ از تاریخچهٔ معتبر API دریافت شده است.")).to_be_visible()
        await expect(a.get_by_text("پاسخ‌گویی موتور هنوز فعال نیست.", exact=False).first).to_be_visible()
        await a.screenshot(path=str(folder/"history-desktop.png"),full_page=True)
        print("E2E: fixture-only T2/T3, API-only Answer presentation PASS")

        # Independent fixed process actor B: its data is not actor A's.
        other = await browser.new_context(viewport={"width": 1280, "height": 800})
        b = await other.new_page()
        await b.goto("http://127.0.0.1:3001/history")
        await expect(b.get_by_test_id("history-state")).to_contain_text("هنوز مکالمه")
        await b.get_by_test_id("create-conversation").click()
        await wait_conversations(b, 1)
        forbidden = await b.request.get("http://127.0.0.1:3001/api/history/conversations/"+c1+"/messages")
        assert forbidden.status == 404, "cross-actor leak"
        assert await b.get_by_test_id("conversation-" + c1).count() == 0
        print("E2E: two isolated fixture actors and 404 for cross-actor access PASS")

        # The third loopback process has NO dependency override.
        noauth = await browser.new_context(viewport={"width": 390, "height": 844},is_mobile=True)
        denied = await noauth.new_page()
        await denied.goto("http://127.0.0.1:3002/history")
        await expect(denied.get_by_test_id("history-state")).to_contain_text("ورود معتبر لازم")
        assert await denied.locator('[data-testid^="conversation-"]').count() == 0
        assert await denied.get_by_text("پاسخ نمونه").count() == 0
        print("E2E: normal API identity denies 401; no Mock fallback PASS")

        mobile = await browser.new_context(viewport={"width": 390, "height": 844},is_mobile=True,
                                            device_scale_factor=1)
        screen = await mobile.new_page()
        await screen.goto("http://127.0.0.1:3000/history")
        await expect(screen.locator('[data-testid^="conversation-"]').first).to_be_visible()
        await load_until(screen, c2)
        await screen.get_by_test_id("conversation-" + c2).click()
        await expect(screen.get_by_text(QUESTIONS["two"], exact=True).first).to_be_visible()
        await screen.screenshot(path=str(folder/"history-mobile.png"),full_page=True)
        # Explicit API failure: no fallback to synthetic Mock scenario.
        async def force_api_failure(route):
            await route.fulfill(status=503,content_type="application/json",
                                body='{"error":"unavailable"}')
        await screen.route("**/api/history/conversations?**",force_api_failure)
        await screen.get_by_test_id("refresh-history").click()
        await expect(screen.get_by_test_id("history-state")).to_contain_text("خطای دریافت")
        assert await screen.get_by_text("پاسخ نمونه").count() == 0
        print("E2E: mobile screenshot, HTTP 503 without Mock fallback PASS")

        await mobile.close()
        await noauth.close()
        await other.close()
        await context.close()
        await browser.close()
    print("UI-HISTORY-E2E: PASS (desktop + mobile Chromium / temporary PostgreSQL)")


if __name__ == "__main__":
    asyncio.run(run())
