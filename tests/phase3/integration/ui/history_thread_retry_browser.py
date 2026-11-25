#!/usr/bin/env python3
"""L1 isolated React thread-state regression, explicitly intercepted fixture.
Not signed OIDC, real SQL, target acceptance, or a new canonical witness.
Requires production-built Next on 127.0.0.1:3000.
"""
import os
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
from product_chat_browser import fixture

BASE="http://127.0.0.1:3000"

def main():
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
        raise RuntimeError("THREAD_RETRY_FIXTURE_CI_ONLY")
    owner=fixture("valid_paginated_conversations")["scope_user_id"]
    a,b="conv_retry_a","conv_empty_b"
    list_page=fixture("valid_paginated_conversations")
    list_page["items"]=[]
    list_page["page"]={"limit":2,"has_more":False,"next_cursor":None}
    for cid,stamp in ((a,"2026-01-02T00:00:00Z"),(b,"2026-01-01T00:00:00Z")):
        row=fixture("valid_conversation")
        row.update(conversation_id=cid,owner_user_id=owner,title=cid,
                   created_at=stamp,updated_at=stamp)
        list_page["items"].append(row)
    pending=[]
    state={"a":"hold","posts":0,"reads":{a:0,b:0},"list":"valid"}
    def detail(cid):
        body=fixture("valid_history_messages_page")
        body.update(conversation_id=cid,owner_user_id=owner,items=[],answers=[],
                    page={"limit":30,"has_more":False,"next_cursor":None})
        if cid==a:
            msg=fixture("valid_user_message")
            msg.update(conversation_id=a,owner_user_id=owner,
                       message_id="msg_retry_a",text="پیام آزمایشی ثابت")
            body["items"]=[msg]
        return body
    def intercept(route):
        path=urlsplit(route.request.url).path
        if route.request.method!="GET":
            state["posts"]+=1
            route.fulfill(status=503,json={"error":"ENGINE_NOT_AVAILABLE"})
            return
        if path=="/api/history/conversations":
            if state["list"]=="unavailable":
                route.fulfill(status=503,json={"error":"SIGNED_PRODUCT_API_UNAVAILABLE"})
            elif state["list"]=="other_owner":
                route.fulfill(status=200,json={**list_page,"scope_user_id":"usr_other_fixture","items":[]})
            else:
                route.fulfill(status=200,json=list_page)
            return
        for cid in (a,b):
            if path=="/api/history/conversations/"+cid+"/messages":
                state["reads"][cid]+=1
                if cid==a and state["a"]=="hold":
                    pending.append(route)
                elif cid==a and state["a"]=="error":
                    route.fulfill(status=503,json={"error":"SIGNED_PRODUCT_API_UNAVAILABLE"})
                else:
                    route.fulfill(status=200,json=detail(cid))
                return
        route.fulfill(status=404,json={"error":"NOT_FOUND"})
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={"width":1280,"height":800})
        try:
            page=context.new_page()
            page.route("**/api/history/**",intercept)
            page.route("**/api/product-capabilities",lambda r:r.fulfill(status=200,json={
                "kind":"ui_runtime_capabilities","contract_version":"ui.runtime_capabilities.v1",
                "send_mode":"DISABLED","engine_available":False,"generation_available":False}))
            page.goto(BASE,wait_until="domcontentloaded")
            expect(page.get_by_test_id("history-thread-loading")).to_be_visible()
            assert pending
            state["a"]="error"
            for route in pending:
                route.fulfill(status=503,json={"error":"SIGNED_PRODUCT_API_UNAVAILABLE"})
            pending.clear()
            expect(page.get_by_test_id("history-thread-error")).to_be_visible()
            expect(page.get_by_test_id("retry-history-thread")).to_be_visible()
            expect(page.get_by_test_id("history-thread-loading")).to_have_count(0)
            expect(page.get_by_test_id("history-thread-empty")).to_have_count(0)
            page.get_by_test_id("conversation-"+b).click()
            expect(page.get_by_test_id("history-thread-empty")).to_be_visible()
            expect(page.get_by_test_id("history-thread-error")).to_have_count(0)
            expect(page.get_by_test_id("retry-history-thread")).to_have_count(0)
            page.get_by_test_id("conversation-"+a).click()
            expect(page.get_by_test_id("history-thread-error")).to_be_visible()
            state["a"]="ok"
            count=state["reads"][a]
            page.get_by_test_id("retry-history-thread").click()
            expect(page.get_by_test_id("history-message-msg_retry_a")).to_contain_text("پیام آزمایشی ثابت")
            expect(page.get_by_test_id("history-thread-error")).to_have_count(0)
            expect(page.get_by_test_id("retry-history-thread")).to_have_count(0)
            expect(page.get_by_test_id("history-thread-empty")).to_have_count(0)
            expect(page.get_by_test_id("history-send")).to_be_disabled()
            assert state["reads"][a]>count and state["posts"]==0
            print("F3_L1_THREAD_LOADING_EMPTY_SCOPED_ERROR_RETRY_GET_ONLY_PASS",flush=True)

            # L1 fixture only: allow editing an unsent draft with the existing
            # synthetic NO_DISPATCH_ONLY capability. No POST or real engine.
            # APP_ONLY itself was tested with DISABLED above.
            draft_page=context.new_page()
            try:
                draft_page.route("**/api/history/**",intercept)
                draft_page.route("**/api/product-capabilities",lambda r:r.fulfill(status=200,json={
                    "kind":"ui_runtime_capabilities","contract_version":"ui.runtime_capabilities.v1",
                    "send_mode":"NO_DISPATCH_ONLY","engine_available":False,"generation_available":False}))
                draft_page.goto(BASE,wait_until="domcontentloaded")
                expect(draft_page.get_by_test_id("history-message-msg_retry_a")).to_be_visible()
                question=draft_page.get_by_test_id("history-question")
                expect(question).to_be_enabled()
                draft="پیش‌نویس خصوصی آزمایشی A"
                question.fill(draft)
                expect(question).to_have_value(draft)
                state["list"]="unavailable"
                draft_page.get_by_test_id("refresh-history").click()
                expect(draft_page.get_by_test_id("history-owner-revalidation-required")).to_be_visible()
                expect(question).to_be_disabled()
                expect(question).to_have_value("")
                expect(draft_page.get_by_test_id("history-message-msg_retry_a")).to_have_count(0)
                expect(draft_page.get_by_test_id("history-send")).to_be_disabled()
                state["list"]="valid"
                draft_page.get_by_test_id("refresh-history").click()
                expect(question).to_be_enabled()
                expect(question).to_have_value(draft)
                expect(draft_page.get_by_test_id("history-message-msg_retry_a")).to_be_visible()
                # A later unavailable -> different owner response must not
                # restore A's draft (or any other A content).
                state["list"]="unavailable"
                draft_page.get_by_test_id("refresh-history").click()
                expect(draft_page.get_by_test_id("history-owner-revalidation-required")).to_be_visible()
                expect(question).to_have_value("")
                state["list"]="other_owner"
                draft_page.get_by_test_id("refresh-history").click()
                expect(draft_page.get_by_test_id("history-login-required")).to_be_visible()
                expect(question).to_have_count(0)
                expect(draft_page.get_by_test_id("history-message-msg_retry_a")).to_have_count(0)
                assert state["posts"]==0
                print("F3_L1_DRAFT_HIDDEN_ON_OUTAGE_SAME_OWNER_ONLY_RESTORE_ZERO_POST_PASS",flush=True)
            finally:
                draft_page.close()
        finally:
            context.close()
            browser.close()
if __name__=="__main__":
    main()
