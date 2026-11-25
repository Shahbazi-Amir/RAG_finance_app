"""Separate cross-SHA lab: current signed source -> fresh PG -> prior images.
The prior API source differs by the exact API137 listener/contract transfer.
Web, schema, locks, migrations and other runtime trees are unchanged.
This proves bounded cross-version image/session/SQL continuity, not a schema downgrade. No target, engine or 011.
"""
from __future__ import annotations
import asyncio
import hashlib
import subprocess
import uuid
from browser_history_restore import protected_backup_roundtrip
import json
import os
import re
import time
from pathlib import Path
import ssl
from playwright.async_api import async_playwright
from compose_restored_browser import BothSidesComposeBrowserDemo, ROOT, ORIGIN

PRIOR = "f2b743a1588cac76fddafc36e3b489deb59d42ac"
BRANCH = "refs/heads/integration/f3-foundation-send-fence-restore-20261124"

def verify_pre_switch_dump_in_third_volume(demo,dump,dbname):
    """Restore this specific pre-switch archive, not merely its catalog.

    Third empty volume, same exact local PG17 image, network none, no host
    port, no product service, no role passwords exported. All SQL data
    stays inside the runner; only counts/hashes are reported.
    """
    run=demo.ci_command
    source=demo.restored_pg_id
    inspected=json.loads(run("docker","inspect",source))[0]
    assert source==inspected["Id"] and source!=demo.source_pg_id
    assert any(m.get("Name")==demo.restored_pg_volume for m in inspected["Mounts"])
    assert inspected["State"]["Running"]
    image=inspected["Image"]
    assert re.fullmatch(r"sha256:[a-f0-9]{64}",image)
    roles=run("docker","exec",source,"pg_dumpall","-U","postgres","--roles-only","--no-role-passwords")
    roles=b"\n".join(x for x in roles.splitlines() if x.strip()!=b"CREATE ROLE postgres;")+b"\n"
    def snapshot(cid,db):
        result={}
        for table in ("conversations","messages","send_receipts","execution_attempts","answers"):
            # No arbitrary identifiers or external data; fixed original
            # table names and disposable synthetic DB names only.
            sql="SELECT row_to_json(t)::text FROM history_l1."+table+" AS t ORDER BY owner_id,id"
            raw=run("docker","exec",cid,"psql","-X","-U","postgres","-d",db,"-Atc",sql)
            result[table]={"rows":len(raw.splitlines()),"sha256":hashlib.sha256(raw).hexdigest()}
        return result
    expected=snapshot(source,dbname)
    suffix=uuid.uuid4().hex
    name="f3-pre-switch-verify-"+suffix
    volume=name+"-data"
    label="rag.finance.ci.preswitch="+suffix
    target=None;created=False
    started=time.monotonic_ns()
    try:
        assert run("docker","volume","create","--label",label,volume).decode().strip()==volume
        created=True
        target=run("docker","run","-d","--pull","never","--name",name,"--label",label,
                   "--network","none","--mount","type=volume,source="+volume+",target=/var/lib/postgresql/data",
                   "-e","POSTGRES_PASSWORD="+os.environ["PGPASSWORD"],image).decode().strip()
        assert re.fullmatch(r"[a-f0-9]{64}",target) and target not in (source,demo.source_pg_id)
        info=json.loads(run("docker","inspect",target))[0]
        assert info["Image"]==image and info["HostConfig"]["NetworkMode"]=="none"
        assert not info["HostConfig"]["PortBindings"] and info["Config"]["Labels"]["rag.finance.ci.preswitch"]==suffix
        assert any(m.get("Name")==volume for m in info["Mounts"])
        assert volume not in (demo.source_volume,demo.restored_pg_volume)
        for _ in range(60):
            try:
                run("docker","exec",target,"pg_isready","-U","postgres",timeout=5)
                time.sleep(1.5)
                run("docker","exec",target,"psql","-X","-U","postgres","-d","postgres","-Atc","SELECT 1",timeout=5)
                break
            except RuntimeError:time.sleep(.5)
        else:raise RuntimeError("THIRD_VOLUME_POSTGRES_UNAVAILABLE")
        run("docker","exec","-i",target,"psql","-X","-U","postgres","-d","postgres","-v","ON_ERROR_STOP=1",input_data=roles)
        target_db="history_browser_restore_ci_"+suffix[:16]
        run("docker","exec",target,"createdb","-U","postgres","-T","template0",target_db)
        run("docker","exec","-i",target,"pg_restore","-U","postgres","--exit-on-error","-d",target_db,
            input_data=dump.read_bytes(),timeout=90)
        actual=snapshot(target,target_db)
        assert actual==expected
        def sysid(cid,db):
            return run("docker","exec",cid,"psql","-X","-U","postgres","-d",db,"-Atc","SELECT system_identifier FROM pg_control_system()").strip()
        assert sysid(target,target_db)!=sysid(source,dbname)
        # 14 FORCE RLS tables in original 001-010, exact count not guessed
        # from the dump: compare source and new catalog independently.
        rls="SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('auth_l1','history_l1') AND c.relforcerowsecurity"
        def force_count(cid,db):
            return int(run("docker","exec",cid,"psql","-X","-U","postgres","-d",db,"-Atc",rls).strip())
        source_rls=force_count(source,dbname)
        assert source_rls>0 and force_count(target,target_db)==source_rls
        return {"restored_exact_pre_switch_archive":True,"third_independent_pg_volume":True,
                "network_none":True,"local_pg_image_id":image,
                "history_rows_and_byte_fingerprints_equal":actual,
                "force_rls_catalog_equal":True,"force_rls_table_count":source_rls,
                "duration_ms":(time.monotonic_ns()-started)//1_000_000,
                "raw_backup_or_rows_uploaded":False,"target_verified":False}
    finally:
        if target:run("docker","rm","-f",target)
        if created:run("docker","volume","rm",volume)

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
        # Exact pre-switch backup of the same restored disposable PG.
        dbs=run("docker","exec",self.restored_pg_id,"psql","-U","postgres","-d","postgres","-Atc","SELECT datname FROM pg_database WHERE datname LIKE 'history_browser_restore_ci_%'").decode().splitlines()
        assert len(dbs)==1 and re.fullmatch(r"history_browser_restore_ci_[a-f0-9]{16}",dbs[0])
        backup_dir=self.root/("pre-image-switch-"+uuid.uuid4().hex)
        backup_dir.mkdir(mode=0o700)
        dump=backup_dir/"before-image-switch.dump"
        dump.write_bytes(run("docker","exec",self.restored_pg_id,"pg_dump","-U","postgres","-Fc",dbs[0]))
        dump.chmod(0o600)
        assert dump.read_bytes().startswith(b"PGDMP")
        backup=protected_backup_roundtrip((dump,),backup_dir)[0]
        proc=subprocess.run(["docker","exec","-i",self.restored_pg_id,"pg_restore","--list"],input=dump.read_bytes(),capture_output=True,timeout=30)
        assert proc.returncode==0 and b"history_l1" in proc.stdout and b"auth_l1" in proc.stdout
        assert hashlib.sha256(dump.read_bytes()).hexdigest()==backup["plaintext_sha256"]
        backup["independent_restore"]=verify_pre_switch_dump_in_third_volume(self,dump,dbs[0])
        dump.unlink();backup_dir.rmdir()
        backup["catalog_verified"]=True
        backup["created_before_version_switch"]=True
        backup["restore_of_this_new_dump_tested"]=True
        assert self.counts()==before
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
            "runtime_source_trees_identical":False,"exact_api137_runtime_delta_only":True,"pre_switch_backup":backup,"target_verified":False,
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
