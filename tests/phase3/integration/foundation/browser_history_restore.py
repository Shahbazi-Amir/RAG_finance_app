"""One GitHub runner: real Keycloak, two Chromium contexts, Next BFF,
HTTPS signed Product API, PostgreSQL17, then new-volume restore/replay.

No intercept/fulfill, cookie fabrication, identity header or Engine dispatch.
Only a disposable CI runner may stop its own PG service on port 5432.
"""
from __future__ import annotations
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import traceback
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
from phase3_auth_demo import Demo,ORIGIN,SIGN_ISS,SIGN_AUD,SIGN_KID
from test_history_restore_signed import command,pg17,connect,ssl_server
from apps.api import history_api
from src.phase3.auth.service_proof import BFFServiceVerifier,TrustRejected
from src.phase3.auth.transactional_admission import protected_transaction
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore
from psycopg.pq import TransactionStatus
from cryptography.hazmat.primitives import serialization
import jwt
import repository


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
    # Playwright's APIRequestContext uses its Node driver, not Chromium's
    # NSS trust or Python's system CA bundle. Give only this ephemeral CI CA
    # to that Node subprocess before async_playwright() starts. Do not bypass
    # TLS verification for either browser navigation or direct API requests.
    os.environ["NODE_EXTRA_CA_CERTS"]=str(ca)
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
    # Negative SAN test: same server and same trusted CA, but a hostname not
    # listed in the ephemeral certificate. It MUST be rejected by OpenSSL.
    try:
        with socket.create_connection(("127.0.0.1",3443),timeout=8) as sock:
            with ssl.create_default_context().wrap_socket(
                    sock,server_hostname="localhost"):
                pass
    except ssl.SSLCertVerificationError:
        pass
    else:
        raise AssertionError("NEGATIVE_SAN_VERIFICATION_MUST_REJECT_LOCALHOST")
    print("F3_LAB_OS_CA_CHROMIUM_NSS_TRUST_AND_LOOPBACK_IP_SAN_PASS",flush=True)


def enable_lab_pg_tls(container, key, crt):
    """CI-only PG container, no host/demo mutation. Local socket setup only."""
    verify_isolation()
    assert command(["docker","inspect","--format","{{.Config.Image}}",container]).strip()=="postgres:17.11"
    for _ in range(70):
        try:
            command(["docker","exec",container,"pg_isready","-h","127.0.0.1","-p","5432"])
            break
        except AssertionError:time.sleep(.5)
    else:raise AssertionError("PG_TLS_CONTAINER_NOT_READY")
    for src,target in ((key,"server.key"),(crt,"server.crt")):
        dest="/var/lib/postgresql/data/"+target
        command(["docker","cp",str(src),container+":"+dest])
        command(["docker","exec","-u","0",container,"chown","postgres:postgres",dest])
        command(["docker","exec","-u","0",container,"chmod","0600",dest])
    for setting in ("ssl='on'","ssl_cert_file='server.crt'","ssl_key_file='server.key'"):
        command(["docker","exec","-u","postgres",container,"psql","-X","-U","postgres",
                 "-d","postgres","-v","ON_ERROR_STOP=1","-c","ALTER SYSTEM SET "+setting])
    # Prefix mandatory TLS rules ahead of image defaults; local socket remains
    # available only within the disposable service for administration.
    script="set -eu; cd /var/lib/postgresql/data; test -f pg_hba.conf; " \
           "printf 'hostnossl all all all reject\\nhostssl all all all scram-sha-256\\n' > pg_hba.f3; " \
           "cat pg_hba.conf >> pg_hba.f3; chown postgres:postgres pg_hba.f3; chmod 0600 pg_hba.f3; " \
           "mv pg_hba.f3 pg_hba.conf"
    command(["docker","exec","-u","0",container,"sh","-c",script])
    command(["docker","restart",container])


