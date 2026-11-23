#!/usr/bin/env python3
"""Actual Next server + Chromium app-only smoke, not a mocked History API.

CI must start the production-built Next process with PHASE3_APP_MODE=APP_ONLY
on isolated 127.0.0.1:3000. No IdP/PG/Engine/Runner is touched.
"""
from urllib.parse import urlparse
import os
from playwright.sync_api import sync_playwright, expect

def main():
    origin=os.environ.get("UI_APP_ONLY_BASE_URL","http://127.0.0.1:3100")
    parsed=urlparse(origin)
    if parsed.scheme!="http" or parsed.hostname!="127.0.0.1" or parsed.port!=3100:
        raise RuntimeError("APP_ONLY_TEST_REQUIRES_ISOLATED_LOOPBACK")
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            for width,height in ((1280,800),(390,844),(320,568)):
                page=browser.new_page(viewport={"width":width,"height":height})
                posts=[]
                page.on("request",lambda req: posts.append(req.url)
                        if req.method=="POST" and "/api/history/messages" in req.url else None)
                response=page.goto(origin,wait_until="domcontentloaded")
                assert response is not None and response.status==200
                label=page.get_by_test_id("app-runtime-capability")
                expect(label).to_contain_text("برنامه در حالت بدون موتور",timeout=15000)
                expect(page.get_by_test_id("create-conversation")).to_be_disabled()
                expect(page.get_by_test_id("history-send")).to_be_disabled()
                expect(page.get_by_test_id("history-question")).to_be_disabled()
                # A caller bypassing the disabled HTML button still cannot
                # start a request via the real React form handler.
                page.locator("form.history-compose").evaluate(
                    """(form)=>form.dispatchEvent(
                       new Event('submit',{bubbles:true,cancelable:true}))""")
                page.wait_for_timeout(80)
                assert posts==[],f"UI sent a POST in APP_ONLY at width {width}"
                assert page.evaluate(
                    "document.documentElement.scrollWidth<=window.innerWidth+2")
                capability=page.request.get(origin+"/api/product-capabilities")
                assert capability.status==200
                assert "no-store" in (capability.headers.get("cache-control") or "")
                payload=capability.json()
                assert payload["kind"]=="ui_runtime_capabilities"
                assert payload["contract_version"]=="ui.runtime_capabilities.v1"
                assert payload["send_mode"]=="DISABLED"
                assert payload["engine_available"] is False
                assert payload["generation_available"] is False
                # Direct malicious Send receives a stable refusal BEFORE any
                # durable Send; no identity is submitted and no engine exists.
                denied=page.request.post(origin+"/api/history/messages",
                                          data="{}",headers={"content-type":"application/json"})
                assert denied.status==503,denied.status
                assert denied.json()=={"error":"ENGINE_NOT_AVAILABLE"}
                assert "no-store" in (denied.headers.get("cache-control") or "")
                page.close()
            print("UI_APP_ONLY_REAL_NEXT_CHROMIUM_1280_390_320_NO_SEND_BFF_503_PASS")
        finally:
            browser.close()

if __name__=="__main__":
    main()
