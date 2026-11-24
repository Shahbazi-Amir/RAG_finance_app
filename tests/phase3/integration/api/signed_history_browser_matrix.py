"""Run the unchanged signed OIDC/PG/restore journey in one explicit engine.

The frozen #118 browser harness stays byte-for-byte intact. Each matrix job
owns its separate runner, IdP, database, restored volume and browser. No
route interception, forged session, owner injection or live RAG engine.
"""
from __future__ import annotations
import asyncio
import os
import sys
from playwright.async_api import async_playwright, expect
from test_app_only_browser_journey import AppOnlyBrowserDemo

ENGINES=("chromium","firefox","webkit")

class OrderedSignedBrowserDemo(AppOnlyBrowserDemo):
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
        print("API_F3_REAL_NEXT_BROWSER_NONROOT_OCI_API_TLS_PG_JOURNEY_PASS",flush=True)
        print("F3_SIGNED_ENGINE_COMPLETE="+engine,flush=True)
    finally:
        demo.stop()

if __name__=="__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in ENGINES:
        raise SystemExit("EXPLICIT_BROWSER_ENGINE_REQUIRED")
    asyncio.run(run(sys.argv[1]))