def verify_pg_tls(port, phase):
    cfg=psycopg.conninfo.conninfo_to_dict(os.environ["DB_APP_DSN"])
    cfg["port"]=str(port)
    cfg["dbname"]="postgres"
    for _ in range(80):
        try:
            with connect(port,db="postgres") as c:
                assert c.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]
                break
        except psycopg.Error:time.sleep(.5)
    else:raise AssertionError("PG_TLS_VERIFY_FULL_NOT_READY")
    cfg.update(user="postgres",password=os.environ["PGPASSWORD"])
    for bad in ({"sslmode":"disable"},{"host":"localhost","hostaddr":"127.0.0.1"}):
        candidate=dict(cfg,**bad)
        try:
            with psycopg.connect(**candidate):pass
        except psycopg.OperationalError:pass
        else:raise AssertionError("PG_TLS_NEGATIVE_NOT_REJECTED")
    print("F3_DB_PG_TLS_"+phase+"_VERIFY_FULL_NO_PLAINTEXT_WRONG_SAN_PASS",flush=True)


def configure_source_pg_tls():
    verify_isolation()
    cid=os.environ["F3_CI_PG_CONTAINER_ID"]
    assert re.fullmatch(r"[a-f0-9]{64}",cid)
    assert command(["docker","inspect","--format","{{.Config.Image}}",cid]).strip()=="postgres:17.11"
    ports=json.loads(command(["docker","inspect","--format","{{json .NetworkSettings.Ports}}",cid]))
    assert any(x["HostPort"]=="5432" for x in ports.get("5432/tcp",[]))
    root=Path(os.environ["RUNNER_TEMP"])/"f3-browser-pg-tls"
    root.mkdir(mode=0o700)
    ca,key,crt=ssl_server(root)
    enable_lab_pg_tls(cid,key,crt)
    os.environ["PGSSLMODE"]="verify-full"
    os.environ["PGSSLROOTCERT"]=str(ca)
    for name,value in list(os.environ.items()):
        if name.endswith("_DSN") and "dbname=history_" in value:
            cfg=psycopg.conninfo.conninfo_to_dict(value)
            assert cfg.get("host")=="127.0.0.1" and cfg.get("port")=="5432"
            cfg.update(sslmode="verify-full",sslrootcert=str(ca))
            os.environ[name]=psycopg.conninfo.make_conninfo(**cfg)
    verify_pg_tls(5432,"SOURCE")
    return key,crt


