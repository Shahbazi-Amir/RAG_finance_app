#!/usr/bin/env python3
"""UI-CHAT-013 L1-only real Chromium check with *test-only* route interception.

This is NOT Product API, signed BFF, live Runner, account isolation, or Gate
evidence. Never run this on a public staging service or assert live citations.
Start the Next build on isolated 127.0.0.1:3000 before invoking this script.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[4]
REGISTRY = json.loads((ROOT / "packages/contracts/fixtures/product.v1.cases.json").
                      read_text(encoding="utf-8"))["cases"]

def fixture(name):
    return next(json.loads(json.dumps(c["document"])) for c in REGISTRY
                if c["case_id"] == name and c["expected_valid"])

def main():
    base = os.getenv("UI_CHAT_L1_BASE_URL", "http://127.0.0.1:3000")
    url = urlsplit(base)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or url.port != 3000:
        raise RuntimeError("UI_CHAT_L1_ONLY_LOOPBACK_HTTP_PORT_3000")
    state = {"posts": 0, "status_reads": 0, "engine_reads": 0,
             "logged_in": True, "request": None,
             "source_reads": 0, "source_mode": "valid",
             "owner_mode": "original", "status_mode": "valid", "engine_mode": "valid"}
    conversation_id = "conv_uichat_013"
    user_message = "msg_uichat_013"

    def check_original_query(url):
        assert state["request"] is not None
        fields = parse_qs(urlsplit(url).query, keep_blank_values=True)
        assert set(fields) == {
            "requested_conversation_id", "client_message_id", "idempotency_key"}
        for key in fields:
            assert len(fields[key]) == 1
            assert fields[key][0] == (state["request"][key] or "")

    def intercept(route):
        path = urlsplit(route.request.url).path
        method = route.request.method
        if not state["logged_in"]:
            route.fulfill(status=401, content_type="application/json",
                          body='{"error":"AUTH_REQUIRED"}')
            return
        if path.endswith("/api/history/conversations") and method == "GET":
            body = fixture("valid_paginated_conversations")
            body["page"]["limit"] = 2
            body["page"]["has_more"] = False
            body["page"]["next_cursor"] = None
            body["items"] = []
            if state["posts"]:
                conv = fixture("valid_conversation")
                conv["conversation_id"] = conversation_id
                conv["title"] = "گفت‌وگوی تست فارسی"
                conv["owner_user_id"] = body["scope_user_id"]
                body["items"] = [conv]
            if state["owner_mode"] == "changed":
                body["scope_user_id"] = "usr_owner_B_403_3"
                body["items"] = []
            route.fulfill(status=200, json=body)
        elif path.endswith("/api/history/messages") and method == "POST":
            state["posts"] += 1
            if state["posts"] > 1:
                raise AssertionError("BROWSER_REPOST_IS_FORBIDDEN")
            original = route.request.post_data_json
            assert original["requested_conversation_id"] is None
            state["request"] = original
            receipt = fixture("valid_send_message_receipt")
            receipt["requested_conversation_id"] = None
            receipt["resolved_conversation_id"] = conversation_id
            receipt["client_message_id"] = original["client_message_id"]
            receipt["idempotency_key"] = original["idempotency_key"]
            receipt["message_id"] = user_message
            route.fulfill(status=202, json=receipt)
        elif "/api/history/conversations/" in path and path.endswith("/messages") and method == "GET":
            body = fixture("valid_history_messages_page")
            body["conversation_id"] = conversation_id
            body["page"]["limit"] = 30
            body["page"]["has_more"] = False
            body["page"]["next_cursor"] = None
            body["items"] = []
            body["answers"] = []
            if state["posts"]:
                user = fixture("valid_user_message")
                user["conversation_id"] = conversation_id
                user["owner_user_id"] = body["owner_user_id"]
                user["message_id"] = user_message
                user["text"] = state["request"]["question"]
                body["items"] = [user]
            route.fulfill(status=200, json=body)
        elif path.endswith("/api/history/message-requests/status") and method == "GET":
            check_original_query(route.request.url)
            state["status_reads"] += 1
            original = state["request"]
            assert original
            status = fixture("valid_history_status_not_found")
            status["requested_conversation_id"] = original["requested_conversation_id"]
            status["client_message_id"] = original["client_message_id"]
            status["idempotency_key"] = original["idempotency_key"]
            status["resolved_conversation_id"] = conversation_id
            status["message_id"] = user_message
            status["attempt_id"] = "a" * 32
            status["attempt_request_id"] = "req_attempt_uichat_013"
            status["attempt_trace_id"] = "b" * 32
            status["reserved_answer_id"] = "ans_uichat_013"
            status["status"] = "attempt_pending"
            if state["status_mode"] == "invalid":
                status["unexpected_debug"] = "not-a-contract-field"
            route.fulfill(status=200, json=status)
        elif path.endswith("/api/history/message-requests/engine-status") and method == "GET":
            check_original_query(route.request.url)
            state["engine_reads"] += 1
            original = state["request"]
            assert original
            # A separate API #53 *technical* document: not product Answer,
            # never a live Runner claim or a Citation.
            if state["engine_mode"] == "invalid":
                route.fulfill(status=200, json={"kind": "forged_extra", "answer": "fake"})
                return
            route.fulfill(status=200, json={
                "kind": "no_dispatch_execution_status",
                "contract_version": "api.no_dispatch_status.v1",
                "request_id": "req_engine_status",
                "trace_id": "trace_engine_status",
                "attempt_id": "a" * 32,
                "attempt_trace_id": "b" * 32,
                "product_status": "attempt_pending",
                "preflight_state": "CONTEXT_READY",
                "question_sha256_matches": True,
                "top10_count": 10,
                "generation_calls": 0,
                "dispatch_performed": False,
                "answer": None
            })
        elif path.endswith("/api/history/message-requests/retrieved-sources") and method == "GET":
            check_original_query(route.request.url)
            state["source_reads"] += 1
            rows = [{"position": index, "chunk_id": f"observed_chunk_{index:02}",
                     "source_id": f"observed_source_{index:02}",
                     "chunk_match": "PASS", "source_validation": "UNVERIFIED",
                     "locator_validation": "PENDING_STRUCTURE", "verified_locators": []}
                    for index in range(1, 11)]
            mode = state["source_mode"]
            if mode == "missing":
                route.fulfill(status=404, content_type="application/json",
                              body='{"error":"NOT_FOUND"}')
                return
            if mode == "invalid":
                rows[0]["verified_locators"] = [{"url": "https://example.org/unapproved"}]
            if mode == "xss":
                rows[0]["chunk_id"] = "<script>window.__injected=1</script>"
                rows[0]["source_id"] = "<img src=x onerror=alert(1)>"
            if mode in ("NOT_AVAILABLE", "EVIDENCE_INVALID", "EVIDENCE_NOT_AVAILABLE"):
                rows = []
            route.fulfill(status=200, json={
                "kind": "retrieved_sources",
                "contract_version": "api.retrieved_sources.v1",
                "attempt_id": ("c" if mode == "wrong_attempt" else "a") * 32,
                "attempt_trace_id": "b" * 32,
                "retrieval_state": mode if mode in ("NOT_AVAILABLE", "EVIDENCE_INVALID", "EVIDENCE_NOT_AVAILABLE") else "PARTIAL_UNVERIFIED",
                "engine_sha256": "93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d",
                "chunks_sha256": "3891c4ecad9332ba753cd605bbccd99da9d063f64934a30ee39e495349cffb50",
                "generation_calls": None if mode == "NOT_AVAILABLE" else 0, "rows": rows
            })
        else:
            route.fulfill(status=404, content_type="application/json",
                          body='{"error":"NOT_FOUND"}')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.route("**/api/history/**", intercept)
            page.goto(base, wait_until="domcontentloaded")
            expect(page.get_by_text("هنوز گفت‌وگویی ثبت نشده است.")).to_be_visible()
            page.get_by_test_id("create-conversation").click()
            page.get_by_test_id("history-question").fill("پرسش فارسی دربارهٔ نرخ بهره")
            page.get_by_test_id("history-send").click()
            expect(page.get_by_text("در حال پردازش؛ وضعیت از API دریافت شده است.")).to_be_visible(
                timeout=15000)
            expect(page.get_by_text(
                "بازیابی شواهد کامل شد؛ تولید پاسخ انجام نشده است.")).to_be_visible()
            section = page.get_by_test_id("retrieved-sources-observed")
            expect(section).to_contain_text("observed_chunk_01")
            expect(section).to_contain_text("observed_source_10")
            assert section.locator("li").count() == 10
            assert section.locator("a").count() == 0
            assert page.get_by_test_id("retrieval-evidence-list").count() == 0
            assert state["posts"] == 1
            # Reload MUST never invoke POST: same original client IDs/status GET.
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_test_id("attempt-" + state["request"]["client_message_id"])).to_be_visible(
                timeout=15000)
            expect(page.get_by_text("در حال پردازش؛ وضعیت از API دریافت شده است.")).to_be_visible()
            expect(page.get_by_text(
                "بازیابی شواهد کامل شد؛ تولید پاسخ انجام نشده است.")).to_be_visible()
            section = page.get_by_test_id("retrieved-sources-observed")
            expect(section).to_contain_text("observed_chunk_01")
            expect(section).to_contain_text("observed_source_10")
            assert section.locator("li").count() == 10
            assert section.locator("a").count() == 0
            assert page.get_by_test_id("retrieval-evidence-list").count() == 0
            assert state["posts"] == 1 and state["status_reads"] >= 2
            assert state["engine_reads"] >= 2
            assert state["source_reads"] >= 2
            # Mobile view: focus visibility, expanded navigation state and RTL.
            page.set_viewport_size({"width": 390, "height": 844})
            menu = page.get_by_role("button", name="بازکردن فهرست گفت‌وگوها")
            expect(menu).to_be_visible()
            menu.focus()
            assert menu.evaluate("(el) => getComputedStyle(el).outlineStyle") != "none"
            menu.click()
            expect(menu).to_have_attribute("aria-expanded", "true")
            expect(page.locator(".history-mobile-close")).to_be_focused()
            page.keyboard.press("Escape")
            expect(menu).to_have_attribute("aria-expanded", "false")
            expect(menu).to_be_focused()
            menu.click()
            expect(menu).to_have_attribute("aria-expanded", "true")
            expect(page.get_by_role("dialog", name="فهرست گفتگوها")).to_be_visible()
            page.locator(".history-mobile-close").click()
            expect(menu).to_have_attribute("aria-expanded", "false")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            screenshots=os.getenv("UI_GATE3_SCREENSHOT_DIR")
            if screenshots:
                directory=Path(screenshots)
                directory.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(directory/"synthetic_product_source_mobile_390x844.png"))
            # A later malformed receipt must clear the previously shown rows.
            state["source_mode"] = "invalid"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_test_id("retrieved-sources-unavailable")).to_be_visible()
            assert page.get_by_test_id("retrieved-sources-observed").count() == 0
            state["source_mode"] = "wrong_attempt"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_test_id("retrieved-sources-unavailable")).to_be_visible()
            assert page.get_by_test_id("retrieved-sources-observed").count() == 0
            state["source_mode"] = "xss"
            page.get_by_test_id("recover-status").click()
            source_panel=page.get_by_test_id("retrieved-sources-observed")
            expect(source_panel).to_contain_text("<script>window.__injected=1</script>")
            expect(source_panel).to_contain_text("<img src=x onerror=alert(1)>")
            assert source_panel.locator("script,img,svg,a").count() == 0
            assert page.evaluate("window.__injected === undefined")
            for mode in ("NOT_AVAILABLE", "EVIDENCE_INVALID", "EVIDENCE_NOT_AVAILABLE"):
                state["source_mode"] = mode
                page.get_by_test_id("recover-status").click()
                expect(page.get_by_test_id("retrieved-sources-empty")).to_be_visible()
                assert page.get_by_test_id("retrieved-sources-observed").count() == 0
            state["source_mode"] = "missing"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_test_id("retrieved-sources-pending")).to_be_visible()
            state["source_mode"] = "valid"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_test_id("retrieved-sources-observed")).to_be_visible()
            assert state["posts"] == 1
            expect(page.locator("nav.history-list")).to_contain_text("گفت‌وگوی تست فارسی")
            # A malformed Product Status must clear previously displayed
            # evidence, not retain stale observations from a past GET.
            state["status_mode"] = "invalid"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_text("خواندن وضعیت ناموفق بود؛ نتیجه نامعلوم است.")).to_be_visible()
            assert page.get_by_test_id("retrieved-sources-observed").count() == 0
            state["status_mode"] = "valid"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_test_id("retrieved-sources-observed")).to_be_visible()
            # Bad technical status cannot keep an old CONTEXT_READY display.
            state["engine_mode"] = "invalid"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_text("وضعیت فنی جداگانه در دسترس نیست؛ فقط وضعیت اصلی پیگیری می‌شود.")).to_be_visible()
            assert page.get_by_text("بازیابی شواهد کامل شد؛ تولید پاسخ انجام نشده است.").count() == 0
            state["engine_mode"] = "valid"
            page.get_by_test_id("recover-status").click()
            expect(page.get_by_text("بازیابی شواهد کامل شد؛ تولید پاسخ انجام نشده است.")).to_be_visible()
            # A different valid owner in a separately signed list response
            # must clear the former owner's message/Attempt/cache before display.
            state["owner_mode"] = "changed"
            # Refresh is in the responsive drawer: open it before clicking.
            menu.click()
            expect(page.get_by_role("dialog", name="فهرست گفتگوها")).to_be_visible()
            page.get_by_test_id("refresh-history").click()
            expect(page.get_by_test_id("history-login-required")).to_be_visible()
            assert page.locator("nav.history-list button").count() == 0
            assert page.get_by_test_id("retrieved-sources-observed").count() == 0
            assert page.evaluate(
                "() => sessionStorage.getItem('rag-finance-attempt-correlation-v1')") is None
            assert state["posts"] == 1
            # A second tab, on a new validated owner-B response, never
            # inherits the former tab's A Attempt or captured source rows.
            tab_b = context.new_page()
            tab_b.route("**/api/history/**", intercept)
            tab_b.goto(base, wait_until="domcontentloaded")
            expect(tab_b.get_by_text("هنوز گفت‌وگویی ثبت نشده است.")).to_be_visible()
            assert tab_b.get_by_test_id("retrieved-sources-observed").count() == 0
            assert tab_b.evaluate(
                "() => sessionStorage.getItem('rag-finance-attempt-correlation-v1')") is None
            tab_b.close()
            state["owner_mode"] = "original"
            # Server 401 still purges even on a fresh page.
            state["logged_in"] = False
            # Refresh invokes authenticated GET, even if background polling has
            # already observed the 401 and disabled the in-page Refresh button.
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_test_id("history-login-required")).to_be_visible()
            assert page.locator("nav.history-list button").count() == 0
            assert page.evaluate(
                "() => sessionStorage.getItem('rag-finance-attempt-correlation-v1')") is None
            account_page = context.new_page()
            account_page.goto(base + "/account", wait_until="domcontentloaded")
            expect(account_page.get_by_role("heading", name="حساب و حریم خصوصی")).to_be_visible()
            expect(account_page.get_by_text("امکان درخواست حذف از این رابط هنوز فعال نیست.")).to_be_visible()
            assert account_page.locator('form[action*="delete"]').count() == 0
            assert account_page.locator('form[action*="feedback"]').count() == 0
            account_page.close()
            print("UI_CHAT_L1_BROWSER_POST62_OWNER_MISMATCH_ESCAPE_ACCOUNT_401_PASS")
            context.close()
        finally:
            browser.close()

if __name__ == "__main__":
    main()
