"""Real Chromium HTTPS negative-only Next BFF smoke.

This deliberately does NOT claim Product Login/Logout/A-B History acceptance:
API #48 private Bootstrap is a separate unmerged CI dependency, and the
Product ACTIVE revoke + authenticated History endpoint do not exist.
"""
import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright, expect

ORIGIN = "https://127.0.0.1:3443"


async def check(browser, mobile, images):
    name = "mobile" if mobile else "desktop"
    ctx = await browser.new_context(
        viewport={"width": 390, "height": 844} if mobile
        else {"width": 1280, "height": 800},
        is_mobile=mobile, ignore_https_errors=True, device_scale_factor=1)
    try:
        page = await ctx.new_page()
        await page.goto(ORIGIN + "/login")
        await expect(page.get_by_test_id("login-submit")).to_be_visible()
        cookies = await ctx.cookies(ORIGIN)
        initiators = [c for c in cookies if c["name"] == "__Host-rag-login-init"]
        assert len(initiators) == 1
        assert initiators[0]["secure"] and initiators[0]["httpOnly"]
        assert initiators[0]["sameSite"] == "Lax"
        assert not await page.locator('[data-testid^="history-message-"]').count()

        # Real browser form submission (not an injected fetch). The strict
        # login-page CSP intentionally forbids fetch but permits self forms.
        await page.locator('input[name="csrf"]').fill("wrong-value")
        async with page.expect_response(
            lambda response: response.url.endswith("/api/auth/login")
            and response.request.method == "POST") as awaited:
            await page.get_by_test_id("login-submit").click()
        bad = (await awaited.value).status
        assert bad == 403, ("LOGIN_CSRF_DENY", bad)
        print("UIA010_" + name.upper() + "_LOGIN_CSRF_403_PASS", flush=True)

        # A callback without a correct one-use state is rejected by Next
        # BEFORE any possible Code exchange.
        await page.goto(ORIGIN + "/api/auth/callback?code=synthetic&state=bad")
        await expect(page.get_by_test_id("login-submit")).to_be_visible()
        assert "reason=auth_failed" in page.url
        assert not any(c["name"] == "__Host-rag-session" for c in
                       await ctx.cookies(ORIGIN))
        print("UIA010_" + name.upper() + "_FOREIGN_CALLBACK_NO_COOKIE_PASS", flush=True)

        # Forged opaque-looking browser handle has no privileged meaning.
        await ctx.add_cookies([{
            "name": "__Host-rag-session",
            "value": "T" * 43,
            "url": ORIGIN + "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }])
        # Use the actual browser navigation/form channel under strict CSP.
        await page.goto(ORIGIN + "/login")
        await page.locator("form").evaluate(
            """form => {form.action='/api/auth/logout';
               form.querySelector('input[name=csrf]').value='wrong-value';}""")
        async with page.expect_response(
            lambda response: response.url.endswith("/api/auth/logout")
            and response.request.method == "POST") as awaited_logout:
            await page.get_by_test_id("login-submit").click()
        bad_logout = (await awaited_logout.value).status
        assert bad_logout == 403, ("LOGOUT_CSRF_DENY", bad_logout)
        print("UIA010_" + name.upper() + "_LOGOUT_CSRF_403_PASS", flush=True)
        await ctx.clear_cookies()

        # Missing browser session must not fall through to the old actor
        # selector/CI-only HTTP History proxy.
        await page.goto(ORIGIN + "/history")
        await expect(page.get_by_test_id("history-login-required")).to_be_visible(
            timeout=15000)
        assert await page.locator('[data-testid^="conversation-"]').count() == 0
        assert await page.locator('[data-testid^="history-message-"]').count() == 0
        print("UIA010_" + name.upper() + "_UNAUTH_HISTORY_401_PURGED_PASS", flush=True)
        await page.screenshot(path=str(images / ("auth010-" + name + ".png")))
    finally:
        await ctx.close()


async def run():
    assert os.environ.get("CI") == "true"
    folder = Path(os.environ["RUNNER_TEMP"]) / "auth010-evidence"
    folder.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            await check(browser, False, folder)
            await check(browser, True, folder)
        finally:
            await browser.close()
    print("UIAUTH010_CHROMIUM_HTTPS_NEGATIVE_ONLY_PASS", flush=True)


if __name__ == "__main__":
    asyncio.run(run())