def oidc_same_transaction_matrix(demo,raw_a,raw_b,phase,ids_a,ids_b,revoked=False):
    """Real server-only aliases recovered from actual OIDC browser login.
    Supplemental direct invocation of real admission and repository; no new
    public endpoint, no engine, no alternative login or raw alias export.
    """
    verifier=BFFServiceVerifier(issuer=SIGN_ISS,audience=SIGN_AUD,public_keys={
        SIGN_KID:demo.product_signer.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)})
    path=b"/v1/conversations"
    query=b"limit=2"
    def sign(raw,**changes):
        now=int(time.time())
        payload=dict(iss=SIGN_ISS,aud=SIGN_AUD,iat=now,nbf=now,exp=now+25,
            jti=secrets.token_urlsafe(24),method="GET",
            raw_path_sha256=sha256(path).hexdigest(),
            raw_query_sha256=sha256(query).hexdigest(),
            body_sha256=sha256(b"").hexdigest(),body_len=0,**raw)
        payload.update(changes)
        return jwt.encode(payload,demo.product_signer,algorithm="RS256",
                          headers={"typ":"JWT","kid":SIGN_KID})
    def admitted(c,token,q=query):
        return protected_transaction(c,verifier=verifier,
            replay_store=PostgresDurableReplayStore(),compact_assertion=token,
            method="GET",raw_path=path,raw_query=q,body=b"")
    def idle(c):
        assert c.info.transaction_status==TransactionStatus.IDLE
        assert c.execute("SELECT count(*) AS n FROM history_l1.conversations").fetchone()["n"]==0
    def denied(c,token,q=query):
        try:
            with admitted(c,token,q):
                raise AssertionError("UNAUTHORIZED_ACTION_REACHED")
        except TrustRejected:pass
        else:raise AssertionError("UNAUTHORIZED_PROOF_ACCEPTED")
        idle(c)
    class RollbackProbe(Exception):pass
    def read(c,actor,ids,foreign):
        assert c.info.transaction_status==TransactionStatus.INTRANS
        pid=c.info.backend_pid
        tx=c.execute("SELECT pg_current_xact_id()::text AS tx").fetchone()["tx"]
        c.execute("SELECT set_config('app.owner_id',%s,true)",(foreign,))
        rows=repository.list_conversations(c,actor,limit=100)["items"]
        assert {r["conversation_id"] for r in rows}==ids
        assert c.info.backend_pid==pid
        assert c.execute("SELECT pg_current_xact_id()::text AS tx").fetchone()["tx"]==tx
        assert c.execute("SELECT current_setting('app.owner_id',true) AS o").fetchone()["o"]==actor
    with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,row_factory=dict_row) as c:
        assert c.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()["ssl"]
        idle(c)
        if revoked:
            denied(c,sign(raw_a))
            with admitted(c,sign(raw_b)) as actor:
                assert actor==raw_b["owner_id"]
                read(c,actor,ids_b,raw_a["owner_id"])
            idle(c)
            print("DB_OIDC_SAME_TX_REVOKED_A_DENIED_B_ADMITTED=PASS",flush=True)
            return
        for raw,other,ids,foreign_ids in ((raw_a,raw_b,ids_a,ids_b),(raw_b,raw_a,ids_b,ids_a)):
            token=sign(raw)
            with admitted(c,token) as actor:
                assert actor==raw["owner_id"]
                read(c,actor,ids,other["owner_id"])
                try:repository.list_messages(c,actor,sorted(foreign_ids)[0],session_transaction=True)
                except repository.NotFound:pass
                else:raise AssertionError("FOREIGN_REPOSITORY_READ")
            idle(c)
            denied(c,token)
            denied(c,sign(raw,owner_id=other["owner_id"]))
            denied(c,sign(raw,epoch=raw["epoch"]+1))
            denied(c,sign(raw,generation=raw["generation"]+1))
            denied(c,sign(raw),b"limit=3")
            retry=sign(raw)
            try:
                with admitted(c,retry) as actor:
                    read(c,actor,ids,other["owner_id"])
                    raise RollbackProbe()
            except RollbackProbe:pass
            else:raise AssertionError("INJECTED_ROLLBACK_NOT_OBSERVED")
            idle(c)
            with admitted(c,retry) as actor:
                read(c,actor,ids,other["owner_id"])
            idle(c)
            denied(c,retry)
    print("DB_OIDC_SAME_TX_"+phase+"_TWO_REAL_OWNERS_BINDING_REPLAY_ROLLBACK=PASS",flush=True)


