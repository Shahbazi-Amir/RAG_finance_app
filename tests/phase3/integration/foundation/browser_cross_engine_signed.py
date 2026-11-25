"""Real Firefox/WebKit owner-scoped signed History, isolated hosted CI only.

No interception, mocked identities, ignored TLS, or shared user profiles.
This additional matrix does not claim cross-engine restore or target acceptance.
"""
import asyncio
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from playwright.async_api import Error as PlaywrightError, async_playwright, expect
from browser_history_restore import (
    ROOT, Demo, ORIGIN, verify_isolation, inventory, message_inventory,
    create_extra_question, browser_history, mobile_320_keyboard_accessibility,
    signed_pagination, foreign_owner_denied, cursor_owner_signature_denied,
    send_denied, account_and_accessibility,
)
from browser_lab_trust import isolated_browser_trust


@contextmanager
def hosted_webkit_ca(ca):
    # Linux WebKit uses the system trust backend. This is a disposable
    # GitHub-hosted VM only; never install trust on a self-hosted/Mac target.
    assert os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted","HOSTED_RUNNER_REQUIRED"
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("CI")=="true"
    run=os.environ["GITHUB_RUN_ID"]
    assert run.isdecimal()
    dest="/usr/local/share/ca-certificates/f3-disposable-"+run+".crt"
    assert not Path(dest).exists(),"UNEXPECTED_CA_ALREADY_PRESENT"
    installed=False
    try:
        subprocess.run(["sudo","install","-m","0644",str(ca),dest],check=True,timeout=20)
        installed=True
        subprocess.run(["sudo","update-ca-certificates"],check=True,timeout=60,capture_output=True)
        yield
    finally:
        if installed:
            subprocess.run(["sudo","rm","-f",dest],check=True,timeout=20)
            subprocess.run(["sudo","update-ca-certificates","--fresh"],check=True,timeout=60,capture_output=True)


class FirefoxProfiles:
    """Persistent profiles are separate per user; only the public lab CA is imported."""
    def __init__(self,engine,ca,root):
        self.engine,self.ca,self.root=engine,ca,Path(root)
        self.count=0

    async def new_context(self,**kwargs):
        assert kwargs.pop("ignore_https_errors",None) is False
        assert kwargs.pop("is_mobile",False) is False
        self.count+=1
        profile=self.root/("user-"+str(self.count))
        profile.mkdir(mode=0o700)
        for args in (["-N","--empty-password"],
                     ["-A","-n","F3 disposable CI CA","-t","C,,","-i",str(self.ca)]):
            subprocess.run(["certutil","-d","sql:"+str(profile),*args],
                           check=True,timeout=15,capture_output=True)
        return await self.engine.launch_persistent_context(
            str(profile),headless=True,ignore_https_errors=False,**kwargs)


async def negative_tls(engine, target):
    browser=await engine.launch(headless=True)
    try:
        ctx=await browser.new_context(ignore_https_errors=False)
        page=await ctx.new_page()
        try:
            await page.goto(target,timeout=15000)
        except PlaywrightError as exc:
            # Generic connectivity failures cannot be treated as TLS rejection.
            value=str(exc).lower()
            assert any(marker in value for marker in (
                "certificate","cert_authority","cert_common_name",
                "unknown_issuer","bad_cert_domain","ssl_error",
                "sec_error","tls error","tls_error",
            )),"EXPECTED_CERTIFICATE_REJECTION"
        else:
            raise AssertionError("UNTRUSTED_CA_ACCEPTED")
        finally:
            await ctx.close()
    finally:
        await browser.close()


