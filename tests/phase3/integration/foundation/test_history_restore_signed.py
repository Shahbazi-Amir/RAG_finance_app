"""Foundation lab: real signed HTTPS History on fresh PostgreSQL restore volume.

Uses the repository's existing disposable OIDC login test harness. The IdP
implementation in that harness is synthetic, so this explicitly DOES NOT
assert standard external Keycloak or Web/BFF browser acceptance. Runs only
in a fresh GitHub Actions PostgreSQL17.11 job; no Mac/engine/SQL011.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import time
import unittest
import uuid

import httpx
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from urllib.parse import urlencode
from apps.api import history_api
from src.phase3.storage.postgres import auth_session

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/"tests/phase3/integration/api"))
from test_product_session_011 import RealProductSession011, LIST, REVOKE, port


def command(args, *, env=None, input=None):
    # Never send passwords, JWTs or full DSNs to GitHub logs.
    cp=subprocess.run(args,input=input,env=env,text=True,
                      stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                      timeout=110,check=False)
    if cp.returncode:
        raise AssertionError("ISOLATED_COMMAND_FAILED:"+str(args[0])+
                             ":exit_"+str(cp.returncode))
    return cp.stdout


def pg17(tool, *parts):
    """PG17 client from the exact disposable 17.11 image.

    Ubuntu 24.04 runner's default pg_dump is v16 and cannot dump a PG17
    database; never silently downgrade this versioned backup/restore.
    The GHA temp directory is the only mounted path, not a Mac volume.
    """
    temp=str(Path(os.environ["RUNNER_TEMP"]).resolve())
    return command(["docker","run","--rm","--network","host",
                    "--pull","never",
                    "-e","PGPASSWORD="+os.environ["PGPASSWORD"],
                    "-v",temp+":"+temp,
                    "postgres:17.11",tool,*parts])


def ssl_server(root:Path, *, include_private_dns=False):
    ca_key=root/"restore-ca.key"; ca=root/"restore-ca.crt"
    key=root/"restore-server.key"; crt=root/"restore-server.crt"
    csr=root/"restore-server.csr"
    ext=root/"restore-server.ext"
    command(["openssl","req","-x509","-newkey","rsa:2048","-nodes",
             "-days","1","-keyout",str(ca_key),"-out",str(ca),
             "-subj","/CN=F3IsolatedRestoreCA",
             "-addext","basicConstraints=critical,CA:TRUE"])
    command(["openssl","req","-newkey","rsa:2048","-nodes",
             "-keyout",str(key),"-out",str(csr),
             "-subj","/CN=127.0.0.1"])
    ext.write_text("subjectAltName=IP:127.0.0.1"
                   +(",DNS:f3-pg" if include_private_dns else "")
                   +"\nextendedKeyUsage=serverAuth\n")
    command(["openssl","x509","-req","-in",str(csr),"-CA",str(ca),
             "-CAkey",str(ca_key),"-CAcreateserial","-out",str(crt),
             "-days","1","-extfile",str(ext)])
    key.chmod(0o600)
    return ca,key,crt


def connect(port_number=5432,username="postgres",password=None,db="history_ci",
            extra=""):
    secret=password or os.environ["PGPASSWORD"]
    return psycopg.connect(
        "host=127.0.0.1 port="+str(port_number)+" dbname="+db+
        " user="+username+" password="+secret+" connect_timeout=3 "+extra,
        autocommit=True)


class FoundationRestoredSignedHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true"
                or not os.getenv("GITHUB_RUN_ID")
                or "dbname=history_ci" not in os.getenv("AUTH_MIG_DSN","")):
            raise RuntimeError("F3_RESTORE_REQUIRES_DISPOSABLE_GITHUB_CI")
        RealProductSession011.setUpClass()
        cls.h=RealProductSession011(
            "test_API011_01_pending_denied_then_A_B_real_owner_lists_and_005_replay")
        cls.target=None; cls.volume=None; cls.api_process=None

    @classmethod
    def tearDownClass(cls):
        if cls.api_process is not None:
            cls.api_process.terminate()
            try: cls.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.api_process.kill();cls.api_process.wait(timeout=5)
        if cls.target:
            command(["docker","rm","-f",cls.target])
        if cls.volume:
            command(["docker","volume","rm",cls.volume])
        RealProductSession011.tearDownClass()

    def signed_page(self,pending,url=None,query=""):
        if url is not None:self.h.url=url
        # HTTP raw query is WITHOUT '?': exactly the bytes signed by BFF.
        signed,_=self.h.signed(pending,method="GET",path=LIST,
                               query=query.removeprefix("?").encode("ascii"))
        answer=self.h.request("GET",LIST,signed,query=query)
        self.assertEqual(answer.status_code,200,answer.text[:500])
        return answer.json()

    def browse_ids(self,pending,url):
        cursor=None
        ids=[]
        for index in range(25):
            q="?limit=2"+("&cursor="+cursor if cursor else "")
            obj=self.signed_page(pending,url,q)
            self.assertEqual(obj["scope_user_id"],pending["owner_id"])
            ids.extend(item["conversation_id"] for item in obj["items"])
            if not obj["page"]["has_more"]:
                self.assertIsNone(obj["page"]["next_cursor"])
                break
            cursor=obj["page"]["next_cursor"]
            self.assertTrue(cursor and len(cursor)<513)
        else: self.fail("UNBOUNDED_CURSOR")
        self.assertEqual(len(ids),len(set(ids)),"DUPLICATE_PAGINATION_ID")
        return ids

    def test_f3_signed_ab_history_replays_after_independent_restore(self):
        h=self.h; a,b=h.login("A"),h.login("B")
        self.assertNotEqual(a["owner_id"],b["owner_id"])
        for i in range(5):
            h.seed(a,"F3_A_HISTORY_RESTORE_"+str(i))
        for i in range(3):
            h.seed(b,"F3_B_HISTORY_RESTORE_"+str(i))
        source_url=h.url
        original_a=set(self.browse_ids(a,source_url))
        original_b=set(self.browse_ids(b,source_url))
        self.assertTrue(original_a.isdisjoint(original_b))
        self.assertGreaterEqual(len(original_a),5)
        self.assertGreaterEqual(len(original_b),3)
        # Real persisted user messages in two known synthetic conversations;
        # never use Send HTTP or invoke an engine. Keep exact SQL expectations.
        selected=sorted(original_a)[0]
        selected_b=sorted(original_b)[0]
        detail_cases=[]
        for actor,cid,label in ((a,selected,"A"),(b,selected_b,"B")):
            for i in range(3):
                req={"kind":"send_message_request","contract_version":"product.v1",
                     "requested_conversation_id":cid,"client_message_id":history_api.uid(),
                     "idempotency_key":"api137_"+uuid.uuid4().hex,
                     "question":"API137_PRIVATE_"+label+"_"+str(i)}
                with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,row_factory=dict_row) as c:
                    history_api.send_t1(c,actor["owner_id"],req,history_api.uid(),history_api.uid())
            with connect() as c:
                expected=c.execute("SELECT id,body FROM history_l1.messages WHERE owner_id=%s AND conversation_id=%s ORDER BY created_at,id",(actor["owner_id"],cid)).fetchall()
            self.assertEqual(len(expected),3)
            detail_cases.append((actor,cid,expected))
        foreign_path="/v1/conversations/"+selected+"/messages"
        denied=h.request("GET",foreign_path,
                         h.signed(b,method="GET",path=foreign_path)[0])
        self.assertEqual(denied.status_code,404,denied.text[:500])

        with connect() as c:
            counts_before=c.execute(
                "SELECT owner_id,count(*) AS n FROM history_l1.conversations "
                "WHERE owner_id IN (%s,%s) GROUP BY owner_id",
                (a["owner_id"],b["owner_id"])).fetchall()
            self.assertEqual(len(counts_before),2)
            receipts_before=c.execute(
                "SELECT count(*) FROM history_l1.send_receipts").fetchone()[0]
        lab=os.environ["RUNNER_TEMP"]
        backup=Path(lab)/"f3-history-before-restore.dump"
        globals_path=Path(lab)/"f3-history-roles-private.sql"
        # Pull exact PG17 CLI image once in the disposable lab.
        command(["docker","pull","postgres:17.11"])
        pg17("pg_dump","-h","127.0.0.1","-p","5432","-U","postgres",
             "-F","c","-f",str(backup),"history_ci")
        self.assertGreater(backup.stat().st_size,1024)
        globals_sql=pg17("pg_dumpall","-h","127.0.0.1","-p","5432",
                          "-U","postgres","--globals-only","--no-role-passwords")
        globals_sql="\n".join(line for line in globals_sql.splitlines()
            if not re.match(r"^(CREATE ROLE postgres;|ALTER ROLE postgres WITH)",line))
        globals_path.write_text(globals_sql+"\n",encoding="utf-8")
        globals_path.chmod(0o600)
        ca,key,crt=ssl_server(Path(lab))
        run_id=os.environ["GITHUB_RUN_ID"]+"-"+os.environ.get("GITHUB_RUN_ATTEMPT","1")
        name="f3-history-restore-"+run_id
        volume="f3-history-volume-"+run_id
        self.__class__.volume=volume
        command(["docker","volume","create",volume])
        self.__class__.target=name
        command(["docker","run","-d","--name",name,"-p","127.0.0.1:5433:5432",
                 "--network","bridge","--restart","no",
                 "-e","POSTGRES_PASSWORD="+os.environ["PGPASSWORD"],
                 "-v",volume+":/var/lib/postgresql/data","postgres:17.11"])
        for _ in range(60):
            try:
                with connect(5433,db="postgres"):break
            except psycopg.Error:time.sleep(1)
        else:self.fail("RESTORE_NEW_VOLUME_POSTGRES_NOT_READY")

        for source,target in ((key,"server.key"),(crt,"server.crt")):
            command(["docker","cp",str(source),name+":/var/lib/postgresql/data/"+target])
            command(["docker","exec","-u","0",name,"chown","postgres:postgres",
                     "/var/lib/postgresql/data/"+target])
        command(["docker","exec","-u","0",name,"chmod","0600",
                 "/var/lib/postgresql/data/server.key"])
        with connect(5433,db="postgres") as c:
            c.execute("ALTER SYSTEM SET ssl='on'")
            c.execute("ALTER SYSTEM SET ssl_cert_file='server.crt'")
            c.execute("ALTER SYSTEM SET ssl_key_file='server.key'")
        command(["docker","restart",name])
        trusted="sslmode=verify-full sslrootcert="+str(ca)
        for _ in range(60):
            try:
                with connect(5433,db="postgres",extra=trusted) as c:
                    enabled=c.execute(
                        "SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()"
                    ).fetchone()[0]
                    if enabled:break
            except psycopg.Error:time.sleep(1)
        else:self.fail("RESTORE_SERVER_TLS_NOT_VERIFIED")

        # All security roles are cloned without exporting real role passwords.
        # Passwords here are CI-only synthetic; source secrets never persisted.
        command(["psql","-h","127.0.0.1","-p","5433","-U","postgres",
                 "-d","postgres","-v","ON_ERROR_STOP=1","-f",str(globals_path)])
        with connect(5433,db="postgres",extra=trusted) as admin:
            for role,secret in (("history_app","synthetic_app_only"),
                                ("auth_revoker","synthetic_revoker_only"),
                                ("auth_sessions","synthetic_session_only")):
                admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role),sql.Literal(secret)))
            admin.execute("CREATE DATABASE history_restore_f3_ci")
        pg17("pg_restore","-h","127.0.0.1","-p","5433","-U","postgres",
             "--exit-on-error","-d","history_restore_f3_ci",str(backup))
        with connect(5433,db="history_restore_f3_ci",extra=trusted) as c:
            counts_after=c.execute(
                "SELECT owner_id,count(*) AS n FROM history_l1.conversations "
                "WHERE owner_id IN (%s,%s) GROUP BY owner_id",
                (a["owner_id"],b["owner_id"])).fetchall()
            self.assertEqual(sorted(counts_before),sorted(counts_after))
        with connect(5433,username="history_app",password="synthetic_app_only",
                     db="history_restore_f3_ci",extra=trusted) as c:
            for owner,expected,foreign in (
                (a["owner_id"],len(original_a),len(original_b)),
                (b["owner_id"],len(original_b),len(original_a))):
                with c.transaction():
                    c.execute("SELECT set_config('app.owner_id',%s,true)",(owner,))
                    n=c.execute("SELECT count(*) FROM history_l1.conversations").fetchone()[0]
                    self.assertEqual(n,expected)

        # Newly launched, actual private signed product ASGI on restored PG.
        cfg={
            "contract_version":"api.private_app_only_asgi.v1",
            "listen_host":"127.0.0.1","listen_port":port(),
            "server_tls_cert_file":str(h.temp/"server.pem"),
            "server_tls_key_file":str(h.temp/"server.key"),
            "trusted_bff_ca_file":h.fixture.ca,
            "bff_leaf_cert_sha256":hashlib.sha256(ssl.PEM_cert_to_DER_cert(
                Path(h.fixture.cert).read_text())).hexdigest(),
            "bff_issuer":"urn:rag-finance:synthetic-product-session",
            "bff_audience":"urn:rag-finance:api:history-h1-isolated",
            "bff_kid":"ci-product-session-kid",
            "bff_rs256_public_key_file":str(h.pubkey),
            "history_dsn":("host=127.0.0.1 port=5433 dbname=history_restore_f3_ci "
                           "user=history_app password=synthetic_app_only "+trusted),
            "revoke_dsn":("host=127.0.0.1 port=5433 dbname=history_restore_f3_ci "
                          "user=auth_revoker password=synthetic_revoker_only "+trusted),
        }
        for cert in (h.temp/"server.pem",h.temp/"server.key",Path(h.fixture.ca),
                     Path(h.fixture.cert),Path(h.fixture.key),h.pubkey):
            cert.chmod(0o600)
        config=h.temp/"foundation-restore-app-only.json"
        config.write_text(json.dumps(cfg));config.chmod(0o600)
        # This is a separately launched, real app-only process against
        # the disposable restored DB, never the CI fixture interpreter.
        # Pass only its explicitly required runtime inputs (no ambient
        # CI/PG service/provider settings, credentials or engine flags).
        env={
            "PATH":os.environ["PATH"], "HOME":str(h.temp),
            "LANG":"C.UTF-8", "PYTHONUNBUFFERED":"1",
            "PHASE3_APP_MODE":"APP_ONLY",
            "API_RUNNER_EXECUTION_MODE":"APP_ONLY",
            "API_CURSOR_KEY":os.environ["API_CURSOR_KEY"],
            "API_CURSOR_TTL_SECONDS":os.environ["API_CURSOR_TTL_SECONDS"],
        }
        from apps.api.private_app_only_asgi import assert_app_only_environment
        assert_app_only_environment(env)
        # Bad configured signing material must fail startup rather than
        # listening with a fake 200. Use a separate ephemeral config and port.
        bad_key=h.temp/"api137-invalid-public.pem"
        bad_key.write_text("invalid public key");bad_key.chmod(0o600)
        bad_cfg=h.temp/"api137-invalid-config.json"
        bad_cfg.write_text(json.dumps({**cfg,"bff_rs256_public_key_file":str(bad_key),"listen_port":port()}))
        bad_cfg.chmod(0o600)
        failed=subprocess.run([sys.executable,"-m","apps.api.private_app_only_asgi","--config",str(bad_cfg)],
                              cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(failed.returncode,78)
        self.assertEqual(failed.stderr.strip(),"APP_ONLY_STARTUP_DENIED")
        with socket.socket() as sock:
            sock.settimeout(.5)
            self.assertNotEqual(sock.connect_ex(("127.0.0.1",json.loads(bad_cfg.read_text())["listen_port"])),0)
        security_log=h.temp/"api137-private-security.log"
        log_stream=security_log.open("wb")
        self.addCleanup(log_stream.close)
        proc=subprocess.Popen(
            [sys.executable,"-m","apps.api.private_app_only_asgi","--config",str(config)],
            cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=log_stream)
        self.__class__.api_process=proc
        restored_url="https://127.0.0.1:"+str(cfg["listen_port"])
        h.url=restored_url
        for _ in range(80):
            if proc.poll() is not None:self.fail("RESTORED_PRIVATE_ASGI_STARTUP_DENIED")
            try:
                res=h.request("GET",LIST,headers={"X-Owner-ID":"forged"})
                if res is not None and res.status_code==401:break
            except (httpx.HTTPError,OSError):pass
            time.sleep(.1)
        else:self.fail("RESTORED_PRIVATE_ASGI_UNREACHABLE")
        new_a=set(self.browse_ids(a,restored_url))
        new_b=set(self.browse_ids(b,restored_url))
        self.assertEqual(original_a,new_a)
        self.assertEqual(original_b,new_b)
        denied=h.request("GET",foreign_path,
                         h.signed(b,method="GET",path=foreign_path)[0])
        self.assertEqual(denied.status_code,404,denied.text[:500])
        # Test both ownership directions on the actual restored private API.
        for caller, foreign_ids in ((a, new_b), (b, new_a)):
            for foreign in foreign_ids:
                path="/v1/conversations/"+foreign+"/messages"
                response=h.request("GET",path,h.signed(caller,"GET",path)[0])
                self.assertEqual(response.status_code,404)
        # Real private process; exact SQL message body/IDs and chronological
        # page order; same owner refresh, opposite owner non-disclosure.
        def get(actor,path,q="",override=None,token=None,body=None,headers=None):
            signed=token or h.signed(actor,"GET",path,query=q.removeprefix("?").encode(),override=override)[0]
            response=h.request("GET",path,signed,query=q,body=body,headers=headers)
            self.assertEqual(response.headers.get("cache-control"),"no-store")
            return response
        def error(response,expected,code):
            self.assertEqual(response.status_code,expected)
            doc=response.json()
            self.assertEqual(doc["kind"],"error_response")
            self.assertEqual(doc["contract_version"],"product.v1")
            self.assertEqual(doc["error"]["code"],code)
            self.assertTrue(doc["request_id"] and doc["trace_id"])
            history_api.VALIDATOR.validate(doc)
            return (doc["request_id"],doc["trace_id"])
        pairs=[]
        for actor,cid,expected in detail_cases:
            path="/v1/conversations/"+cid+"/messages"
            observed=[]
            first=get(actor,path,"?limit=1")
            self.assertEqual(first.status_code,200)
            history_api.VALIDATOR.validate(first.json())
            cursor=first.json()["page"]["next_cursor"]
            page=first
            for n in range(3):
                self.assertEqual(page.status_code,200)
                doc=page.json();history_api.VALIDATOR.validate(doc)
                self.assertEqual(doc["owner_user_id"],actor["owner_id"])
                self.assertEqual(doc["answers"],[])
                observed.extend((v["message_id"],v["text"]) for v in doc["items"])
                nxt=doc["page"]["next_cursor"]
                if n<2:
                    self.assertTrue(doc["page"]["has_more"] and nxt)
                    page=get(actor,path,"?limit=1&cursor="+nxt)
                else:self.assertFalse(doc["page"]["has_more"]);self.assertIsNone(nxt)
            self.assertEqual(observed,expected)
            refresh=get(actor,path,"?limit=3")
            self.assertEqual(refresh.status_code,200)
            self.assertEqual([(v["message_id"],v["text"]) for v in refresh.json()["items"]],expected)
            other=b if actor is a else a
            denied=get(other,path)
            pairs.append(error(denied,404,"NOT_FOUND"))
            self.assertNotIn(expected[0][1],denied.text)
            pairs.append(error(get(other,path,"?limit=1&cursor="+cursor),404,"NOT_FOUND"))
            flipped=("A" if cursor[0]!="A" else "B")+cursor[1:]
            pairs.append(error(get(actor,path,"?limit=1&cursor="+flipped),422,"INVALID_CURSOR"))
            pairs.append(error(get(actor,path,"?limit=2&cursor="+cursor),422,"INVALID_CURSOR"))
        # Strict temporal and identity binding on a fresh signature per case.
        now=int(time.time())
        invalid=[{"iss":"urn:api137:wrong"},{"aud":"urn:api137:wrong"},
                 {"epoch":a["epoch"]+1},{"generation":a["generation"]+1},
                 {"owner_id":b["owner_id"]},{"iat":now-60,"nbf":now-60,"exp":now-30},
                 {"nbf":now+120,"iat":now+120,"exp":now+145}]
        for override in invalid:
            pairs.append(error(get(a,LIST,override=override),401,"AUTH_REQUIRED"))
        token,_=h.signed(a,"GET",LIST)
        bad_token=token[:-10]+("A" if token[-10]!="A" else "B")+token[-9:]
        pairs.append(error(get(a,LIST,token=bad_token),401,"AUTH_REQUIRED"))
        pairs.append(error(get(a,LIST,"?limit=2",token=token),401,"AUTH_REQUIRED"))
        pairs.append(error(get(a,LIST,body=b"API137_BODY_CANARY"),401,"AUTH_REQUIRED"))
        for q in ("?limit=0","?limit=101","?limit=2&limit=3","?owner=API137_QUERY_CANARY"):
            pairs.append(error(get(a,LIST,q),422,"INVALID_REQUEST"))
        for path in ("/v1/message-requests/claim-test-status","/v1/message-requests/invited-live-result","/openapi.json"):
            pairs.append(error(get(a,path),404,"NOT_FOUND"))
        self.assertEqual(len(set(x[0] for x in pairs)),len(pairs))
        self.assertEqual(len(set(x[1] for x in pairs)),len(pairs))
        # SQL role-controlled synthetic session rotation and expiry in the
        # restored clone only. No client is allowed to issue sessions.
        with psycopg.connect("host=127.0.0.1 port=5433 dbname=history_restore_f3_ci user=auth_sessions password=synthetic_session_only "+trusted,
                             autocommit=True,row_factory=dict_row) as c:
            old=auth_session.issue(c,a["owner_id"],a["epoch"],idle_seconds=60,absolute_seconds=120)
            fresh=auth_session.rotate(c,old.opaque,old.epoch,old.generation)
            self.assertEqual(old.absolute_expires_at,fresh.absolute_expires_at)
            expired=auth_session.issue(c,a["owner_id"],a["epoch"],idle_seconds=60,absolute_seconds=120)
        def actor_for(issued):
            return {"owner_id":issued.owner_id,"session_verifier":issued.opaque,"epoch":issued.epoch,"generation":issued.generation}
        self.assertEqual(get(actor_for(fresh),LIST).status_code,200)
        pairs.append(error(get(actor_for(old),LIST),401,"AUTH_REQUIRED"))
        pairs.append(error(get(actor_for(fresh),LIST,override={"generation":old.generation}),401,"AUTH_REQUIRED"))
        self.assertEqual(get(actor_for(expired),LIST).status_code,200)
        with connect(5433,db="history_restore_f3_ci",extra=trusted) as c:
            c.execute("""UPDATE auth_l1.sessions SET created_at=clock_timestamp()-interval '130 seconds',
                last_activity_at=clock_timestamp()-interval '130 seconds',
                idle_expires_at=clock_timestamp()-interval '70 seconds',
                absolute_expires_at=clock_timestamp()-interval '10 seconds'
                WHERE digest_sha256=%s""",(hashlib.sha256(expired.opaque.encode()).hexdigest(),))
        pairs.append(error(get(actor_for(expired),LIST),401,"AUTH_REQUIRED"))
        self.assertEqual(get(b,LIST).status_code,200)
        # Original source and restored History are unchanged by HTTP reads
        # and denied requests. Auth replay rows are intentionally excluded.
        with connect(5433,db="history_restore_f3_ci",extra=trusted) as c:
            for actor,cid,expected in detail_cases:
                self.assertEqual(c.execute("SELECT id,body FROM history_l1.messages WHERE owner_id=%s AND conversation_id=%s ORDER BY created_at,id",(actor["owner_id"],cid)).fetchall(),expected)
            self.assertEqual(c.execute("SELECT count(*) FROM history_l1.send_receipts").fetchone()[0],receipts_before)
        log_stream.flush()
        logs=security_log.read_text(encoding="utf-8",errors="replace")
        entries=[json.loads(line) for line in logs.splitlines() if line.startswith('{"event":"private_request_denied"')]
        self.assertGreaterEqual(len(entries),10)
        self.assertTrue(all(e=={"event":"private_request_denied","status":401} for e in entries))
        for canary in (token,bad_token,a["session_verifier"],b["session_verifier"],old.opaque,fresh.opaque,
                       expired.opaque,a["owner_id"],b["owner_id"],"API137_PRIVATE_","API137_BODY_CANARY","API137_QUERY_CANARY"):
            self.assertNotIn(canary,logs)
        matrix={"sql_detail_messages":6,"detail_pages":6,"refresh_same_ids":True,"canonical_error_count":len(pairs),
                "security_log_fixed_events":len(entries),"raw_secrets_absent":True,
                "invalid_signer_startup_exit":78,"invalid_signer_listen":False,
                "expired_signature_denied":True,"expired_db_session_denied":True,"rotation_new_200_old_401":True,
                "absolute_expiry_unchanged":True,"readiness_policy_approved":False,
                "fixture_routes_denied":3,"durable_send_count_unchanged":True}
        print("API137_SIGNED_DETAIL_CURSOR_SECURITY_ROTATION_MATRIX_PASS",flush=True)
        # A valid one-use assertion must not be accepted twice after restore.
        for actor in (a,b):
            proof=h.signed(actor)[0]
            self.assertEqual(h.list(actor,token=proof).status_code,200)
            self.assertEqual(h.list(actor,token=proof).status_code,401)
        # Encoded / slash aliases must be denied before even invalid JSON is
        # parsed; run twice to cover retries on the real signed runtime.
        for _ in range(2):
            for path in ("/v1/messages","/v1/%6dessages","/v1%2Fmessages",
                         "/v1/messages/","/v1/messages%2f"):
                direct=h.request("POST",path,body=b"not valid JSON")
                self.assertEqual(direct.status_code,503)
                self.assertIn("ENGINE_NOT_CONFIGURED",direct.text)
                self.assertEqual(direct.headers.get("cache-control"),"no-store")
        with connect(5433,db="history_restore_f3_ci",extra=trusted) as c:
            after_send=c.execute("SELECT count(*) FROM history_l1.send_receipts").fetchone()[0]
            self.assertEqual(receipts_before,after_send)
        ready=h.request("GET","/internal/ready")
        self.assertEqual(ready.status_code,200)
        self.assertEqual(ready.json()["bootstrap_idp"],"not_probed")
        def signed_ready(actor):
            token,_=h.signed(actor,method="GET",path="/health/ready")
            result=h.request("GET","/health/ready",token)
            self.assertEqual(result.headers.get("cache-control"),"no-store")
            return result
        self.assertEqual(signed_ready(a).status_code,200)
        self.assertEqual(signed_ready(b).status_code,200)
        self.assertEqual(h.request("GET","/health/ready").status_code,503)
        # Restart should never mask an unavailable Postgres dependency.
        command(["docker","stop",name])
        down=h.request("GET","/internal/ready")
        self.assertEqual(down.status_code,503)
        self.assertEqual(signed_ready(a).status_code,503)
        command(["docker","start",name])
        for _ in range(50):
            try:
                res=h.request("GET","/internal/ready")
                if res.status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.2)
        else:self.fail("RESTORED_DATABASE_UNAVAILABLE_AFTER_RESTART")
        self.assertEqual(signed_ready(a).status_code,200)
        self.assertEqual(signed_ready(b).status_code,200)
        operation_id=str(uuid.uuid4())
        raw=json.dumps({"operation_id":operation_id},separators=(",",":")).encode()
        revoke=h.request("POST",REVOKE,h.signed(a,"POST",REVOKE,raw)[0],body=raw)
        self.assertEqual(revoke.status_code,200,revoke.text[:500])
        self.assertEqual(h.list(a).status_code,401)
        self.assertEqual(h.list(b).status_code,200)
        self.assertEqual(signed_ready(a).status_code,503)
        self.assertEqual(signed_ready(b).status_code,200)
        print("F3_FOUNDATION_RESTORED_SIGNED_ACTOR_READINESS_AND_REVOKE_PASS")

        output=ROOT/"ci_receipts"/"f3_foundation_restored_signed_history.json"
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({
            "schema":"foundation.f3.signed_history_restored_lab.v1",
            "source_sha":os.environ["GITHUB_SHA"],
            "api137_extended_matrix":matrix,
            "environment":"disposable_GHA_PG17_to_independent_Docker_volume",
            "owners_distinct":True,
            "source_and_restored_ids_equal_A":len(original_a),
            "source_and_restored_ids_equal_B":len(original_b),
            "signed_https_mtls":True,
            "pg_role":"history_app_non_super_non_bypass",
            "restore_tls_verify_full":True,
            "owner_B_direct_A_detail":404,
            "send":503,
            "send_durable_receipts_unchanged":True,
            "all_restored_cross_owner_ids_bidirectional_404":True,
            "restored_signed_assertion_replay_both_owners_401":True,
            "send_aliases_repeated_invalid_json_503":True,
            "revoke_A":200,"stale_A":401,"B_after_revoke":200,
            "pg_stop_readiness":503,
            "pg_restart_readiness":200,
            "signed_readiness_valid_A_B":200,
            "signed_readiness_missing_proof":503,
            "signed_readiness_pg_down":503,
            "signed_readiness_pg_recovered":200,
            "signed_readiness_revoked_A":503,
            "signed_readiness_B_after_A_revoke":200,
            "bootstrap_idp_verified":False,
            "real_browser_idp_login":False,
            "mac_target_tested":False,
            "engine_calls":0,
            "module_gate_accepted":False,
            "outcome":"PASS_RESTORED_SIGNED_API_SQL_SUBSET_NOT_BROWSER_JOURNEY",
        },indent=2)+"\n")
        print("F3_FOUNDATION_RESTORED_SIGNED_AB_HISTORY_PG17_LAB_PASS_NOT_BROWSER")

if __name__=="__main__":
    unittest.main()
