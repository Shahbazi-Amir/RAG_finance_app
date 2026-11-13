"""Real reproducible Phase-3 demo: Chromium -> Next -> Keycloak -> API -> PostgreSQL.

Only on ephemeral GitHub CI runner (or identically provisioned local isolation).
No Playwright route.fulfill/interception, identity selection headers or fake 401.
Includes temporary DB function grants, synthetic Keycloak users and seeded data.
"""
from __future__ import annotations

import asyncio
from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from tempfile import TemporaryDirectory
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
import uuid

import httpx
import jwt
import psycopg
from psycopg.rows import dict_row
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.async_api import async_playwright, expect

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/"tests/phase3/integration/api")]
from initial_oidc_harness import DisposableKeycloak
from test_bootstrap_oidc_010 import cert_bundle
from src.phase3.storage.postgres import auth_session
from apps.api import history_api

ORIGIN="https://127.0.0.1:3443"
TITLE={
    "A":["گزارش نمونهٔ سپهر — حساب نمایشی الف","مقایسهٔ موجودی — حساب نمایشی الف"],
    "B":["گزارش نمونهٔ دماوند — حساب نمایشی ب","روند هزینه‌ها — حساب نمایشی ب"],
}
SIGN_ISS="urn:rag-finance:synthetic-product-session"
SIGN_AUD="urn:rag-finance:api:history-h1-isolated"
SIGN_KID="ci-product-session-kid"


def available_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1",0))
        return s.getsockname()[1]


def secret_key():
    return urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")


def save_bytes(path,data):
    path.write_bytes(data)
    path.chmod(0o600)
    return str(path)


