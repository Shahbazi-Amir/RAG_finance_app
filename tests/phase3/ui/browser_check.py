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
            page = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
            dialogs = []
            confirm_accept = {"enabled": True}
            def handle_dialog(dialog):
                # This is a real, documented destructive action on in-memory data.
                if dialog.type == "confirm" and "گفتگوی آزمایشی فعلی" in dialog.message:
                    if confirm_accept["enabled"]:
                        dialog.accept()
                    else:
                        dialog.dismiss()
                else:
                    dialogs.append(dialog.message)
                    dialog.dismiss()
            page.on("dialog", handle_dialog)
            page.goto(base, wait_until="domcontentloaded", timeout=15000)
            expect(page.get_by_text("نسخهٔ آزمایشی؛ پاسخ‌ها نمونه‌اند و به موتور پاسخ‌گویی متصل نیستند.")).to_be_visible()
            assert page.locator(".side-panel").count() == 0, "The large intro column reappeared"
            sidebar = page.locator(".sidebar-desktop")
            expect(sidebar).to_be_visible()
            assert sidebar.bounding_box()["x"] + sidebar.bounding_box()["width"] >= 1279, (
                "Desktop navigation is not on the right edge"
            )
            expect(sidebar.get_by_role("button", name="حساب کاربری")).to_be_visible()
            expect(sidebar.get_by_role("button", name="حریم خصوصی")).to_be_visible()
            expect(sidebar.get_by_text("هنوز گفتگویی در این صفحه ندارید.")).to_be_visible()
            # Collapse/expand is a real and accessible desktop interaction.
            sidebar.get_by_role("button", name="جمع‌کردن نوار کناری").click()
            expect(sidebar).to_have_class(re.compile("is-collapsed"))
            sidebar.get_by_role("button", name="بازکردن نوار کناری").click()
            expect(sidebar).not_to_have_class(re.compile("is-collapsed"))
            assert page.locator(".chat-panel").evaluate("(el) => getComputedStyle(el).backgroundColor") == "rgba(0, 0, 0, 0)", "The large white chat card reappeared"
            assert page.locator(".chat-panel").evaluate("(el) => getComputedStyle(el).boxShadow") == "none", "The chat card shadow reappeared"
            width = page.locator(".chat-panel").bounding_box()["width"]
            assert 720 <= width <= 800, f"Desktop reading column is not ~720-800px: {width}"
            expect(page.get_by_role("heading", name="چه پرسشی دربارهٔ امور مالی دارید؟")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "Desktop horizontal overflow"
            assert page.locator(".messages").evaluate("(el) => getComputedStyle(el).overflowY") != "auto", "Nested messages scroll returned"
            assert page.locator(".sidebar-desktop").evaluate("(el) => getComputedStyle(el).position") == "sticky"
            assert page.locator(".chat-footer").evaluate("(el) => getComputedStyle(el).position") == "sticky"
            assert page.locator(".composer").is_visible(), "Composer should be visible at the desktop viewport"
            composer_box = page.locator(".composer").bounding_box()
            assert composer_box and 0 <= composer_box["y"] and composer_box["y"] + composer_box["height"] <= 800 + 1, (
                "Composer was outside 1280x800 viewport before scrolling"
            )
            # Technical controls are intentionally progressive disclosure.
            if page.locator(".test-tools").get_attribute("open") is None:
                page.locator(".test-tools summary").click()
            expect(page.locator("#scenario")).to_be_visible()
            page.locator("#scenario").select_option("answer")
            page.locator("#question").fill("سؤال آزمون منبع")
            page.get_by_role("button", name=re.compile("^ارسال")).click()
            expect(page.locator(".answer-text").last).to_contain_text("نه پاسخ موتور واقعی.", timeout=12000)
            expect(page.locator(".source-button").last).to_be_visible()
            expect(sidebar.locator(".nav-thread")).to_have_count(1)
            # Both placeholders are honest (no account, email or accepted consent).
            sidebar.get_by_role("button", name="حساب کاربری").click()
            expect(page.get_by_text("ورود و مدیریت حساب هنوز متصل نیست.")).to_be_visible()
            assert page.locator(".message-set").count() == 0, "Chat should be hidden outside its view"
            sidebar.get_by_role("button", name="حریم خصوصی").click()
            expect(page.get_by_text("مدیریت رضایت و درخواست حذف در نسخهٔ متصل ارائه می‌شود.")).to_be_visible()
            sidebar.locator(".nav-thread").click()
            expect(page.locator(".message-set")).to_have_count(1)
            expect(page.locator(".answer-text").last).to_contain_text("نه پاسخ موتور واقعی.")
            # A declined local-clear confirmation must preserve all messages.
            confirm_accept["enabled"] = False
            sidebar.locator(".nav-new-chat").click()
            expect(page.locator(".message-set")).to_have_count(1)
            confirm_accept["enabled"] = True
            expect(page.locator(".claim .source-button").last).to_be_visible()
            expect(page.get_by_text("اطمینان پاسخ ارزیابی نشده است.")).to_be_visible()
            expect(page.get_by_role("heading", name="چه پرسشی دربارهٔ امور مالی دارید؟")).to_have_count(0)
            assert page.locator(".message-set").last.locator(".state-line").count() == 0, (
                "Completed normal answer displayed redundant status labels"
            )
            assert page.locator(".message-set").last.locator(".outcome").count() == 0, (
                "Obsolete outcome label reappeared"
            )
            assert "null" not in page.locator(".messages").inner_text(), "Technical null leaked to chat"
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
            # Keep the technical drawer collapsed in the visual evidence.
            if page.locator(".test-tools").get_attribute("open") is not None:
                page.locator(".test-tools summary").click()
            page.evaluate("window.scrollTo(0, 0)")
            # At 1280x800 the first short exchange, header and composer should be in view.
            for selector in [".sidebar-desktop .nav-brand", ".user-bubble", ".answer-text", ".composer"]:
                box = page.locator(selector).last.bounding_box()
                assert box and box["y"] >= -1 and box["y"] + box["height"] <= 801, (
                    f"{selector} is clipped in initial 1280x800 reading view: {box}"
                )
            page.screenshot(path=str(evidence / "desktop.png"), full_page=True)
            # Real DOM injection regression: React must render malicious strings as text.
            sidebar.locator(".nav-new-chat").click()
            if page.locator(".test-tools").get_attribute("open") is None:
                page.locator(".test-tools summary").click()
            page.locator("#scenario").select_option("malicious")
            page.locator("#question").fill("آزمایش HTML و URL مخرب")
            page.get_by_role("button", name=re.compile("^ارسال")).click()
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
            # Replay and conflict remain usable behind the disclosure.
            if page.locator(".test-tools").get_attribute("open") is None:
                page.locator(".test-tools summary").click()
            page.get_by_role("button", name="تکرار همان درخواست (Replay)").click()
            expect(page.get_by_text(re.compile("replayed"), exact=False).last).to_be_visible(timeout=12000)
            page.get_by_role("button", name="آزمایش تعارض (Conflict)").click()
            expect(page.get_by_text("درخواست تکراری با متن متفاوت پذیرفته نشد؛ پیام جدیدی ثبت نشد.")).to_be_visible(timeout=12000)
            # Distinct non-success states must not be swallowed by a generic success label.
            for scenario, expected_status in [
                ("partial", "پاسخ ناقص است"),
                ("unknown", "نتیجه مشخص نیست"),
                ("error", "خطای فنی رخ داد"),
                ("no_answer", "شواهد کافی برای پاسخ"),
                ("clarification", "برای پاسخ دقیق‌تر"),
                ("refusal", "در این نمونه امکان پاسخ‌گویی"),
            ]:
                sidebar.locator(".nav-new-chat").click()
                if page.locator(".test-tools").get_attribute("open") is None:
                    page.locator(".test-tools summary").click()
                page.locator("#scenario").select_option(scenario)
                page.locator("#question").fill("بررسی وضعیت نمونه")
                page.get_by_role("button", name=re.compile("^ارسال")).click()
                expect(page.locator(".message-set").last.locator(".state-line")).to_contain_text(
                    expected_status, timeout=12000
                )
                assert page.locator(".message-set").last.locator(".state-line").count() == 1, (
                    "More than one status is visible for one answer"
                )
            # Regression: the renderable local "cancel requested" flag is scoped to
            # each attempt and must reset on a fresh run, replay and clear.
            sidebar.locator(".nav-new-chat").click()
            if page.locator(".test-tools").get_attribute("open") is None:
                page.locator(".test-tools summary").click()
            page.locator("#scenario").select_option("answer")
            page.locator("#question").fill("لغو سمت Mock")
            page.get_by_role("button", name=re.compile("^ارسال")).click()
            cancel_button = page.get_by_role("button", name="درخواست توقف پردازش")
            expect(cancel_button).to_be_enabled(timeout=5000)
            cancel_button.click()
            expect(page.locator(".message-set").last).to_contain_text("توقف پردازش در شبیه‌ساز تأیید شد", timeout=8000)
            # Retry the same message: cancellation request must not remain disabled.
            page.get_by_role("button", name="تکرار همان درخواست (Replay)").click()
            cancel_button = page.get_by_role("button", name="درخواست توقف پردازش")
            expect(cancel_button).to_be_enabled(timeout=5000)
            page.get_by_role("button", name="توقف نمایش").click()
            expect(page.locator(".message-set").last).to_contain_text("نمایش پاسخ متوقف شد", timeout=5000)
            assert "توقف پردازش در شبیه‌ساز تأیید شد" not in page.locator(".message-set").last.inner_text(), (
                "Display-only cancellation was shown as server-confirmed stop"
            )
            # Clearing the chat resets the mock and its render flags.
            sidebar.locator(".nav-new-chat").click()
            expect(page.locator(".message-set")).to_have_count(0)
            page.locator("#question").fill("تلاش تازه بعد از پاک‌کردن")
            page.get_by_role("button", name=re.compile("^ارسال")).click()
            expect(page.get_by_role("button", name="درخواست توقف پردازش")).to_be_enabled(timeout=5000)
            mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            mobile.goto(base, wait_until="domcontentloaded", timeout=15000)
            expect(mobile.locator("#question")).to_be_visible()
            expect(mobile.get_by_text("نسخهٔ آزمایشی؛ پاسخ‌ها نمونه‌اند و به موتور پاسخ‌گویی متصل نیستند.")).to_be_visible()
            assert mobile.locator(".composer").is_visible(), "Composer is not visible at 390x844"
            mobile_composer = mobile.locator(".composer").bounding_box()
            assert mobile_composer and 0 <= mobile_composer["y"] and mobile_composer["y"] + mobile_composer["height"] <= 844 + 1, (
                "Composer was outside the 390x844 initial viewport"
            )
            assert mobile.locator(".mobile-topbar").is_visible(), "Mobile header is not visible at 390x844"
            expect(mobile.locator(".sidebar-desktop")).to_be_hidden()
            menu_toggle = mobile.get_by_role("button", name="بازکردن منوی ناوبری")
            menu_toggle.click()
            menu = mobile.get_by_role("dialog", name="منوی ناوبری")
            expect(menu).to_be_visible()
            menu_close = menu.get_by_role("button", name="بستن منوی ناوبری")
            expect(menu_close).to_be_focused()
            mobile.keyboard.press("Shift+Tab")
            assert menu.locator(":focus").count() == 1, "Shift+Tab escaped mobile navigation"
            mobile.keyboard.press("Escape")
            expect(menu).to_have_count(0)
            expect(menu_toggle).to_be_focused()
            menu_toggle.click()
            menu = mobile.get_by_role("dialog", name="منوی ناوبری")
            menu.get_by_role("button", name="حساب کاربری").click()
            expect(mobile.get_by_text("ورود و مدیریت حساب هنوز متصل نیست.")).to_be_visible()
            expect(menu).to_have_count(0)
            menu_toggle.click()
            menu = mobile.get_by_role("dialog", name="منوی ناوبری")
            menu.get_by_role("button", name="حریم خصوصی").click()
            expect(mobile.get_by_text("مدیریت رضایت و درخواست حذف در نسخهٔ متصل ارائه می‌شود.")).to_be_visible()
            menu_toggle.click()
            menu = mobile.get_by_role("dialog", name="منوی ناوبری")
            menu.get_by_role("button", name="صفحهٔ گفتگو").click()
            expect(mobile.locator("#question")).to_be_visible()
            mobile.locator("#question").fill("گفتگوی موقت در موبایل")
            mobile.get_by_role("button", name=re.compile("^ارسال")).click()
            expect(mobile.locator(".message-set")).to_have_count(1)
            expect(mobile.locator(".answer-text").last).to_contain_text("نه پاسخ موتور واقعی.", timeout=12000)
            menu_toggle.click()
            menu = mobile.get_by_role("dialog", name="منوی ناوبری")
            expect(menu.locator(".nav-thread")).to_have_count(1)
            menu.get_by_role("button", name="حساب کاربری").click()
            expect(mobile.get_by_text("ورود و مدیریت حساب هنوز متصل نیست.")).to_be_visible()
            menu_toggle.click()
            menu = mobile.get_by_role("dialog", name="منوی ناوبری")
            menu.locator(".nav-thread").click()
            expect(mobile.locator(".message-set")).to_have_count(1)
            expect(mobile.locator(".answer-text").last).to_contain_text("نه پاسخ موتور واقعی.")
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
