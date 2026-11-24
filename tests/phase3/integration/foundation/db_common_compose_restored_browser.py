"""Foundation CI-only post-Restore Compose topology.

The unchanged, already tested API-owner journey does the first browser login,
SQL witness, fresh independent PG restore, TLS, signed API and repeat journey.
Here we additionally move Web/BFF, ingress and Bootstrap into actual containers
on the restored API/PG/IdP network *before* replaying the browser assertions.
The loopback-only CI BFF/Bootstrap contract stays unchanged: a byte relay
shares Web's network namespace and never terminates mTLS or injects identity.

No product staging profile or real domain is used. Before restore, Web and
Bootstrap are still host processes. Bootstrap uses the frozen CI worker and
pinned initial-login overlay, not the deployable private-staging entrypoint.
"""
from __future__ import annotations

import asyncio
from base64 import urlsafe_b64decode
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import socket
import subprocess
import time
import sys
from unittest.mock import patch

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from psycopg.conninfo import make_conninfo
from playwright.async_api import async_playwright, expect
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests/phase3/integration/api"))
from db_common_compose_browser_journey import AppOnlyBrowserDemo, ORIGIN
from src.phase3.storage.postgres import auth_session


def verify_isolation():
    assert os.environ.get("CI")=="true" and os.environ.get("GITHUB_ACTIONS")=="true"
    assert os.environ.get("GITHUB_RUN_ID")
    assert re.search(r"dbname=history_browser_restore_ci_[a-f0-9]{16}(?: |$)",os.environ.get("AUTH_MIG_DSN",""))
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