async def execute(name):
    verify_isolation()
    assert os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert name in ("firefox","webkit")
    os.environ["PHASE3_APP_MODE"]="APP_ONLY"
    demo=Demo()
    contexts=[]
    browser=None
    try:
        demo.start()
        # Prove the new CA is not already trusted before installing/importing it.
        async with async_playwright() as pw:
            await negative_tls(getattr(pw,name),ORIGIN+"/login")
        with ExitStack() as stack:
            stack.enter_context(isolated_browser_trust(demo.ca))
            profiles=stack.enter_context(tempfile.TemporaryDirectory(prefix="f3-engine-profiles-"))
            if name=="webkit":
                stack.enter_context(hosted_webkit_ca(demo.ca))
            async with async_playwright() as pw:
                engine=getattr(pw,name)
                if name=="firefox":
                    adapter=FirefoxProfiles(engine,demo.ca,profiles)
                else:
                    browser=await engine.launch(headless=True)
                    adapter=browser
                try:
                    out=Path(os.environ["RUNNER_TEMP"])/("f3-"+name)
                    ctx_a,page_a,_,raw_a=await demo.browser_login(adapter,"A",False,out,strict_https=True)
                    contexts.append(ctx_a)
                    ctx_b,page_b,_,raw_b=await demo.browser_login(adapter,"B",False,out,strict_https=True)
                    contexts.append(ctx_b)
                    create_extra_question(demo,"A")
                    create_extra_question(demo,"B")
                    rows,receipts,cluster=inventory(demo)
                    messages=message_inventory(demo)
                    ids_a={r[1] for r in rows if r[0]==demo.owners["A"]}
                    ids_b={r[1] for r in rows if r[0]==demo.owners["B"]}
                    assert len(ids_a)==len(ids_b)==3 and ids_a.isdisjoint(ids_b)
                    for page,label,ids,foreign in ((page_a,"A",ids_a,ids_b),(page_b,"B",ids_b,ids_a)):
                        await browser_history(page,label,ids,demo.owners[label],messages)
                        await mobile_320_keyboard_accessibility(page)
                        await signed_pagination(page,ids)
                        await foreign_owner_denied(page,foreign)
                        await send_denied(page)
                        await account_and_accessibility(page)
                        await browser_history(page,label,ids,demo.owners[label],messages)
                    await cursor_owner_signature_denied(page_a,page_b)
                    assert inventory(demo)==(rows,receipts,cluster)
                    assert message_inventory(demo)==messages
                    # Genuine logout, then original raw signed A/B session checks.
                    tab=await ctx_a.new_page()
                    await tab.goto(ORIGIN+"/login")
                    await expect(tab.get_by_test_id("logout-submit")).to_be_visible()
                    async with tab.expect_response(lambda r:r.url.endswith("/api/auth/logout")
                        and r.request.method=="POST",timeout=25000) as waiting:
                        await tab.get_by_test_id("logout-submit").click()
                    assert (await waiting.value).status==303
                    await expect(tab.get_by_test_id("logout-success")).to_be_visible()
                    assert demo.signed_private(raw_a).status_code==401
                    assert demo.signed_private(raw_b).status_code==200
                    # Auto focus refresh can already have invalidated A. Require
                    # the real DOM, no forced click on an already-disabled button.
                    if await page_a.get_by_test_id("refresh-history").is_enabled():
                        await page_a.get_by_test_id("refresh-history").click()
                    await expect(page_a.get_by_test_id("history-login-required")).to_be_visible()
                    await expect(page_a.locator('[data-testid^="history-message-"]')).to_have_count(0)
                    await expect(page_a.locator('[data-testid^="conversation-"]')).to_have_count(0)
                    await page_b.get_by_test_id("refresh-history").click()
                    await expect(page_b.locator('[data-testid^="conversation-"]').first).to_be_visible()
                    await foreign_owner_denied(page_b,ids_a)
                    assert inventory(demo)==(rows,receipts,cluster)
                    assert message_inventory(demo)==messages
                    receipt={"sha":os.environ["GITHUB_SHA"],"browser":name,
                             "scope":"DISPOSABLE_CI_SIGNED_PRE_RESTORE_ONLY",
                             "strict_https":True,"untrusted_ca_denied":True,
                             "real_two_user_oidc":True,"clicked_sql_dom_detail":True,
                             "mobile_keyboard":True,"cursor_and_foreign_denials":True,
                             "account_read_only_policy_status_and_mobile":True,
                             "skip_link_and_selected_normal_text_contrast":True,
                             "send_503_no_history_mutation":True,
                             "original_session_a_401_b_200":True,"revoked_dom_empty":True,
                             "restore_tested":False,"target_accepted":False,
                             "engine_calls":0,"sql_011":False}
                    output=ROOT/"ci_receipts"/"f3_cross_engine_signed.json"
                    output.parent.mkdir(parents=True,exist_ok=True)
                    output.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
                    print("F3_REAL_"+name.upper()+"_STRICT_OIDC_AB_SQL_DOM_REVOKE_PASS",flush=True)
                finally:
                    for ctx in contexts:
                        await ctx.close()
                    if browser is not None:await browser.close()
    finally:
        demo.stop()


if __name__=="__main__":
    asyncio.run(execute(sys.argv[1]))
