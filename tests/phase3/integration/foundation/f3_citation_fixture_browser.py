"""Actual React DOM against labelled test-only wire fixtures; not live source authority.
No request to provider, external source, real account or target.
"""
import copy
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[4]
BASE="http://127.0.0.1:3000"
CASES=json.loads((ROOT/"packages/contracts/fixtures/product.v1.cases.json").read_text())["cases"]
def fixture(name):return copy.deepcopy(next(x["document"] for x in CASES if x["case_id"]==name))
def scenario(mode):
    conv=fixture("valid_conversation")
    listing=fixture("valid_paginated_conversations")
    owner=conv["owner_user_id"];cid=conv["conversation_id"]
    listing.update(scope_user_id=owner,items=[conv],page={"limit":2,"has_more":False,"next_cursor":None})
    answer=fixture("valid_answer_unresolved_source")
    answer.update(conversation_id=cid,answer_text="پاسخ صرفاً برای آزمون نمایش قرارداد")
    answer["claims"]=[{"claim_id":"claim_1","text":"ادعای نمایشی اول","citation_ids":["cite_1"]},
                      {"claim_id":"claim_2","text":"ادعای نمایشی دوم","citation_ids":["cite_2"]}]
    common={"resolution_status":"verified","attribution_status":"verified",
      "credited_author_name":"نویسنده نمایشی","editorial_supervisor_name":None,"speaker_name":None,
      "content_authority_type":"author","display_title_origin":"source_record"}
    answer["citations"]=[
      {"citation_id":"cite_1","claim_ids":["claim_1"],"source":{**common,"source_id":"src_test_web",
        "source_type":"website","display_title":"منبع نمایشی اول",
        "locator":{"kind":"url","url":"https://example.org/fixture-only","page":None,"timestamp_ms":None}}},
      {"citation_id":"cite_2","claim_ids":["claim_2"],"source":{**common,"source_id":"src_test_book",
        "source_type":"book","display_title":"منبع نمایشی دوم",
        "locator":{"kind":"book_page","url":None,"page":12,"timestamp_ms":None}}}]
    # Deliberately *wire-shape* positive fixture; no actual verified source, external navigation or product evidence.
    answer["provenance"]={"origin":"LIVE_VERIFIED","rag_binding":{"status":"verified",
      "blocked_by":None,"release_id":"fixture_only","adapter_verified":True},
      "producer_reference":"synthetic-wire-test","source_fingerprint":"a"*64}
    if mode=="unverified":
        answer=fixture("valid_answer_unresolved_source");answer["conversation_id"]=cid
        answer["answer_text"]="F3_HIDDEN_SYNTHETIC_ANSWER"
    if mode=="debug":answer["internal_prompt"]="F3_HIDDEN_INTERNAL_PROMPT"
    if mode=="unsafe":answer["citations"][0]["source"]["locator"]["url"]="javascript:alert(1)"
    if mode=="cross_claim":answer["citations"][0]["claim_ids"]=["claim_2"]
    user=fixture("valid_user_message")
    user.update(conversation_id=cid,owner_user_id=owner)
    assistant={**user,"role":"assistant","message_id":answer["message_id"],
      "answer_id":answer["answer_id"],"text":"F3_HIDDEN_RAW_ASSISTANT_DEBUG",
      "created_at":"2026-01-02T00:00:00Z"}
    user["created_at"]="2026-01-01T00:00:00Z"
    user["message_id"]="fixture_user_message"
    page={"kind":"conversation_messages_page","contract_version":"product.v1",
      "conversation_id":cid,"owner_user_id":owner,"items":[user,assistant],
      "answers":[answer],"page":{"limit":30,"has_more":False,"next_cursor":None}}
    return cid,listing,page,answer

def main():
    assert os.getenv("CI")==os.getenv("GITHUB_ACTIONS")=="true"
    results={}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            for mode in ("positive","unverified","debug","unsafe","cross_claim"):
                cid,listing,thread,answer=scenario(mode)
                context=browser.new_context(viewport={"width":1280,"height":800})
                page=context.new_page(); seen={"list":0,"thread":0,"post":0}
                def intercept(route):
                    u=urlsplit(route.request.url)
                    if route.request.method!="GET":
                        seen["post"]+=1;route.fulfill(status=503,json={"error":"ENGINE_NOT_AVAILABLE"});return
                    if u.path=="/api/history/conversations":
                        seen["list"]+=1;route.fulfill(status=200,json=listing);return
                    if u.path=="/api/history/conversations/"+cid+"/messages":
                        seen["thread"]+=1;route.fulfill(status=200,json=thread);return
                    route.fulfill(status=404,json={"error":"NOT_FOUND"})
                page.route("**/api/history/**",intercept)
                page.goto(BASE,wait_until="domcontentloaded")
                expect(page.get_by_test_id("conversation-"+cid)).to_be_visible()
                page.get_by_test_id("conversation-"+cid).click()
                page.wait_for_function("document.querySelector('.history-messages') !== null")
                if mode=="positive":
                    panel=page.get_by_test_id("answer-"+answer["answer_id"])
                    expect(panel).to_be_visible()
                    claims=panel.locator(".product-claim")
                    expect(claims).to_have_count(2)
                    expect(claims.nth(0)).to_contain_text("ادعای نمایشی اول")
                    expect(claims.nth(0)).to_contain_text("src_test_web")
                    expect(claims.nth(1)).to_contain_text("src_test_book")
                    assert "src_test_book" not in claims.nth(0).inner_text()
                    assert "src_test_web" not in claims.nth(1).inner_text()
                    expect(panel.get_by_role("link",name="بازکردن پیوند معتبر منبع")).to_have_count(1)
                    expect(panel.get_by_role("link",name="بازکردن پیوند معتبر منبع")).to_have_attribute("href","https://example.org/fixture-only")
                    expect(panel.get_by_test_id("verified-source-locator")).to_have_count(2)
                    expect(panel.get_by_text("دلیل انتخاب این منبع در قرارداد فعلی ارائه نشده است.")).to_have_count(2)
                elif mode=="unverified":
                    expect(page.get_by_text("پاسخ نمونه یا تأییدنشده از API دریافت شده و عمداً نمایش داده نمی‌شود.")).to_be_visible()
                    assert page.locator(".product-answer").count()==0
                else:
                    expect(page.locator(".history-error")).to_be_visible()
                    assert page.locator(".product-answer").count()==0
                for canary in ("F3_HIDDEN_RAW_ASSISTANT_DEBUG","F3_HIDDEN_INTERNAL_PROMPT","F3_HIDDEN_SYNTHETIC_ANSWER"):
                    assert canary not in page.locator("body").inner_text()
                assert seen["thread"]>=1 and seen["post"]==0
                results[mode]=True
                context.close()
        finally:browser.close()
    out=ROOT/"ci_receipts/f3_citation_dom_fixture.json";out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
      "scope":"REAL_REACT_CHROMIUM_TEST_ONLY_INTERCEPTED_WIRE_FIXTURE",
      "cases":results,"claim_local_citation_association":True,"unknown_reason_explicit":True,
      "debug_raw_assistant_and_prompt_not_rendered":True,"actual_source_authority":False,
      "engine_calls":0,"accepted":False},indent=2)+"\n")
    print("F3_CLAIM_CITATION_DOM_FIXTURE_AND_DEBUG_NEGATIVE_PASS")

if __name__=="__main__":main()
