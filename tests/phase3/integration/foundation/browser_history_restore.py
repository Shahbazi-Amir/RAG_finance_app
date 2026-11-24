"""One GitHub runner: real Keycloak, two Chromium contexts, Next BFF,
HTTPS signed Product API, PostgreSQL17, then new-volume restore/replay.

No intercept/fulfill, cookie fabrication, identity header or Engine dispatch.
Only a disposable CI runner may stop its own PG service on port 5432.
"""
from __future__ import annotations
import asyncio
import hashlib
import math
import json
import os
from pathlib import Path
import re
import secrets
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
from test_history_restore_signed import command,pg17,connect as pg_connect,ssl_server
from apps.api import history_api

# This runner preserves the original history_ci test DB. A distinctly named
# clone is created only inside the disposable runner for the real listener.
PRIVATE_DB="history_ci_f3_signed"
PG_TLS=None
DB_NAME="history_ci"

def connect(port_number=5432, *, db=None):
    chosen=db or DB_NAME
    extra=("sslmode=verify-full sslrootcert="+str(PG_TLS[0])
           if PG_TLS is not None and chosen==PRIVATE_DB else "")
    return pg_connect(port_number,db=chosen,extra=extra)

def source_service():
    candidates=[]
    for cid in command(["docker","ps","-q"]).splitlines():
        ports=json.loads(command(["docker","inspect","--format",
                     "{{json .NetworkSettings.Ports}}",cid]))
        if any(b.get("HostPort")=="5432" for b in (ports.get("5432/tcp") or [])):
            candidates.append(cid)
    assert len(candidates)==1,("PG_SOURCE_HOST_PORT_COLLISION",len(candidates))
    assert command(["docker","inspect","--format","{{.Config.Image}}",
                    candidates[0]]).strip()=="postgres:17.11"
    return candidates[0]

def install_pg_tls(container, port_number):
    ca,key,crt=PG_TLS
    for src,dst in ((key,"server.key"),(crt,"server.crt")):
        target="/var/lib/postgresql/data/"+dst
        command(["docker","cp",str(src),container+":"+target])
        command(["docker","exec","-u","0",container,"chown","postgres:postgres",target])
    command(["docker","exec","-u","0",container,"chmod","0600",
             "/var/lib/postgresql/data/server.key"])
    with pg_connect(port_number,db="postgres") as admin:
        admin.execute("ALTER SYSTEM SET ssl='on'")
        admin.execute("ALTER SYSTEM SET ssl_cert_file='server.crt'")
        admin.execute("ALTER SYSTEM SET ssl_key_file='server.key'")
    command(["docker","restart",container])
    for _ in range(60):
        try:
            with pg_connect(port_number,db="postgres",
                extra="sslmode=verify-full sslrootcert="+str(ca)) as c:
                if c.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]:
                    return
        except psycopg.Error:time.sleep(.5)
    raise AssertionError("BROWSER_LAB_PG_TLS_NOT_VERIFIED")

def prepare_private_database():
    global PG_TLS,DB_NAME
    root=Path(os.environ["RUNNER_TEMP"])/"f3-browser-private-pg-tls"
    root.mkdir(mode=0o700)
    PG_TLS=ssl_server(root, include_private_dns=os.getenv("F3_BROWSER_SIGNED_IMAGE")=="1")
    install_pg_tls(source_service(),5432)
    updates={}
    roles=set()
    for k,v in os.environ.items():
        if not k.endswith("_DSN"):continue
        opts=psycopg.conninfo.conninfo_to_dict(v)
        if opts.get("dbname")!="history_ci":continue
        assert opts.get("host")=="127.0.0.1" and opts.get("port")=="5432"
        roles.add(opts["user"])
        updates[k]=psycopg.conninfo.make_conninfo(v,dbname=PRIVATE_DB,
            sslmode="verify-full",sslrootcert=str(PG_TLS[0]))
    assert {"DB_APP_DSN","AUTH_REVOKER_DSN","AUTH_MIG_DSN"} <= updates.keys()
    with pg_connect(db="postgres") as c:
        c.execute(sql.SQL("CREATE DATABASE {} TEMPLATE history_ci").format(sql.Identifier(PRIVATE_DB)))
        c.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(PRIVATE_DB)))
        for role in sorted(roles):
            c.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(PRIVATE_DB),sql.Identifier(role)))
    DB_NAME=PRIVATE_DB
    os.environ.update(updates)
    # Actual product-role TLS, not just a postgres superuser probe.
    for name in ("DB_APP_DSN","AUTH_REVOKER_DSN"):
        with psycopg.connect(os.environ[name]) as c:
            assert c.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]

