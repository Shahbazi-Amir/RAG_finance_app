#!/usr/bin/env python3
"""Real Chromium → production Next → actual History BFF baseline (NO stubs).

This is a *negative* baseline on the exact integrated source, not an A/B
acceptance. There is deliberately NO route.fulfill(), route.fetch(),
request interception, injected cookie, owner header, or synthetic API.
When signed History is absent, the real GET must fail closed with 503.
"""
import asyncio
import os
from urllib.parse import urlsplit

from playwright.async_api import async_playwright, expect

ORIGIN = "http://127.0.0.1:3100"


async def baseline(browser, width, height):
    context = await browser.new_context(viewport={"width": width, "height": height})
    try:
        page = await context.new_page()
        events = []
        page.on("request", lambda request: events.append(
            (request.method, request.url)) if "/api/history/" in request.url else None)
        async with page.expect_response(
            lambda response: response.request.method == "GET"
            and "/api/history/conversations?limit=2" in response.url,
            timeout=20000,
        ) as pending:
            landing = await page.goto(ORIGIN + "/history", wait_until="domcontentloaded")
        assert landing is not None and landing.status == 200
        history_response = await pending.value
        assert history_response.status == 503, (
            "BASELINE_CHANGED_RECHECK_REAL_SIGNED_HISTORY", history_response.status)
        await expect(page.get_by_test_id("history-state")).to_contain_text(
            "تاریخچه در دسترس نیست", timeout=15000)
        await expect(page.get_by_test_id("history-owner-revalidation-required")
                     ).to_be_visible()
        await expect(page.get_by_test_id("history-send")).to_be_disabled()
        await expect(page.get_by_test_id("history-question")).to_be_disabled()
        await expect(page.get_by_test_id("app-runtime-capability")).to_contain_text(
            "برنامه در حالت بدون موتور", timeout=15000)
        await expect(page.get_by_test_id("app-runtime-capability")).to_contain_text(
            "تاریخچه فقط پس از ورود و اتصال امن", timeout=15000)
        assert await page.locator('[data-testid^="history-message-"]').count() == 0
        assert await page.locator('[data-testid^="conversation-"]').count() == 0
        assert not any(method == "POST" for method, _ in events)

        # Browser sends *one explicit adversarial POST* through the actual BFF,
        # with no synthetic session or actor. This must not allocate T1/T2.
        denied = await page.evaluate("""async () => {
          const response = await fetch('/api/history/messages', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type':'application/json'},
            body: '{}'
          });
          return {status:response.status, body:await response.json()};
        }""")
        assert denied == {"status": 503, "body": {"error": "ENGINE_NOT_AVAILABLE"}}
        assert len([e for e in events if e[0] == "POST"]) == 1
        # The first actual login boundary on this unconfigured app-only
        # profile is HTTPS ingress/mTLS proxy proof, BEFORE any IdP session.
        login = await page.goto(ORIGIN + "/login", wait_until="domcontentloaded")
        assert login is not None and login.status == 503, (
            "UNSIGNED_PLAINTEXT_LOGIN_MUST_NOT_ISSUE_COOKIE",
            login.status if login else None)
        assert not any(c["name"].startswith("__Host-rag-")
                       for c in await context.cookies(ORIGIN))
        print(f"UI_REAL_NEXT_LOGIN_HTTPS_INGRESS_MISSING_503_{width}_PASS", flush=True)
        print(f"UI_REAL_NEXT_UNAUTHENTICATED_HISTORY_503_NO_SEND_{width}_PASS", flush=True)
    finally:
        await context.close()


async def main():
    if os.environ.get("CI") != "true" or os.environ.get("PHASE3_APP_MODE") != "APP_ONLY":
        raise RuntimeError("REAL_APP_ONLY_BASELINE_REQUIRES_CI_AND_NO_ENGINE")
    target = urlsplit(os.environ.get("UI_BASELINE_ORIGIN", ORIGIN))
    if target.geturl() != ORIGIN:
        raise RuntimeError("BASELINE_ORIGIN_MUST_BE_ISOLATED_127_0_0_1_3100")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await baseline(browser, 1280, 800)
            await baseline(browser, 390, 844)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
