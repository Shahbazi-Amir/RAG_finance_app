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


def ssl_server(root:Path):
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
    ext.write_text("subjectAltName=IP:127.0.0.1\n"
                   "extendedKeyUsage=serverAuth\n")
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
        answer=self.h.list(pending,query=query)
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
        selected=next(iter(original_a))
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
        command(["pg_dump","-h","127.0.0.1","-p","5432","-U","postgres",
                 "-F","c","-f",str(backup),"history_ci"])
        self.assertGreater(backup.stat().st_size,1024)
        globals_sql=command(["pg_dumpall","-h","127.0.0.1","-p","5432",
                             "-U","postgres","--globals-only","--no-role-passwords"])
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
                                ("auth_revoker","synthetic_revoker_only")):
                admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role),sql.Literal(secret)))
            admin.execute("CREATE DATABASE history_restore_f3_ci")
        command(["pg_restore","-h","127.0.0.1","-p","5433","-U","postgres",
                 "--exit-on-error","-d","history_restore_f3_ci",str(backup)])
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
                Path(h.fixture.cert).read_text()).encode()).hexdigest(),
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
        env=dict(os.environ)
        env.pop("CI",None);env.pop("GITHUB_ACTIONS",None)
        env["API_RUNNER_EXECUTION_MODE"]="APP_ONLY"
        for flag in ("OPENAI_API_KEY","API_PROVIDER_KEY","C018_RUNNER_PATH",
                     "QDRANT_URL","MODEL_GATEWAY_URL","API_ENGINE_ENABLED"):
            env.pop(flag,None)
        proc=subprocess.Popen(
            [sys.executable,"-m","apps.api.private_app_only_asgi","--config",str(config)],
            cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.__class__.api_process=proc
        restored_url="https://127.0.0.1:"+str(cfg["listen_port"])
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
        direct=h.request("POST","/v1/messages",body=b'{"question":"NO_DISPATCH"}')
        self.assertEqual(direct.status_code,503)
        self.assertIn("ENGINE_NOT_CONFIGURED",direct.text)
        with connect(5433,db="history_restore_f3_ci",extra=trusted) as c:
            after_send=c.execute("SELECT count(*) FROM history_l1.send_receipts").fetchone()[0]
            self.assertEqual(receipts_before,after_send)
        ready=h.request("GET","/internal/ready")
        self.assertEqual(ready.status_code,200)
        self.assertEqual(ready.json()["bootstrap_idp"],"not_probed")
        # Restart should never mask an unavailable Postgres dependency.
        command(["docker","stop",name])
        down=h.request("GET","/internal/ready")
        self.assertEqual(down.status_code,503)
        command(["docker","start",name])
        for _ in range(50):
            try:
                res=h.request("GET","/internal/ready")
                if res.status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.2)
        else:self.fail("RESTORED_DATABASE_UNAVAILABLE_AFTER_RESTART")
        operation_id=str(uuid.uuid4())
        raw=json.dumps({"operation_id":operation_id},separators=(",",":")).encode()
        revoke=h.request("POST",REVOKE,h.signed(a,"POST",REVOKE,raw)[0],body=raw)
        self.assertEqual(revoke.status_code,200,revoke.text[:500])
        self.assertEqual(h.list(a).status_code,401)
        self.assertEqual(h.list(b).status_code,200)

        output=ROOT/"ci_receipts"/"f3_foundation_restored_signed_history.json"
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({
            "schema":"foundation.f3.signed_history_restored_lab.v1",
            "source_sha":os.environ["GITHUB_SHA"],
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
            "revoke_A":200,"stale_A":401,"B_after_revoke":200,
            "pg_stop_readiness":503,
            "pg_restart_readiness":200,
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