def verify_isolation():
    assert os.environ.get("CI")=="true" and os.environ.get("GITHUB_ACTIONS")=="true"
    assert os.environ.get("GITHUB_RUN_ID")
    assert "dbname=history_ci" in os.environ.get("AUTH_MIG_DSN","")
    assert os.environ.get("PGHOST")=="127.0.0.1"
    assert os.environ.get("PGPORT")=="5432"


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


def create_extra_question(demo,label):
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
        req={"kind":"send_message_request","contract_version":"product.v1",
             "requested_conversation_id":cid,
             "client_message_id":history_api.uid(),
             "idempotency_key":"f3history_"+uuid.uuid4().hex,
             "question":"F3_REAL_POSTGRES_"+label}
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
        response=await page.request.get(
            ORIGIN+"/api/history/conversations/"+cid+"/messages?limit=20")
        assert response.status==200,("SELF_DETAIL",label,response.status)
        body=await response.json()
        assert body["owner_user_id"]==expected_owner,("DETAIL_OWNER_MISMATCH",label,cid)
        expected={(m[2],m[3]) for m in expected_messages
                  if m[0]==expected_owner and m[1]==cid}
        actual=[(item["message_id"],item["text"]) for item in body["items"]]
        assert len(actual)==len(set(actual)) and set(actual)==expected, (
            "BROWSER_SQL_MESSAGE_ID_BODY_PARITY",label,cid,len(actual),len(expected))
        assert response.headers.get("cache-control")=="no-store"
        # Open actual conversation; prove rendered user message matches SQL,
        # not just HTTP JSON. Seeded demo contains user messages only.
        thread=page.get_by_test_id("conversation-"+cid)
        await thread.click()
        await expect(thread).to_have_attribute("aria-current","page")
        await expect(page.locator('[data-testid^="history-message-"]')).to_have_count(len(expected))
        for mid,body_text in expected:
            message=page.get_by_test_id("history-message-"+mid)
            await expect(message.locator(".history-message-text")).to_have_text(body_text)
        assert set(await page.locator('[data-testid^="history-message-"]').evaluate_all(
            "(nodes)=>nodes.map(n=>n.dataset.testid.replace('history-message-',''))"))=={x[0] for x in expected}
        foreign_marker="F3_REAL_POSTGRES_"+("B" if label=="A" else "A")
        assert foreign_marker not in await page.locator("main.history-shell").inner_text()
    return ids


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


async def cursor_owner_signature_denied(page_a,page_b):
    """Actual signed cursor is bound to the authenticated owner and HMAC."""
    results=[]
    for page in (page_a,page_b):
        response=await page.request.get(
            ORIGIN+"/api/history/conversations?limit=1")
        assert response.status==200,("CURSOR_SOURCE",response.status)
        doc=await response.json()
        assert doc["page"]["has_more"],"MISSING_REAL_PAGINATION"
        cursor=doc["page"]["next_cursor"]
        assert cursor and len(cursor)<=512
        results.append(cursor)
    for original,foreign,cursor in (
        (page_a,page_b,results[0]),(page_b,page_a,results[1])):
        foreign_resp=await foreign.request.get(
            ORIGIN+"/api/history/conversations?limit=1&cursor="+cursor)
        assert foreign_resp.status==404,("CURSOR_OWNER_FENCE",foreign_resp.status)
        tampered=("B" if cursor[0]!="B" else "A")+cursor[1:]
        bad=await original.request.get(
            ORIGIN+"/api/history/conversations?limit=1&cursor="+tampered)
        assert bad.status==422,("CURSOR_SIGNATURE_TAMPER",bad.status)
        wrong_limit=await original.request.get(
            ORIGIN+"/api/history/conversations?limit=2&cursor="+cursor)
        assert wrong_limit.status==422,("CURSOR_LIMIT_BIND",wrong_limit.status)


