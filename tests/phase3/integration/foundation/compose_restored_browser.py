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
import sys
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from psycopg.conninfo import make_conninfo
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests/phase3/integration/api"))
from test_app_only_browser_journey import AppOnlyBrowserDemo, ORIGIN


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
        self.stop_child(self.host_ingress)
        self.stop_child(self.host_web)
        self.stop_child(self.bootstrap_process)
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


async def main():
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
        raise RuntimeError("FOUNDATION_COMPOSE_RESTORE_CI_ONLY")
    demo=ComposeRestoredBrowserDemo()
    try:
        demo.configure_source_pg_tls()
        demo.start()
        async with async_playwright() as p:
            browser=await p.chromium.launch()
            try:
                await demo.journey(browser,demo.root/"browser-output")
            finally:
                await browser.close()
        receipt=demo.compose_witness
        receipt["post_restore_ordinary_browser_replay_passed"]=True
        receipt["post_restore_new_oidc_login_passed"]=True
        receipt["post_restore_signed_readiness_and_revoke_passed"]=True
        receipt["post_restore_sql_http_dom_parity_and_zero_send_passed"]=True
        output=ROOT/"ci_receipts/f3_post_restore_shared_compose.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
        print("F3_POST_RESTORE_SHARED_COMPOSE_REAL_BROWSER_SQL_REPLAY_PASS",flush=True)
    finally:
        demo.stop()


if __name__=="__main__":
    asyncio.run(main())