class ComposeRestoredBrowserDemo(AppOnlyBrowserDemo):
    def add(self, cmd, env=None, cwd=ROOT):
        proc = super().add(cmd, env, cwd)
        if cmd[0] == "./node_modules/.bin/next":
            self.host_web = proc
            self.web_env = {k:v for k,v in env.items() if k.startswith("AUTH_CI_")}
        elif len(cmd) > 1 and str(cmd[1]).endswith("auth_010_https_proxy.mjs"):
            self.host_ingress = proc
        return proc

    @contextmanager
    def fresh_volume(self):
        with super().fresh_volume() as restored:
            try:
                yield restored
            finally:
                self.stop_compose()

    def raw_from_alias(self, handle):
        if not getattr(self, "compose_project", None):
            return super().raw_from_alias(handle)
        # The actual Web UID owns the alias store; never relax its permissions.
        name = "alias-" + sha256(handle.encode()).hexdigest() + ".json"
        record = json.loads(self.ci_command("sudo", "cat", str(self.shared/name)))
        assert record["status"] == "ACTIVE"
        def decode(value):
            return urlsafe_b64decode(value + "="*((-len(value))%4))
        ciphertext = decode(record["ciphertext"]) + decode(record["tag"])
        verifier = AESGCM(self.alias_key).decrypt(decode(record["iv"]),ciphertext,None)
        return {"session_ref":verifier.decode(),"owner_id":record["ownerId"],
                "epoch":record["epoch"],"generation":record["generation"]}

    def compose(self, *args, timeout=120):
        return self.ci_command("docker", "compose", "--project-name", self.compose_project,
                               "--file", str(self.compose_file), *args, timeout=timeout)

    @staticmethod
    def env_file(path, entries):
        # Fixture values have no newlines or interpolation characters.
        assert all(re.fullmatch(r"[A-Z][A-Z0-9_]*", k) and
                   isinstance(v,str) and not any(c in v for c in "\n\r$")
                   for k,v in entries.items())
        path.write_text("".join(k+"="+v+"\n" for k,v in entries.items()),encoding="utf-8")
        path.chmod(0o600)

    def start_compose(self, dsns, network):
        run = self.ci_command
        sha = os.environ["F3_EXACT_SHA"]
        assert re.fullmatch(r"[a-f0-9]{40}", sha)
        assert run("git","rev-parse","HEAD").decode().strip() == sha
        web_image = os.environ["F3_COMPOSE_BROWSER_WEB_IMAGE"]
        api_image = os.environ["API_F3_BROWSER_IMAGE"]
        assert web_image == "f3-compose-browser-web:" + sha
        assert api_image == "api-f3-browser:" + sha
        images = {}
        for image, uid in ((web_image,"11003:11003"),(api_image,"11001:11001")):
            d=json.loads(run("docker","image","inspect",image))[0]
            assert d["Config"]["User"] == uid
            assert d["Config"]["Labels"]["org.opencontainers.image.revision"] == sha
            assert re.fullmatch(r"sha256:[a-f0-9]{64}",d["Id"])
            images[image]=d["Id"]

        # Keep the existing browser cookies and sealed alias store. Stop the
        # host services before binding the same browser ingress port.
        for child in (self.host_ingress,self.host_web,self.bootstrap_process):
            if child is not None and any(p is child for p,_ in self.children):
                self.stop_child(child)
        self.bootstrap_process = None

        lab = self.root/"compose-restored"
        lab.mkdir(mode=0o700)
        webfiles, bootfiles, ingressfiles, auditdir, fixture = [lab/n for n in
                                        ("web","bootstrap","ingress","audit","fixture")]
        for d in (webfiles,bootfiles,ingressfiles,auditdir,fixture):
            d.mkdir(mode=0o700)

        def copy_secret(src, directory, name, target="/run/lab"):
            dst=directory/name
            shutil.copyfile(src,dst)
            dst.chmod(0o600)
            return target+"/"+name

        env=dict(self.web_env)
        for key in ("AUTH_CI_BOOTSTRAP_SIGN_KEY","AUTH_CI_PRODUCT_SIGN_KEY",
                    "AUTH_CI_BOOTSTRAP_CA","AUTH_CI_BOOTSTRAP_CERT",
                    "AUTH_CI_BOOTSTRAP_KEY"):
            # Existing CI-only BFF readers require /tmp paths. Preserve
            # the trust check; place only the fixture mount under /tmp.
            env[key]=copy_secret(env[key],webfiles,key.lower(),"/tmp/f3-ci-lab")
        proxy_tls={key:copy_secret(env.pop(key),ingressfiles,key.lower())
                   for key in ("AUTH_CI_TLS_CERT","AUTH_CI_TLS_KEY")}
        env["AUTH_CI_SHARED_STORE_DIR"]="/tmp/f3-ci-aliases"
        env.update(CI="true",PHASE3_APP_MODE="APP_ONLY",NEXT_TELEMETRY_DISABLED="1")
        env.pop("AUTH_CI_PRODUCT_CHAT_MODE",None)
        assert env["AUTH_CI_PUBLIC_ORIGIN"] == ORIGIN
        webenv=lab/"web.env"
        self.env_file(webenv,env)
        proxyenv=lab/"proxy.env"
        self.env_file(proxyenv,{**proxy_tls,**{k:env[k] for k in
                      ("CI","AUTH_CI_PROXY_SECRET","AUTH_CI_DEMO_MODE")}})

        worker=json.loads((self.root/"restore-bootstrap.json").read_text())
        assert worker["fault"] == ""
        for key in ("ca","server_cert","server_key"):
            worker[key]=copy_secret(worker[key],bootfiles,key+".pem")
        pgca=copy_secret(self.restore_pg_ca,bootfiles,"pg-ca.pem")
        worker["db_dsn"]={role:make_conninfo(dsn,host="pg-restore",port=5432,
                          sslmode="verify-full",sslrootcert=pgca,gssencmode="disable")
                          for role,dsn in worker["db_dsn"].items()}
        shutil.copyfile(worker["audit_path"],auditdir/"exchange.sqlite")
        (auditdir/"exchange.sqlite").chmod(0o600)
        worker["audit_path"]="/run/audit/exchange.sqlite"
        config=bootfiles/"worker.json"
        config.write_text(json.dumps(worker),encoding="utf-8")
        config.chmod(0o600)
        # Exact CI fixture overlay already fetched and checked by workflow.
        shutil.copyfile(ROOT/"tests/phase3/integration/api/bootstrap_010_worker.py",
                        fixture/"bootstrap_010_worker.py")
        shutil.copyfile(ROOT/"src/phase3/auth/initial_oidc_login.py",
                        fixture/"initial_oidc_login.py")
        for f in fixture.iterdir():
            f.chmod(0o444)
        fixture.chmod(0o755)

        api=json.loads(run("docker","inspect",self.api_container))[0]
        api_name=api["Name"].lstrip("/")
        assert re.fullmatch(r"api-restored-[a-f0-9]{32}",api_name)
        assert set(api["NetworkSettings"]["Networks"]) == {network}
        idp=json.loads(run("docker","inspect",self.kc.container))[0]
        assert idp["Config"]["Image"] == self.kc.IMAGE
        assert set(idp["NetworkSettings"]["Networks"]) == {self.kc.network}
        run("docker","network","connect","--alias","f3-ci-idp",network,self.kc.container)
        self.compose_idp_network=network

        self.compose_project="f3-restored-"+uuid.uuid4().hex[:20]
        self.compose_file=lab/"compose.json"
        self.compose_chowns=[]
        for uid, directory in ((11003,webfiles),(11003,self.shared),(11003,ingressfiles),
                               (11001,bootfiles),(11001,auditdir)):
            self.compose_chowns.append(directory)
            run("sudo","chown","-R",f"{uid}:{uid}",str(directory))

        def mount(src,dst,ro=True):
            return {"type":"bind","source":str(src),"target":dst,"read_only":ro}
        def common(image,uid):
            return {"image":image,"pull_policy":"never","user":f"{uid}:{uid}",
                    "read_only":True,"cap_drop":["ALL"],"security_opt":["no-new-privileges:true"],
                    "init":True,"restart":"no","tmpfs":["/tmp:rw,nosuid,noexec,size=32m"],
                    "healthcheck":{"disable":True}}
        web={**common(web_image,11003),"env_file":[str(webenv)],
             "networks":["restored"],"ports":["127.0.0.1:3443:3444"],
             "tmpfs":["/tmp:rw,nosuid,noexec,size=32m,uid=11003,gid=11003",
                      "/srv/release/apps/web/.next/cache:rw,nosuid,size=64m,uid=11003,gid=11003"],
             "volumes":[mount(webfiles,"/tmp/f3-ci-lab"),
                        mount(self.shared,"/tmp/f3-ci-aliases",False)]}
        bootstrap={**common(api_image,11001),"network_mode":"service:web",
                   "depends_on":["web"],
                   "command":["python3","-u","/srv/release/tests/phase3/integration/api/bootstrap_010_worker.py",
                              "/run/lab/worker.json"],
                   "environment":{"CI":"true","GITHUB_ACTIONS":"true"},
                   "volumes":[mount(bootfiles,"/run/lab"),mount(auditdir,"/run/audit",False),
                     mount(fixture/"bootstrap_010_worker.py",
                           "/srv/release/tests/phase3/integration/api/bootstrap_010_worker.py"),
                     mount(fixture/"initial_oidc_login.py",
                           "/srv/release/src/phase3/auth/initial_oidc_login.py")]}
        ingress={**common(web_image,11003),"network_mode":"service:web","depends_on":["web"],
                 "env_file":[str(proxyenv)],"command":["node","/run/fixture/ingress.mjs"],
                 "volumes":[mount(ingressfiles,"/run/lab"),
                            mount(ROOT/"tests/phase3/integration/ui/auth_010_https_proxy.mjs",
                                  "/run/fixture/ingress.mjs")]}
        endpoints={"product_port":int(self.product_origin.rsplit(":",1)[1]),
                   "api_host":api_name,"idp_port":self.kc.port}
        relay={**common(web_image,11003),"network_mode":"service:web","depends_on":["web"],
               "environment":{"CI":"true","F3_CI_RELAY":json.dumps(endpoints)},
               "command":["node","/run/fixture/relay.mjs"],
               "volumes":[mount(ROOT/"tests/phase3/integration/foundation/ci_loopback_relay.mjs",
                                 "/run/fixture/relay.mjs")]}
        self.compose_file.write_text(json.dumps({
            "services":{"web":web,"bootstrap":bootstrap,"ingress":ingress,"relay":relay},
            "networks":{"restored":{"external":True,"name":network}},
        }),encoding="utf-8")
        self.compose_file.chmod(0o600)
        self.compose("config","--quiet")
        self.compose("up","-d","--no-build","--pull","never")

        services={}
        for service,image,uid in (("web",web_image,11003),("bootstrap",api_image,11001),
                                  ("ingress",web_image,11003),("relay",web_image,11003)):
            cid=self.compose("ps","-q",service).decode().strip()
            assert cid
            d=json.loads(run("docker","inspect",cid))[0]
            assert d["State"]["Running"] and d["Image"] == images[image]
            assert d["Config"]["User"] == f"{uid}:{uid}"
            assert d["HostConfig"]["ReadonlyRootfs"]
            assert d["Config"]["Labels"]["com.docker.compose.project"] == self.compose_project
            services[service]=d
        # Keep BFF private signing keys and encrypted alias store out of the
        # ingress and relay containers; verify mounts, not just config intent.
        for service in ("bootstrap","ingress","relay"):
            sources={m["Source"] for m in services[service]["Mounts"]}
            assert str(webfiles) not in sources and str(self.shared) not in sources
        assert str(ingressfiles) in {m["Source"] for m in services["ingress"]["Mounts"]}
        webid=services["web"]["Id"]
        assert set(services["web"]["NetworkSettings"]["Networks"]) == {network}
        assert services["web"]["HostConfig"]["PortBindings"] == {
            "3444/tcp":[{"HostIp":"127.0.0.1","HostPort":"3443"}]}
        for service in ("bootstrap","ingress","relay"):
            assert services[service]["HostConfig"]["NetworkMode"] == "container:"+webid
            assert not services[service]["HostConfig"]["PortBindings"]
        # All actual components on one restored network, no public binding.
        members=json.loads(run("docker","network","inspect",network))[0]["Containers"]
        assert {webid,api["Id"],idp["Id"]}.issubset(members)
        assert len(members)==4 # Web namespace, signed API, PG, Keycloak
        for cid in members:
            d=json.loads(run("docker","inspect",cid))[0]
            for bindings in (d["HostConfig"]["PortBindings"] or {}).values():
                assert all(b["HostIp"]=="127.0.0.1" for b in bindings)
        self.await_url(ORIGIN+"/login",ssl.create_default_context(cafile=self.ca))
        # Bootstrap mTLS endpoint through the private shared namespace.
        # The CI fixture has a bounded health endpoint, never a target probe.
        probe=(
            "const fs=require('fs'),https=require('https');"
            "const req=https.get(process.env.AUTH_CI_BOOTSTRAP_ORIGIN+'/__fixture_health',"
            "{ca:fs.readFileSync(process.env.AUTH_CI_BOOTSTRAP_CA),"
            "cert:fs.readFileSync(process.env.AUTH_CI_BOOTSTRAP_CERT),"
            "key:fs.readFileSync(process.env.AUTH_CI_BOOTSTRAP_KEY)},"
            "r=>{r.resume();process.exit(r.statusCode===200?0:1)});"
            "req.setTimeout(5000,()=>req.destroy());req.on('error',()=>process.exit(1));"
        )
        self.compose("exec","-T","web","node","-e",probe)
        self.compose_witness={
            "source_sha":sha,"run_id":os.environ["GITHUB_RUN_ID"],
            "scope":"POST_RESTORE_ONLY_COMPOSE_WEB_BOOTSTRAP_INGRESS_REAL_OCI_API_PG_KEYCLOAK",
            "web_image_id":images[web_image],"api_image_id":images[api_image],
            "shared_network_member_count":len(members),
            "web_bootstrap_ingress_relay_shared_namespace":True,
            "no_public_port":True,"ci_fixture_bootstrap":True,
            "ingress_no_bff_signer_or_alias_mount":True,
            "source_phase_web_bootstrap_containerized":False,
            "full_compose_verified":False,"target_verified":False,"accepted":False,
        }
        print("F3_POST_RESTORE_SHARED_COMPOSE_NAMESPACE_READY",flush=True)

    async def verify_browser_privacy(self, browser, a, b, raw_a, raw_b, aid, message):
        # Do not parse JSON blindly on an empty 304/502/503. Before the
        # unchanged adversarial assertions, diagnose the first HTTP boundary
        # with the already established real browser sessions. Never print
        # URLs, headers, cookie values, raw body, identity or signing data.
        for label,page in (("A",a),("B",b)):
            for conditional in (False,True):
                result=await page.evaluate("""async conditional => {
                    const headers=conditional?{'If-None-Match':'*',
                        'If-Modified-Since':'Tue, 01 Jan 2030 00:00:00 GMT'}:{};
                    const r=await fetch('/api/history/conversations?limit=2',
                        {cache:'no-store',headers});
                    return {status:r.status, json:(r.headers.get('content-type')||'')
                      .toLowerCase().includes('application/json'),
                      noStore:r.headers.get('cache-control')==='no-store'};
                }""",conditional)
                print("F3_COMPOSE_BROWSER_HTTP_BOUNDARY",json.dumps(
                    {"actor":label,"conditional":conditional,**result}),flush=True)
                assert result=={"status":200,"json":True,"noStore":True}, (
                    "COMPOSE_REAL_HISTORY_BOUNDARY",label,conditional,result)
        await super().verify_browser_privacy(browser,a,b,raw_a,raw_b,aid,message)

    def switch_to_restored(self, dsns, network):
        super().switch_to_restored(dsns,network)
        self.start_compose(dsns,network)

    def stop_compose(self):
        project=getattr(self,"compose_project",None)
        try:
            if project and self.compose_file.is_file():
                self.compose("down","--remove-orphans",timeout=90)
        finally:
            self.compose_project=None
            try:
                network=getattr(self,"compose_idp_network",None)
                if network:
                    self.ci_command("docker","network","disconnect",network,self.kc.container)
                    self.compose_idp_network=None
            finally:
                for directory in getattr(self,"compose_chowns",[]):
                    self.ci_command("sudo","chown","-R",f"{os.getuid()}:{os.getgid()}",
                                    str(directory))
                self.compose_chowns=[]