async def foreign_owner_denied(page,foreign_ids):
    for foreign_id in sorted(foreign_ids):
        resp=await page.request.get(
            ORIGIN+"/api/history/conversations/"+foreign_id+"/messages?limit=20")
        assert resp.status==404,("FOREIGN_OWNER_READ",foreign_id,resp.status)
        assert resp.headers.get("cache-control")=="no-store"
        assert "F3_REAL_POSTGRES_A" not in await resp.text()
        assert "F3_REAL_POSTGRES_B" not in await resp.text()


async def send_denied(page):
    # APP_ONLY must reject *before* parsing bytes or idempotency fields.
    # Test retries and corrupted payload, not just a happy-path 503.
    cases=[
        ('{"question":"NEVER_DISPATCH"}',{"content-type":"application/json"}),
        ('{"question":"NEVER_DISPATCH","idempotency_key":"f3_retry_same_key_12345678"}',
         {"content-type":"application/json"}),
        ('{"question":"NEVER_DISPATCH","idempotency_key":"f3_retry_same_key_12345678"}',
         {"content-type":"application/json"}),
        ('{"invalid":"json"',{"content-type":"application/json"}),
        ("X"*65536,{"content-type":"text/plain"}),
    ]
    for body,headers in cases:
        r=await page.request.post(ORIGIN+"/api/history/messages",
            data=body,headers=headers)
        assert r.status==503,("SEND_NOT_DISABLED_OR_PAYLOAD_PARSED",r.status)
        assert (await r.json())["error"]=="ENGINE_NOT_AVAILABLE"


async def measure_history_requests(page_a,page_b,owner_a,owner_b):
    # Bounded synthetic observations, not approved workload/SLO.
    values=[]
    async def one(page,owner):
        start=time.monotonic()
        response=await page.request.get(ORIGIN+"/api/history/conversations?limit=2")
        elapsed=round(1000*(time.monotonic()-start),3)
        assert response.status==200
        assert (await response.json())["scope_user_id"]==owner
        assert response.headers.get("cache-control")=="no-store"
        values.append(elapsed)
    for _ in range(4):
        await one(page_a,owner_a)
        await one(page_b,owner_b)
    sequential=list(values)
    values.clear()
    for _ in range(4):
        await asyncio.gather(one(page_a,owner_a),one(page_b,owner_b))
    def summary(data):
        ordered=sorted(data)
        def percentile(p):return ordered[math.ceil(p*len(ordered))-1]
        return {"n":len(ordered),"p50_ms":percentile(.5),"p95_ms":percentile(.95),
                "p99_ms":percentile(.99),"max_ms":max(ordered),"errors":0}
    return {"serial":summary(sequential),"two_concurrent":summary(values),
            "engine_metrics":None,"approved_workload":False,"approved_slo":None}


def protected_backup_roundtrip(paths,root):
    # Only synthetic disposable DB data. Ephemeral key stays in memory;
    # raw backup is needed during pg_dump and pg_restore, mode 0600.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag
    key=AESGCM.generate_key(bit_length=256)
    cipher=AESGCM(key)
    evidence=[]
    for p in paths:
        assert p.stat().st_mode&0o777==0o600
        content=p.read_bytes()
        nonce=secrets.token_bytes(12)
        aad=p.name.encode("ascii")
        encrypted=nonce+cipher.encrypt(nonce,content,aad)
        target=root/(p.name+".aesgcm")
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:f.write(encrypted)
        assert target.stat().st_mode&0o777==0o600
        p.unlink()
        assert not p.exists()
        payload=target.read_bytes()
        try:
            AESGCM(AESGCM.generate_key(bit_length=256)).decrypt(payload[:12],payload[12:],aad)
        except InvalidTag:
            pass
        else:raise AssertionError("WRONG_BACKUP_KEY_ACCEPTED")
        try:
            cipher.decrypt(payload[:12],payload[12:-1]+bytes([payload[-1]^1]),aad)
        except InvalidTag:
            pass
        else:raise AssertionError("TAMPERED_BACKUP_ACCEPTED")
        plain=cipher.decrypt(payload[:12],payload[12:],aad)
        assert hashlib.sha256(plain).digest()==hashlib.sha256(content).digest()
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:f.write(plain)
        evidence.append({"name":p.name,"bytes":len(content),"plaintext_sha256":hashlib.sha256(plain).hexdigest(),
                        "encrypted_sha256":hashlib.sha256(payload).hexdigest(),"mode":"0600",
                        "wrong_key_and_tamper_denied":True})
        target.unlink()
    return evidence