async def prove_real_logout_waits_for_admitted_transaction(demo,tab,raw,ids):
    """Hold the real signed SQL transaction while normal browser Logout runs.

    A real pg_blocking_pids edge, not a sleep alone, proves that 003 revoke
    waits for 004's protected read transaction. No raw actor/proof exported.
    """
    from concurrent.futures import Future
    from threading import Event
    ready=Future()
    release=Event()
    path=b"/v1/conversations"
    query=b"limit=2"
    def hold():
        try:
            now=int(time.time())
            claims=dict(iss=SIGN_ISS,aud=SIGN_AUD,iat=now,nbf=now,exp=now+25,
                jti=secrets.token_urlsafe(24),method="GET",
                raw_path_sha256=sha256(path).hexdigest(),
                raw_query_sha256=sha256(query).hexdigest(),
                body_sha256=sha256(b"").hexdigest(),body_len=0,**raw)
            token=jwt.encode(claims,demo.product_signer,algorithm="RS256",
                             headers={"typ":"JWT","kid":SIGN_KID})
            verifier=BFFServiceVerifier(issuer=SIGN_ISS,audience=SIGN_AUD,public_keys={
                SIGN_KID:demo.product_signer.public_key().public_bytes(
                    serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)})
            with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,row_factory=dict_row) as c:
                with protected_transaction(c,verifier=verifier,replay_store=PostgresDurableReplayStore(),
                        compact_assertion=token,method="GET",raw_path=path,raw_query=query,body=b"") as owner:
                    assert owner==raw["owner_id"]
                    assert {x["conversation_id"] for x in repository.list_conversations(c,owner,limit=100)["items"]}==ids
                    ready.set_result(c.info.backend_pid)
                    assert release.wait(12),"LOCK_OBSERVER_DID_NOT_RELEASE"
                assert c.info.transaction_status==TransactionStatus.IDLE
        except BaseException as exc:
            if not ready.done():ready.set_exception(exc)
            raise
    def observe(pid):
        deadline=time.monotonic()+5
        with connect() as admin:
            while time.monotonic()<deadline:
                blocked=admin.execute("""SELECT EXISTS(SELECT 1 FROM pg_stat_activity a
                    WHERE a.datname=current_database() AND a.usename='auth_revoker'
                    AND %s=ANY(pg_blocking_pids(a.pid)))""",(pid,)).fetchone()[0]
                if blocked:return True
                time.sleep(.05)
        return False
    worker=asyncio.create_task(asyncio.to_thread(hold))
    click=None
    try:
        pid=await asyncio.wait_for(asyncio.wrap_future(ready),timeout=8)
        async with tab.expect_response(lambda x:x.url.endswith("/api/auth/logout")
                and x.request.method=="POST",timeout=25000) as waiting:
            click=asyncio.create_task(tab.get_by_test_id("logout-submit").click())
            assert await asyncio.to_thread(observe,pid),"NO_REAL_REVOKER_BLOCKING_EDGE"
            print("DB_OIDC_REAL_BROWSER_LOGOUT_PG_BLOCKING_PID_EDGE=PASS",flush=True)
            release.set()
            await asyncio.wait_for(worker,timeout=8)
            await click
        assert (await waiting.value).status==303
        print("DB_OIDC_REAL_BROWSER_LOGOUT_COMMITTED_AFTER_READ_TX_RELEASE=PASS",flush=True)
    finally:
        release.set()
        await asyncio.gather(worker,*([] if click is None else [click]),return_exceptions=True)


