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
from urllib.parse import urlencode

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


def conversation_count(owner: str = OWNER_A) -> int:
    with psycopg.connect(os.environ["API_HISTORY_DSN"], autocommit=True,
                         row_factory=dict_row) as conn:
        with conn.transaction():
            scoped(conn, owner)
            return conn.execute(
                """SELECT count(*) AS n FROM history_l1.conversations
                   WHERE owner_id=%s AND state='active'""",
                (owner,)).fetchone()["n"]


async def wait_conversation_count(expected: int):
    # Poll only the disposable test DB until the server-confirmed Create exists.
    # UI button text/list length before the POST response is NOT that evidence.
    async def check():
        for _ in range(100):
            count = await asyncio.to_thread(conversation_count)
            if count == expected:
                return
            if count > expected:
                raise AssertionError("Unexpected duplicate conversation inserted")
            await asyncio.sleep(0.05)
        raise AssertionError("Missing expected committed conversation")
    await asyncio.wait_for(check(), timeout=10)


def receipt_count(client_id: str, owner: str = OWNER_A) -> int:
    with psycopg.connect(os.environ["API_HISTORY_DSN"], autocommit=True,
                         row_factory=dict_row) as conn:
        with conn.transaction():
            scoped(conn, owner)
            return conn.execute(
                """SELECT count(*) AS n FROM history_l1.send_receipts
                   WHERE owner_id=%s AND client_message_id=%s""",
                (owner, client_id)).fetchone()["n"]



def total_receipts(owner: str = OWNER_A) -> int:
    """Actual owner-scoped DB rows; proves a rejected proxy POST didn't write."""
    with psycopg.connect(os.environ["API_HISTORY_DSN"],autocommit=True,
                         row_factory=dict_row) as conn:
        with conn.transaction():
            scoped(conn,owner)
            return conn.execute(
                "SELECT count(*) AS n FROM history_l1.send_receipts WHERE owner_id=%s",
                (owner,)).fetchone()["n"]


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

