"""Run the unchanged signed OIDC/PG/restore journey in one explicit engine.

The frozen #118 browser harness stays byte-for-byte intact. Each matrix job
owns its separate runner, IdP, database, restored volume and browser. No
route interception, forged session, owner injection or live RAG engine.
"""
from __future__ import annotations
import asyncio
import os
import time
import httpx
import sys
from urllib.parse import urljoin
from playwright.async_api import async_playwright, expect
from test_app_only_browser_journey import AppOnlyBrowserDemo
from signed_history_content_guard import SignedContentGuardMixin, assert_content_dom, TITLE, BODY

ENGINES=("chromium","firefox","webkit")

class OrderedSignedBrowserDemo(SignedContentGuardMixin, AppOnlyBrowserDemo):
    def check_restored_outage(self, actor, new_id):
        super().check_restored_outage(actor,new_id)
        self.browser_restore_pg_id=new_id
        self.browser_restore_actor=actor

    async def real_browser_outage_recovery(self,page,conversation_id,rows,owner):
        # The only container controlled here is the exact already-verified
        # disposable restored PG instance. Never touch the source or target.
        pg_id=self.browser_restore_pg_id
        actor=self.browser_restore_actor
        self.assert_restore_pg_binding(pg_id)
        assert self.readiness(actor).status_code==200
        before=self.counts()
        selector='[data-testid^="history-message-"]'
        await expect(page.locator(selector)).to_have_count(31)
        self.ci_command("docker","stop","--time","2",pg_id)
        try:
            assert self.readiness(actor).status_code==503
            async with page.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and "cursor=" not in r.url and r.request.method=="GET",
                timeout=30000) as pending:
                await page.get_by_test_id("refresh-history").click()
            denied=await pending.value
            assert denied.status==503
            assert denied.headers.get("cache-control")=="no-store"
            await expect(page.get_by_test_id("history-owner-revalidation-required")).to_be_visible()
            await expect(page.get_by_test_id("history-list-error")).to_be_visible()
            await expect(page.locator(selector)).to_have_count(0)
            await expect(page.get_by_test_id("history-send")).to_be_disabled()
        finally:
            self.ci_command("docker","start",pg_id)
            self.assert_restore_pg_binding(pg_id)
        for _ in range(60):
            try:
                if self.readiness(actor).status_code==200:break
            except httpx.HTTPError:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError("SIGNED_BROWSER_PG_RESTART_NOT_READY")
        async with page.expect_response(
            lambda r: "/api/history/conversations?limit=2" in r.url
            and "cursor=" not in r.url and r.request.method=="GET",
            timeout=30000) as pending:
            await page.get_by_test_id("refresh-history").click()
        assert (await pending.value).status==200
        await expect(page.get_by_test_id("history-list-error")).to_have_count(0)
        await expect(page.get_by_test_id("history-owner-revalidation-required")).to_have_count(0)
        await expect(page.locator(selector)).to_have_count(30,timeout=20000)
        await super().verify_31_message_page2(page,conversation_id,rows,owner)
        actual=await page.locator(selector).evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('data-testid'))")
        assert actual==["history-message-"+row["id"] for row in rows]
        await expect(page.get_by_test_id("history-send")).to_be_disabled()
        assert self.counts()==before
        print("F3_SIGNED_REAL_PG_OUTAGE_UI_HIDDEN_RETRY_RECOVERY_NO_STALE_ALERT_PASS",flush=True)

    async def verify_signed_reload(self,page,conversation_id,rows,owner):
        # Actual full document reload, not an intercepted API or in-memory state.
        # Reopen the same persisted conversation through ordinary UI and prove
        # 30+1 IDs and exact bodies against the independent SQL expectation.
        before=self.counts()
        mutations=[]
        def record(request):
            if "/api/" in request.url and request.method in ("POST","PUT","PATCH","DELETE"):
                mutations.append(request.method)
        page.on("request",record)
        try:
            async with page.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and "cursor=" not in r.url and r.request.method=="GET",timeout=30000) as wait:
                response=await page.reload(wait_until="domcontentloaded")
            assert response.status==200
            result=await wait.value
            assert result.status==200
            doc=await result.json()
            assert doc["scope_user_id"]==owner
            assert any(x["conversation_id"]==conversation_id and x["title"]==TITLE
                       for x in doc["items"])
            await expect(page.get_by_test_id("conversation-"+conversation_id)).to_be_visible()
            await page.get_by_test_id("conversation-"+conversation_id).click()
            await AppOnlyBrowserDemo.verify_31_message_page2(self,page,conversation_id,rows,owner)
            nodes=page.locator('[data-testid^="history-message-"]')
            actual=await nodes.evaluate_all("(nodes) => nodes.map(n => n.getAttribute('data-testid'))")
            assert actual==["history-message-"+row["id"] for row in rows]
            await assert_content_dom(page,conversation_id,self.guard_mid,TITLE,BODY,self.guard_foreign_body)
            await expect(page.get_by_test_id("more-messages")).to_have_count(0)
            await expect(page.get_by_test_id("history-send")).to_be_disabled()
            assert not mutations and self.counts()==before
            print("F3_SIGNED_FULL_RELOAD_31_LITERAL_IDS_ZERO_MUTATION_PASS",flush=True)
        finally:
            page.remove_listener("request",record)

    async def verify_signed_account(self,page,owner):
        # Ordinary authenticated browser context, actual Next account route.
        # No artificial policy grants or writes. The account page remains
        # read-only until Product/Legal approve the relevant contracts.
        href=await page.get_by_role("link",name="حساب، حریم خصوصی و وضعیت قابلیت‌ها").get_attribute("href")
        assert href=="/account"
        before=self.counts()
        account=await page.context.new_page()
        mutations=[]
        account.on("request",lambda r: mutations.append(r.method)
                   if r.method in ("POST","PUT","PATCH","DELETE") and "/api/" in r.url else None)
        try:
            response=await account.goto(urljoin(page.url,href),wait_until="domcontentloaded")
            assert response.status==200
            await expect(account.get_by_role("heading",name="حساب و حریم خصوصی")).to_be_visible()
            await expect(account.get_by_text("وضعیت ثبت رضایت: نامعلوم؛ پذیرش خودکار انجام نمی‌شود.")).to_be_visible()
            await expect(account.get_by_text("امکان درخواست حذف از این رابط هنوز فعال نیست.")).to_be_visible()
            await expect(account.get_by_text("Export و Feedback در این نسخه فعال نیستند.")).to_be_visible()
            await expect(account.locator("main.history-shell")).to_have_attribute("dir","rtl")
            assert await account.locator("form,button,input,textarea,select").count()==0
            async with account.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and "cursor=" not in r.url and r.request.method=="GET",timeout=30000) as wait:
                await account.get_by_role("link",name="بازگشت به گفت‌وگو").click()
            result=await wait.value
            assert result.status==200
            assert (await result.json())["scope_user_id"]==owner
            await expect(account.get_by_test_id("history-send")).to_be_disabled()
            assert not mutations and self.counts()==before
            print("F3_SIGNED_ACCOUNT_READONLY_RETURN_OWNER_NO_MUTATION_PASS",flush=True)
        finally:
            await account.close()

    async def verify_signed_keyboard(self,page):
        await page.set_viewport_size({"width":320,"height":720})
        menu=page.get_by_role("button",name="بازکردن فهرست گفت‌وگوها")
        await menu.click()
        close=page.get_by_role("button",name="بستن فهرست")
        await expect(close).to_be_focused()
        dialog=page.get_by_role("dialog",name="فهرست گفتگوها")
        await expect(dialog).to_have_attribute("aria-modal","true")
        last=dialog.get_by_role("link",name="حساب کاربری و خروج امن")
        await page.keyboard.press("Shift+Tab")
        await expect(last).to_be_focused()
        await page.keyboard.press("Tab")
        await expect(close).to_be_focused()
        assert await page.locator("section.history-main").get_attribute("inert") is not None
        await page.set_viewport_size({"width":1280,"height":800})
        await expect(page.get_by_role("heading",name="گفت‌وگوی مالی")).to_be_focused()
        assert await page.locator("section.history-main").get_attribute("inert") is None
        print("F3_SIGNED_REAL_KEYBOARD_WRAP_RESIZE_FOCUS_PASS",flush=True)

    async def verify_31_message_page2(self, page, conversation_id, rows, expected_owner):
        await super().verify_31_message_page2(page, conversation_id, rows, expected_owner)
        nodes=page.locator('[data-testid^="history-message-"]')
        expected=["history-message-"+row["id"] for row in rows]
        await expect(nodes).to_have_count(len(expected))
        actual=await nodes.evaluate_all("(nodes) => nodes.map(n => n.getAttribute('data-testid'))")
        assert actual==expected, "SIGNED_DOM_ORDER_DIFFERS_FROM_SQL"
        assert len(set(actual))==31
        await expect(page.get_by_test_id("more-messages")).to_have_count(0)
        await expect(page.locator("main.history-shell")).to_have_attribute("dir","rtl")
        self.exact_order_witnesses=getattr(self,"exact_order_witnesses",0)+1
        print("F3_SIGNED_31_DOM_EXACT_ORDER_RTL_TERMINAL_PASS",flush=True)
        if self.exact_order_witnesses==2:
            await self.real_browser_outage_recovery(page,conversation_id,rows,expected_owner)
            await self.verify_signed_reload(page,conversation_id,rows,expected_owner)
            await self.verify_signed_keyboard(page)
            await self.verify_signed_account(page,expected_owner)

async def run(engine):
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
        raise RuntimeError("SIGNED_BROWSER_MATRIX_CI_ONLY")
    if engine not in ENGINES:
        raise RuntimeError("UNSUPPORTED_BROWSER_ENGINE")
    demo=OrderedSignedBrowserDemo()
    try:
        demo.start()
        async with async_playwright() as p:
            browser_type=getattr(p,engine)
            browser=await browser_type.launch()
            try:
                assert browser.browser_type.name==engine
                await demo.journey(browser,demo.root/"browser-output")
            finally:
                await browser.close()
        assert demo.exact_order_witnesses==2
        assert demo.content_guard_witnesses==3, 'SIGNED_CONTENT_GUARD_CHECKPOINT_COUNT'
        print("API_F3_REAL_NEXT_BROWSER_NONROOT_OCI_API_TLS_PG_JOURNEY_PASS",flush=True)
        print("F3_SIGNED_ENGINE_COMPLETE="+engine,flush=True)
    finally:
        demo.stop()

if __name__=="__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in ENGINES:
        raise SystemExit("EXPLICIT_BROWSER_ENGINE_REQUIRED")
    asyncio.run(run(sys.argv[1]))