def migration_ledger_snapshot(phase,source_cluster,baseline=None):
    manifest=ROOT/"infra/postgres/dev_f3_isolated/MIGRATIONS_001_010_PINNED.tsv"
    assert sha256(manifest.read_bytes()).hexdigest()=="9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7"
    expected={}
    for line in manifest.read_text().splitlines()[1:]:
        ver,direction,source,path,blob=line.split("\t")
        if direction=="UP":
            expected[ver]=(source,blob,sha256((ROOT/path).read_bytes()).hexdigest())
    assert sorted(expected)==[f"{n:03d}" for n in range(1,11)]
    with connect() as c:
        rows=c.execute("""SELECT trim(version),trim(source_commit),trim(git_blob_sha1),
            trim(sql_sha256),status,started_at,applied_at,applied_txid,cluster_system_id
            FROM db55_audit.migration_runs ORDER BY version""").fetchall()
        assert len(rows)==10
        for ver,source,blob,digest,status,started,applied,tx,cluster in rows:
            assert expected[ver]==(source,blob,digest)
            assert status=="APPLIED" and applied>=started and tx is not None
            assert cluster==str(source_cluster)
        physical=c.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n
            ON n.oid=c.relnamespace WHERE n.nspname IN ('auth_l1','history_l1')
            AND c.relkind IN ('r','p') AND c.relrowsecurity AND c.relforcerowsecurity""").fetchone()[0]
        assert physical==14
    # Verify actual denied service login, not just catalog ACL.
    try:
        with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True) as c:
            c.execute("SELECT count(*) FROM db55_audit.migration_runs")
    except psycopg.errors.InsufficientPrivilege:pass
    else:raise AssertionError("PRODUCT_ROLE_CAN_READ_MIGRATION_LEDGER")
    fingerprint=sha256(json.dumps(rows,default=str).encode()).hexdigest()
    if baseline is not None:assert fingerprint==baseline,"BROWSER_LEDGER_RESTORE_DRIFT"
    print("F3_DB_BROWSER_MIGRATION_LEDGER_"+phase+"_10_EXACT_ROWS_PRIVATE_14_FORCE_RLS=PASS",flush=True)
    return fingerprint


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


HISTORY_TABLES=("conversations","messages","create_receipts","send_receipts",
                "execution_attempts","answers")


def restricted_history_snapshot(demo, phase, baseline=None):
    """Independent read-only SQL on the same limited product LOGIN, not admin.
    Trusted test owner IDs originate from real CI OIDC logins, not request input.
    GUC assignment here exercises RLS only; it does not establish API identity.
    Keep row values and digests private; receipt contains only PASS and counts.
    """
    verify_isolation()
    dsn=os.environ["DB_APP_DSN"]
    cfg=psycopg.conninfo.conninfo_to_dict(dsn)
    assert cfg.get("sslmode")=="verify-full" and cfg.get("sslrootcert")==os.environ["PGSSLROOTCERT"]
    assert (cfg.get("host"),cfg.get("port"),cfg.get("dbname"),cfg.get("user")) == (
        "127.0.0.1","5432","history_ci","history_app"),"UNSAFE_HISTORY_ROLE_DSN"
    owners=(demo.owners["A"],demo.owners["B"])
    assert all(owners) and owners[0]!=owners[1],"OIDC_OWNER_COLLISION"
    result={}
    with psycopg.connect(dsn,autocommit=True) as c:
        assert c.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0],"PG_SERVICE_TLS_NOT_ACTIVE"
        flags=c.execute("SELECT current_user,rolsuper,rolbypassrls,rolinherit,"
                        "rolcreaterole,rolcreatedb FROM pg_roles "
                        "WHERE rolname=current_user").fetchone()
        assert flags==("history_app",False,False,False,False,False),"UNSAFE_HISTORY_ROLE"
        for label,owner,other in (("A",owners[0],owners[1]),("B",owners[1],owners[0])):
            with c.transaction():
                c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                c.execute("SELECT set_config('app.owner_id',%s,true)",(owner,))
                data={}
                for table in HISTORY_TABLES:
                    qualified=sql.Identifier("history_l1",table)
                    assert c.execute("SELECT row_security_active(%s::regclass)",
                                     ("history_l1."+table,)).fetchone()[0],"RLS_INACTIVE"
                    rows=c.execute(sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY 1")
                                   .format(qualified)).fetchall()
                    assert all(json.loads(r[0])["owner_id"]==owner for r in rows),"OWNER_LEAK"
                    assert c.execute(sql.SQL("SELECT count(*) FROM {} WHERE owner_id=%s")
                                     .format(qualified),(other,)).fetchone()[0]==0,"FOREIGN_ROW"
                    payload=json.dumps(rows,separators=(",",":"),ensure_ascii=True)
                    data[table]=(len(rows),sha256(payload.encode()).hexdigest())
                assert data["conversations"][0]==3 and data["messages"][0]>0,"EMPTY_OWNER"
                result[label]=data
            # Same physical connection after COMMIT: no owner context may leak.
            with c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                for table in HISTORY_TABLES:
                    assert c.execute(sql.SQL("SELECT count(*) FROM {}")
                        .format(sql.Identifier("history_l1",table))).fetchone()[0]==0,"UNSET_OWNER_LEAK"
    if baseline is not None:
        assert result==baseline,"RESTRICTED_HISTORY_CONTENT_OR_COUNT_DRIFT"
    print("F3_DB_REAL_OIDC_ROLE_SIX_TABLES_"+phase+"_PARITY_PASS",flush=True)
    return result


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


def restore_separate_volume(demo,original_records,source_system_id,pg_tls):
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
    enable_lab_pg_tls(name,*pg_tls)
    verify_pg_tls(5433,"FRESH_RESTORE")
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
    assert service[0]==os.environ["F3_CI_PG_CONTAINER_ID"] or os.environ["F3_CI_PG_CONTAINER_ID"].startswith(service[0]),"PG_SOURCE_ID_MISMATCH"
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
    verify_pg_tls(5432,"RESTORED")
    # Preserve the original GitHub-Actions service container for a genuine
    # reversible rollback; never stop or restart any host/demo container.
    return (new_name,volume,new_id,service[0])


def rollback_to_original_lab_database(restored, source_system_id):
    """Reverse CI-only DB port switch without writes and measure recovery.

    Neither a production/staging volume nor a Mac installation is touched.
    Rollback before revoke: a stale backup must NOT resurrect revoked users.
    """
    new_name,_,restored_id,original_cid=restored
    assert source_system_id!=restored_id
    image=command(["docker","inspect","--format","{{.Config.Image}}",original_cid]).strip()
    assert image=="postgres:17.11","UNSAFE_SOURCE_IMAGE_FOR_ROLLBACK"
    start=time.monotonic()
    command(["docker","stop",new_name])
    command(["docker","start",original_cid])
    for _ in range(100):
        try:
            with connect() as c:
                live=c.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0]
                if live==source_system_id:
                    verify_pg_tls(5432,"ROLLBACK")
                    return round(time.monotonic()-start,3)
        except psycopg.Error:
            pass
        time.sleep(.5)
    raise AssertionError("ORIGINAL_PG_CLUSTER_NOT_RESTORED_TO_HOST_PORT")


async def execute():
    verify_isolation()
    os.environ["PHASE3_APP_MODE"]="APP_ONLY"
    demo=Demo()
    restored=None
    browser=None
    ctx_a=ctx_b=None
    try:
        pg_tls=configure_source_pg_tls()
        demo.start()
        trust_ephemeral_browser_ca(demo)
        output=Path(os.environ["RUNNER_TEMP"])/"f3-browser-source-restored"
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            ctx_a,page_a,_,raw_a=await demo.browser_login(browser,"A",False,output,require_trusted_tls=True)
            ctx_b,page_b,_,raw_b=await demo.browser_login(browser,"B",False,output,require_trusted_tls=True)
            a_id=create_extra_question(demo,"A")
            b_id=create_extra_question(demo,"B")
            source,receipt_before,source_cluster=inventory(demo)
            ledger_before=migration_ledger_snapshot("SOURCE",source_cluster)
            messages_before=message_inventory(demo)
            restricted_before=restricted_history_snapshot(demo,"SOURCE")
            ids_a={r[1] for r in source if r[0]==demo.owners["A"]}
            ids_b={r[1] for r in source if r[0]==demo.owners["B"]}
            assert len(ids_a)==3 and len(ids_b)==3 and ids_a.isdisjoint(ids_b)
            assert a_id in ids_a and b_id in ids_b
            oidc_same_transaction_matrix(demo,raw_a,raw_b,"SOURCE",ids_a,ids_b)
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
            restricted_history_snapshot(demo,"SOURCE_AFTER_SEND",restricted_before)
            print("F3_REAL_BROWSER_KEYCLOAK_NEXT_PG17_AB_PAGING_DETAIL_SEND503_PRE_RESTORE_PASS",
                  flush=True)

            restored=restore_separate_volume(demo,source,source_cluster,pg_tls)
            restricted_history_snapshot(demo,"RESTORED_BEFORE_BROWSER",restricted_before)
            migration_ledger_snapshot("RESTORED",source_cluster,ledger_before)
            oidc_same_transaction_matrix(demo,raw_a,raw_b,"RESTORED",ids_a,ids_b)
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
            restricted_history_snapshot(demo,"RESTORED_AFTER_BROWSER",restricted_before)

            # Exercise a genuine reversal: restored disposable volume -> original
            # *unchanged* GitHub Actions PostgreSQL service. No writes since the
            # initial snapshot: fake or resurrected Answer/receipt is forbidden.
            rollback_seconds=rollback_to_original_lab_database(restored,source_cluster)
            restricted_history_snapshot(demo,"ROLLBACK_BEFORE_BROWSER",restricted_before)
            migration_ledger_snapshot("ROLLBACK",source_cluster,ledger_before)
            oidc_same_transaction_matrix(demo,raw_a,raw_b,"ROLLBACK",ids_a,ids_b)
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
            restricted_history_snapshot(demo,"ROLLBACK_AFTER_BROWSER",restricted_before)
            print("F3_REAL_BROWSER_CI_PG_BACKUP_RESTORE_ROLLBACK_REAL_AB_HISTORY_PASS",
                  flush=True)

            # Genuine Logout form and old cookie on original Chromium context.
            tab=await ctx_a.new_page()
            await tab.goto(ORIGIN+"/login")
            await expect(tab.get_by_test_id("logout-submit")).to_be_visible()
            await prove_real_logout_waits_for_admitted_transaction(demo,tab,raw_a,ids_a)
            stale=await page_a.request.get(
                ORIGIN+"/api/history/conversations?limit=2")
            assert stale.status==401,("REVOKED_A_STILL_READS",stale.status)
            surviving=await page_b.request.get(
                ORIGIN+"/api/history/conversations?limit=2")
            assert surviving.status==200
            await foreign_owner_denied(page_b,ids_a)
            restricted_history_snapshot(demo,"AFTER_REVOKE",restricted_before)
            migration_ledger_snapshot("AFTER_REVOKE",source_cluster,ledger_before)
            oidc_same_transaction_matrix(demo,raw_a,raw_b,"AFTER_REVOKE",ids_a,ids_b,revoked=True)
            result={
                "schema":"foundation.f3.real_browser_pg_restored_same_context.v1",
                "sha":command(["git","rev-parse","HEAD"]).strip(),
                "env":"disposable-GitHub-Actions-standard-Keycloak-Chromium-Next-mTLS-PG17",
                "genuine_two_browser_context_oidc":True,
                "strict_https_browser_ca_loopback_ip_san":True,
                "browser_default_history_sql_equal":True,
                "browser_pagination_and_detail_sql_equal":True,
                "browser_detail_message_id_and_body_sql_equal":True,
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
                "db_restricted_history_role":"history_app",
                "db_restricted_sql_read_only":True,
                "db_restricted_six_tables_exact_parity":True,
                "db_restricted_cross_owner_unset_context_zero":True,
                "db_restricted_sql_checkpoints":7,
                "db_restricted_owner_counts":{
                    label:{table:entry[0] for table,entry in tables.items()}
                    for label,tables in restricted_before.items()},
                "db_transport":"PG17_VERIFY_FULL_CA_SAN_SOURCE_RESTORE_ROLLBACK",
                "db_tls_plaintext_wrong_san_negative":True,
                "db_guc_is_not_identity_proof":True,
                "db_real_oidc_same_transaction_matrix":"SOURCE_RESTORED_ROLLBACK_REVOKED_A_DENIED_B_ADMITTED",
                "db_real_oidc_replay_rollback_and_forged_binding_denied":True,
                "db_browser_migration_ledger":"ACTUAL_PINNED_001_010_EXECUTION_SOURCE_RESTORE_ROLLBACK_REVOKE_EXACT_PRIVATE",
                "db_browser_migration_ledger_rows":10,
                "db_browser_migration_ledger_checkpoints":4,
                "db_browser_db55_bridge":"NOT_RUN_IN_BROWSER_FIXTURE",
                "approved_rto_threshold":None,
                "signed_history_a_after_restore":200,
                "signed_history_b_after_restore":200,
                "old_a_after_revoke":401,
                "db_real_browser_logout_pg_lock_edge_then_commit":True,
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
    try:
        asyncio.run(execute())
    except Exception as exc:
        # Playwright's raw exception renders the full HTTP request headers,
        # including the real ephemeral __Host-rag-session cookie. Do NOT log
        # an exception traceback or args. Keep only the failing source line,
        # exception class and a stable redacted failure marker.
        frames=traceback.extract_tb(exc.__traceback__)
        safe_file=Path(__file__).resolve()
        own=next((frame for frame in reversed(frames)
                  if Path(frame.filename).resolve()==safe_file),None)
        location=own.lineno if own else 0
        print("F3_BROWSER_INTEGRATED_FAILED_REDACTED class="
              +type(exc).__name__+" source_line="+str(location),
              file=sys.stderr,flush=True)
        raise SystemExit(1) from None
