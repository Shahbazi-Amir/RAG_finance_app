"""Transferred offline UI probes: signed detail pagination, native URL denial,
and same-context browser Back after real revoke. Disposable CI only.
No fake cookie, owner injection, intercepted route, or Engine dispatch.
"""
from dataclasses import dataclass
from urllib.parse import quote, urlsplit
import json
import re

from playwright.async_api import expect

ID=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
CURSOR=re.compile(r"[A-Za-z0-9_-]{1,512}\Z")
MARKER=re.compile(r"F3_REAL_POSTGRES_[AB](?:_\d+)?\Z")


def no_store(headers):
    value=headers.get("cache-control","")
    if not isinstance(value,str):return False
    parts,current,quoted,escaped=[],[],False,False
    for char in value:
        if escaped:
            current.append(char);escaped=False
        elif char=="\\" and quoted:
            current.append(char);escaped=True
        elif char=='"':
            current.append(char);quoted=not quoted
        elif char=="," and not quoted:
            parts.append("".join(current).strip().lower());current=[]
        else:current.append(char)
    if quoted or escaped:return False
    parts.append("".join(current).strip().lower())
    return "no-store" in parts and not any(p.split("=",1)[0].strip()=="public" for p in parts)


def checked_denial(status,headers,body,forbidden,*,expected):
    assert status==expected,("PRIVATE_DENIAL_STATUS",status,expected)
    assert no_store(headers),"PRIVATE_DENIAL_CACHE"
    assert isinstance(body,str),"PRIVATE_DENIAL_NOT_TEXT"
    try:decoded=json.dumps(json.loads(body),ensure_ascii=False)
    except (ValueError,TypeError,RecursionError):decoded=body
    assert not any(token in body or token in decoded for token in forbidden),"PRIVATE_DENIAL_DATA_LEAK"


def checked_message_page(body,owner,expected,seen,limit):
    assert body["owner_user_id"]==owner,"DETAIL_OWNER_MISMATCH"
    items=body["items"]
    assert isinstance(items,list) and len(items)<=limit,"DETAIL_PAGE_LIMIT"
    ids=[]
    for item in items:
        mid,text=item["message_id"],item["text"]
        assert mid in expected and expected[mid]==text,"DETAIL_SQL_ID_BODY_MISMATCH"
        assert mid not in seen and mid not in ids,"DETAIL_DUPLICATE_MESSAGE"
        ids.append(mid)
    info=body["page"]
    more,cursor=info["has_more"],info["next_cursor"]
    assert type(more) is bool,"DETAIL_INVALID_MORE"
    if more:
        assert ids and len(ids)==limit,"DETAIL_EMPTY_OR_SHORT_NONFINAL_PAGE"
        assert isinstance(cursor,str) and CURSOR.fullmatch(cursor),"DETAIL_INVALID_CURSOR"
    else:assert cursor is None,"DETAIL_UNEXPECTED_FINAL_CURSOR"
    return ids,cursor