def restore_separate_volume(demo,original_records,source_system_id):
    work=Path(os.environ["RUNNER_TEMP"])/"f3-browser-protected-backup"
    work.mkdir(mode=0o700)
    backup=work/"f3-browser-full-history.dump"
    roles=work/"f3-browser-roles.sql"
    backup.touch(mode=0o600,exist_ok=False)
    command(["docker","pull","postgres:17.11"])
    pg17("pg_dump","-h","127.0.0.1","-p","5432","-U","postgres",
         "-F","c","-f",str(backup),DB_NAME)
    assert backup.stat().st_size>1024
    globals_sql=pg17("pg_dumpall","-h","127.0.0.1","-p","5432",
        "-U","postgres","--globals-only","--no-role-passwords")
    roles.write_text("\n".join(line for line in globals_sql.splitlines()
      if not re.match(r"^(CREATE ROLE postgres;|ALTER ROLE postgres WITH)",line))+"\n")
    roles.chmod(0o600)
    demo.backup_evidence=protected_backup_roundtrip((backup,roles),work)
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
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        if demo.private_product:
            c.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(DB_NAME)))
            for role in sorted(users):
                if role in available:
                    c.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(DB_NAME),sql.Identifier(role)))
    if demo.private_product:
        install_pg_tls(name,5433)
    pg17("pg_restore","-h","127.0.0.1","-p","5433","-U","postgres",
         "--exit-on-error","-d",DB_NAME,str(backup))
    backup.unlink()
    roles.unlink()
    work.rmdir()
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
    if demo.image_lab:
        demo.image_lab.detach_pg()
    command(["docker","stop",service[0]])
    if demo.private_product:
        demo.assert_private_readiness(503)
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
    if demo.image_lab:
        demo.image_lab.attach_pg(new_name)
    # Preserve the original GitHub-Actions service container for a genuine
    # reversible rollback; never stop or restart any host/demo container.
    return (new_name,volume,new_id,service[0])


def rollback_to_original_lab_database(restored, source_system_id, demo=None):
    """Reverse CI-only DB port switch without writes and measure recovery.

    Neither a production/staging volume nor a Mac installation is touched.
    Rollback before revoke: a stale backup must NOT resurrect revoked users.
    """
    new_name,_,restored_id,original_cid=restored
    assert source_system_id!=restored_id
    image=command(["docker","inspect","--format","{{.Config.Image}}",original_cid]).strip()
    assert image=="postgres:17.11","UNSAFE_SOURCE_IMAGE_FOR_ROLLBACK"
    start=time.monotonic()
    if demo and demo.image_lab:
        demo.image_lab.detach_pg()
    command(["docker","stop",new_name])
    command(["docker","start",original_cid])
    if demo and demo.image_lab:
        demo.image_lab.attach_pg(original_cid)
    for _ in range(100):
        try:
            with connect() as c:
                live=c.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0]
                if live==source_system_id:
                    return round(time.monotonic()-start,3)
        except psycopg.Error:
            pass
        time.sleep(.5)
    raise AssertionError("ORIGINAL_PG_CLUSTER_NOT_RESTORED_TO_HOST_PORT")


