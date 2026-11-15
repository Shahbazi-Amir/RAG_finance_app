#!/usr/bin/env python3
"""Real Chromium over Next loopback with intercepted #53 fixed CI fixture.

Four states, same persisted T2 Attempt after Refresh, no second POST, and
Fixture citations cannot appear as LIVE_VERIFIED sources. NO remote staging.
"""
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[4]
CASES = json.loads((ROOT / "packages/contracts/fixtures/product.v1.cases.json")
                   .read_text(encoding="utf-8"))["cases"]
READY = json.loads((ROOT / "tests/phase3/ui/fixtures/"
                    "staging_invited_live_result_ready.example.json")
                   .read_text(encoding="utf-8"))


def product_case(name):
    return next(json.loads(json.dumps(case["document"])) for case in CASES
                if case["case_id"] == name and case["expected_valid"])


def one_case(page, base, case_state):
    calls = {"send": 0, "status": [], "fixture": [], "engine": 0, "body": None}
    conv_id = READY["resolved_conversation_id"]
    msg_id = "msg_invited_fixture"
    expected = {
        "READY": "پاسخ نمونهٔ آزمایشی (نه پاسخ واقعی یا تأییدشده).",
        "PENDING": "نمونهٔ آزمایشی در انتظار نتیجه است.",
        "FAILED": "اجرای نمونهٔ آزمایشی ناموفق بود؛ پاسخی وجود ندارد.",
        "UNKNOWN": "نتیجهٔ نمونهٔ آزمایشی نامعلوم است؛ ارسال مجدد مجاز نیست."
    }

    def correlators(url):
        assert calls["body"] is not None
        q = parse_qs(urlsplit(url).query, keep_blank_values=True)
        keys = ["requested_conversation_id", "client_message_id", "idempotency_key"]
        assert set(q) == set(keys), q
        for key in keys:
            assert q[key] == [calls["body"][key] or ""], (key, q)
        return {key: q[key][0] for key in keys}

    def intercept(route):
        url = route.request.url
        path = urlsplit(url).path
        method = route.request.method
        if path.endswith("/api/history/conversations") and method == "GET":
            response = product_case("valid_paginated_conversations")
            response["page"].update(limit=2, next_cursor=None, has_more=False)
            response["items"] = []
            if calls["send"]:
                row = product_case("valid_conversation")
                row["conversation_id"] = conv_id
                row["owner_user_id"] = response["scope_user_id"]
                row["title"] = "گفت‌وگوی نمونهٔ آزمونی"
                response["items"] = [row]
            route.fulfill(status=200, json=response)
        elif path.endswith("/api/history/messages") and method == "POST":
            calls["send"] += 1
            assert calls["send"] == 1, "SECOND POST ON REFRESH/POLL"
            original = route.request.post_data_json
            assert original["requested_conversation_id"] is None
            calls["body"] = original
            receipt = product_case("valid_send_message_receipt")
            receipt.update(requested_conversation_id=None,
                           resolved_conversation_id=conv_id,
                           client_message_id=original["client_message_id"],
                           idempotency_key=original["idempotency_key"],
                           message_id=msg_id)
            route.fulfill(status=202, json=receipt)
        elif path.endswith("/api/history/conversations/" + conv_id + "/messages"):
            assert method == "GET"
            response = product_case("valid_history_messages_page")
            response.update(conversation_id=conv_id, items=[], answers=[])
            response["page"].update(limit=30, next_cursor=None, has_more=False)
            if calls["send"]:
                user = product_case("valid_user_message")
                user["owner_user_id"] = response["owner_user_id"]
                user["conversation_id"] = conv_id
                user["message_id"] = msg_id
                user["text"] = calls["body"]["question"]
                response["items"] = [user]
            route.fulfill(status=200, json=response)
        elif path.endswith("/api/history/message-requests/status"):
            assert method == "GET"
            calls["status"].append(correlators(url))
            response = product_case("valid_history_status_not_found")
            response.update(
                requested_conversation_id=None,
                client_message_id=calls["body"]["client_message_id"],
                idempotency_key=calls["body"]["idempotency_key"],
                resolved_conversation_id=conv_id,
                message_id=msg_id,
                attempt_id=READY["attempt_id"],
                attempt_request_id=READY["attempt_request_id"],
                attempt_trace_id=READY["attempt_trace_id"],
                reserved_answer_id="ans_invited_fixture",
                status={"FAILED": "failed", "UNKNOWN": "attempt_unknown"}
                    .get(case_state, "attempt_pending"))
            route.fulfill(status=200, json=response)
        elif path.endswith("/api/history/message-requests/engine-status"):
            assert method == "GET"
            correlators(url)
            calls["engine"] += 1
            route.fulfill(status=200, json={
                "kind": "no_dispatch_execution_status",
                "contract_version": "api.no_dispatch_status.v1",
                "request_id": "req_engine_fixture",
                "trace_id": "trace_engine_fixture",
                "attempt_id": READY["attempt_id"],
                "attempt_trace_id": READY["attempt_trace_id"],
                "product_status": {"FAILED": "failed", "UNKNOWN": "attempt_unknown"}
                    .get(case_state, "attempt_pending"),
                "preflight_state": "UNKNOWN",
                "question_sha256_matches": None,
                "top10_count": None,
                "generation_calls": 0,
                "dispatch_performed": False,
                "answer": None
            })
        elif path.endswith("/api/history/message-requests/invited-live-result"):
            assert method == "GET"
            calls["fixture"].append(correlators(url))
            response = json.loads(json.dumps(READY))
            response.update(
                requested_conversation_id=calls["body"]["requested_conversation_id"],
                client_message_id=calls["body"]["client_message_id"],
                idempotency_key=calls["body"]["idempotency_key"],
                result_status=case_state)
            if case_state != "READY":
                response["answer"] = None
                response["retention_expires_at_unix"] = None
            route.fulfill(status=200, json=response)
        else:
            raise AssertionError("UNEXPECTED ROUTE OR METHOD " + method + " " + path)

    page.route("**/api/history/**", intercept)
    page.goto(base + "/ci-fixture-review", wait_until="domcontentloaded")
    expect(page.get_by_test_id("fixture-review-banner")).to_be_visible()
    expect(page.get_by_text("هنوز گفت‌وگویی ثبت نشده است.")).to_be_visible()
    page.get_by_test_id("create-conversation").click()
    page.get_by_test_id("history-question").fill("تست پاسخ و استناد فارسی")
    page.get_by_test_id("history-send").click()
    expect(page.get_by_text(expected[case_state], exact=True)).to_be_visible(timeout=15000)
    assert calls["send"] == 1
    attempt = calls["body"]["client_message_id"]

    def assert_fixture():
        if case_state == "READY":
            expect(page.get_by_test_id("ci-fixture-answer")).to_have_text(READY["answer"]["text"])
            expect(page.get_by_text("fixture:budget-example-001")).to_be_visible()
            expect(page.get_by_text("fixture-cite-budget-01")).to_be_visible()
            expect(page.get_by_text("سند ساختگی آزمون بودجه")).to_be_visible()
            expect(page.get_by_text("استناد Fixture، نه شاهد واقعی")).to_be_visible()
            assert page.get_by_role("link", name="بازکردن پیوند معتبر منبع").count() == 0
            assert page.get_by_test_id("ci-fixture-result").locator("a").count() == 0
        else:
            assert page.get_by_test_id("ci-fixture-answer").count() == 0
            assert page.get_by_text(READY["answer"]["text"]).count() == 0

    assert_fixture()
    before_status = len(calls["status"])
    before_fixture = len(calls["fixture"])
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_test_id("attempt-" + attempt)).to_be_visible(timeout=15000)
    expect(page.get_by_text(expected[case_state], exact=True)).to_be_visible(timeout=15000)
    assert_fixture()
    assert calls["send"] == 1
    assert len(calls["status"]) > before_status
    assert len(calls["fixture"]) > before_fixture
    assert len(calls["status"]) >= 2 and len(calls["fixture"]) >= 2
    assert all(q == calls["status"][0] for q in calls["status"])
    assert all(q == calls["fixture"][0] for q in calls["fixture"])
    assert calls["fixture"][0] == calls["status"][0]
    assert page.get_by_test_id("ci-fixture-result").count() == 1
    print("UI_FIXTURE_" + case_state + "_CHROMIUM_SAME_ATTEMPT_GET_ONLY_1_POST_PASS",
          flush=True)


def main():
    base = os.environ.get("UI_CHAT_L1_BASE_URL", "http://127.0.0.1:3000")
    url = urlsplit(base)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or url.port != 3000:
        raise RuntimeError("FIXTURE_REVIEW_ONLY_127_0_0_1_3000")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for state in ("READY", "PENDING", "FAILED", "UNKNOWN"):
                context = browser.new_context(viewport={"width": 1280, "height": 800})
                try:
                    one_case(context.new_page(), base, state)
                finally:
                    context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