class Demo:
    def __init__(self):
        self.tmp=TemporaryDirectory(prefix="rag-phase3-demo-")
        self.root=Path(self.tmp.name)
        self.kc=DisposableKeycloak()
        self.children=[]
        self.roles_added=False
        self.owners={}
        self.alias_key=secrets.token_bytes(32)

    def add(self,cmd,env=None,cwd=ROOT):
        log=(self.root/("process-"+str(len(self.children))+".log")).open("wb")
        p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=log)
        self.children.append((p,log))
        return p

    def grant(self,grant):
        with psycopg.connect(os.environ["AUTH_MIG_DSN"],autocommit=True) as c:
            if grant:
                c.execute("GRANT USAGE ON SCHEMA auth_l1 TO history_app")
            names=["consume_service_assertion(text,bigint)",
                   "admit_session_fenced(text,text,bigint,integer)"]
            for name in names:
                c.execute(("GRANT" if grant else "REVOKE")+
                          " EXECUTE ON FUNCTION auth_l1."+name+
                          (" TO " if grant else " FROM ")+"history_app,auth_revoker")
            c.execute(("GRANT" if grant else "REVOKE")+
                " EXECUTE ON FUNCTION auth_l1.revoke_one(text,bigint)"+
                (" TO " if grant else " FROM ")+"auth_revoker")
            if not grant:
                c.execute("REVOKE USAGE ON SCHEMA auth_l1 FROM history_app")

    def configure_keycloak(self):
        root=self.kc.base+"/admin/realms/"+self.kc.REALM+"/clients"
        with httpx.Client(trust_env=False,timeout=20) as client:
            auth=client.post(self.kc.base+
                "/realms/master/protocol/openid-connect/token",
                data={"grant_type":"password","client_id":"admin-cli",
                      "username":"ci-bootstrap","password":self.kc.password})
            assert auth.status_code==200,"KEYCLOAK_ADMIN_UNAVAILABLE"
            headers={"Authorization":"Bearer "+auth.json()["access_token"]}
            response=client.get(root,headers=headers,
                                params={"clientId":self.kc.CLIENT_ID})
            assert response.status_code==200 and len(response.json())==1
            entry=response.json()[0]
            entry["redirectUris"]=[ORIGIN+"/callback"]
            response=client.put(root+"/"+entry["id"],headers=headers,json=entry)
            assert response.status_code==204,"KEYCLOAK_CLIENT_PIN_FAILED"
        print("DEMO_KEYCLOAK_TWO_SYNTHETIC_USERS_REGISTERED_HTTPS_PIN_PASS",flush=True)

    def seed(self):
        issuer=self.kc.oidc["issuer"]
        for name in ("A","B"):
            sub=self.kc.accounts[name]["sub"]
            with psycopg.connect(os.environ["AUTH_MAP_DSN"],
                                 autocommit=True,row_factory=dict_row) as c:
                mapped=auth_session.map_identity(c,issuer,sub)
            owner=mapped["owner_id"]
            self.owners[name]=owner
            with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,
                                 row_factory=dict_row) as c:
                for title in TITLE[name]:
                    original={
                        "kind":"create_conversation_request",
                        "contract_version":"product.v1",
                        "client_conversation_id":history_api.uid(),
                        "idempotency_key":"demo_"+uuid.uuid4().hex,
                        "title":title,
                    }
                    history_api.create_conversation(
                        c,owner,original,history_api.uid(),history_api.uid())
        assert self.owners["A"]!=self.owners["B"]
        print("DEMO_POSTGRESQL_PRESEEDED_TWO_OWNER_ONLY_CONVERSATION_SETS_PASS",flush=True)

    def await_url(self,url,context,expected=200):
        for _ in range(90):
            if any(p.poll() is not None for p,_ in self.children):
                raise RuntimeError("DEMO_PRIVATE_SERVER_EXITED")
            try:
                with httpx.Client(verify=context,timeout=1,trust_env=False) as c:
                    resp=c.get(url)
                    if resp.status_code==expected:return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        raise RuntimeError("DEMO_PRIVATE_SERVER_NOT_READY")

    def start(self):
        if os.environ.get("CI")!="true" or os.environ.get("GITHUB_ACTIONS")!="true":
            raise RuntimeError("DEMO_ONLY_EPHEMERAL_CI")
        if "dbname=history_ci" not in os.environ.get("AUTH_MIG_DSN",""):
            raise RuntimeError("DEMO_ONLY_TEMP_PRODUCT_DB")
        self.kc.start()
        self.configure_keycloak()
        self.grant(True)
        self.roles_added=True
        self.seed()
        ca,server,client=cert_bundle(self.root)
        self.ca=ca
        self.client=client
        bootstrap_private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        product_private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        def store_private(name,key):
            return save_bytes(self.root/name,key.private_bytes(
                serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()))
        def store_public(name,key):
            return save_bytes(self.root/name,key.public_key().public_bytes(
                serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        bootstrap_key=store_private("bootstrap-sign.key",bootstrap_private)
        product_key=store_private("product-sign.key",product_private)
        bootstrap_pub=Path(store_public("bootstrap-sign.pem",bootstrap_private)).read_text()
        product_pub=store_public("product-sign.pem",product_private)
        self.product_signer=product_private
        audit=self.root/"exchange-audit.sqlite"
        import sqlite3
        with sqlite3.connect(audit) as db:
            db.execute("CREATE TABLE token_exchanges(worker TEXT,code_sha256 TEXT)")
            db.commit()
        bootstrap_port=available_port()
        product_port=available_port()
        self.bootstrap_origin="https://127.0.0.1:"+str(bootstrap_port)
        self.product_origin="https://127.0.0.1:"+str(product_port)
        worker={
            "worker_id":"demo", "port":bootstrap_port,"fault":"",
            "service_issuer":"urn:rag-finance:synthetic-bootstrap",
            "audience":"urn:rag-finance:api:bootstrap-ci",
            "service_keys":{"ci-bootstrap-kid":bootstrap_pub},
            "fingerprints":{
                "urn:rag-finance:synthetic-bootstrap":sha256(client[2]).hexdigest()},
            "material_keys":{"new":Fernet.generate_key().decode()},
            "active_kid":"new",
            "db_dsn":{
                "replay":os.environ["REPLAY_API_DSN"],
                "bootstrap":os.environ["LOGIN_BOOTSTRAP_DSN"],
                "claim_reader":os.environ["LOGIN_CLAIM_DSN"],
                "issuer":os.environ["LOGIN_ISSUER_DSN"],
                "mapper":os.environ["AUTH_MAP_DSN"],
                "binder":os.environ["LOGIN_BINDER_DSN"],
                "reader":os.environ["LOGIN_READER_DSN"],
            },
            "oidc":self.kc.oidc,"client_id":self.kc.CLIENT_ID,
            "redirect_uri":ORIGIN+"/callback",
            "audit_path":str(audit),"ca":ca,
            "server_cert":server[0],"server_key":server[1],
        }
        worker_config=self.root/"worker.json"
        worker_config.write_text(json.dumps(worker))
        worker_config.chmod(0o600)
        self.add([sys.executable,"-u",str(ROOT/
            "tests/phase3/integration/api/bootstrap_010_worker.py"),str(worker_config)])
        product_env=dict(os.environ)
        product_env.update(
            API_PRODUCT_PROOF_PUBLIC_KEY_PATH=product_pub,
            API_PRODUCT_PROOF_ISSUER=SIGN_ISS,
            API_PRODUCT_PROOF_AUDIENCE=SIGN_AUD,
            API_PRODUCT_PROOF_KID=SIGN_KID,
        )
        self.add([sys.executable,"-m","uvicorn","apps.api.product_session_api:app",
            "--host","127.0.0.1","--port",str(product_port),
            "--ssl-certfile",server[0],"--ssl-keyfile",server[1],
            "--ssl-ca-certs",ca,"--ssl-cert-reqs","2","--no-access-log"],product_env)
        private_context=ssl.create_default_context(cafile=ca)
        private_context.load_cert_chain(client[0],client[1])
        self.await_url(self.bootstrap_origin+"/__fixture_health",private_context)
        self.await_url(self.product_origin+"/v1/conversations",private_context,401)

        shared=self.root/"aliases"
        shared.mkdir(mode=0o700)
        self.shared=shared
        web_env=dict(os.environ)
        web_env.update(
            AUTH_CI_SHARED_STORE_DIR=str(shared),
            AUTH_CI_ALIAS_AES_KEY=urlsafe_b64encode(self.alias_key).decode().rstrip("="),
            AUTH_CI_CSRF_SECRET=secret_key(),
            AUTH_CI_PROXY_SECRET=secret_key(),
            AUTH_CI_PUBLIC_ORIGIN=ORIGIN,
            AUTH_CI_LOGIN_MODE="true",
            AUTH_CI_DEMO_MODE="true",
            AUTH_CI_IDP_AUTHORIZATION_ORIGIN=self.kc.base,
            AUTH_CI_BOOTSTRAP_ORIGIN=self.bootstrap_origin,
            AUTH_CI_BOOTSTRAP_SIGN_KEY=bootstrap_key,
            AUTH_CI_BOOTSTRAP_CA=ca,
            AUTH_CI_BOOTSTRAP_CERT=client[0],
            AUTH_CI_BOOTSTRAP_KEY=client[1],
            AUTH_CI_BOOTSTRAP_ISSUER="urn:rag-finance:synthetic-bootstrap",
            AUTH_CI_BOOTSTRAP_AUDIENCE="urn:rag-finance:api:bootstrap-ci",
            AUTH_CI_BOOTSTRAP_KID="ci-bootstrap-kid",
            AUTH_CI_PRODUCT_ORIGIN=self.product_origin,
            AUTH_CI_PRODUCT_SIGN_KEY=product_key,
            AUTH_CI_PRODUCT_ISSUER=SIGN_ISS,
            AUTH_CI_PRODUCT_AUDIENCE=SIGN_AUD,
            AUTH_CI_PRODUCT_KID=SIGN_KID,
            AUTH_CI_DEMO_OWNER_A=self.owners["A"],
            AUTH_CI_DEMO_OWNER_B=self.owners["B"],
            AUTH_CI_TLS_CERT=server[0],
            AUTH_CI_TLS_KEY=server[1],
        )
        self.add(["./node_modules/.bin/next","start","-H","127.0.0.1",
                  "-p","3000"],web_env,ROOT/"apps/web")
        self.add(["node","tests/phase3/integration/ui/auth_010_https_proxy.mjs"],
                 web_env)
        # Public TLS does not require a client cert; private links do.
        self.await_url(ORIGIN+"/login",ssl.create_default_context(cafile=ca))
        print("DEMO_REAL_KEYCLOAK_NEXT_MTLS_API_PG_READY",flush=True)

    def raw_from_alias(self,handle):
        name="alias-"+sha256(handle.encode()).hexdigest()+".json"
        record=json.loads((self.shared/name).read_text())
        assert record["status"]=="ACTIVE"
        def decode(value):
            return urlsafe_b64decode(value+"="*((-len(value))%4))
        cipher=decode(record["ciphertext"])+decode(record["tag"])
        verifier=AESGCM(self.alias_key).decrypt(decode(record["iv"]),cipher,None)
        return {"session_ref":verifier.decode(),"owner_id":record["ownerId"],
                "epoch":record["epoch"],"generation":record["generation"]}

    def signed_private(self,raw):
        now=int(time.time())
        query="limit=2"
        payload={
            "iss":SIGN_ISS,"aud":SIGN_AUD,
            "iat":now,"nbf":now,"exp":now+25,
            "jti":secrets.token_urlsafe(24),"method":"GET",
            "raw_path_sha256":sha256(b"/v1/conversations").hexdigest(),
            "raw_query_sha256":sha256(query.encode()).hexdigest(),
            "body_sha256":sha256(b"").hexdigest(),"body_len":0,
            **raw,
        }
        token=jwt.encode(payload,self.product_signer,algorithm="RS256",
                         headers={"typ":"JWT","kid":SIGN_KID})
        tls=ssl.create_default_context(cafile=self.ca)
        tls.load_cert_chain(self.client[0],self.client[1])
        with httpx.Client(verify=tls,trust_env=False,timeout=8) as client:
            return client.get(self.product_origin+"/v1/conversations?"+query,
                headers={"Authorization":"BFF-Assertion "+token})

    async def browser_login(self,browser,label,mobile,output):
        ctx=await browser.new_context(
            viewport={"width":390,"height":844} if mobile else {"width":1280,"height":800},
            is_mobile=mobile,device_scale_factor=1,ignore_https_errors=True)
        page=await ctx.new_page()
        await page.goto(ORIGIN+"/login")
        await expect(page.get_by_test_id("login-submit")).to_be_visible()
        async with page.expect_response(
            lambda r: r.url.endswith("/api/auth/login") and
            r.request.method=="POST",timeout=16000) as start_wait:
            await page.get_by_test_id("login-submit").click()
        start_reply=await start_wait.value
        location=urlsplit(page.url)
        location_class=("KEYCLOAK" if location.port==self.kc.port and
                        location.hostname=="127.0.0.1"
                        else "NEXT" if location.port==3443 else "OTHER")
        form_visible=await page.locator('input[name="username"]').count()
        print("DEMO_LOGIN_DIAGNOSTIC",json.dumps({
            "post_http":start_reply.status,
            "site":location_class,
            "path_kind":"OIDC_AUTH" if location.path.endswith(
                "/protocol/openid-connect/auth") else
                "LOGIN_ACTION" if "/login-actions/" in location.path
                else "OTHER",
            "idp_form_present":bool(form_visible),
        }),flush=True)
        assert start_reply.status==303,"DEMO_START_REJECTED"
        await page.locator('input[name="username"]').wait_for(state="visible",timeout=9000)
        await page.locator('input[name="username"]').fill(self.kc.accounts[label]["email"])
        await page.locator('input[name="password"]').fill(self.kc.accounts[label]["password"])
        async with page.expect_response(
            lambda r: "/api/history/conversations?limit=2" in r.url
            and r.request.method=="GET",timeout=30000) as response_wait:
            await page.locator("#kc-login").click()
        response=await response_wait.value
        assert response.status==200, ("LOGIN_HISTORY",label,response.status)
        page_body=await response.json()
        assert page_body["kind"]=="conversation_page"
        assert page_body["scope_user_id"]==self.owners[label]
        titles=[item["title"] for item in page_body["items"]]
        assert set(titles)==set(TITLE[label]),("WRONG_HISTORY",label)
        foreign=TITLE["B" if label=="A" else "A"]
        assert not set(titles).intersection(foreign)
        await expect(page.locator('nav.history-list')).to_contain_text(TITLE[label][0])
        for title in foreign:
            assert title not in await page.locator('nav.history-list').inner_text()
        if mobile:
            await page.locator(".mobile-menu-trigger").click()
            await expect(page.get_by_test_id("refresh-history")).to_be_visible()
        cookies=[c for c in await ctx.cookies(ORIGIN)
                 if c["name"]=="__Host-rag-session"]
        assert len(cookies)==1 and cookies[0]["secure"] and cookies[0]["httpOnly"]
        assert cookies[0]["sameSite"]=="Lax"
        handle=cookies[0]["value"]
        raw=self.raw_from_alias(handle)
        assert raw["owner_id"]==self.owners[label]
        assert raw["session_ref"]!=handle
        assert self.signed_private(raw).status_code==200
        output.mkdir(parents=True,exist_ok=True)
        await page.screenshot(path=str(output/(
            ("mobile" if mobile else "desktop")+"-"+label+"-history.png")),
            full_page=True)
        return ctx,page,handle,raw

    async def scenario(self,browser,mobile,output):
        mode="MOBILE" if mobile else "DESKTOP"
        ctx_a=ctx_b=None
        try:
            ctx_a,page_a,old_cookie,raw_a=await self.browser_login(
                browser,"A",mobile,output)
            print("DEMO_"+mode+"_KEYCLOAK_A_COOKIE_OWN_HISTORY_PASS",flush=True)
            ctx_b,page_b,_,raw_b=await self.browser_login(
                browser,"B",mobile,output)
            print("DEMO_"+mode+"_KEYCLOAK_B_COOKIE_OWN_HISTORY_PASS",flush=True)
            # Same browser context as A, second tab starts a real native
            # Logout form POST with CSRF and verified server-only session.
            other_tab=await ctx_a.new_page()
            await other_tab.goto(ORIGIN+"/login")
            await expect(other_tab.get_by_test_id("logout-submit")).to_be_visible()
            async with other_tab.expect_response(
                lambda r: r.url.endswith("/api/auth/logout") and
                r.request.method=="POST",timeout=25000) as posted:
                await other_tab.get_by_test_id("logout-submit").click()
            receipt=await posted.value
            assert receipt.status==303,("NO_COMMIT_RECEIPT",receipt.status)
            await expect(other_tab.get_by_test_id("logout-success")).to_be_visible()
            print("DEMO_"+mode+"_REAL_LOGOUT_COMMITTED_RECEIPT_PASS",flush=True)
            # API-level post-revoke check uses actual Product verifier recovered
            # from its encrypted server-only alias, not any browser identity.
            assert self.signed_private(raw_a).status_code==401
            result_b=self.signed_private(raw_b)
            assert result_b.status_code==200
            assert result_b.json()["scope_user_id"]==self.owners["B"]
            print("DEMO_"+mode+"_REAL_API_A_401_B_200_AFTER_REVOKE_PASS",flush=True)
            async with page_a.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and r.request.method=="GET",timeout=15000) as denied:
                await page_a.get_by_test_id("refresh-history").click()
            denied_response=await denied.value
            assert denied_response.status==401
            await expect(page_a.get_by_test_id("history-login-required")).to_be_visible()
            assert await page_a.locator('[data-testid^="conversation-"]').count()==0
            for title in TITLE["A"]:
                assert title not in await page_a.locator("main.history-shell").inner_text()
            print("DEMO_"+mode+"_OLD_BROWSER_COOKIE_401_PURGED_PASS",flush=True)
            async with page_b.expect_response(
                lambda r: "/api/history/conversations?limit=2" in r.url
                and r.request.method=="GET",timeout=15000) as refreshed_b:
                await page_b.get_by_test_id("refresh-history").click()
            assert (await refreshed_b.value).status==200
            await expect(page_b.locator("nav.history-list")).to_contain_text(TITLE["B"][0])
            await page_a.screenshot(path=str(output/(
                ("mobile" if mobile else "desktop")+"-A-after-logout.png")),
                full_page=True)
            print("DEMO_"+mode+"_B_SESSION_STILL_PRIVATE_PASS",flush=True)
        finally:
            if ctx_a is not None:await ctx_a.close()
            if ctx_b is not None:await ctx_b.close()

    def stop(self):
        for proc,log in reversed(self.children):
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill();proc.wait(timeout=4)
            log.close()
        if self.roles_added:
            try:self.grant(False)
            except psycopg.Error:pass
        try:self.kc.stop()
        finally:self.tmp.cleanup()


async def execute():
    demo=Demo()
    try:
        demo.start()
        output=Path(os.environ.get("RUNNER_TEMP","/tmp"))/"phase3-demo-evidence"
        async with async_playwright() as playwright:
            browser=await playwright.chromium.launch()
            try:
                await demo.scenario(browser,False,output)
                await demo.scenario(browser,True,output)
            finally:
                await browser.close()
        print("DEMO_PHASE3_REAL_CHROMIUM_DESKTOP_MOBILE_A_B_LOGOUT_PASS",flush=True)
    finally:
        demo.stop()


if __name__=="__main__":
    asyncio.run(execute())
