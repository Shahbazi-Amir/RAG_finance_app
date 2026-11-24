"""Disposable CI-only prior-candidate rollback of the deny-only Web/API topology.
Not a signed History/PG rollback, target install, engine or release approval.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone

PRIOR = '9c14c56d847cc3657fc69327e4df59b002273719'
LAST_OBSERVED = '0647ac903a597aa62d26d5547d764e90d23b0020'
BRANCH = 'refs/heads/integration/f3-foundation-history-two-users-20261124'
REPO = 'Shahbazi-Amir/RAG_finance_app'
SHA = re.compile(r'[0-9a-f]{40}')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')
COMPOSE = 'infra/phase3_l1/compose.app-only.internal.yml'

class Denied(RuntimeError):
    pass

def require(ok, code):
    if not ok:
        raise Denied(code)

def check_context(env, root, username):
    require(all(env.get(k)=='true' for k in ('CI','GITHUB_ACTIONS')), 'CI_ONLY')
    require(env.get('RUNNER_OS')=='Linux' and env.get('RUNNER_ENVIRONMENT')=='github-hosted'
            and username=='runner', 'HOSTED_RUNNER_ONLY')
    require(not any(env.get(k) for k in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH','COMPOSE_FILE','COMPOSE_PROFILES','COMPOSE_ENV_FILES')), 'AMBIENT_DOCKER_OR_COMPOSE_OVERRIDE')
    require(env.get('GITHUB_REPOSITORY')==REPO and env.get('GITHUB_REF')==BRANCH,
            'REPOSITORY_OR_BRANCH_DENIED')
    require(str(root)==env.get('GITHUB_WORKSPACE') and str(root).startswith('/home/runner/work/'), 'WORKSPACE_DENIED')
    require(SHA.fullmatch(env.get('GITHUB_SHA','')) and env['GITHUB_SHA'] not in (PRIOR,LAST_OBSERVED), 'SHA_DENIED')
    for key in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT'):
        require(re.fullmatch(r'[1-9][0-9]{0,19}',env.get(key,'')), 'RUN_ID_DENIED')
    require(str(env.get('RUNNER_TEMP','')).startswith('/home/runner/work/_temp'), 'TEMP_DENIED')
    return 'f3-prior-rollback-'+env['GITHUB_RUN_ID']+'-'+env['GITHUB_RUN_ATTEMPT']

def check_image(image, sha, uid):
    require(DIGEST.fullmatch(image.get('Id','')), 'IMAGE_ID_DENIED')
    config=image.get('Config') or {}
    require((config.get('Labels') or {}).get('org.opencontainers.image.revision')==sha, 'IMAGE_SOURCE_MISMATCH')
    require(config.get('User')==uid and image.get('Os')=='linux' and image.get('Architecture')=='amd64','IMAGE_RUNTIME_MISMATCH')
    return image['Id']

def check_container(data, image_id, project, network, uid):
    h=data['HostConfig']; c=data['Config']; n=data['NetworkSettings']
    require(data['Image']==image_id and data['State']['Running'] is True, 'CONTAINER_IMAGE_OR_STATE_MISMATCH')
    require(c['User']==uid and c['Labels'].get('com.docker.compose.project')==project, 'CONTAINER_OWNER_MISMATCH')
    require(h['ReadonlyRootfs'] is True and 'ALL' in (h.get('CapDrop') or []) and
            any(s.startswith('no-new-privileges') for s in (h.get('SecurityOpt') or [])), 'CONTAINER_HARDENING_MISMATCH')
    require(not h.get('PortBindings') and set(n['Networks'])=={network}, 'PUBLIC_OR_UNEXPECTED_NETWORK')
    require(not any(m['Type'] in ('volume','bind') for m in data.get('Mounts',[])), 'PERSISTENT_OR_HOST_MOUNT_DENIED')
    require(h['Memory']>0 and h['PidsLimit']>0 and h['NanoCpus']>0, 'RESOURCE_LIMIT_MISSING')
    return data['Id']

def check_topology(doc, project, tags):
    require(doc.get('name')==project and set(doc.get('services',{}))=={'api','web'},'COMPOSE_PROJECT_OR_SERVICES_DENIED')
    require(not doc.get('volumes') and not doc.get('secrets') and not doc.get('configs'),'COMPOSE_DATA_OR_SECRET_DENIED')
    networks=doc.get('networks',{})
    require(set(networks)=={'private'} and networks['private'].get('internal') is True and not networks['private'].get('external'),'COMPOSE_NETWORK_DENIED')
    for kind,uid in (('api','11001:11001'),('web','11003:11003')):
        svc=doc['services'][kind]
        require(svc.get('image')==tags[kind] and svc.get('user')==uid and svc.get('read_only') is True,'COMPOSE_IMAGE_OR_USER_DENIED')
        require(not any(svc.get(k) for k in ('ports','volumes','secrets','configs','network_mode','privileged','devices','pid','ipc')),'COMPOSE_EXTRA_ACCESS_DENIED')
        require(set(svc.get('networks',{}))=={'private'} and svc.get('pull_policy')=='never','COMPOSE_SERVICE_NETWORK_OR_PULL_DENIED')

API_SMOKE = '''import json,urllib.request,urllib.error
b="http://127.0.0.1:8080"
with urllib.request.urlopen(b+"/health/live",timeout=5) as r:
 d=json.load(r);assert r.status==200 and d["process_alive"] is True and d["application_ready"] is False
for p in ("/health/ready","/v1/messages"):
 req=urllib.request.Request(b+p,data=b"{invalid" if p.endswith("messages") else None,method="POST" if p.endswith("messages") else "GET")
 try: urllib.request.urlopen(req,timeout=5);raise AssertionError("UNEXPECTED_SUCCESS")
 except urllib.error.HTTPError as e: assert e.code==503
'''
WEB_SMOKE = '''(async()=>{const b="http://127.0.0.1:3000";
const r=await fetch(b+"/api/product-capabilities"),j=await r.json();
if(!r.ok||j.send_mode!=="DISABLED"||j.engine_available!==false||j.generation_available!==false)throw Error("CAPABILITY");
const s=await fetch(b+"/api/history/messages",{method:"POST",headers:{"content-type":"application/json"},body:"{invalid"});
const d=await s.json();if(s.status!==503||d.error!=="ENGINE_NOT_AVAILABLE")throw Error("SEND");
})().catch(()=>process.exit(1))'''

class Lab:
    def __init__(self, root, env, project):
        self.root=root; self.env=dict(env); self.project=project; self.current=env['GITHUB_SHA']; self.active=None
        self.images={}; self.records=[]; self.started=False
    def cmd(self,*args,env=None,timeout=600):
        # Do not emit raw command stdout/stderr: no secret or private config logs.
        p=subprocess.run(args,cwd=self.root,env=env or self.env,capture_output=True,timeout=timeout)
        require(p.returncode==0,'COMMAND_FAILED_'+args[0]+'_'+(args[1] if len(args)>1 else ''))
        return p.stdout
    def obj(self,*args):
        data=json.loads(self.cmd(*args)); require(isinstance(data,list) and len(data)==1,'INSPECT_SHAPE');return data[0]
    def tag(self,kind,sha):
        return 'rag-f3-app-only-'+kind+':'+self.project+'-'+sha
    def compose(self,*args,sha=None,timeout=600):
        e=dict(self.env,F3_PROJECT_NAME=self.project,F3_SOURCE_SHA=sha or self.active or self.current,
               F3_RELEASE_TAG=self.project+'-'+(sha or self.active or self.current))
        return self.cmd('docker','compose','--project-name',self.project,'--file',COMPOSE,*args,env=e,timeout=timeout)
    def prepare(self):
        require(self.cmd('git','rev-parse','HEAD').decode().strip()==self.current,'HEAD_DRIFT')
        require(not self.cmd('git','status','--porcelain','--untracked-files=no').strip(),'TRACKED_DIRTY')
        for sha in (PRIOR,LAST_OBSERVED):
            self.cmd('git','merge-base','--is-ancestor',sha,self.current)
        require(self.cmd('docker','context','show').decode().strip()=='default','NONLOCAL_DOCKER_CONTEXT')
        require(not self.cmd('docker','ps','-aq','--filter','label=com.docker.compose.project='+self.project).strip(),'PROJECT_ALREADY_EXISTS')
        require(not self.cmd('docker','network','ls','-q','--filter','label=com.docker.compose.project='+self.project).strip(),'NETWORK_ALREADY_EXISTS')
        # Compose and migrations must be identical for this app-image-only rollback.
        for path in (COMPOSE,'infra/postgres/migrations'):
            require(self.cmd('git','rev-parse',PRIOR+':'+path)==self.cmd('git','rev-parse',self.current+':'+path),'TOPOLOGY_OR_MIGRATION_DRIFT')
        for sha in (PRIOR,self.current):
            with tempfile.TemporaryDirectory(prefix='f3-rollback-src-',dir=self.env['RUNNER_TEMP']) as tmp:
                archive=Path(tmp)/'source.tar'; tree=Path(tmp)/'source';tree.mkdir()
                self.cmd('git','archive','--format=tar','--output='+str(archive),sha)
                self.cmd('tar','-xf',str(archive),'-C',str(tree))
                require(not (tree/'infra/postgres/migrations/011_product_answer_claims.up.sql').exists(),'SQL011_DENIED')
                for kind,uid in (('api','11001:11001'),('web','11003:11003')):
                    tag=self.tag(kind,sha)
                    self.cmd('docker','build','--platform','linux/amd64','--file',str(tree/('infra/phase3_l1/Dockerfile.'+kind)),
                             '--build-arg','SOURCE_SHA='+sha,'--tag',tag,str(tree),timeout=1200)
                    self.images[sha,kind]=check_image(self.obj('docker','image','inspect',tag),sha,uid)
        require(all(self.images[PRIOR,k]!=self.images[self.current,k] for k in ('api','web')),'CANDIDATE_ID_NOT_DISTINCT')
    def activate(self,sha,label):
        require(sha in (PRIOR,self.current),'UNAPPROVED_SHA')
        # Validate the resolved Compose definition before any runtime mutation.
        definition=json.loads(self.compose('config','--format','json',sha=sha))
        check_topology(definition,self.project,{k:self.tag(k,sha) for k in ('api','web')})
        self.active=sha; self.started=True
        self.compose('up','-d','--no-build','--pull','never','--force-recreate','--wait','--wait-timeout','120',sha=sha)
        nets=self.cmd('docker','network','ls','-q','--filter','label=com.docker.compose.project='+self.project).decode().split()
        require(len(nets)==1,'NETWORK_COUNT');net=self.obj('docker','network','inspect',nets[0]);require(net['Internal'] is True,'NETWORK_NOT_INTERNAL')
        ids={}
        for kind,uid in (('api','11001:11001'),('web','11003:11003')):
            cid=self.compose('ps','-q',kind).decode().strip();require(re.fullmatch(r'[0-9a-f]{64}',cid),'CONTAINER_ID')
            data=self.obj('docker','inspect',cid)
            ids[kind]=check_container(data,self.images[sha,kind],self.project,net['Name'],uid)
        require(set(net['Containers'])==set(ids.values()),'NETWORK_MEMBERS_MISMATCH')
        self.cmd('docker','exec',ids['api'],'python3','-c',API_SMOKE,timeout=20)
        self.cmd('docker','exec',ids['web'],'node','-e',WEB_SMOKE,timeout=20)
        self.records.append({'phase':label,'sha':sha,'image_ids':{k:self.images[sha,k] for k in ids},'container_ids':ids,
                             'live_200':True,'ready_503':True,'send_503':True,'no_engine_capability':True,
                             'timestamp':datetime.now(timezone.utc).isoformat()})
        return ids
    def inject_failure(self,ids):
        cid=ids['api'];require(self.active==self.current,'NOT_CURRENT_CANDIDATE')
        d=self.obj('docker','inspect',cid);require(d['Config']['Labels'].get('com.docker.compose.project')==self.project and d['Image']==self.images[self.current,'api'],'FAILURE_TARGET_DENIED')
        self.cmd('docker','stop','--time','5',cid,timeout=30)
        require(self.obj('docker','inspect',cid)['State']['Running'] is False,'INJECTION_NOT_OBSERVED')
        return 'CANDIDATE_API_STOPPED_OBSERVED'
    def cleanup(self):
        if self.started:
            self.compose('down','--remove-orphans',timeout=120)
    def execute(self):
        try:
            self.prepare()
            self.activate(PRIOR,'prior_baseline')
            current=self.activate(self.current,'candidate')
            failure=self.inject_failure(current)
            start=time.monotonic_ns()
            self.activate(PRIOR,'prior_rollback')
            elapsed=(time.monotonic_ns()-start)//1_000_000
            require(self.records[0]['image_ids']==self.records[2]['image_ids'],'ROLLBACK_IMAGE_ID_DRIFT')
            require(all(self.records[0]['container_ids'][k]!=self.records[2]['container_ids'][k] for k in ('api','web')),'ROLLBACK_NOT_RECREATED')
            receipt={'schema':'foundation.f3.prior_candidate_deny_only_rollback_ci.v1','source_sha':self.current,
                'prior_sha':PRIOR,'run_id':self.env['GITHUB_RUN_ID'],'run_attempt':self.env['GITHUB_RUN_ATTEMPT'],
                'observations':self.records,'fault':failure,'rollback_ms':elapsed,'scope':'CI_DENY_ONLY_WEB_API_NO_DB',
                'signed_history_pg_rollback_verified':False,'target_verified':False,'owner_accepted':False,'release':'HOLD'}
        finally:
            self.cleanup()
        return receipt

def main():
    import getpass
    root=Path.cwd().resolve();env=dict(os.environ);project=check_context(env,root,getpass.getuser())
    receipt=Lab(root,env,project).execute()
    output=root/'ci_receipts/f3_prior_candidate_deny_only_rollback.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2)+'\n')
    print('F3_PRIOR_CANDIDATE_DENY_ONLY_REAL_COMPOSE_FAILURE_ROLLBACK_PASS')

if __name__=='__main__':
    main()
