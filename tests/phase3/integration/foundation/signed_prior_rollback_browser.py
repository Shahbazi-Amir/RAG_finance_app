"""Separate cross-SHA lab: current signed source -> fresh PG -> prior images.
The prior and current runtime trees are identical; only CI/test/provenance
changed. This proves image/session/SQL continuity, not a schema downgrade or
a rollback of a different product implementation. No target, engine or 011.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import time
from pathlib import Path
import ssl
from playwright.async_api import async_playwright
from compose_restored_browser import BothSidesComposeBrowserDemo, ROOT, ORIGIN

PRIOR = "c9f52669a5b86d89bd08b6992f1a150fba9b2a9f"
BRANCH = "refs/heads/integration/f3-foundation-send-fence-restore-20261124"

class SignedPriorRollback(BothSidesComposeBrowserDemo):
    async def verify_browser_privacy(self, browser, a, b, raw_a, raw_b, aid, message):
        # The unchanged same-SHA restored environment has already passed
        # readiness/outage checks. Observe it before switching the binaries.
        await super().verify_browser_privacy(browser,a,b,raw_a,raw_b,aid,message)
        before=self.counts()
        run=self.ci_command
        sha=os.environ["GITHUB_SHA"]
        assert os.environ["GITHUB_REF"]==BRANCH and sha!=PRIOR
        assert run("git","rev-parse","HEAD").decode().strip()==sha
        network=json.loads(run("docker","inspect",self.restored_pg_id))[0]["NetworkSettings"]["Networks"]
        assert len(network)==1
        network=next(iter(network))
        old_api=json.loads(run("docker","inspect",self.api_container))[0]
        assert old_api["Id"]==self.api_container and old_api["Image"]==self.source_witness["api_image_id"]
        assert set(old_api["NetworkSettings"]["Networks"])=={network}
        assert old_api["HostConfig"]["ReadonlyRootfs"] is True
        name=old_api["Name"].lstrip("/")
        assert re.fullmatch(r"api-restored-[a-f0-9]{32}",name)
        assert old_api["Config"]["User"]=="11001:11001"
        current_api=os.environ["API_F3_BROWSER_IMAGE"]
        current_web=os.environ["F3_COMPOSE_BROWSER_WEB_IMAGE"]
        assert current_api=="api-f3-browser:"+sha and current_web=="f3-compose-browser-web:"+sha
        prior_api="f3-rollback-signed-api:"+PRIOR
        prior_web="f3-rollback-signed-web:"+PRIOR
        prior_ids={}
        for tag,uid in ((prior_api,"11001:11001"),(prior_web,"11003:11003")):
            d=json.loads(run("docker","image","inspect",tag))[0]
            assert d["Config"]["Labels"]["org.opencontainers.image.revision"]==PRIOR
            assert d["Config"]["User"]==uid and d["Architecture"]=="amd64" and d["Os"]=="linux"
            assert re.fullmatch(r"sha256:[0-9a-f]{64}",d["Id"])
            prior_ids[tag]=d["Id"]
        assert prior_ids[prior_api]!=self.source_witness["api_image_id"]
        assert prior_ids[prior_web]!=self.source_witness["web_image_id"]
        doc=json.loads(self.compose_file.read_text())
        assert set(doc["services"])=={"web","bootstrap","ingress","relay"}
        assert doc["networks"]=={"restored":{"external":True,"name":network}}
        old_services={}
        for kind in doc["services"]:
            cid=self.compose("ps","-q",kind).decode().strip()
            d=json.loads(run("docker","inspect",cid))[0]
            assert d["Config"]["Labels"]["com.docker.compose.project"]==self.compose_project
            assert d["HostConfig"]["ReadonlyRootfs"] is True
            old_services[kind]=d["Id"]
            expected=current_api if kind=="bootstrap" else current_web
            assert doc["services"][kind]["image"]==expected
            doc["services"][kind]["image"]=prior_api if kind=="bootstrap" else prior_web
        pg_before=json.loads(run("docker","inspect",self.restored_pg_id))[0]
        assert pg_before["State"]["Running"] and any(m.get("Name")==self.restored_pg_volume for m in pg_before["Mounts"])
        mount=self.container_secret_dir
        envfile=self.root/"restore-api-cursor.env"
        assert mount==self.root/"restore-api-container-secrets" and envfile.is_file()
        port=self.api_env["APP_ONLY_CI_API_PORT"]
        assert old_api["HostConfig"]["PortBindings"]=={"8443/tcp":[{"HostIp":"127.0.0.1","HostPort":port}]}
        # Stop only the exact owned restored API; leave PostgreSQL, IdP,
        # bootstrap audit store and BFF aliases intact. Do not delete volumes.
        run("docker","stop","--time","2",self.api_container)
        assert not json.loads(run("docker","inspect",self.api_container))[0]["State"]["Running"]
        start=time.monotonic_ns()
        self.compose("down","--remove-orphans",timeout=90)
        run("docker","rm",self.api_container)
        self.api_container=None
        self.compose_file.write_text(json.dumps(doc))
        self.compose("config","--quiet")
        self.api_container=run("docker","run","-d","--pull","never","--name",name,
            "--network",network,"--read-only","--cap-drop","ALL",
            "--security-opt","no-new-privileges",
            "--mount","type=bind,source="+str(mount)+",target=/run/secrets,readonly",
            "--env-file",str(envfile),"-p","127.0.0.1:"+port+":8443",prior_api).decode().strip()
        api=json.loads(run("docker","inspect",self.api_container))[0]
        assert api["Image"]==prior_ids[prior_api] and api["Id"]!=old_api["Id"]
        assert api["HostConfig"]["ReadonlyRootfs"] and api["Config"]["User"]=="11001:11001"
        assert set(api["NetworkSettings"]["Networks"])=={network}
        assert api["HostConfig"]["PortBindings"]==old_api["HostConfig"]["PortBindings"]
        tls=ssl.create_default_context(cafile=self.ca)
        tls.load_cert_chain(self.client[0],self.client[1])
        self.await_url(self.product_origin+"/internal/ready",tls)
        self.compose("up","-d","--no-build","--pull","never")
        services={}
        for kind in doc["services"]:
            cid=self.compose("ps","-q",kind).decode().strip()
            d=json.loads(run("docker","inspect",cid))[0]
            expected=prior_api if kind=="bootstrap" else prior_web
            assert d["Id"]!=old_services[kind] and d["State"]["Running"]
            assert d["Image"]==prior_ids[expected] and d["HostConfig"]["ReadonlyRootfs"]
            assert d["Config"]["Labels"]["com.docker.compose.project"]==self.compose_project
            assert d["Config"]["User"]==("11001:11001" if kind=="bootstrap" else "11003:11003")
            assert "ALL" in d["HostConfig"]["CapDrop"]
            services[kind]=d
        webid=services["web"]["Id"]
        assert set(services["web"]["NetworkSettings"]["Networks"])=={network}
        assert services["web"]["HostConfig"]["PortBindings"]=={"3444/tcp":[{"HostIp":"127.0.0.1","HostPort":"3443"}]}
        for kind in ("bootstrap","ingress","relay"):
            assert services[kind]["HostConfig"]["NetworkMode"]=="container:"+webid
            assert not services[kind]["HostConfig"]["PortBindings"]
            sources={m["Source"] for m in services[kind]["Mounts"]}
            assert str(self.shared) not in sources and str(self.root/"compose-restored/web") not in sources
        members=json.loads(run("docker","network","inspect",network))[0]["Containers"]
        assert set(members)=={webid,api["Id"],self.restored_pg_id,
            json.loads(run("docker","inspect",self.kc.container))[0]["Id"]}
        pg_after=json.loads(run("docker","inspect",self.restored_pg_id))[0]
        assert pg_after["Id"]==pg_before["Id"] and pg_after["Mounts"]==pg_before["Mounts"]
        assert pg_after["State"]["StartedAt"]==pg_before["State"]["StartedAt"]
        self.await_url(ORIGIN+"/login",ssl.create_default_context(cafile=self.ca))
        assert self.signed_private(raw_a).status_code==200
        assert self.signed_private(raw_b).status_code==200
        await super().verify_browser_privacy(browser,a,b,raw_a,raw_b,aid,message)
        assert self.counts()==before
        self.rollback_receipt={
            "schema":"foundation.f3.signed_prior_rollback_browser_ci.v1",
            "source_sha":sha,"prior_sha":PRIOR,"run_id":os.environ["GITHUB_RUN_ID"],
            "current_images":{"api":old_api["Image"],"web":self.source_witness["web_image_id"]},
            "prior_images":{"api":prior_ids[prior_api],"web":prior_ids[prior_web]},
            "fault_current_api_stop_observed":True,"restored_pg_not_restarted":True,
            "same_restored_pg_volume":True,"both_existing_signed_sessions_survived":True,
            "durable_history_counts_equal":True,
            "switch_and_existing_session_checks_ms":(time.monotonic_ns()-start)//1_000_000,
            "runtime_source_trees_identical":True,"target_verified":False,
            "prior_approved_release":False,"accepted":False,"release":"HOLD",
        }
        print("F3_SIGNED_PRIOR_IMAGE_SWITCH_EXISTING_AB_SQL_PASS",flush=True)
        # Parent now performs ordinary new OIDC login, SQL/HTTP/DOM pagination
        # and detail, Send denial, refresh, committed revoke and source checks
        # against the prior binaries. Receipt emitted only after all pass.

async def main():
    assert os.getenv("CI")=="true" and os.getenv("GITHUB_ACTIONS")=="true"
    assert os.getenv("RUNNER_ENVIRONMENT")=="github-hosted" and os.getenv("GITHUB_REF")==BRANCH
    assert not any(os.getenv(k) for k in ("DOCKER_HOST","DOCKER_CONTEXT","COMPOSE_FILE","COMPOSE_PROFILES"))
    demo=SignedPriorRollback()
    try:
        with demo.source_environment():
            async with async_playwright() as p:
                browser=await p.chromium.launch()
                try:
                    await demo.journey(browser,demo.root/"browser-output")
                finally:
                    await browser.close()
        receipt=demo.rollback_receipt
        receipt["prior_image_new_login_dom_pagination_detail_send_revoke_and_source_parity_passed"]=True
        receipt["fresh_pg_volume_distinct_from_source"]=demo.restored_pg_volume!=demo.source_volume
        assert receipt["fresh_pg_volume_distinct_from_source"]
        output=ROOT/"ci_receipts/f3_signed_prior_rollback_browser.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(receipt,indent=2)+"\n")
        print("F3_SIGNED_PRIOR_IMAGE_ROLLBACK_REAL_BROWSER_PG_PASS_RELEASE_HOLD",flush=True)
    finally:
        demo.stop()

if __name__=="__main__":
    asyncio.run(main())
