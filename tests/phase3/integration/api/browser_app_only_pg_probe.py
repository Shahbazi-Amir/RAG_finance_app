"""Normal browser OIDC + BFF History; no interception, injected sessions or owner."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright, expect

ROOT = Path("/run/browser")
ORIGIN = "https://ragfinance.ir"
IDP = "https://lab-idp.test"
LIST = ORIGIN + "/api/history/conversations"
COOKIE = "__Host-rag-session"


def trust_ca():
    nss = Path.home() / ".pki/nssdb"
    nss.mkdir(parents=True, exist_ok=True)
    subprocess.run(["certutil", "-N", "-d", "sql:"+str(nss), "--empty-password"], check=True)
    subprocess.run(["certutil", "-A", "-d", "sql:"+str(nss), "-n", "F3 ephemeral lab CA",
                    "-t", "C,,", "-i", str(ROOT/"ca.crt")], check=True)


def login(browser, user):
    ctx = browser.new_context(ignore_https_errors=False, viewport={"width":1280,"height":900})
    page = ctx.new_page()
    for _ in range(60):
        try:
            response = page.goto(ORIGIN+"/login", wait_until="domcontentloaded", timeout=5000)
            if response and response.status == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise AssertionError("ingress-not-ready")
    # Report only phase and HTTP status, never callback URL, tokens or credentials.
    print("BROWSER_LOGIN_FORM_READY",flush=True)
    with page.expect_response(lambda r: r.url == ORIGIN+"/api/auth/login" and r.request.method=="POST",timeout=20000) as submitted:
        page.get_by_test_id("login-submit").click()
    assert submitted.value.status == 303, "login-start-not-303"
    print("BROWSER_BOOTSTRAP_START_303",flush=True)
    page.wait_for_url(IDP+"/**", timeout=20000)
    print("BROWSER_IDP_FORM_READY",flush=True)
    page.locator("#username").fill(user["username"])
    page.locator("#password").fill(user["password"])
    with page.expect_response(lambda r: r.url.startswith(ORIGIN+"/api/auth/callback?"),timeout=30000) as callback:
        page.locator("#kc-login").click()
    assert callback.value.status == 303, "callback-not-303"
    print("BROWSER_BOOTSTRAP_CALLBACK_303",flush=True)
    page.wait_for_url(ORIGIN+"/", timeout=30000)
    session = [c for c in ctx.cookies() if c["name"] == COOKIE]
    assert len(session)==1 and session[0]["secure"] and session[0]["httpOnly"]
    assert session[0]["path"]=="/" and session[0]["sameSite"]=="Lax"
    assert page.request.get(LIST+"?limit=2").status==200
    print("BROWSER_SESSION_AND_SIGNED_HISTORY_200",flush=True)
    return ctx,page,session[0]["value"]


def expect_json(response, status):
    assert response.status == status
    assert response.headers.get("cache-control") == "no-store"
    return response.json() if status==200 else None


def run(mode):
    users=json.loads((ROOT/"users.json").read_text())
    trust_ca()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True, args=["--disable-background-networking"])
        print("BROWSER_STAGE",mode,flush=True)
        a,pa,old=login(browser,users["a"])
        b,pb,_=login(browser,users["b"])
        la=expect_json(pa.request.get(LIST+"?limit=2"),200)
        lb=expect_json(pb.request.get(LIST+"?limit=2"),200)
        assert la["scope_user_id"] != lb["scope_user_id"]
        if mode=="map":
            assert not la["items"] and not lb["items"]
            print("REAL_OIDC_TWO_SUBJECTS_COOKIE_AND_EMPTY_HISTORY_PASS")
        else:
            assert [x["conversation_id"] for x in la["items"]]==["browser-a-3","browser-a-2"]
            assert [x["conversation_id"] for x in lb["items"]]==["browser-b-1"]
            assert la["page"]["has_more"]
            cursor=la["page"]["next_cursor"]
            second=expect_json(pa.request.get(LIST+"?limit=2&cursor="+cursor),200)
            assert [x["conversation_id"] for x in second["items"]]==["browser-a-1"]
            assert not second["page"]["has_more"]
            expect(pa.get_by_test_id("conversation-browser-a-3")).to_be_visible()
            expect(pa.get_by_test_id("conversation-browser-b-1")).to_have_count(0)
            pa.get_by_role("button",name="نمایش گفت‌وگوهای بیشتر").click()
            expect(pa.get_by_test_id("conversation-browser-a-1")).to_be_visible()
            pa.get_by_test_id("conversation-browser-a-1").click()
            expect(pa.get_by_test_id("history-message-browser-msg-a")).to_have_text("lab browser A")
            detail=expect_json(pa.request.get(LIST+"/browser-a-1/messages?limit=30"),200)
            assert detail["owner_user_id"]==la["scope_user_id"]
            assert [(x["message_id"],x["text"]) for x in detail["items"]]==[("browser-msg-a","lab browser A")]
            expect(pb.get_by_test_id("conversation-browser-b-1")).to_be_visible()
            expect(pb.get_by_test_id("conversation-browser-a-1")).to_have_count(0)
            denied=pb.request.get(LIST+"/browser-a-1/messages?limit=30")
            expect_json(denied,404)
            assert "lab browser A" not in denied.text()
            pa.reload(wait_until="domcontentloaded")
            expect(pa.get_by_test_id("conversation-browser-a-3")).to_be_visible()
            pa.get_by_role("button",name="نمایش گفت‌وگوهای بیشتر").click()
            pa.get_by_test_id("conversation-browser-a-1").click()
            expect(pa.get_by_test_id("history-message-browser-msg-a")).to_have_text("lab browser A")
            expect(pa.get_by_test_id("history-send")).to_be_disabled()
            expect(pa.get_by_test_id("app-runtime-capability")).to_contain_text("بدون موتور")
            expect_json(pa.request.post(ORIGIN+"/api/history/messages",data="invalid-no-read"),503)
            # Normal logout via real form; replay the exact previously issued cookie
            # only for the negative assertion, never to establish a session.
            pa.goto(ORIGIN+"/login",wait_until="domcontentloaded")
            pa.get_by_test_id("logout-submit").click()
            pa.wait_for_url(ORIGIN+"/login?reason=logged_out",timeout=20000)
            expect(pa.get_by_test_id("logout-success")).to_be_visible()
            expect_json(pa.request.get(LIST+"?limit=2",headers={"Cookie":COOKIE+"="+old}),401)
            expect_json(pb.request.get(LIST+"?limit=2"),200)
            print("BROWSER_"+mode.upper()+"_OIDC_DOM_SQL_IDS_PAGINATION_REFRESH_AB_REVOKE_SEND_PASS")
        a.close();b.close();browser.close()


if __name__=="__main__":
    assert len(sys.argv)==2 and sys.argv[1] in ("map","source","restore")
    try:
        run(sys.argv[1])
    except Exception as exc:
        # Browser exceptions may include callback code, state or account data.
        # Do not emit raw exception text, traces, HAR, screenshots or storage state.
        print("BROWSER_PROBE_FAILED",sys.argv[1],type(exc).__name__,file=sys.stderr)
        raise SystemExit(1) from None