class BothSidesComposeBrowserDemo(ComposeRestoredBrowserDemo):
    """The first real browser request and the repeat run inside Compose.

    The original Actions PG/host processes are used only to seed the lab
    and establish fixture certificates. The first user journey runs on a
    separately owned TLS PG volume; the second is a backup of that exact
    source volume including the real browser sessions created there.
    """

    @contextmanager
    def source_environment(self):
        opts=dict(conninfo_to_dict(os.environ["DB_APP_DSN"]),user="postgres",password=os.environ["PGPASSWORD"])
        with psycopg.connect(**opts,autocommit=True) as admin:
            self.db_install_system_id=str(admin.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0])
        self.start()
        with AppOnlyBrowserDemo.fresh_volume(self) as (dsns,pg,network):
            try:
                self.source_pg_id=pg
                self.source_network=network
                self.source_pg_port=self.restore_pg_port
                info=json.loads(self.ci_command("docker","inspect",pg))[0]
                self.source_pg_label=info["Config"]["Labels"]["rag.finance.ci.restore"]
                self.source_pg_image=info["Image"]
                self.source_volume=next(m["Name"] for m in info["Mounts"]
                    if m["Destination"]=="/var/lib/postgresql/data")
                dsns=self.configure_restore_pg_tls(pg,dsns)
                # Keep the source CA path stable across the second TLS setup.
                stable=self.root/"source-pg-ca.pem"
                shutil.copyfile(self.restore_pg_ca,stable)
                stable.chmod(0o600)
                dsns={k:make_conninfo(v,sslrootcert=str(stable)) for k,v in dsns.items()}
                self.source_dsns=dsns
                self.verify_db_tls(dsns["DB_APP_DSN"],"SOURCE")
                self.switch_to_initial_compose(dsns,network)
                self.source_witness=dict(self.compose_witness)
                self.source_witness["scope"]="SOURCE_COMPOSE_BEFORE_FIRST_BROWSER_LOGIN"
                self.source_witness["source_phase_web_bootstrap_containerized"]=True
                with patch.dict(os.environ,dsns):
                    yield
            finally:
                self.stop_compose()
                self.stop_container_api()

    def switch_to_initial_compose(self,dsns,network):
        super().switch_to_restored(dsns,network)
        print("F3_SOURCE_SHARED_COMPOSE_BEFORE_BROWSER_LOGIN_READY",flush=True)

    @contextmanager
    def fresh_volume(self):
        # Parent journey has already passed source list/detail/refresh/send
        # in the real Web image before requesting the backup.
        assert self.compose_project and self.api_container
        assert self.source_witness["source_phase_web_bootstrap_containerized"]
        self.source_witness["source_browser_sql_http_dom_and_send_passed"]=True
        print("F3_SOURCE_SHARED_COMPOSE_BROWSER_SQL_PASS",flush=True)
        with self.clone_owned_source() as restored:
            try:
                # Shut down only our source Web/API/Bootstrap. Keep the
                # source PG intact and the original browser cookie/alias.
                self.stop_compose()
                self.stop_container_api()
                # Preserve the fixture exchange counter across the switch.
                shutil.copyfile(self.root/"compose-restored/audit/exchange.sqlite",
                                self.root/"exchange-audit.sqlite")
                for name in ("restore-pg-tls","restore-api-container-secrets",
                             "compose-restored"):
                    shutil.move(str(self.root/name),str(self.root/("source-"+name)))
                (self.root/"restore-bootstrap.json").unlink()
                yield restored
            finally:
                self.stop_compose()
                self.stop_container_api()

    def switch_to_restored(self,dsns,network):
        # The source was a real OCI API, not a host process. Keep identical
        # signer, origins, cursor key and encrypted aliases when switching.
        worker=json.loads(Path(self.bootstrap_command[-1]).read_text())
        mapping={"replay":"REPLAY_API_DSN","bootstrap":"LOGIN_BOOTSTRAP_DSN",
                 "claim_reader":"LOGIN_CLAIM_DSN","issuer":"LOGIN_ISSUER_DSN",
                 "mapper":"AUTH_MAP_DSN","binder":"LOGIN_BINDER_DSN",
                 "reader":"LOGIN_READER_DSN"}
        assert set(worker["db_dsn"])==set(mapping)
        worker["db_dsn"]={k:dsns[v] for k,v in mapping.items()}
        path=self.root/"restore-bootstrap.json"
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(worker,f)
        self.start_container_api(dsns,network)
        self.start_compose(dsns,network)
        self.restore_mig_dsn=dsns["DB_MIG_DSN"]
        assert self.compose_witness["api_image_id"]==self.source_witness["api_image_id"]
        assert self.compose_witness["web_image_id"]==self.source_witness["web_image_id"]

    async def prove_post_revoke_compose_restore(self,a,b,raw_a,raw_b,aid,bid,bmid,bmessage,expected,sql_before,before,restored,restored_id):
        """Restore only the committed-revocation snapshot, not a stale backup."""
        assert restored_id==self.restored_pg_id
        assert self.signed_private(raw_a).status_code==401
        assert self.signed_private(raw_b).status_code==200
        second_witness=dict(self.compose_witness)
        with psycopg.connect(restored["AUTH_SESSION_DSN"],autocommit=True,row_factory=dict_row) as auth:
            assert auth_session.inspect(auth,raw_a["session_ref"]) is None
            assert auth_session.inspect(auth,raw_b["session_ref"]) is not None
        began=time.monotonic()
        with self.clone_owned_source(post_revoke_dsns=restored) as (third,pg,network):
            backup_restore_ms=round((time.monotonic()-began)*1000)
            outage_start=time.monotonic()
            self.stop_compose()
            self.stop_container_api()
            shutil.copyfile(self.root/"compose-restored/audit/exchange.sqlite",self.root/"exchange-audit.sqlite")
            for name in ("restore-pg-tls","restore-api-container-secrets","compose-restored"):
                shutil.move(str(self.root/name),str(self.root/("pre-post-revoke-"+name)))
            (self.root/"restore-bootstrap.json").unlink()
            try:
                third=self.configure_restore_pg_tls(pg,third)
                self.switch_to_restored(third,network)
                assert self.compose_witness["api_image_id"]==second_witness["api_image_id"]
                assert self.compose_witness["web_image_id"]==second_witness["web_image_id"]
                with psycopg.connect(third["AUTH_SESSION_DSN"],autocommit=True,row_factory=dict_row) as auth:
                    assert auth_session.inspect(auth,raw_a["session_ref"]) is None
                    assert auth_session.inspect(auth,raw_b["session_ref"]) is not None
                assert self.signed_private(raw_a).status_code==401
                assert self.signed_private(raw_b).status_code==200
                assert self.counts()==before
                self.restricted_db_snapshot("POST_REVOKE_RESTORE",third,sql_before,revoked=True)
                # A is already logged out: the disabled refresh control is
                # correct. Re-test the real ordinary BFF HTTP boundary without
                # re-injecting the removed cookie or forcing a disabled click.
                await expect(a.get_by_test_id("refresh-history")).to_be_disabled()
                denied=await a.evaluate("""async () => {
                    const r=await fetch('/api/history/conversations?limit=2',{cache:'no-store'});
                    return {status:r.status,noStore:r.headers.get('cache-control')==='no-store'};
                }""")
                assert denied=={"status":401,"noStore":True}
                await expect(a.get_by_test_id("history-login-required")).to_be_visible()
                print("DB_COMMON_POST_REVOKE_BROWSER_DISABLED_REFRESH_AND_REAL_BFF_401=PASS",flush=True)
                assert await a.locator('[data-testid^="conversation-"]').count()==0
                async with b.expect_response(lambda r:"/api/history/conversations?limit=2" in r.url and "cursor=" not in r.url and r.request.method=="GET") as wait:
                    await b.get_by_test_id("refresh-history").click()
                response=await wait.value
                assert response.status==200
                doc=await response.json()
                assert doc["scope_user_id"]==self.owners["B"]
                assert [x["conversation_id"] for x in doc["items"]]==[x["id"] for x in expected["B"][:2]]
                async with b.expect_response(lambda r:"/api/history/conversations?" in r.url and "cursor=" in r.url and r.request.method=="GET") as wait:
                    await b.get_by_role("button",name="نمایش گفت‌وگوهای بیشتر").click()
                page2=await wait.value
                assert page2.status==200
                assert [x["conversation_id"] for x in (await page2.json())["items"]]==[x["id"] for x in expected["B"][2:]]
                for row in expected["B"]:
                    await expect(b.get_by_test_id("conversation-"+row["id"])).to_be_visible()
                other=next(row["id"] for row in expected["B"] if row["id"]!=bid)
                await b.get_by_test_id("conversation-"+other).click()
                async with b.expect_response(lambda r:"/api/history/conversations/"+bid+"/messages?" in r.url and r.request.method=="GET") as wait:
                    await b.get_by_test_id("conversation-"+bid).click()
                detail=await wait.value
                assert detail.status==200
                payload=await detail.json()
                assert payload["owner_user_id"]==self.owners["B"]
                assert [(x["message_id"],x["text"]) for x in payload["items"]]==[(bmid,bmessage)]
                await expect(b.get_by_test_id("history-message-"+bmid)).to_contain_text(bmessage)
                status=await b.evaluate("""async id => (await fetch('/api/history/conversations/'+id+'/messages?limit=2',{cache:'no-store'})).status""",aid)
                assert status==404
                assert (await b.evaluate("""async () => (await fetch('/api/history/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status"""))==503
                assert self.counts()==before
                self.restricted_db_snapshot("POST_REVOKE_BROWSER",third,sql_before,revoked=True)
                measured=round((time.monotonic()-outage_start)*1000)
                self.post_revoke_witness={"three_distinct_volumes":len({self.source_volume,self.restored_pg_volume,self.post_revoke_pg_volume})==3,
                    "three_distinct_pg_containers":len({self.source_pg_id,self.restored_pg_id,self.post_revoke_pg_id})==3,
                    "source_sha":os.environ["F3_EXACT_SHA"],"api_image_id":self.compose_witness["api_image_id"],
                    "web_image_id":self.compose_witness["web_image_id"],"committed_revoke_a_denied_b_replayed":True,
                    "measured_backup_restore_ms":backup_restore_ms,"measured_cutover_to_browser_replay_ms":measured,
                    "approved_operational_rpo_rto":False,"accepted":False}
                assert self.post_revoke_witness["three_distinct_volumes"] and self.post_revoke_witness["three_distinct_pg_containers"]
                print("DB_COMMON_POST_REVOKE_THIRD_VOLUME_ORDINARY_BROWSER_A401_B200_EXACT_PARITY=PASS",flush=True)
            finally:
                self.stop_compose()
                self.stop_container_api()
                self.compose_witness=second_witness

    @contextmanager
    def clone_owned_source(self, post_revoke_dsns=None):
        """Use only the exact CI source service and newly created resources.

        A fresh Postgres data directory, not another database in the old
        container. Keep dump/role metadata only in process memory; do not
        export credentials, screenshots, or backups from the disposable lab.
        """
        if post_revoke_dsns is None:
            cid=self.source_pg_id
            source_dsn_map=self.source_dsns
            source_port=self.source_pg_port
            source_label=self.source_pg_label
            source_network=self.source_network
            source_volume=self.source_volume
            source_image=self.source_pg_image
        else:
            cid=self.restored_pg_id
            source_dsn_map=post_revoke_dsns
            source_port=self.restore_pg_port
            source_label=self.restored_pg_label
            source_network=self.restored_pg_network
            source_volume=self.restored_pg_volume
            source_image=self.restored_pg_image
            assert cid!=self.source_pg_id and source_volume!=self.source_volume
            assert self.compose_idp_network==source_network
        if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
                or not re.fullmatch(r"[a-f0-9]{64}", cid)
                or cid.startswith(os.environ["API_F3_ISOLATED_PG_CID"])):
            raise RuntimeError("OWNED_SOURCE_CLONE_DENIED")
        source_dsns = {}
        dbname = conninfo_to_dict(source_dsn_map["DB_APP_DSN"])["dbname"]
        assert re.fullmatch(r"history_browser_restore_ci_[a-f0-9]{16}",dbname)
        for key,value in source_dsn_map.items():
            options = conninfo_to_dict(value)
            assert options["dbname"] == dbname
            assert options["host"] == "127.0.0.1"
            assert int(options["port"]) == source_port
            assert options.get("sslmode") == "verify-full"
            assert options.get("user") and options.get("password")
            # The new CA is configured on the new independent volume.
            for field in ("sslmode","sslrootcert","gssencmode"):
                options.pop(field,None)
            source_dsns[key]=options
        required = {"DB_APP_DSN", "DB_MIG_DSN", "AUTH_MIG_DSN", "AUTH_REVOKER_DSN",
                    "AUTH_MAP_DSN", "AUTH_SESSION_DSN", "REPLAY_API_DSN",
                    "LOGIN_BOOTSTRAP_DSN", "LOGIN_CLAIM_DSN", "LOGIN_ISSUER_DSN",
                    "LOGIN_BINDER_DSN", "LOGIN_READER_DSN"}
        assert required.issubset(source_dsns)
        def docker(*args, data=None, timeout=60):
            result = subprocess.run(["docker", *args], input=data,
                                    capture_output=True, timeout=timeout)
            if result.returncode:
                raise RuntimeError("FRESH_VOLUME_DOCKER_COMMAND_FAILED")
            return result.stdout
        source = json.loads(docker("inspect", cid))[0]
        assert source["Id"] == cid and source["State"]["Running"]
        assert source["Config"]["Labels"]["rag.finance.ci.restore"] == source_label
        assert set(source["NetworkSettings"]["Networks"]) == {source_network}
        assert source["NetworkSettings"]["Ports"]["5432/tcp"] == [
            {"HostIp":"127.0.0.1","HostPort":str(source_port)}]
        assert any(m.get("Name")==source_volume for m in source["Mounts"])
        image = source["Image"]
        assert image == source_image
        assert re.fullmatch(r"sha256:[a-f0-9]{64}", image)
        # No password hashes in the global backup. Restore the exact CI
        # role names and attributes; provision synthetic passwords only
        # from the explicit current-job DSNs in the new server.
        roles = docker("exec", cid, "pg_dumpall", "-U", "postgres", "--roles-only",
                       "--no-role-passwords")
        roles = b"\n".join(line for line in roles.splitlines()
                           if line.strip() != b"CREATE ROLE postgres;") + b"\n"
        dump = docker("exec", cid, "pg_dump", "-U", "postgres", "-Fc", dbname)
        assert dump.startswith(b"PGDMP")
        suffix = uuid.uuid4().hex
        name = "api-browser-pg-" + suffix
        volume = name + "-data"
        network = name + "-net"
        dbname = "history_browser_restore_ci_" + suffix[:16]
        label = "rag.finance.ci.restore=" + suffix
        made_volume = made_network = False
        new_id = None
        try:
            assert docker("volume", "create", "--label", label, volume).decode().strip() == volume
            made_volume = True
            docker("network", "create", "--label", label, network)
            made_network = True
            # Docker may allocate a different ephemeral published port on
            # stop/start. Pin the loopback port for both restart exercises.
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                expected_port = reservation.getsockname()[1]
            assert expected_port != 5432
            result = docker("run", "-d", "--pull", "never", "--name", name,
                            "--label", label, "--network", network,
                            "--network-alias", "pg-restore",
                            "--network-alias", "wrong-pg-name",
                            "-p", f"127.0.0.1:{expected_port}:5432",
                            "--mount", "type=volume,source=" + volume +
                            ",target=/var/lib/postgresql/data",
                            "-e", "POSTGRES_PASSWORD=" + os.environ["PGPASSWORD"], image)
            new_id = result.decode().strip()
            assert re.fullmatch(r"[a-f0-9]{64}", new_id) and new_id != source["Id"]
            info = json.loads(docker("inspect", new_id))[0]
            assert info["Config"]["Labels"]["rag.finance.ci.restore"] == suffix
            assert info["Image"] == image
            mounts = [m for m in info["Mounts"] if m["Destination"] == "/var/lib/postgresql/data"]
            assert len(mounts) == 1 and mounts[0]["Name"] == volume
            assert not any(m.get("Name") == volume for m in source["Mounts"])
            assert set(info["NetworkSettings"]["Networks"]) == {network}
            port_map = info["NetworkSettings"]["Ports"]["5432/tcp"]
            assert len(port_map) == 1 and port_map[0]["HostIp"] == "127.0.0.1"
            port = int(port_map[0]["HostPort"])
            assert port == expected_port
            self.restore_pg_port = port
            admin_opts = dict(host="127.0.0.1", port=port, dbname="postgres",
                              user="postgres", password=os.environ["PGPASSWORD"],
                              connect_timeout=2)
            for _ in range(60):
                try:
                    with psycopg.connect(**admin_opts, autocommit=True):
                        break
                except psycopg.OperationalError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("FRESH_VOLUME_PG_NOT_READY")
            docker("exec", "-i", new_id, "psql", "-X", "-v", "ON_ERROR_STOP=1",
                   "-U", "postgres", "-d", "postgres", data=roles)
            with psycopg.connect(**admin_opts, autocommit=True) as admin:
                for options in source_dsns.values():
                    admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(options["user"]), sql.Literal(options["password"])))
                admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                    sql.Identifier(dbname)))
            docker("exec", "-i", new_id, "pg_restore", "-U", "postgres", "--single-transaction", "--exit-on-error",
                   "-d", dbname, data=dump)
            del roles, dump
            clone_dsns = {key: make_conninfo(**{**value, "port": port, "dbname": dbname})
                          for key, value in source_dsns.items()}
            assert new_id != self.source_pg_id and volume != self.source_volume
            if post_revoke_dsns is None:
                self.restored_pg_id=new_id
                self.restored_pg_volume=volume
                self.restored_pg_label=suffix
                self.restored_pg_network=network
                self.restored_pg_image=image
                print("F3_FULL_COMPOSE_SECOND_INDEPENDENT_VOLUME_RESTORE_PASS",flush=True)
            else:
                assert new_id!=self.restored_pg_id and volume!=self.restored_pg_volume
                self.post_revoke_pg_id=new_id
                self.post_revoke_pg_volume=volume
                print("DB_COMMON_THIRD_INDEPENDENT_POST_REVOKE_VOLUME_RESTORE_PASS",flush=True)
            yield clone_dsns, new_id, network
        finally:
            # Exact resources generated in this invocation; no prune or
            # deletion of an existing CI/service or legacy volume.
            if new_id is not None:
                docker("rm", "-f", new_id)
            if made_volume:
                docker("volume", "rm", volume)
            if made_network:
                docker("network", "rm", network)


