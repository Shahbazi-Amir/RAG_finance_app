#!/usr/bin/env python3
"""Optional REAL browser checks against a running loopback Next UI, NOT a mock DOM substitute.

Run only after npm ci/build succeeded, with an isolated Playwright Python install
and installed Chromium. Capture evidence locally; do not publish/use a tunnel.
"""
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


def main():
    base = os.environ.get("UI_L1_BASE_URL", "http://127.0.0.1:3000")
    u = urlsplit(base)
    if u.scheme != "http" or u.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Only loopback HTTP UI is permitted for this L1 check")
    evidence = Path(os.environ.get("UI_L1_SCREENSHOT_DIR", "/tmp/ragfinance-ui-l1-screenshots"))
    evidence.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("chromium")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
            dialogs = []
            def handle_dialog(dialog):
                dialogs.append(dialog.message)
                dialog.dismiss()
            page.on("dialog", handle_dialog)
            page.goto(base, wait_until="domcontentloaded", timeout=15000)
            expect(page.get_by_text("نسخهٔ آزمایشی — پاسخ‌های نمونه")).to_be_visible()
            page.locator("#scenario").select_option("answer")
            page.locator("#question").fill("سؤال آزمون منبع")
            page.get_by_role("button", name=re.compile("ارسال پرسش")).click()
            expect(page.locator(".answer-text").last).to_contain_text("نه پاسخ موتور واقعی.", timeout=12000)
            expect(page.locator(".source-button").last).to_be_visible()
            opener = page.locator(".source-button").last
            opener.click()
            drawer = page.get_by_role("dialog", name="جزئیات منبع نمونه")
            expect(drawer).to_be_visible()
            close = drawer.get_by_role("button", name="بستن پنل منبع")
            expect(close).to_be_focused()
            page.keyboard.press("Shift+Tab")
            assert drawer.locator(":focus").count() == 1, "Shift+Tab escaped dialog"
            page.keyboard.press("Tab")
            expect(close).to_be_focused()
            # Tab from last focusable wraps to the first.
            drawer.get_by_role("button", name="بازگشت به گفتگو").focus()
            page.keyboard.press("Tab")
            expect(close).to_be_focused()
            page.keyboard.press("Escape")
            expect(drawer).to_have_count(0)
            expect(opener).to_be_focused()
            page.screenshot(path=str(evidence / "desktop.png"), full_page=True)
            # Real DOM injection regression: React must render malicious strings as text.
            page.get_by_role("button", name="شروع گفتگوی آزمایشی تازه").click()
            page.locator("#scenario").select_option("malicious")
            page.locator("#question").fill("آزمایش HTML و URL مخرب")
            page.get_by_role("button", name=re.compile("ارسال پرسش")).click()
            content = page.locator(".answer-text").last
            expect(content).to_contain_text("<script>alert(1)</script>", timeout=12000)
            assert content.locator("script,img,svg").count() == 0, "HTML parsed instead of escaped"
            page.locator(".source-button").last.click()
            drawer = page.get_by_role("dialog", name="جزئیات منبع نمونه")
            expect(drawer).to_contain_text("<svg/onload=alert(1)>", timeout=5000)
            assert drawer.locator("script,img,svg").count() == 0, "Untrusted metadata parsed as HTML"
            assert drawer.locator("a[href]").count() == 0, "Unresolved synthetic source became a link"
            expect(drawer.locator(".disabled-link")).to_be_visible()
            assert not dialogs, f"JavaScript dialog executed: {dialogs}"
            page.keyboard.press("Escape")
            # Replay and conflict share a message row in UI.
            page.get_by_role("button", name="ارسال مجدد با همان شناسه").click()
            expect(page.get_by_text(re.compile("replayed"), exact=False).last).to_be_visible(timeout=12000)
            page.get_by_role("button", name="آزمایش Conflict").click()
            expect(page.get_by_text("متن متفاوت با همان کلید رد شد؛ پیام جدید ثبت نشد.")).to_be_visible(timeout=12000)
            # Regression: the renderable local "cancel requested" flag is scoped to
            # each attempt and must reset on a fresh run, replay and clear.
            page.get_by_role("button", name="شروع گفتگوی آزمایشی تازه").click()
            page.locator("#scenario").select_option("answer")
            page.locator("#question").fill("لغو سمت Mock")
            page.get_by_role("button", name=re.compile("ارسال پرسش")).click()
            cancel_button = page.get_by_role("button", name="درخواست لغو به سرور نمونه")
            expect(cancel_button).to_be_enabled(timeout=5000)
            cancel_button.click()
            expect(page.locator(".message-set").last).to_contain_text("Mock توقف را تأیید کرد", timeout=8000)
            # Retry the same message: cancellation request must not remain disabled.
            page.get_by_role("button", name="ارسال مجدد با همان شناسه").click()
            cancel_button = page.get_by_role("button", name="درخواست لغو به سرور نمونه")
            expect(cancel_button).to_be_enabled(timeout=5000)
            page.get_by_role("button", name="توقف نمایش (نه موتور)").click()
            expect(page.locator(".message-set").last).to_contain_text("فقط نمایش متوقف شد", timeout=5000)
            assert "Mock توقف را تأیید کرد" not in page.locator(".message-set").last.inner_text(), (
                "Display-only cancellation was shown as server-confirmed stop"
            )
            # Clearing the chat resets the mock and its render flags.
            page.get_by_role("button", name="شروع گفتگوی آزمایشی تازه").click()
            expect(page.locator(".message-set")).to_have_count(0)
            page.locator("#question").fill("تلاش تازه بعد از پاک‌کردن")
            page.get_by_role("button", name=re.compile("ارسال پرسش")).click()
            expect(page.get_by_role("button", name="درخواست لغو به سرور نمونه")).to_be_enabled(timeout=5000)
            mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            mobile.goto(base, wait_until="domcontentloaded", timeout=15000)
            expect(mobile.locator("#question")).to_be_visible()
            assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "Mobile horizontal overflow"
            mobile.locator("#question").focus()
            expect(mobile.locator("#question")).to_be_focused()
            mobile.screenshot(path=str(evidence / "mobile.png"), full_page=True)
            mobile.close()
            page.close()
        finally:
            browser.close()
    print("BROWSER CHECK PASS: component DOM, source drawer focus, XSS and responsive checks")
    print(f"Real screenshots (local): {evidence}")


if __name__ == "__main__":
    main()