async def collect_signed_messages(page,origin,cid,owner,expected,*,limit=20):
    url=origin+"/api/history/conversations/"+quote(cid,safe="")+"/messages?limit="+str(limit)
    ids,cursors,cursor=[],set(),None
    for _ in range(len(expected)//limit+2):
        response=await page.request.get(url+("&cursor="+cursor if cursor else ""))
        assert response.status==200,("DETAIL_HTTP_STATUS",response.status)
        assert no_store(response.headers),"DETAIL_PRIVATE_CACHE"
        new,cursor=checked_message_page(await response.json(),owner,expected,set(ids),limit)
        ids.extend(new)
        if cursor is None:break
        assert cursor not in cursors,"DETAIL_REPEATED_CURSOR"
        cursors.add(cursor)
    else:raise AssertionError("DETAIL_UNBOUNDED_PAGINATION")
    assert set(ids)==set(expected),"DETAIL_SQL_COVERAGE"
    return ids


async def assert_clicked_message_pages(page,cid,expected,signed_order):
    button=page.get_by_test_id("conversation-"+cid)
    await button.click()
    await expect(button).to_have_attribute("aria-current","page")
    rendered=page.locator('[data-testid^="history-message-"]')
    more=page.get_by_role("button",name="پیام‌های بیشتر",exact=True)
    for count in range(30,len(expected),30):
        await expect(rendered).to_have_count(count,timeout=20000)
        await expect(more).to_be_visible()
        await more.click()
    await expect(rendered).to_have_count(len(expected),timeout=20000)
    await expect(more).to_have_count(0)
    ids=await rendered.evaluate_all("(nodes)=>nodes.map(n=>n.getAttribute('data-testid').replace('history-message-',''))")
    assert len(ids)==len(set(ids)) and set(ids)==set(expected),"DETAIL_DOM_SQL_COVERAGE"
    assert ids==signed_order,"DETAIL_DOM_HTTP_ORDER_MISMATCH"
    for mid in ids:
        await expect(page.get_by_test_id("history-message-"+mid).locator(".history-message-text")).to_have_text(expected[mid])
    assert await page.locator('[data-testid^="answer-"]').count()==0


async def assert_foreign_message_cursor_denied(original,foreign,origin):
    response=await original.request.get(origin+"/api/history/conversations?limit=100")
    assert response.status==200 and no_store(response.headers)
    found=False
    for item in (await response.json())["items"]:
        cid=item["conversation_id"]
        url=origin+"/api/history/conversations/"+quote(cid,safe="")+"/messages?limit=1"
        own=await original.request.get(url)
        assert own.status==200 and no_store(own.headers)
        doc=await own.json()
        if not doc["page"]["has_more"]:continue
        cursor=doc["page"]["next_cursor"]
        assert isinstance(cursor,str) and CURSOR.fullmatch(cursor)
        own_next=await original.request.get(url+"&cursor="+cursor)
        assert own_next.status==200 and no_store(own_next.headers)
        foreign_next=await foreign.request.get(url+"&cursor="+cursor)
        checked_denial(foreign_next.status,foreign_next.headers,await foreign_next.text(),
                       ("F3_REAL_POSTGRES_",cid,doc["owner_user_id"]),expected=404)
        found=True
    assert found,"DETAIL_CURSOR_FIXTURE_MISSING"


def validate_fixture(rows,owner_a,owner_b,messages):
    assert owner_a!=owner_b and all(ID.fullmatch(x) for x in (owner_a,owner_b)),"OWNER_FIXTURE_INVALID"
    ids_a={r[1] for r in rows if r[0]==owner_a}
    ids_b={r[1] for r in rows if r[0]==owner_b}
    assert ids_a and ids_b and not ids_a.intersection(ids_b),"OWNER_FIXTURE_OVERLAP"
    assert all(ID.fullmatch(x) for x in ids_a|ids_b),"THREAD_FIXTURE_INVALID"
    scoped=[m for m in messages if m[0]==owner_a and m[1] in ids_a and MARKER.fullmatch(m[3])]
    assert scoped and all(ID.fullmatch(m[2]) for m in scoped),"PRIVATE_MESSAGE_FIXTURE_MISSING"
    assert len({m[2] for m in scoped})==len(scoped),"MESSAGE_FIXTURE_DUPLICATE"
    selected=sorted(scoped,key=lambda m:m[2])[0]
    markers=tuple(sorted({m[3] for m in scoped}))
    all_mids=tuple(sorted({m[2] for m in messages if m[0]==owner_a and m[1] in ids_a}))
    assert all(ID.fullmatch(x) for x in all_mids)
    return selected,markers,tuple(sorted(ids_a)),tuple(sorted(ids_b)),(*markers,*sorted(ids_a),*all_mids,owner_a)


@dataclass
class BackProbe:
    page:object
    origin:str
    cid:str
    markers:tuple
    ids_a:tuple
    ids_b:tuple
    forbidden:tuple


OBSERVE="""markers => {
  const result=[];
  addEventListener('pageshow', e => {
    if(e.persisted) result.push(markers.some(m => (document.body?.innerText||'').includes(m)));
  });
  window.__f3BackProbePersisted=result;
}"""
READ_BACK="""() => ({
  persisted_count:(window.__f3BackProbePersisted||[]).length,
  leaked:(window.__f3BackProbePersisted||[]).some(Boolean)
})"""
PRIVATE_STORAGE="""markers => {
  let count=0;
  for(const store of [localStorage,sessionStorage])
    for(let i=0;i<store.length;i++){
      const key=store.key(i),value=store.getItem(key)||'';
      if(markers.some(m=>value.includes(m)||key.includes(m)))count++;
    }
  return count;
}"""


def check_origin(origin):
    parsed=urlsplit(origin)
    assert parsed.scheme=="https" and parsed.hostname=="127.0.0.1" and parsed.path=="" and not parsed.query and not parsed.fragment and not parsed.username,"CI_LOOPBACK_ONLY"


async def prepare_back_probe(context,origin,rows,owner_a,owner_b,messages):
    check_origin(origin)
    selected,markers,ids_a,ids_b,forbidden=validate_fixture(rows,owner_a,owner_b,messages)
    _,cid,mid,expected_text=selected
    page=await context.new_page()
    try:
        response=await page.goto(origin+"/history")
        assert response is not None and response.status in (200,304) and page.url==origin+"/history"
        item=page.get_by_test_id("conversation-"+cid)
        await expect(page.locator('[data-testid^="conversation-"]').first).to_be_visible(timeout=20000)
        if not await item.is_visible():
            await page.get_by_role("button",name="نمایش گفت‌وگوهای بیشتر").click()
        await expect(item).to_be_visible()
        await item.click()
        target=page.get_by_test_id("history-message-"+mid)
        await expect(page.locator('[data-testid^="history-message-"]').first).to_be_visible(timeout=20000)
        if not await target.is_visible():
            await page.get_by_role("button",name="پیام‌های بیشتر",exact=True).click()
        await expect(target).to_be_visible(timeout=20000)
        await expect(target.locator(".history-message-text")).to_have_text(expected_text)
        await page.evaluate(OBSERVE,list(markers))
        account=await page.goto(origin+"/account")
        assert account is not None and account.status in (200,304) and page.url==origin+"/account"
        await expect(page.get_by_role("heading",name="حساب و حریم خصوصی")).to_be_visible()
        return BackProbe(page,origin,cid,markers,ids_a,ids_b,forbidden)
    except BaseException:
        await page.close()
        raise


async def navigate_private_denial(context,origin,path,forbidden,*,expected):
    check_origin(origin)
    assert re.fullmatch(r"/api/history/conversations(?:/[A-Za-z0-9_-]{1,128}/messages)?\?limit=(?:2|20)",path)
    target=origin+path
    tab=await context.new_page()
    try:
        response=await tab.goto(target,wait_until="domcontentloaded",timeout=20000)
        assert response is not None and response.url==target and tab.url==target,"DIRECT_DENIAL_WRONG_URL"
        assert response.request.is_navigation_request() and response.request.method=="GET","DIRECT_DENIAL_NOT_GET_NAVIGATION"
        assert response.request.redirected_from is None,"DIRECT_DENIAL_REDIRECT"
        checked_denial(response.status,response.headers,await response.text(),forbidden,expected=expected)
        print("F3_NATIVE_BROWSER_DIRECT_DENIAL_PASS",expected,flush=True)
    finally:await tab.close()


def detail_path(cid):
    return "/api/history/conversations/"+quote(cid,safe="")+"/messages?limit=20"


async def verify_foreign_before_revoke(probe,surviving_page):
    await navigate_private_denial(surviving_page.context,probe.origin,detail_path(probe.cid),probe.forbidden,expected=404)


async def verify_revoked_back(probe,surviving_page):
    page,origin=probe.page,probe.origin
    try:
        await page.go_back(wait_until="domcontentloaded")
        assert page.url==origin+"/history","BACK_WRONG_LOCATION"
        assert not (await page.evaluate(READ_BACK))["leaked"],"BFCACHE_PAGESHOW_PRIVATE_TEXT"
        await expect(page.get_by_test_id("history-login-required")).to_be_visible(timeout=20000)
        await expect(page.locator('[data-testid^="conversation-"]')).to_have_count(0)
        await expect(page.locator('[data-testid^="history-message-"]')).to_have_count(0)
        result=await page.evaluate(READ_BACK)
        assert not result["leaked"],"BFCACHE_PAGESHOW_PRIVATE_TEXT"
        print("F3_BFCACHE_PERSISTED_EVENT_OBSERVED" if result["persisted_count"]>0 else "F3_BFCACHE_PERSISTED_EVENT_NOT_OBSERVED",flush=True)
        text=await page.locator("body").inner_text()
        assert not any(m in text for m in probe.markers),"BACK_PRIVATE_TEXT"
        assert await page.evaluate(PRIVATE_STORAGE,list(probe.markers))==0,"BACK_PRIVATE_STORAGE_TEXT"
        paths=["/api/history/conversations?limit=2",*(detail_path(cid) for cid in probe.ids_a)]
        for path in paths:
            reply=await page.request.get(origin+path)
            checked_denial(reply.status,reply.headers,await reply.text(),probe.forbidden,expected=401)
        for path in paths[1:]:
            reply=await surviving_page.request.get(origin+path)
            checked_denial(reply.status,reply.headers,await reply.text(),probe.forbidden,expected=404)
        await navigate_private_denial(page.context,origin,paths[0],probe.forbidden,expected=401)
        await navigate_private_denial(page.context,origin,detail_path(probe.cid),probe.forbidden,expected=401)
        await navigate_private_denial(surviving_page.context,origin,detail_path(probe.cid),probe.forbidden,expected=404)
        alive=await surviving_page.request.get(origin+paths[0])
        assert alive.status==200 and no_store(alive.headers)
        observed={item["conversation_id"] for item in (await alive.json())["items"]}
        assert observed and observed<=set(probe.ids_b),"SURVIVING_OWNER_SCOPE"
        print("F3_REVOKED_BROWSER_BACK_PRIVATE_401_AND_SURVIVOR_404_PASS",flush=True)
    finally:await page.close()