async def main():
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
        raise RuntimeError("FOUNDATION_COMPOSE_RESTORE_CI_ONLY")
    demo=BothSidesComposeBrowserDemo()
    try:
        with demo.source_environment():
            trust_ephemeral_browser_ca(demo)
            async with async_playwright() as p:
                browser=await p.chromium.launch()
                try:
                    await demo.journey(browser,demo.root/"browser-output")
                finally:
                    await browser.close()
        receipt=demo.compose_witness
        receipt["scope"]="SOURCE_AND_RESTORED_SHARED_COMPOSE_CI_FIXTURE_BOOTSTRAP"
        receipt["post_revoke_third_volume"]=demo.post_revoke_witness
        receipt["strict_browser_tls"]=True
        receipt["source_phase_web_bootstrap_containerized"]=True
        receipt["source_witness"]=demo.source_witness
        receipt["two_independent_pg_volumes"]=demo.source_volume!=demo.restored_pg_volume
        receipt["source_pg_id_distinct_from_restore"]=demo.source_pg_id!=demo.restored_pg_id
        # This is the shared CI lab topology, not a fully deployable staging
        # stack: Bootstrap is still the pinned CI-only worker.
        receipt["shared_compose_before_after_lab_verified"]=True
        receipt["full_compose_verified"]=False
        receipt["post_restore_ordinary_browser_replay_passed"]=True
        receipt["post_restore_new_oidc_login_passed"]=True
        receipt["post_restore_signed_readiness_and_revoke_passed"]=True
        receipt["post_restore_sql_http_dom_parity_and_zero_send_passed"]=True
        output=ROOT/"ci_receipts/f3_post_restore_shared_compose.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
        print("F3_POST_RESTORE_SHARED_COMPOSE_REAL_BROWSER_SQL_REPLAY_PASS",flush=True)
        print("F3_BOTH_SIDES_SHARED_COMPOSE_BROWSER_SQL_FRESH_VOLUME_PASS",flush=True)
    finally:
        demo.stop()


if __name__=="__main__":
    asyncio.run(main())