async def execute():
    verify_isolation()
    os.environ["PHASE3_APP_MODE"]="APP_ONLY"
    private=os.environ.get("F3_BROWSER_PRIVATE_RUNTIME")=="1"
    if private:
        prepare_private_database()
    demo=Demo(private_product=private)
    image_mode=os.getenv("F3_BROWSER_SIGNED_IMAGE")=="1"
    if image_mode:
        assert private
        demo.source_pg=source_service()
    restored=None
    browser=None
    ctx_a=ctx_b=None
    try:
        demo.start()
        output=Path(os.environ["RUNNER_TEMP"])/"f3-browser-source-restored"
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            ctx_a,page_a,handle_a,_=await demo.browser_login(browser,"A",False,output)
            ctx_b,page_b,handle_b,_=await demo.browser_login(browser,"B",False,output)
            async def same_handles():
                for ctx,handle in ((ctx_a,handle_a),(ctx_b,handle_b)):
                    cookies=[c for c in await ctx.cookies(ORIGIN) if c["name"]=="__Host-rag-session"]
                    assert len(cookies)==1 and cookies[0]["value"]==handle
            await same_handles()
            a_id=create_extra_question(demo,"A")
            b_id=create_extra_question(demo,"B")
            source,receipt_before,source_cluster=inventory(demo)
            messages_before=message_inventory(demo)
            ids_a={r[1] for r in source if r[0]==demo.owners["A"]}
            ids_b={r[1] for r in source if r[0]==demo.owners["B"]}
            assert len(ids_a)==3 and len(ids_b)==3 and ids_a.isdisjoint(ids_b)
            assert a_id in ids_a and b_id in ids_b
            await browser_history(page_a,"A",ids_a,demo.owners["A"],messages_before)
            await browser_history(page_b,"B",ids_b,demo.owners["B"],messages_before)
            await signed_pagination(page_a,ids_a)
            await signed_pagination(page_b,ids_b)
            await mobile_320_keyboard_accessibility(page_a)
            await mobile_320_keyboard_accessibility(page_b)
            await foreign_owner_denied(page_a,ids_b)
            await foreign_owner_denied(page_b,ids_a)
            await cursor_owner_signature_denied(page_a,page_b)
            await send_denied(page_a)
            await send_denied(page_b)
            assert inventory(demo)[1]==receipt_before
            assert message_inventory(demo)==messages_before,("NO_ENGINE_SEND_CREATED_MESSAGE",)
            measurements={"before_restore":await measure_history_requests(page_a,page_b,demo.owners["A"],demo.owners["B"])}
            print("F3_REAL_BROWSER_KEYCLOAK_NEXT_PG17_AB_PAGING_DETAIL_SEND503_PRE_RESTORE_PASS",
                  flush=True)

            restored=restore_separate_volume(demo,source,source_cluster)
            if private:
                demo.assert_private_readiness(200)
            if demo.image_lab:
                demo.image_lab.reload()
                tls=__import__("ssl").create_default_context(cafile=demo.ca)
                tls.load_cert_chain(demo.client[0],demo.client[1])
                demo.await_url(demo.product_origin+"/internal/ready",tls,200)
                demo.assert_private_readiness(200)
            if demo.web_lab:
                demo.web_lab.reload()
                demo.await_url(ORIGIN+"/login",__import__("ssl").create_default_context(cafile=demo.ca))
            # Continue same real two browser contexts, same session cookie,
            # same Keycloak process and Next/BFF/API, now independent PG volume.
            await browser_history(page_a,"A",ids_a,demo.owners["A"],messages_before)
            await browser_history(page_b,"B",ids_b,demo.owners["B"],messages_before)
            await mobile_320_keyboard_accessibility(page_a)
            await mobile_320_keyboard_accessibility(page_b)
            await signed_pagination(page_a,ids_a)
            await signed_pagination(page_b,ids_b)
            await foreign_owner_denied(page_a,ids_b)
            await foreign_owner_denied(page_b,ids_a)
            await cursor_owner_signature_denied(page_a,page_b)
            await send_denied(page_a)
            await send_denied(page_b)
            after,receipt_after,new_cluster=inventory(demo)
            assert source==after and receipt_before==receipt_after
            assert message_inventory(demo)==messages_before,("RESTORED_MESSAGES_SQL_DRIFT",)
            assert new_cluster==restored[2] and new_cluster!=source_cluster
            await same_handles()
            measurements["after_restore"]=await measure_history_requests(page_a,page_b,demo.owners["A"],demo.owners["B"])

            # Exercise a genuine reversal: restored disposable volume -> original
            # *unchanged* GitHub Actions PostgreSQL service. No writes since the
            # initial snapshot: fake or resurrected Answer/receipt is forbidden.
            rollback_seconds=rollback_to_original_lab_database(restored,source_cluster,demo)
            if private:
                demo.assert_private_readiness(200)
            await browser_history(page_a,"A",ids_a,demo.owners["A"],messages_before)
            await browser_history(page_b,"B",ids_b,demo.owners["B"],messages_before)
            await mobile_320_keyboard_accessibility(page_a)
            await mobile_320_keyboard_accessibility(page_b)
            await signed_pagination(page_a,ids_a)
            await signed_pagination(page_b,ids_b)
            await foreign_owner_denied(page_a,ids_b)
            await foreign_owner_denied(page_b,ids_a)
            await cursor_owner_signature_denied(page_a,page_b)
            await send_denied(page_a)
            await send_denied(page_b)
            reverted,reverted_receipts,reverted_cluster=inventory(demo)
            assert reverted_cluster==source_cluster,("ROLLBACK_DIFFERENT_PG_CLUSTER",)
            assert reverted==source and reverted_receipts==receipt_before
            assert message_inventory(demo)==messages_before,("ROLLBACK_MESSAGE_DRIFT",)
            await same_handles()
            measurements["after_rollback"]=await measure_history_requests(page_a,page_b,demo.owners["A"],demo.owners["B"])
            print("F3_REAL_BROWSER_CI_PG_BACKUP_RESTORE_ROLLBACK_REAL_AB_HISTORY_PASS",
                  flush=True)

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
                "actual_private_app_only_entrypoint":private,
                "pg_tls_verify_full_product_roles":private,
                "private_readiness_source_200_pg_stop_503_restored_200_rollback_200":private,
                "actual_signed_runtime_image":bool(demo.image_lab),
                "signed_image_archive_replay":demo.image_lab.roundtrip if demo.image_lab else None,
                "signed_api_internal_network_no_published_ports":bool(demo.image_lab),
                "signed_api_nonroot_readonly_only_api_secrets_mount":bool(demo.image_lab),
                "web_host_process_not_container":not bool(demo.web_lab),
                "actual_web_image":bool(demo.web_lab),
                "web_nonroot_secret_file_modes_and_mtls_positive_missing_cert_negative_pre_post":bool(demo.web_lab),
                "web_image_archive_replay":demo.web_lab.roundtrip if demo.web_lab else None,
                "web_internal_network_no_published_ports":bool(demo.web_lab),
                "ci_bootstrap_and_https_proxy_used":True,
                "browser_default_history_sql_equal":True,
                "browser_pagination_and_detail_sql_equal":True,
                "browser_detail_message_id_and_body_sql_equal":True,
                "browser_clicked_detail_dom_id_and_text_sql_equal_pre_restore_post_rollback":True,
                "private_get_no_store_and_foreign_404_no_store":True,
                "literal_cookie_handles_unchanged_after_restore_and_rollback":True,
                "measured_history_latency_ms":measurements,
                "synthetic_backup_aes256gcm_roundtrip":demo.backup_evidence,
                "all_a_conversations_cross_owner_404":True,
                "all_b_conversations_cross_owner_404":True,
                "cursor_owner_404_hmac_tamper_422_limit_422_pre_post_restore":True,
                "real_authenticated_browser_mobile_320_rtl_keyboard_pre_post_restore":True,
                "b_direct_a_detail_404":True,
                "send_bff_503_no_extra_receipts":True,
                "both_real_owners_repeated_invalid_and_retried_send_503_no_durable_effect":True,
                "fresh_pg_volume_independent_cluster":True,
                "same_browser_cookie_after_pg_restore":True,
                "same_browser_cookie_after_pg_rollback":True,
                "rollback_returns_to_original_ci_pg_cluster":True,
                "real_authenticated_browser_mobile_320_rtl_keyboard_after_rollback":True,
                "rollback_source_rows_and_messages_exact_sql_equal":True,
                "rollback_without_intervening_durable_send":True,
                "rollback_wall_clock_seconds":rollback_seconds,
                "approved_rto_threshold":None,
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
