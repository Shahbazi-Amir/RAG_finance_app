import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock
import copy

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('rollback',ROOT/'scripts/phase3/f3_prior_candidate_rollback_ci.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CURRENT='a'*40
ROOT_CI=Path('/home/runner/work/RAG_finance_app/RAG_finance_app')
ENV={'CI':'true','GITHUB_ACTIONS':'true','RUNNER_OS':'Linux','RUNNER_ENVIRONMENT':'github-hosted',
     'GITHUB_REPOSITORY':m.REPO,'GITHUB_REF':m.BRANCH,'GITHUB_WORKSPACE':str(ROOT_CI),
     'GITHUB_SHA':CURRENT,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','RUNNER_TEMP':'/home/runner/work/_temp'}
ID='sha256:'+'b'*64
PROJECT='f3-prior-rollback-123-1';NETWORK=PROJECT+'_private'

def image():
    return {'Id':ID,'Os':'linux','Architecture':'amd64','Config':{'User':'11001:11001','Labels':{'org.opencontainers.image.revision':CURRENT}}}

def container():
    return {'Id':'c'*64,'Image':ID,'State':{'Running':True},'Config':{'User':'11001:11001','Labels':{'com.docker.compose.project':PROJECT}},
            'HostConfig':{'ReadonlyRootfs':True,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges:true'],'PortBindings':{},'Memory':256*1024**2,'PidsLimit':64,'NanoCpus':10**9},
            'NetworkSettings':{'Networks':{NETWORK:{}}},'Mounts':[]}

class GuardTests(unittest.TestCase):
    def test_context_accepts_only_expected_disposable_branch(self):
        self.assertEqual(m.check_context(ENV,ROOT_CI,'runner'),PROJECT)
    def test_context_denies_non_ci_and_self_hosted(self):
        for k,v in [('CI','false'),('GITHUB_ACTIONS','false'),('RUNNER_ENVIRONMENT','self-hosted'),('RUNNER_OS','macOS')]:
            with self.subTest(k=k),self.assertRaises(m.Denied):m.check_context(dict(ENV,**{k:v}),ROOT_CI,'runner')
    def test_context_denies_other_repo_branch_or_user(self):
        for k,v in [('GITHUB_REPOSITORY','other/project'),('GITHUB_REF','refs/heads/main')]:
            with self.subTest(k=k),self.assertRaises(m.Denied):m.check_context(dict(ENV,**{k:v}),ROOT_CI,'runner')
        with self.assertRaises(m.Denied):m.check_context(ENV,ROOT_CI,'root')
    def test_context_denies_wrong_workspace_or_temp(self):
        with self.assertRaises(m.Denied):m.check_context(ENV,Path('/tmp'), 'runner')
        with self.assertRaises(m.Denied):m.check_context(dict(ENV,RUNNER_TEMP='/tmp'),ROOT_CI,'runner')
    def test_context_denies_old_sha_and_injected_project(self):
        for k,v in [('GITHUB_SHA',m.PRIOR),('GITHUB_SHA',m.LAST_OBSERVED),('GITHUB_SHA','HEAD'),('GITHUB_RUN_ID','x;evil'),('GITHUB_RUN_ATTEMPT','0')]:
            with self.subTest(k=k),self.assertRaises(m.Denied):m.check_context(dict(ENV,**{k:v}),ROOT_CI,'runner')
    def test_context_denies_ambient_remote_docker(self):
        for k in ('DOCKER_HOST','DOCKER_CONTEXT','COMPOSE_FILE','COMPOSE_PROFILES'):
            with self.subTest(k=k),self.assertRaises(m.Denied):m.check_context(dict(ENV,**{k:'unexpected'}),ROOT_CI,'runner')
    def test_compose_preflight_denies_unexpected_topology(self):
        tags={'api':'api:ci','web':'web:ci'}
        doc={'name':PROJECT,'networks':{'private':{'internal':True}},'services':{k:{'image':tags[k],'user':uid,'read_only':True,'networks':{'private':None},'pull_policy':'never'} for k,uid in [('api','11001:11001'),('web','11003:11003')]}}
        m.check_topology(doc,PROJECT,tags)
        for key,value in [('ports',['80:80']),('volumes',['/tmp:/tmp']),('network_mode','host'),('privileged',True),('image','other:ci')]:
            d=copy.deepcopy(doc);d['services']['api'][key]=value
            with self.subTest(key=key),self.assertRaises(m.Denied):m.check_topology(d,PROJECT,tags)
        d=copy.deepcopy(doc);d['networks']['private']['external']=True
        with self.assertRaises(m.Denied):m.check_topology(d,PROJECT,tags)
    def test_image_identity(self):
        self.assertEqual(m.check_image(image(),CURRENT,'11001:11001'),ID)
        for key,value in [('Id','bad'),('Os','windows'),('Architecture','arm64')]:
            with self.subTest(key=key),self.assertRaises(m.Denied):m.check_image(dict(image(),**{key:value}),CURRENT,'11001:11001')
    def test_image_label_and_uid(self):
        with self.assertRaises(m.Denied):m.check_image(image(),m.PRIOR,'11001:11001')
        with self.assertRaises(m.Denied):m.check_image(image(),CURRENT,'0:0')
    def test_container_security(self):
        self.assertEqual(m.check_container(container(),ID,PROJECT,NETWORK,'11001:11001'),'c'*64)
        for key,value in [('ReadonlyRootfs',False),('CapDrop',[]),('SecurityOpt',[]),('PortBindings',{'8080/tcp':[{}]}),('Memory',0),('PidsLimit',0),('NanoCpus',0)]:
            d=container();d['HostConfig'][key]=value
            with self.subTest(key=key),self.assertRaises(m.Denied):m.check_container(d,ID,PROJECT,NETWORK,'11001:11001')
    def test_container_denies_mount_and_foreign_network(self):
        for mounts in [[{'Type':'volume'}],[{'Type':'bind'}]]:
            d=container();d['Mounts']=mounts
            with self.assertRaises(m.Denied):m.check_container(d,ID,PROJECT,NETWORK,'11001:11001')
        d=container();d['NetworkSettings']['Networks']['foreign']={}
        with self.assertRaises(m.Denied):m.check_container(d,ID,PROJECT,NETWORK,'11001:11001')
    def test_container_denies_wrong_identity_or_project(self):
        for expected,project in [('sha256:'+'d'*64,PROJECT),(ID,'foreign')]:
            with self.assertRaises(m.Denied):m.check_container(container(),expected,project,NETWORK,'11001:11001')
        d=container();d['State']['Running']=False
        with self.assertRaises(m.Denied):m.check_container(d,ID,PROJECT,NETWORK,'11001:11001')

class SequenceTests(unittest.TestCase):
    def lab(self):
        lab=m.Lab(ROOT_CI,ENV,PROJECT);lab.prepare=Mock();lab.inject_failure=Mock(return_value='CANDIDATE_API_STOPPED_OBSERVED');lab.cleanup=Mock();return lab
    def test_order_and_scope_of_receipt(self):
        lab=self.lab(); calls=[]
        def activation(sha,label):
            calls.append((sha,label));ids={'api':label+'a','web':label+'w'}
            lab.records.append({'sha':sha,'image_ids':{'api':sha+'a','web':sha+'w'},'container_ids':ids});return ids
        lab.activate=Mock(side_effect=activation)
        result=lab.execute()
        self.assertEqual(calls,[(m.PRIOR,'prior_baseline'),(CURRENT,'candidate'),(m.PRIOR,'prior_rollback')])
        lab.inject_failure.assert_called_once_with({'api':'candidatea','web':'candidatew'})
        lab.cleanup.assert_called_once()
        self.assertFalse(result['signed_history_pg_rollback_verified']);self.assertFalse(result['target_verified']);self.assertFalse(result['owner_accepted']);self.assertEqual(result['release'],'HOLD')
    def test_no_receipt_on_prepare_failure(self):
        lab=self.lab();lab.prepare.side_effect=m.Denied('DRIFT');lab.activate=Mock()
        with self.assertRaises(m.Denied):lab.execute()
        lab.activate.assert_not_called();lab.cleanup.assert_called_once()
    def test_no_receipt_on_fault_failure(self):
        lab=self.lab();lab.activate=Mock(return_value={'api':'a','web':'w'});lab.inject_failure.side_effect=m.Denied('INJECTION_NOT_OBSERVED')
        with self.assertRaises(m.Denied):lab.execute()
        self.assertEqual(lab.activate.call_count,2);lab.cleanup.assert_called_once()
    def test_no_receipt_on_rollback_identity_drift(self):
        lab=self.lab()
        def activation(sha,label):
            ids={'api':label+'a','web':label+'w'};lab.records.append({'image_ids':{'api':label},'container_ids':ids});return ids
        lab.activate=Mock(side_effect=activation)
        with self.assertRaisesRegex(m.Denied,'ROLLBACK_IMAGE_ID_DRIFT'):lab.execute()
        lab.cleanup.assert_called_once()
    def test_no_receipt_on_rollback_container_reuse(self):
        lab=self.lab()
        def activation(sha,label):
            ids={'api':sha+'a','web':sha+'w'};lab.records.append({'image_ids':{'api':sha},'container_ids':ids});return ids
        lab.activate=Mock(side_effect=activation)
        with self.assertRaisesRegex(m.Denied,'ROLLBACK_NOT_RECREATED'):lab.execute()
    def test_cleanup_cannot_remove_unstarted_project(self):
        lab=m.Lab(ROOT_CI,ENV,PROJECT);lab.compose=Mock();lab.cleanup();lab.compose.assert_not_called()
    def test_fault_does_not_stop_unowned_container(self):
        lab=m.Lab(ROOT_CI,ENV,PROJECT);lab.active=CURRENT;lab.images[CURRENT,'api']=ID;d=container();d['Config']['Labels']['com.docker.compose.project']='foreign';lab.obj=Mock(return_value=d);lab.cmd=Mock()
        with self.assertRaises(m.Denied):lab.inject_failure({'api':'c'*64})
        lab.cmd.assert_not_called()

if __name__=='__main__':unittest.main()
