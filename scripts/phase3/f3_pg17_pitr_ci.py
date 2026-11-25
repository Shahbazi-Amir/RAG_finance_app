"""Physical PG17 PITR on exclusively owned network-none disposable CI volumes.
Exact History/Auth 001–010; never an approved restore target or RPO/RTO.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
BRANCH="refs/heads/integration/f3-foundation-send-fence-restore-20261124"
IMAGE="postgres:17.11"
DB="f3_pitr_ci"

def require(condition, code):
    if not condition: raise RuntimeError(code)

def run(*args, data=None, check=True, timeout=120):
    p=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if check: require(p.returncode==0,"COMMAND_FAILED_"+args[0]+"_"+args[1])
    return p

def out(*args,**kw): return run(*args,**kw).stdout.decode().strip()

def context():
    require(os.getenv("CI")==os.getenv("GITHUB_ACTIONS")=="true","CI_ONLY")
    require(os.getenv("RUNNER_ENVIRONMENT")=="github-hosted" and os.getenv("RUNNER_OS")=="Linux","HOSTED_LINUX_ONLY")
    require(os.getenv("GITHUB_REPOSITORY")=="Shahbazi-Amir/RAG_finance_app" and os.getenv("GITHUB_REF")==BRANCH,"BRANCH_DENIED")
    require(os.getenv("GITHUB_WORKSPACE")==str(ROOT) and str(ROOT).startswith("/home/runner/work/"),"WORKSPACE_DENIED")
    require(not any(os.getenv(k) for k in ("DOCKER_HOST","DOCKER_CONTEXT","DOCKER_TLS_VERIFY","DOCKER_CERT_PATH")),"REMOTE_DOCKER_DENIED")
    require(out("docker","context","show")=="default","DOCKER_CONTEXT_DENIED")
    sha=os.environ["GITHUB_SHA"]
    require(re.fullmatch("[0-9a-f]{40}",sha) and out("git","rev-parse","HEAD")==sha,"SHA_DENIED")
    require(not (ROOT/"infra/postgres/migrations/011_product_answer_claims.up.sql").exists(),"SQL011_DENIED")
    return sha

class Lab:
    def __init__(self):
        self.prefix="f3-pitr-"+uuid.uuid4().hex
        self.volumes=[]
        self.containers=[]
    def volume(self,suffix):
        name=self.prefix+"-"+suffix
        require(run("docker","volume","inspect",name,check=False).returncode!=0,"VOLUME_COLLISION")
        out("docker","volume","create","--label","foundation.f3.pitr="+self.prefix,name)
        self.volumes.append(name);return name
    def create(self,suffix,args,*,entry=None,temporary=False):
        name=self.prefix+"-"+suffix
        require(run("docker","container","inspect",name,check=False).returncode!=0,"CONTAINER_COLLISION")
        cmd=["docker","run","--network","none","--label","foundation.f3.pitr="+self.prefix,"--name",name]
        cmd+=["--rm"] if temporary else ["-d"]
        if entry:cmd+=["--entrypoint",entry]
        cmd+=args
        if not temporary:self.containers.append(name)
        result=out(*cmd,timeout=180)
        if not temporary:
            d=json.loads(out("docker","container","inspect",name))[0]
            require(d["Config"]["Labels"]["foundation.f3.pitr"]==self.prefix and d["HostConfig"]["NetworkMode"]=="none" and not d["HostConfig"]["PortBindings"],"ISOLATION_DENIED")
        return result if temporary else name
    def exec(self,name,*args,root=False,check=True,data=None,timeout=120):
        require(name in self.containers,"UNKNOWN_CONTAINER")
        return run("docker","exec","-i","-u","0" if root else "postgres",name,*args,check=check,data=data,timeout=timeout)
    def sql(self,name,sql,db=DB):
        return self.exec(name,"psql","-X","-qAt","-v","ON_ERROR_STOP=1","-U","postgres","-d",db,data=sql.encode()).stdout.decode().strip()
    def wait(self,name,db="postgres",seconds=80):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if (self.exec(name,"cat","/proc/1/comm",check=False).stdout.strip()==b"postgres"
                and self.exec(name,"psql","-X","-qAt","-U","postgres","-d",db,"-c","SELECT 1",check=False).returncode==0):return
            time.sleep(.5)
        raise RuntimeError("PG_NOT_READY")
    def cleanup(self):
        for name in reversed(self.containers):
            p=run("docker","container","inspect",name,check=False)
            if p.returncode==0:
                d=json.loads(p.stdout)[0]
                require(d["Config"]["Labels"].get("foundation.f3.pitr")==self.prefix,"CLEANUP_CONTAINER_OWNER_DENIED")
                out("docker","rm","-f",name)
        for name in reversed(self.volumes):
            p=run("docker","volume","inspect",name,check=False)
            if p.returncode==0:
                require(json.loads(p.stdout)[0]["Labels"].get("foundation.f3.pitr")==self.prefix,"CLEANUP_VOLUME_OWNER_DENIED")
                out("docker","volume","rm",name)
        require(all(run("docker","volume","inspect",n,check=False).returncode!=0 for n in self.volumes),"CLEANUP_VOLUME_REMAINS")

def scoped(owner,body):
    return "BEGIN; SET LOCAL ROLE history_app; SELECT set_config('app.owner_id','"+owner+"',true); "+body+"; COMMIT;"

def owner_rows(lab,name,owner):
    rows=lab.sql(name,scoped(owner,"SELECT coalesce(string_agg(id||':'||body,',' ORDER BY id),'') FROM history_l1.messages"))
    return rows.splitlines()[-1] if "\n" in rows else ""

def post_recovery_role_and_expiry(lab, restored):
    # Only the disconnected synthetic restored cluster; no real user policy.
    # Use the real database clock rather than sleeping for 15 minutes.
    h=lambda text:hashlib.sha256((lab.prefix+text).encode()).hexdigest()
    old,new,expired=h("rotate-old"),h("rotate-new"),h("expired")
    for digest in (old,expired):
        require(lab.sql(restored,"SET ROLE auth_sessions; SELECT auth_l1.issue_session('B',0,'"+digest+"',60,120) IS NOT NULL;")=="t","ISSUE_POST_RECOVERY")
    deadline_before=lab.sql(restored,"SELECT absolute_expires_at::text FROM auth_l1.sessions WHERE digest_sha256='"+old+"';")
    require(lab.sql(restored,"SET ROLE auth_sessions; SELECT (auth_l1.rotate_session('"+old+"','"+new+"',0,0)->>'generation')::int;")=="1","ROTATION_GENERATION")
    require(lab.sql(restored,"SET ROLE auth_sessions; SELECT auth_l1.validate_session('"+old+"') IS NULL AND auth_l1.validate_session('"+new+"') IS NOT NULL;")=="t","ROTATION_REUSE")
    require(lab.sql(restored,"SELECT absolute_expires_at::text FROM auth_l1.sessions WHERE digest_sha256='"+new+"';")==deadline_before,"ROTATION_EXTENDED_ABSOLUTE")
    # Fixture-only clock adjustment to an already elapsed valid session window.
    lab.sql(restored,"UPDATE auth_l1.sessions SET created_at=clock_timestamp()-interval '130 seconds',last_activity_at=clock_timestamp()-interval '130 seconds',idle_expires_at=clock_timestamp()-interval '70 seconds',absolute_expires_at=clock_timestamp()-interval '10 seconds' WHERE digest_sha256='"+expired+"';")
    require(lab.sql(restored,"SET ROLE auth_sessions; SELECT auth_l1.validate_session('"+expired+"') IS NULL;")=="t","EXPIRED_SESSION_ACCEPTED")
    def deny(sql, code):
        result=lab.exec(restored,"psql","-X","-qAt","-v","ON_ERROR_STOP=1","-U","postgres","-d",DB,
                    data=sql.encode(),check=False)
        require(result.returncode!=0,code)
    deny("SET ROLE auth_sessions; SELECT auth_l1.rotate_session('"+expired+"','"+h("expired-new")+"',0,0);","EXPIRED_ROTATION_ACCEPTED")
    deny("SET ROLE auth_sessions; SELECT auth_l1.rotate_session('"+old+"','"+h("reused-old")+"',0,0);","OLD_ROTATION_ACCEPTED")
    live,gone1,gone2=h("replay-live"),h("replay-expired1"),h("replay-expired2")
    lab.sql(restored,"INSERT INTO auth_l1.service_assertion_replays(issuer_jti_sha256,consumed_at,expires_at) VALUES ('"+live+"',clock_timestamp()-interval '2 seconds',clock_timestamp()+interval '10 minutes'),('"+gone1+"',clock_timestamp()-interval '2 minutes',clock_timestamp()-interval '1 minute'),('"+gone2+"',clock_timestamp()-interval '2 minutes',clock_timestamp()-interval '1 minute');")
    before=lab.sql(restored,"SELECT count(*) FROM auth_l1.service_assertion_replays;")
    require(before=="3","REPLAY_FIXTURE_COUNT")
    # Background cleanup role has only its fixed SECURITY DEFINER function.
    for sql,code in (
        ("SELECT * FROM auth_l1.sessions;","CLEANER_SESSION_READ"),
        ("SELECT * FROM history_l1.messages;","CLEANER_HISTORY_READ"),
        ("SELECT * FROM auth_l1.service_assertion_replays;","CLEANER_RAW_REPLAY_READ"),
        ("DELETE FROM auth_l1.service_assertion_replays;","CLEANER_RAW_REPLAY_DELETE"),
        ("SELECT auth_l1.consume_service_assertion('"+h("forbidden")+"',extract(epoch from clock_timestamp())::bigint+20);","CLEANER_CONSUME"),
        ("SELECT auth_l1.purge_expired_service_assertions(0);","ZERO_BATCH"),
        ("SELECT auth_l1.purge_expired_service_assertions(1001);","OVERSIZE_BATCH")):
        deny("SET ROLE auth_replay_cleaner; "+sql,code)
    require(lab.sql(restored,"SET ROLE auth_replay_cleaner; SELECT auth_l1.purge_expired_service_assertions(1);")=="1","BOUNDED_PURGE_1")
    require(lab.sql(restored,"SET ROLE auth_replay_cleaner; SELECT auth_l1.purge_expired_service_assertions(1);")=="1","BOUNDED_PURGE_2")
    require(lab.sql(restored,"SET ROLE auth_replay_cleaner; SELECT auth_l1.purge_expired_service_assertions(1);")=="0","LIVE_PURGED")
    require(lab.sql(restored,"SELECT count(*) FROM auth_l1.service_assertion_replays WHERE issuer_jti_sha256='"+live+"';")=="1","VALID_REPLAY_LOST")
    require(lab.sql(restored,"SELECT count(*) FROM auth_l1.service_assertion_replays;")=="1","REPLAY_COUNT_DRIFT")
    deny("SET ROLE auth_trust_api; SELECT auth_l1.consume_service_assertion('"+gone1+"',extract(epoch from clock_timestamp()-interval '1 minute')::bigint);","EXPIRED_REPLAY_REUSED")
    require(lab.sql(restored,"SELECT count(*) FROM history_l1.messages;")=="4","CLEANER_HISTORY_MUTATED")
    return {"scope":"DISCONNECTED_RESTORED_PG_SYNTHETIC_AUTH_ONLY","rotation_generation_increment":True,
            "old_generation_reuse_denied":True,"absolute_deadline_unchanged":True,
            "expired_validate_and_rotate_denied":True,"cleaner_privilege_negatives":7,
            "expired_replay_removed":2,"valid_replay_preserved":1,"expired_replay_reuse_denied":True,
            "history_rows_unchanged":True,"history_retention_policy_approved":False,
            "auth_expiry_policy_approved":False,"native_background_job_started":False}

def execute(sha):
    lab=Lab()
    started=time.monotonic()
    try:
        out("docker","pull","--platform","linux/amd64",IMAGE,timeout=240)
        image=json.loads(out("docker","image","inspect",IMAGE))[0]
        image_id=image["Id"]
        require(image["Architecture"]=="amd64" and image["Os"]=="linux" and re.fullmatch("sha256:[a-f0-9]{64}",image_id),"IMAGE_ID_DENIED")
        srcvol,walvol,basevol,restorevol=[lab.volume(s) for s in ("source","wal","base","restore")]
        src=lab.create("source",["-e","POSTGRES_HOST_AUTH_METHOD=trust","-v",srcvol+":/var/lib/postgresql/data","-v",walvol+":/wal","-v",basevol+":/base",image_id,
           "postgres","-c","listen_addresses=","-c","archive_mode=on","-c","archive_command=cp %p /wal/%f","-c","wal_level=replica"])
        lab.wait(src)
        lab.exec(src,"chown","postgres:postgres","/wal","/base",root=True)
        require(lab.sql(src,"SHOW server_version;","postgres").startswith("17.11"),"PG_VERSION")
        lab.sql(src,"CREATE ROLE history_migrator NOLOGIN NOSUPERUSER BYPASSRLS; CREATE ROLE history_app NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;","postgres")
        lab.sql(src,"CREATE ROLE auth_migrator NOLOGIN NOSUPERUSER BYPASSRLS;","postgres")
        auth_roles=("auth_revoker","db55_lab_auditor","auth_mapper","auth_sessions","auth_reauth",
          "auth_trust_api","auth_replay_cleaner","auth_reset_issuer","auth_reset_executor",
          "auth_reset_lookup","auth_reset_idp_recorder","auth_login_bootstrap","auth_login_issuer",
          "auth_login_binder","auth_login_reader","auth_login_cleaner","auth_login_claim_reader")
        for role in auth_roles:
            lab.sql(src,"CREATE ROLE "+role+" NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;","postgres")
        lab.sql(src,"CREATE DATABASE "+DB+";","postgres")
        lab.sql(src,"REVOKE CONNECT,TEMP ON DATABASE "+DB+" FROM PUBLIC; GRANT CONNECT,CREATE ON DATABASE "+DB+" TO history_migrator,auth_migrator; GRANT CONNECT ON DATABASE "+DB+" TO history_app;")
        lab.sql(src,"GRANT CONNECT ON DATABASE "+DB+" TO "+",".join(auth_roles)+";")
        files=sorted((ROOT/"infra/postgres/migrations").glob("*.up.sql"))
        require(len(files)==10 and [p.name[:3] for p in files]==[str(i).zfill(3) for i in range(1,11)],"MIGRATION_COUNT")
        hashes={}
        for p in files:
            require(out("git","hash-object",str(p))==out("git","rev-parse",sha+":"+str(p.relative_to(ROOT))),"SQL_DRIFT")
            data=p.read_bytes();hashes[p.name]=hashlib.sha256(data).hexdigest()
            role="history_migrator" if p.name[:3] in ("001","002") else "auth_migrator"
            lab.sql(src,"SET ROLE "+role+";\n"+data.decode())
        # Synthetic Auth SQL only, no IdP/browser/session token material.
        lab.sql(src,"INSERT INTO auth_l1.owners(owner_id) VALUES ('A'),('B');")
        digests={o:hashlib.sha256((lab.prefix+o).encode()).hexdigest() for o in ("A","B")}
        def auth_valid(name,owner):
            return lab.sql(name,"SET ROLE auth_sessions; SELECT auth_l1.validate_session('"+digests[owner]+"') IS NOT NULL;")=="t"
        def revoke(name,owner):
            return lab.sql(name,"SET ROLE auth_sessions; SELECT auth_l1.revoke_one('"+digests[owner]+"',0);")=="t"
        for owner in ("A","B"):
            require(lab.sql(src,"SET ROLE auth_sessions; SELECT auth_l1.issue_session('"+owner+"',0,'"+digests[owner]+"',900,1800) IS NOT NULL;")=="t","SESSION_ISSUE")
            require(auth_valid(src,owner),"SESSION_PRE_BASE_INVALID")
        for owner in ("A","B"):
            lab.sql(src,scoped(owner,"INSERT INTO history_l1.conversations(owner_id,id) VALUES ('"+owner+"','c"+owner+"'); INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body) VALUES ('"+owner+"','m0"+owner+"','c"+owner+"','user','before_base')"))
        lab.exec(src,"pg_basebackup","-U","postgres","-D","/base","-X","stream","--checkpoint=fast","--manifest-checksums=SHA256",timeout=180)
        lab.exec(src,"pg_verifybackup","/base",timeout=180)
        manifest_sha=lab.exec(src,"sha256sum","/base/backup_manifest").stdout.decode().split()[0]
        # Check actual manifest rejection of altered base bytes, never restore them.
        lab.exec(src,"sh","-ec","cp /base/PG_VERSION /tmp/f3-pitr-version; printf 'tamper\\n' >> /base/PG_VERSION")
        require(lab.exec(src,"pg_verifybackup","/base",check=False).returncode!=0,"TAMPER_ACCEPTED")
        lab.exec(src,"sh","-ec","cp /tmp/f3-pitr-version /base/PG_VERSION; rm /tmp/f3-pitr-version")
        lab.exec(src,"pg_verifybackup","/base",timeout=180)
        for owner in ("A","B"):
            lab.sql(src,scoped(owner,"INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body) VALUES ('"+owner+"','m1"+owner+"','c"+owner+"','user','at_target')"))
        require(revoke(src,"A") and not auth_valid(src,"A") and auth_valid(src,"B"),"TARGET_REVOCATION_STATE")
        target="f3_safe_target"
        target_lsn=lab.sql(src,"SELECT pg_create_restore_point('"+target+"');")
        require(re.fullmatch("[0-9A-F]+/[0-9A-F]+",target_lsn),"TARGET_LSN")
        target_rows={o:owner_rows(lab,src,o) for o in ("A","B")}
        require(target_rows=={"A":"m0A:before_base,m1A:at_target","B":"m0B:before_base,m1B:at_target"},"TARGET_ROWS")
        for owner in ("A","B"):
            lab.sql(src,scoped(owner,"INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body) VALUES ('"+owner+"','m2"+owner+"','c"+owner+"','user','after_target')"))
        require(revoke(src,"B") and not auth_valid(src,"A") and not auth_valid(src,"B"),"POST_TARGET_REVOCATION_STATE")
        archive_name=lab.sql(src,"SELECT pg_walfile_name(pg_current_wal_insert_lsn());")
        require(re.fullmatch("[0-9A-F]{24}",archive_name),"WAL_NAME")
        lab.sql(src,"SELECT pg_switch_wal();")
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if lab.exec(src,"test","-s","/wal/"+archive_name,check=False).returncode==0:break
            time.sleep(.5)
        else:raise RuntimeError("WAL_NOT_ARCHIVED")
        source_rows={o:owner_rows(lab,src,o) for o in ("A","B")}
        require(all("after_target" in v for v in source_rows.values()),"SOURCE_AFTER_TARGET_MISSING")
        # Copy the verified physical base into a completely different volume.
        # Physical recovery intentionally preserves system identifier.
        lab.create("copy",["-u","0","-v",basevol+":/base:ro","-v",restorevol+":/restore",image_id,
            "-ec","cp -a /base/. /restore/; chown -R postgres:postgres /restore; chmod 0700 /restore; touch /restore/recovery.signal; chown postgres:postgres /restore/recovery.signal"],entry="sh",temporary=True)
        restore_start=time.monotonic()
        restored=lab.create("restored",["-v",restorevol+":/var/lib/postgresql/data","-v",walvol+":/wal:ro",image_id,
          "postgres","-c","listen_addresses=","-c","archive_mode=off","-c","restore_command=cp /wal/%f %p",
          "-c","recovery_target_name="+target,"-c","recovery_target_action=promote"])
        lab.wait(restored,DB)
        deadline=time.monotonic()+50
        while time.monotonic()<deadline:
            if lab.sql(restored,"SELECT pg_is_in_recovery();")=="f":break
            time.sleep(.5)
        else:raise RuntimeError("RECOVERY_NOT_PROMOTED")
        require({o:owner_rows(lab,restored,o) for o in ("A","B")}==target_rows,"PITR_ROWS_DRIFT")
        require(lab.sql(restored,"SELECT count(*) FROM history_l1.messages;")=="4","AFTER_TARGET_LEAK")
        require(lab.sql(src,"SELECT count(*) FROM history_l1.messages;")=="6","SOURCE_MUTATED")
        require(lab.sql(restored,"SELECT system_identifier FROM pg_control_system();")==lab.sql(src,"SELECT system_identifier FROM pg_control_system();"),"PHYSICAL_LINEAGE_DRIFT")
        require(lab.sql(restored,"SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('history_l1','auth_l1') AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity;")=="14","FORCE_RLS_DRIFT")
        require(not auth_valid(restored,"A") and auth_valid(restored,"B"),"PITR_SESSION_STATE_DRIFT")
        require(not auth_valid(src,"A") and not auth_valid(src,"B"),"SOURCE_REVOCATION_DRIFT")
        # The recovery point legitimately predates B's revoke. This is a
        # security hazard for a real target, NOT authorization to serve it.
        # Reconcile only the owned synthetic lab clone before any reuse.
        require(revoke(restored,"B") and not auth_valid(restored,"B") and not auth_valid(restored,"A"),"RECONCILIATION_DENIED")
        require(lab.sql(restored,"SELECT count(*) FROM pg_roles WHERE rolname='history_app' AND NOT rolsuper AND NOT rolbypassrls;")=="1","ROLE_DRIFT")
        require(lab.sql(restored,scoped("A","SELECT count(*) FROM history_l1.messages WHERE owner_id='B'")).splitlines()[-1]=="0","CROSS_OWNER_LEAK")
        require(lab.sql(restored,scoped("B","SELECT count(*) FROM history_l1.messages WHERE owner_id='A'")).splitlines()[-1]=="0","CROSS_OWNER_LEAK")
        denied=lab.exec(restored,"psql","-X","-qAt","-v","ON_ERROR_STOP=1","-U","postgres","-d",DB,
            data=scoped("A","INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body) VALUES ('B','forbidden','cB','user','bad')").encode(),check=False)
        require(denied.returncode!=0,"CROSS_OWNER_WRITE_ACCEPTED")
        require(lab.sql(restored,"SELECT count(*) FROM history_l1.messages;")=="4","NEGATIVE_WRITE_MUTATED")
        auth_maintenance=post_recovery_role_and_expiry(lab,restored)
        require(lab.sql(src,"SELECT count(*) FROM history_l1.messages;")=="6","SOURCE_DRIFT_AFTER_MAINTENANCE")
        receipt={"schema":"foundation.f3.pg17_physical_pitr_ci.v1","source_sha":sha,
          "run_id":os.environ["GITHUB_RUN_ID"],"image_id":image_id,"migration_sha256":hashes,
          "network_none_no_published_ports":True,"physical_base_manifest_sha256":manifest_sha,
          "base_manifest_verified":True,"tampered_base_rejected":True,"wal_archive_verified":True,
          "restore_point_reached":True,"source_rows":6,"restored_target_rows":4,
          "later_rows_excluded":2,"distinct_volume_same_physical_cluster_lineage":True,
          "force_rls_tables":14,"both_owner_read_denials":True,"foreign_write_denied":True,
          "pre_target_revocation_preserved":True,"later_revocation_not_present_at_target":True,
          "synthetic_later_revocation_reconciled_before_any_reuse":True,"target_reconciliation_policy_approved":False,
          "source_unchanged":True,"restored_auth_maintenance":auth_maintenance,"restore_and_validation_ms":round((time.monotonic()-restore_start)*1000),
          "total_lab_ms":round((time.monotonic()-started)*1000),"rpo_rto_approved":False,
          "scope":"PG17.11_HISTORY_AUTH_001_010_CI_PHYSICAL_PITR_ONLY","target_verified":False,
          "engine_calls":0,"sql011":False,"accepted":False}
    finally:lab.cleanup()
    receipt["temporary_volumes_removed"]=True
    return receipt

if __name__=="__main__":
    receipt=execute(context())
    p=ROOT/"ci_receipts/f3_pg17_pitr.json";p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(receipt,indent=2)+"\n")
    print("F3_PG17_PHYSICAL_PITR_TARGET_AND_RLS_PASS_CI_ONLY")