async def assert_h1_session_loss(browser, c2: str, mobile: bool, folder: Path):
    """Prove a previous A 200 cannot rehydrate History after any 401.

    Tests *real* Chromium fetch ordering through Playwright-controlled fixture
    responses, against the existing synthetic actor A loopback Next/API process.
    No identity override, user selector or product Auth route is added.
    """
    label = "mobile" if mobile else "desktop"
    context = await browser.new_context(
        viewport={"width": 390, "height": 844} if mobile
        else {"width": 1280, "height": 800}, is_mobile=mobile)
    page = await context.new_page()
    held_started, release_held, held_finished = (
        asyncio.Event(), asyncio.Event(), asyncio.Event())
    try:
        await page.goto("http://127.0.0.1:3000/history")
        menu = page.get_by_role("button", name="بازکردن منوی تاریخچه")
        if mobile:
            await menu.click()
        await load_until(page, c2)
        await page.get_by_test_id("conversation-" + c2).click()
        await expect(page.get_by_text(QUESTIONS["two"], exact=True)).to_be_visible()

        # Two distinct private, unsent drafts in this *same* page's memory.
        draft_thread = "پیش‌نویس محرمانهٔ A برای گفت‌وگو"
        draft_local = "پیش‌نویس محرمانهٔ A برای مکالمهٔ محلی"
        await page.get_by_test_id("history-question").fill(draft_thread)
        if mobile:
            await menu.click()
        await page.get_by_test_id("new-draft").click()
        await page.get_by_test_id("history-question").fill(draft_local)
        if mobile:
            await menu.click()
        await load_until(page, c2)
        await page.get_by_test_id("conversation-" + c2).click()
        await expect(page.get_by_test_id("history-question")).to_have_value(draft_thread)

        # This is a valid 200 produced by the genuine A fixture before loss;
        # delaying its *delivery* doesn't forge a DTO or inject identity.
        held_path = ("conversations/" + c2 + "/messages?limit=2" if mobile
                     else "conversations?limit=2")
        held_url = "http://127.0.0.1:3000/api/history/" + held_path
        real_reply = await page.request.get(held_url)
        assert real_reply.status == 200, "A fixture must own the held success"
        held_body = await real_reply.text()
        assert held_body and held_body.startswith("{")

        async def hold_previous_a_200(route):
            held_started.set()
            try:
                await asyncio.wait_for(release_held.wait(), timeout=15)
                await route.fulfill(status=200, content_type="application/json",
                                    body=held_body)
            finally:
                held_finished.set()

        async def lose_session(route):
            await route.fulfill(status=401, content_type="application/json",
                                body='{"detail":"synthetic fixture session loss"}')

        hold_match = ("**/api/history/conversations/" + c2 + "/messages?**"
                      if mobile else "**/api/history/conversations?**")
        denial_match = ("**/api/history/conversations?**" if mobile
                        else "**/api/history/conversations/" + c2 + "/messages?**")
        await page.route(hold_match, hold_previous_a_200)
        if mobile:
            await menu.click()
            await load_until(page, c2)
            await page.get_by_test_id("conversation-" + c2).click()
        else:
            await page.get_by_test_id("refresh-history").click()
        await asyncio.wait_for(held_started.wait(), timeout=10)

        # The request starting later returns 401 while the older success has
        # explicitly NOT been released. Test both orderings across viewports:
        # desktop holds list/denies thread, mobile holds thread/denies list.
        await page.route(denial_match, lose_session)
        if mobile:
            await menu.click()
            await page.get_by_test_id("refresh-history").click()
        else:
            await page.get_by_test_id("conversation-" + c2).click()

        async def assert_cleared():
            await expect(page.get_by_test_id("history-login-required")).to_be_visible()
            await expect(page.get_by_test_id("history-login-required")).to_contain_text(
                "ورود معتبر")
            await expect(page.get_by_test_id("history-state")).to_contain_text(
                "ورود معتبر لازم")
            await expect(page.locator('[data-testid^="conversation-"]')).to_have_count(0)
            await expect(page.locator('[data-testid^="history-message-"]')).to_have_count(0)
            await expect(page.locator('[data-testid^="pending-"]')).to_have_count(0)
            await expect(page.get_by_test_id("history-question")).to_have_value("")
            await expect(page.get_by_test_id("history-question")).to_be_disabled()
            await expect(page.get_by_test_id("history-send")).to_be_disabled()
            await expect(page.get_by_test_id("new-draft")).to_be_disabled()
            await expect(page.get_by_test_id("refresh-history")).to_be_disabled()
            await expect(page.get_by_text(QUESTIONS["two"], exact=True)).to_have_count(0)
            assert not await page.get_by_text(draft_thread, exact=True).count()
            assert not await page.get_by_text(draft_local, exact=True).count()

        await assert_cleared()
        assert not release_held.is_set(), "the 200 must remain held past 401"

        # Observe the actual late response, not merely its Route callback;
        # two browser animation frames let React commit any stale continuation.
        async with page.expect_response(
            lambda response: response.url.startswith(held_url)
            and response.status == 200, timeout=10000) as late_response:
            release_held.set()
        delivered = await late_response.value
        await delivered.finished()
        await asyncio.wait_for(held_finished.wait(), timeout=10)
        await page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))")
        await assert_cleared()
        await page.screenshot(
            path=str(folder / ("history-h1-session-loss-" + label + ".png")),
            full_page=True)
        print("H1-UI: " + label +
              " fixture A private drafts/list/thread cleared on 401, "
              "older successful response ignored PASS")
    finally:
        release_held.set()
        await context.close()


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
        # Two database conversations with the same stored title need distinct
        # visible navigation markers and full accessible IDs. Never change DB titles.
        first_row = a.get_by_test_id("conversation-" + c1)
        second_row = a.get_by_test_id("conversation-" + c2)
        for conversation_id, row in ((c1, first_row), (c2, second_row)):
            assert "گفت‌وگوی جدید" in (await row.inner_text())
            accessible_name = await row.get_attribute("aria-label")
            assert accessible_name and conversation_id in accessible_name
            await expect(a.get_by_test_id("history-marker-" + conversation_id)).to_be_visible()
        marker_a = await a.get_by_test_id("history-marker-" + c1).inner_text()
        marker_b = await a.get_by_test_id("history-marker-" + c2).inner_text()
        assert marker_a != marker_b, "Same-title navigation rows are indistinguishable"
        assert all(x.startswith(("شناسه:", "پرسش:")) for x in (marker_a, marker_b))
        print("E2E: same-title DB conversations have distinct accessible display-only markers PASS")
        await a.get_by_test_id("conversation-" + c1).click()
        await expect(a.get_by_text(QUESTIONS["one"], exact=True)).to_be_visible()
        await a.reload()
        await expect(a.get_by_test_id("conversation-" + c2)).to_be_visible(timeout=12000)
        await expect(a.get_by_text(QUESTIONS["two"], exact=True)).to_be_visible()
        await a.get_by_test_id("conversation-" + c1).click()
        await expect(a.get_by_text(QUESTIONS["one"], exact=True)).to_be_visible()
        print("E2E: two conversations, navigation and DB-backed refresh PASS")

        # Server-reported DB commits, not an already-present 2-row sidebar,
        # prove that all three extra Create operations finished before paging.
        for expected in (3, 4, 5):
            await a.get_by_test_id("create-conversation").click()
            await wait_conversation_count(expected)
            await expect(a.get_by_test_id("create-conversation")).to_be_enabled(timeout=10000)
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
        # The first page is loaded asynchronously after conversation selection.
        # This question is one of the two earliest messages in this fixture.
        await expect(a.get_by_text(QUESTIONS["seed"], exact=True)).to_be_visible(timeout=10000)
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

        # Fail-closed regression: genuine persisted T1 with a discarded POST
        # response followed by a malformed 200 status must NEVER turn confirmed.
        drop_first = True
        captured.clear()
        await a.route("**/api/history/messages", drop_response)
        await send_ui(a, "آزمون وضعیت نامعتبر و منع تأیید")
        await expect(a.get_by_text("نتیجهٔ شبکه نامعلوم است؛ ثبت پیام تأیید نشده.")).to_be_visible()
        assert captured and receipt_count(captured[0]["client_message_id"]) == 1
        await a.unroute("**/api/history/messages", drop_response)
        pending_id = captured[0]["client_message_id"]
        # Fetch actual persisted T1 status via an independent APIRequestContext
        # (NOT the page route); every forged response starts with valid server data.
        original_status_url = (
            "http://127.0.0.1:3000/api/history/message-requests/status?"
            + urlencode({
                "requested_conversation_id": captured[0]["requested_conversation_id"] or "",
                "client_message_id": pending_id,
                "idempotency_key": captured[0]["idempotency_key"]
            }))
        original_status_response = await a.request.get(original_status_url)
        assert original_status_response.status == 200
        valid_status_body = await original_status_response.json()
        assert valid_status_body["status"] == "persisted"
        malformed = {"mode": "unknown_status"}
        handled = {"event": asyncio.Event()}

        async def corrupt_status(route):
            body = copy.deepcopy(valid_status_body)
            if malformed["mode"] == "unknown_status":
                body["status"] = "forged_confirmed"
            else:
                body["attempt_id"] = "pretend_attempt_from_browser"
            await route.fulfill(status=200,content_type="application/json",
                                body=json.dumps(body,ensure_ascii=False))
            handled["event"].set()

        await a.route("**/api/history/message-requests/status?**", corrupt_status)
        for mode in ("unknown_status", "forged_attempt"):
            malformed["mode"] = mode
            handled["event"] = asyncio.Event()
            await a.get_by_test_id("recover-status").click()
            await asyncio.wait_for(handled["event"].wait(), timeout=10)
            await expect(a.get_by_test_id("history-error")).to_contain_text(
                "پاسخ سرور قابل تأیید نیست")
            await expect(a.get_by_test_id("pending-" + pending_id)).to_contain_text(
                "نتیجهٔ شبکه نامعلوم است")
            assert receipt_count(pending_id) == 1
        await a.unroute("**/api/history/message-requests/status?**", corrupt_status)
        await a.get_by_test_id("recover-status").click()
        # Recovery to a real T1 receipt is not equivalent to its message being
        # present on the currently loaded cursor page. If the pending bubble
        # stays visible, it must say *confirmed persisted*, not unknown.
        # If the page already loaded the message, the exact question is visible.
        pending_after_recovery = a.get_by_test_id("pending-" + pending_id)
        if await pending_after_recovery.count():
            await expect(pending_after_recovery).to_contain_text(
                "پیام ثبت شد؛ پاسخ‌گویی موتور هنوز فعال نیست.")
        else:
            await expect(a.get_by_text("آزمون وضعیت نامعتبر و منع تأیید", exact=True)).to_be_visible()
        await expect(a.get_by_test_id("history-error")).to_have_count(0)
        assert receipt_count(pending_id) == 1
        print("E2E: invalid Status enum/T2 evidence fails closed before real recovery PASS")

        # Real Proxy bytes cap, checked against the disposable DB: 413 and no write.
        before_receipts = total_receipts()
        oversized = await a.request.post("http://127.0.0.1:3000/api/history/messages",
            data="x" * 8193,headers={"content-type":"application/json"})
        assert oversized.status == 413
        assert total_receipts() == before_receipts, "rejected proxy POST wrote to DB"
        print("E2E: 8192-byte application Proxy cap rejects oversized POST PASS")

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
        menu_button = screen.get_by_role("button", name="بازکردن منوی تاریخچه")
        await expect(menu_button).to_be_visible()
        await expect(menu_button).to_have_attribute("aria-expanded", "false")
        await expect(screen.locator(".history-sidebar")).to_be_hidden()
        await expect(screen.get_by_test_id("history-question")).to_be_visible()
        assert await screen.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
            "Mobile History has horizontal overflow")
        compose_box = await screen.locator(".history-compose .composer").bounding_box()
        assert compose_box and compose_box["y"] + compose_box["height"] <= 845, (
            "History composer unavailable in initial mobile viewport")
        await menu_button.click()
        await expect(menu_button).to_have_attribute("aria-expanded", "true")
        dialog = screen.get_by_role("dialog", name="منوی تاریخچه")
        await expect(dialog).to_be_visible()
        mobile_close = dialog.get_by_role("button", name="بستن منوی تاریخچه")
        await expect(mobile_close).to_be_focused()
        await screen.keyboard.press("Shift+Tab")
        await expect(dialog.locator("a").last).to_be_focused()
        await screen.keyboard.press("Tab")
        await expect(mobile_close).to_be_focused()
        await screen.keyboard.press("Escape")
        await expect(dialog).to_have_count(0)
        await expect(menu_button).to_be_focused()
        await expect(menu_button).to_have_attribute("aria-expanded", "false")
        await menu_button.click()
        dialog = screen.get_by_role("dialog", name="منوی تاریخچه")
        await load_until(screen, c2)
        await screen.screenshot(path=str(folder/"history-mobile-menu.png"),full_page=True)
        await dialog.get_by_test_id("conversation-" + c2).click()
        await expect(dialog).to_have_count(0)
        await expect(menu_button).to_be_focused()
        await expect(screen.get_by_text(QUESTIONS["two"], exact=True).first).to_be_visible()
        await expect(screen.get_by_test_id("history-question")).to_be_visible()
        await screen.screenshot(path=str(folder/"history-mobile.png"),full_page=True)
        print("E2E: mobile drawer Escape/Tab/focus/selection and visible composer PASS")
        # Explicit API failure: no fallback to synthetic Mock scenario.
        async def force_api_failure(route):
            await route.fulfill(status=503,content_type="application/json",
                                body='{"error":"unavailable"}')
        await screen.route("**/api/history/conversations?**",force_api_failure)
        await menu_button.click()
        dialog = screen.get_by_role("dialog", name="منوی تاریخچه")
        await dialog.get_by_test_id("refresh-history").click()
        await expect(dialog.get_by_test_id("history-state")).to_contain_text("خطای دریافت")
        assert await screen.get_by_text("پاسخ نمونه").count() == 0
        await dialog.get_by_role("button", name="بستن منوی تاریخچه").click()
        await expect(menu_button).to_be_focused()
        print("E2E: mobile screenshot, HTTP 503 without Mock fallback PASS")

        # Separate fresh desktop/mobile contexts prove an in-flight A success
        # cannot revive private UI after a later, unrelated History 401.
        await assert_h1_session_loss(browser, c2, mobile=False, folder=folder)
        await assert_h1_session_loss(browser, c2, mobile=True, folder=folder)

        await mobile.close()
        await noauth.close()
        await other.close()
        await context.close()
        await browser.close()
    print("UI-HISTORY-E2E: PASS (desktop + mobile Chromium / temporary PostgreSQL)")


if __name__ == "__main__":
    asyncio.run(run())
