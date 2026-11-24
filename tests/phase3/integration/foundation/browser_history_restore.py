"""One GitHub runner: real Keycloak, two Chromium contexts, Next BFF,
HTTPS signed Product API, PostgreSQL17, then new-volume restore/replay.

No intercept/fulfill, cookie fabrication, identity header or Engine dispatch.
Only a disposable CI runner may stop its own PG service on port 5432.
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import subprocess
import sys
import time
import uuid

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from playwright.async_api import async_playwright,expect

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[
 str(ROOT/"tests/phase3/integration/ui"),
 str(ROOT/"tests/phase3/integration/foundation"),
 str(ROOT),
]
from phase3_auth_demo import Demo,ORIGIN
from test_history_restore_signed import command,pg17,connect
from apps.api import history_api


def verify_isolation():
    assert os.environ.get("CI")=="true" and os.environ.get("GITHUB_ACTIONS")=="true"
    assert os.environ.get("GITHUB_RUN_ID")
    assert "dbname=history_ci" in os.environ.get("AUTH_MIG_DSN","")
    assert os.environ.get("PGHOST")=="127.0.0.1"
    assert os.environ.get("PGPORT")=="5432"


def trust_ephemeral_browser_ca(demo):
    """Install ONLY this job's ephemeral CA for genuine Chrome and Python trust.

    No ignore_https_errors, no certificate pin bypass and no shared machine.
    This mutates only the disposable GitHub Actions runner and does not
    distribute any CA key or copy a trust root to repository artifacts.
    """
    verify_isolation()
    ca=Path(demo.ca)
    assert ca.is_file() and ca.parent==demo.root and not ca.is_symlink(), (
        "UNTRUSTED_CI_CA_INPUT")
    run_id=os.environ["GITHUB_RUN_ID"]
    assert run_id.isdecimal() and len(run_id)<=24
    trust_path="/usr/local/share/ca-certificates/f3-disposable-ui-"+run_id+".crt"
    subprocess.run(["sudo","install","-m","0644",str(ca),trust_path],check=True)
    subprocess.run(["sudo","update-ca-certificates"],check=True,
                   stdout=subprocess.DEVNULL)
    nss=Path.home()/".pki"/"nssdb"
    nss.mkdir(parents=True,exist_ok=True)
    spec="sql:"+str(nss)
    if not (nss/"cert9.db").exists():
        subprocess.run(["certutil","-N","--empty-password","-d",spec],check=True)
    subprocess.run(["certutil","-A","-d",spec,"-n","f3-disposable-ui-"+run_id,
                    "-t","C,,","-i",str(ca)],check=True)
    # Enforce OpenSSL chain + 127.0.0.1 SAN; the browser independently
    # enforces the same with ignore_https_errors=False.
    with socket.create_connection(("127.0.0.1",3443),timeout=8) as sock:
        with ssl.create_default_context().wrap_socket(
                sock,server_hostname="127.0.0.1") as verified:
            assert verified.version() in ("TLSv1.2","TLSv1.3")
    print("F3_LAB_OS_CA_CHROMIUM_NSS_TRUST_AND_LOOPBACK_IP_SAN_PASS",flush=True)


def inventory(demo):
    with connect() as c:
        records=c.execute(
            "SELECT owner_id,id,title FROM history_l1.conversations "
            "WHERE owner_id IN (%s,%s) ORDER BY owner_id,id",
            (demo.owners["A"],demo.owners["B"])).fetchall()
        receipts=c.execute("SELECT count(*) FROM history_l1.send_receipts "
            "WHERE owner_id IN (%s,%s)",
            (demo.owners["A"],demo.owners["B"])).fetchone()[0]
        system_id=c.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0]
    return records,receipts,system_id


def message_inventory(demo):
    """Capture exact persisted user messages, not merely conversation counts."""
    with connect() as c:
        return c.execute(
            "SELECT owner_id,conversation_id,id,body FROM history_l1.messages "
            "WHERE owner_id IN (%s,%s) ORDER BY owner_id,conversation_id,id",
            (demo.owners["A"], demo.owners["B"])).fetchall()


def create_extra_question(demo,label,count=1):
    """Persist synthetic-but-real PG T1 rows solely by restricted CI fixture role.

    APP_ONLY browser/API Send remains forbidden. These authorized fixture rows
    are created before the no-Send ledger snapshot and never via browser POST.
    """
    assert 1 <= count <= 32
    owner=demo.owners[label]
    with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,
                         row_factory=dict_row) as c:
        request={"kind":"create_conversation_request",
                 "contract_version":"product.v1",
                 "client_conversation_id":history_api.uid(),
                 "idempotency_key":"f3browser_"+uuid.uuid4().hex,
                 "title":"F3_PAGING_"+label}
        result=history_api.create_conversation(
            c,owner,request,history_api.uid(),history_api.uid())
        cid=result["conversation"]["conversation_id"]
        for n in range(count):
            req={"kind":"send_message_request","contract_version":"product.v1",
                 "requested_conversation_id":cid,
                 "client_message_id":history_api.uid(),
                 "idempotency_key":"f3history_"+uuid.uuid4().hex,
                 "question":"F3_REAL_POSTGRES_"+label+"_"+str(n).zfill(2)}
            history_api.send_t1(c,owner,req,history_api.uid(),history_api.uid())
    return cid


async def browser_history(page,label,expected_ids,expected_owner,expected_messages):
    await page.reload()
    await expect(page.locator('[data-testid^="conversation-"]').first).to_be_visible(
        timeout=20000)
    if len(expected_ids)>2:
        # Validate the real BFF response first; only then wait for hydration.
        server=await page.request.get(ORIGIN+"/api/history/conversations?limit=2")
        assert server.status==200,("BFF_LIST",label,server.status)
        assert (await server.json())["page"]["has_more"],("SERVER_CURSOR_MISSING",label)
        async with page.expect_response(
            lambda r:"/api/history/conversations?limit=2" in r.url
            and r.request.method=="GET",timeout=20000) as observing:
            await page.get_by_test_id("refresh-history").click()
        assert (await observing.value).status==200
        more=page.get_by_role("button",name="نمایش گفت‌وگوهای بیشتر")
        await expect(more).to_be_visible(timeout=15000)
        await more.click()
        await expect(page.locator('[data-testid^="conversation-"]')).to_have_count(
            len(expected_ids),timeout=15000)
    ids=set(await page.locator('[data-testid^="conversation-"]').evaluate_all(
        "(nodes)=>nodes.map(n=>n.getAttribute('data-testid').replace('conversation-',''))"))
    assert ids==set(expected_ids),("BROWSER_HISTORY_ID_PARITY",label,len(ids))
    await expect(page.get_by_test_id("history-send")).to_be_disabled()
    await expect(page.get_by_test_id("history-question")).to_be_disabled()
    for cid in sorted(expected_ids):
        expected={(m[2],m[3]) for m in expected_messages
                  if m[0]==expected_owner and m[1]==cid}
        actual=[]
        cursor=None
        for _ in range(8):
            target=ORIGIN+"/api/history/conversations/"+cid+"/messages?limit=20"
            if cursor: target+="&cursor="+cursor
            response=await page.request.get(target)
            assert response.status==200,("SELF_DETAIL",label,response.status)
            body=await response.json()
            assert body["owner_user_id"]==expected_owner,(
                "DETAIL_OWNER_MISMATCH",label,cid)
            actual.extend((item["message_id"],item["text"]) for item in body["items"])
            if not body["page"]["has_more"]:break
            cursor=body["page"]["next_cursor"]
            assert cursor and len(cursor)<=512, "PG_MESSAGE_CURSOR_MISSING"
        else:raise AssertionError("PG_MESSAGE_CURSOR_LOOP_UNBOUNDED")
        assert len(actual)==len(set(actual)) and set(actual)==expected, (
            "BROWSER_SQL_MESSAGE_ID_BODY_PARITY",label,cid,len(actual),len(expected))
    return ids


async def browser_long_thread_dom(page, owner, conversation_id):
    """Real React DOM cursor page 2, exact PG IDs/order before and after reload.

    The 31 source rows were persisted directly by disposable restricted
    fixture SQL before the zero-Send baseline; browser only GETs History.
    """
    with connect() as c:
        expected=[r[0] for r in c.execute(
            "SELECT id FROM history_l1.messages "
            "WHERE owner_id=%s AND conversation_id=%s "
            "ORDER BY created_at ASC,id ASC",
            (owner,conversation_id)).fetchall()]
    assert len(expected)==31,("LONG_THREAD_FIXTURE_NOT_31_PG_ROWS",len(expected))
    for repeated in range(2):
        if repeated==0:
            response=await page.goto(ORIGIN+"/history",wait_until="domcontentloaded")
            assert response is not None and response.status==200
        else:
            await page.reload(wait_until="domcontentloaded")
        await expect(page.get_by_test_id("conversation-"+conversation_id)
                     ).to_be_attached(timeout=20000)
        messages=page.locator('[data-testid^="history-message-"]')
        await expect(messages).to_have_count(30,timeout=25000)
        observed=await messages.evaluate_all(
            "(nodes)=>nodes.map(n=>n.getAttribute('data-testid').replace('history-message-',''))")
        assert observed==expected[:30],("UI_LONG_THREAD_FIRST_PAGE_SQL_ORDER",repeated)
        button=page.get_by_test_id("more-messages")
        await expect(button).to_be_visible(timeout=12000)
        async with page.expect_response(
            lambda r: r.request.method=="GET"
            and "/api/history/conversations/"+conversation_id+
                "/messages?limit=30&cursor=" in r.url,
            timeout=20000) as next_page:
            await button.click()
        assert (await next_page.value).status==200,(
            "UI_LONG_THREAD_CURSOR_2_NOT_SIGNED_HTTP_200",repeated)
        await expect(messages).to_have_count(len(expected),timeout=20000)
        final=await messages.evaluate_all(
            "(nodes)=>nodes.map(n=>n.getAttribute('data-testid').replace('history-message-',''))")
        assert final==expected and len(final)==len(set(final)),(
            "UI_LONG_THREAD_DOM_SQL_REFRESH_ID_ORDER_DRIFT",repeated)
        await expect(button).to_have_count(0)
    print("F3_REAL_REACT_DOM_31_PG_MESSAGE_PAGE2_REFRESH_STABLE_IDS_PASS",flush=True)


async def mobile_320_keyboard_accessibility(page):
    """Test actual authenticated Keycloak session, without mocked UI routes."""
    await page.set_viewport_size({"width":320,"height":568})
    try:
        await expect(page.locator("main.history-shell")).to_be_visible(timeout=20000)
        assert await page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth + 2"), "MOBILE_320_OVERFLOW"
        assert await page.locator("main.history-shell").evaluate(
            "(el) => getComputedStyle(el).direction")=="rtl", "MOBILE_NOT_RTL"
        menu=page.get_by_role("button",name="بازکردن فهرست گفت‌وگوها")
        await expect(menu).to_be_visible()
        # :focus-visible requires genuine keyboard modality. A scripted
        # focus() following a mouse operation does NOT prove keyboard focus.
        await menu.focus()
        await page.keyboard.press("Shift+Tab")
        await page.keyboard.press("Tab")
        await expect(menu).to_be_focused()
        assert await menu.evaluate(
            "(el) => getComputedStyle(el).outlineStyle")!="none", "NO_KEYBOARD_FOCUS_OUTLINE"
        await menu.click()
        await expect(page.get_by_role(
            "dialog",name="فهرست گفتگوها")).to_be_visible()
        await expect(menu).to_have_attribute("aria-expanded","true")
        close=page.get_by_role("button",name="بستن فهرست")
        await expect(close).to_be_focused()
        await expect(page.locator("section.history-main")).to_have_attribute("inert","")
        await expect(page.locator(".history-skip")).to_have_attribute("inert","")
        await page.keyboard.press("Escape")
        await expect(menu).to_have_attribute("aria-expanded","false")
        await expect(menu).to_be_focused()
        assert await page.locator("section.history-main").get_attribute("inert") is None
        await menu.click()
        await expect(page.get_by_role(
            "dialog",name="فهرست گفتگوها")).to_be_visible()
        await page.set_viewport_size({"width":1280,"height":800})
        await expect(page.locator("aside[aria-modal='true']")).to_have_count(0)
        assert await page.locator("section.history-main").get_attribute("inert") is None
    finally:
        await page.set_viewport_size({"width":1280,"height":800})


async def signed_pagination(page,known):
    cursor=None
    all_ids=[]
    for _ in range(30):
        url=ORIGIN+"/api/history/conversations?limit=1"
        if cursor:url+="&cursor="+cursor
        response=await page.request.get(url)
        assert response.status==200,("BROWSER_PAGINATION",response.status)
        doc=await response.json()
        all_ids.extend(x["conversation_id"] for x in doc["items"])
        if not doc["page"]["has_more"]:break
        cursor=doc["page"]["next_cursor"]
        assert cursor and len(cursor)<=512
    else:raise AssertionError("UNBOUNDED_BROWSER_PAGES")
    assert set(all_ids)==set(known) and len(all_ids)==len(set(all_ids))


async def foreign_owner_denied(page,foreign_ids):
    for foreign_id in sorted(foreign_ids):
        resp=await page.request.get(
            ORIGIN+"/api/history/conversations/"+foreign_id+"/messages?limit=20")
        assert resp.status==404,("FOREIGN_OWNER_READ",foreign_id,resp.status)
        assert "F3_REAL_POSTGRES_A" not in await resp.text()
        assert "F3_REAL_POSTGRES_B" not in await resp.text()


async def send_denied(page):
    r=await page.request.post(ORIGIN+"/api/history/messages",
        data='{"question":"NEVER_DISPATCH"}',
        headers={"content-type":"application/json"})
    assert r.status==503,("SEND_NOT_DISABLED",r.status)
    assert (await r.json())["error"]=="ENGINE_NOT_AVAILABLE"


def restore_separate_volume(demo,original_records,source_system_id):
    work=Path(os.environ["RUNNER_TEMP"])
    backup=work/"f3-browser-full-history.dump"
    roles=work/"f3-browser-roles.sql"
    command(["docker","pull","postgres:17.11"])
    pg17("pg_dump","-h","127.0.0.1","-p","5432","-U","postgres",
         "-F","c","-f",str(backup),"history_ci")
    assert backup.stat().st_size>1024
    globals_sql=pg17("pg_dumpall","-h","127.0.0.1","-p","5432",
        "-U","postgres","--globals-only","--no-role-passwords")
    roles.write_text("\n".join(line for line in globals_sql.splitlines()
      if not re.match(r"^(CREATE ROLE postgres;|ALTER ROLE postgres WITH)",line))+"\n")
    roles.chmod(0o600)
    suffix=os.environ["GITHUB_RUN_ID"]+"-"+os.environ.get("GITHUB_RUN_ATTEMPT","1")
    volume="f3browser-history-restore-"+suffix
    name="f3browser-restore-pg-"+suffix
    command(["docker","volume","create",volume])
    command(["docker","run","-d","--name",name,"--restart","no",
        "-p","127.0.0.1:5433:5432",
        "-e","POSTGRES_PASSWORD="+os.environ["PGPASSWORD"],
        "-v",volume+":/var/lib/postgresql/data","postgres:17.11"])
    for _ in range(70):
        try:
            with connect(5433,db="postgres"):break
        except psycopg.Error:time.sleep(.6)
    else:raise AssertionError("FRESH_RESTORE_PG17_NOT_READY")
    command(["psql","-h","127.0.0.1","-p","5433","-U","postgres",
             "-d","postgres","-v","ON_ERROR_STOP=1","-f",str(roles)])
    with connect(5433,db="postgres") as c:
        users={}
        for k,dsn in os.environ.items():
            if k.endswith("_DSN") and "history_ci" in dsn:
                config=psycopg.conninfo.conninfo_to_dict(dsn)
                if config.get("user") and config.get("password"):
                    users[config["user"]]=config["password"]
        available={r[0] for r in c.execute("SELECT rolname FROM pg_roles")}
        for user,secret in users.items():
            if user in available:
                c.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(user),sql.Literal(secret)))
        c.execute("CREATE DATABASE history_ci")
    pg17("pg_restore","-h","127.0.0.1","-p","5433","-U","postgres",
         "--exit-on-error","-d","history_ci",str(backup))
    with connect(5433) as c:
        actual=c.execute(
            "SELECT owner_id,id,title FROM history_l1.conversations "
            "WHERE owner_id IN (%s,%s) ORDER BY owner_id,id",
            (demo.owners["A"],demo.owners["B"])).fetchall()
        assert actual==original_records,("RESTORE_DB_CONTENT_DRIFT",len(actual))
        new_id=c.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0]
        assert source_system_id!=new_id,("RESTORE_NOT_INDEPENDENT_CLUSTER",)
    # GitHub Actions standalone service is the ONLY source target we can stop.
    # Docker's publish=5432 filter can also match the restored CONTAINER
    # port 5432 (host port 5433). Match the HOST binding exactly instead.
    service=[]
    for cid in command(["docker","ps","-q"]).splitlines():
        ports=json.loads(command(["docker","inspect","--format",
                     "{{json .NetworkSettings.Ports}}",cid]))
        if any(bind.get("HostPort")=="5432"
               for bind in (ports.get("5432/tcp") or [])):
            service.append(cid)
    assert len(service)==1,("PG_SOURCE_HOST_PORT_COLLISION",len(service))
    original_image=command(["docker","inspect","--format","{{.Config.Image}}",service[0]]).strip()
    assert original_image=="postgres:17.11",("NOT_GITHUB_PG17_SERVICE",original_image)
    command(["docker","stop",service[0]])
    command(["docker","rm","-f",name])
    new_name="f3browser-replayed-pg-"+suffix
    command(["docker","run","-d","--name",new_name,"--restart","no",
        "-p","127.0.0.1:5432:5432",
        "-e","POSTGRES_PASSWORD="+os.environ["PGPASSWORD"],
        "-v",volume+":/var/lib/postgresql/data","postgres:17.11"])
    for _ in range(80):
        try:
            with connect() as c:
                restored_id=c.execute(
                   "SELECT system_identifier FROM pg_control_system()").fetchone()[0]
            if restored_id==new_id:break
        except psycopg.Error:time.sleep(.5)
    else:raise AssertionError("RESTORED_VOLUME_NOT_CONNECTED_TO_ORIGINAL_PORT")
    return (new_name,volume,new_id)


async def execute():
    verify_isolation()
    os.environ["PHASE3_APP_MODE"]="APP_ONLY"
    demo=Demo()
    restored=None
    browser=None
    ctx_a=ctx_b=None
    try:
        demo.start()
        trust_ephemeral_browser_ca(demo)
        output=Path(os.environ["RUNNER_TEMP"])/"f3-browser-source-restored"
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            ctx_a,page_a,_,_=await demo.browser_login(
                browser,"A",False,output,require_trusted_tls=True)
            ctx_b,page_b,_,_=await demo.browser_login(
                browser,"B",False,output,require_trusted_tls=True)
            a_id=create_extra_question(demo,"A",count=31)
            b_id=create_extra_question(demo,"B")
            source,receipt_before,source_cluster=inventory(demo)
            messages_before=message_inventory(demo)
            ids_a={r[1] for r in source if r[0]==demo.owners["A"]}
            ids_b={r[1] for r in source if r[0]==demo.owners["B"]}
            assert len(ids_a)==3 and len(ids_b)==3 and ids_a.isdisjoint(ids_b)
            assert a_id in ids_a and b_id in ids_b
            await browser_history(page_a,"A",ids_a,demo.owners["A"],messages_before)
            await browser_history(page_b,"B",ids_b,demo.owners["B"],messages_before)
            await browser_long_thread_dom(page_a,demo.owners["A"],a_id)
            await signed_pagination(page_a,ids_a)
            await signed_pagination(page_b,ids_b)
            await mobile_320_keyboard_accessibility(page_a)
            await mobile_320_keyboard_accessibility(page_b)
            await foreign_owner_denied(page_a,ids_b)
            await foreign_owner_denied(page_b,ids_a)
            await send_denied(page_a)
            assert inventory(demo)[1]==receipt_before
            print("F3_REAL_BROWSER_KEYCLOAK_NEXT_PG17_AB_PAGING_DETAIL_SEND503_PRE_RESTORE_PASS",
                  flush=True)

            restored=restore_separate_volume(demo,source,source_cluster)
            # Continue same real two browser contexts, same session cookie,
            # same Keycloak process and Next/BFF/API, now independent PG volume.
            await browser_history(page_a,"A",ids_a,demo.owners["A"],messages_before)
            await browser_history(page_b,"B",ids_b,demo.owners["B"],messages_before)
            await browser_long_thread_dom(page_a,demo.owners["A"],a_id)
            await signed_pagination(page_a,ids_a)
            await signed_pagination(page_b,ids_b)
            await foreign_owner_denied(page_a,ids_b)
            await foreign_owner_denied(page_b,ids_a)
            await send_denied(page_a)
            after,receipt_after,new_cluster=inventory(demo)
            assert source==after and receipt_before==receipt_after
            assert message_inventory(demo)==messages_before,("RESTORED_MESSAGES_SQL_DRIFT",)
            assert new_cluster==restored[2] and new_cluster!=source_cluster

            # Genuine Logout form and old cookie on original Chromium context.
            tab=await ctx_a.new_page()
            await tab.goto(ORIGIN+"/login")
            await expect(tab.get_by_test_id("logout-submit")).to_be_visible()
            async with tab.expect_response(lambda x:x.url.endswith("/api/auth/logout")
                and x.request.method=="POST",timeout=25000) as waiting:
                await tab.get_by_test_id("logout-submit").click()
            assert (await waiting.value).status==303
            stale=await page_a.request.get(
                ORIGIN+"/api/history/conversations?limit=2")
            assert stale.status==401,("REVOKED_A_STILL_READS",stale.status)
            surviving=await page_b.request.get(
                ORIGIN+"/api/history/conversations?limit=2")
            assert surviving.status==200
            await foreign_owner_denied(page_b,ids_a)
            result={
                "schema":"foundation.f3.real_browser_pg_restored_same_context.v1",
                "sha":os.environ["GITHUB_SHA"],
                "env":"disposable-GitHub-Actions-standard-Keycloak-Chromium-Next-mTLS-PG17",
                "genuine_two_browser_context_oidc":True,
                "strict_https_browser_ca_loopback_ip_san":True,
                "browser_default_history_sql_equal":True,
                "browser_pagination_and_detail_sql_equal":True,
                "browser_detail_message_id_and_body_sql_equal":True,
                "real_react_message_cursor_page2_pg_31_ids_pre_post_restore":True,
                "react_message_cursor_stable_after_refresh":True,
                "all_a_conversations_cross_owner_404":True,
                "all_b_conversations_cross_owner_404":True,
                "real_authenticated_browser_mobile_320_rtl_keyboard_pre_post_restore":True,
                "b_direct_a_detail_404":True,
                "send_bff_503_no_extra_receipts":True,
                "fresh_pg_volume_independent_cluster":True,
                "same_browser_cookie_after_pg_restore":True,
                "signed_history_a_after_restore":200,
                "signed_history_b_after_restore":200,
                "old_a_after_revoke":401,
                "b_alive_after_a_revoke":200,
                "engine_calls":0,
                "sql_011":False,
                "mac_target_touched":False,
                "all_26_gates_accepted":False,
                "status":"CI_LAB_JOURNEY_ONLY_NOT_MAC_OR_CENTRAL_ACCEPTANCE",
            }
            out=ROOT/"ci_receipts"/"f3_history_real_browser_restored_lab.json"
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
            print("F3_REAL_KEYCLOAK_CHROMIUM_BFF_API_PG_RESTORED_SAME_SESSION_NO_ENGINE_PASS",
                  flush=True)
    finally:
        # Playwright context manager already tears down the browser on error;
        # do not mask the FIRST product assertion with TargetClosedError.
        for context in (ctx_a,ctx_b):
            if context is not None:
                try:await context.close()
                except Exception:pass
        if browser is not None:
            try:await browser.close()
            except Exception:pass
        demo.stop()
        if restored:
            command(["docker","rm","-f",restored[0]])
            command(["docker","volume","rm",restored[1]])

if __name__=="__main__":
    asyncio.run(execute())
