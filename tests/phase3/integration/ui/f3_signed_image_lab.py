"""CI-only real signed image, internal Docker network, opaque TCP relay.
No private BFF key or source tree is mounted in the API container.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import socket
import socketserver
import subprocess
import threading
import time

import psycopg

def docker(*args, check=True):
    p=subprocess.run(["docker",*map(str,args)],capture_output=True,text=True,
                     timeout=240,check=False)
    if check and p.returncode:
        raise RuntimeError("CI_DOCKER_"+str(args[0])+"_EXIT_"+str(p.returncode))
    return p.stdout.strip() if check else p.returncode

def sudo(*args):
    subprocess.run(["sudo",*map(str,args)],check=True,capture_output=True,timeout=20)

class Relay(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with socket.create_connection((self.server.target,getattr(self.server,"target_port",8443)),timeout=5) as upstream:
                upstream.settimeout(20)
                self.request.settimeout(20)
                sockets=(upstream,self.request)
                while True:
                    ready,_,_=select.select(sockets,[],[],25)
                    if not ready:return
                    for s in ready:
                        data=s.recv(65536)
                        if not data:return
                        (self.request if s is upstream else upstream).sendall(data)
        except OSError:
            return

class SignedImageLab:
    def __init__(self,root,port,config,source_pg):
        if (os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true"
                or os.getenv("F3_BROWSER_SIGNED_IMAGE")!="1"):
            raise RuntimeError("DISPOSABLE_CI_ONLY")
        self.root=root
        suffix=os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"]
        assert suffix.replace("-","").isdigit()
        self.network="f3-signed-private-"+suffix
        self.name="f3-signed-api-"+suffix
        self.image=os.environ["F3_SIGNED_IMAGE_TAG"]
        self.pg=None
        self.relay=None
        self.thread=None
        self.secrets=root/"api-container-secrets"
        self.secrets.mkdir(mode=0o700)
        self.roundtrip=None
        self.image_id=docker("image","inspect","--format","{{.Id}}",self.image)
        assert docker("image","inspect","--format",'{{index .Config.Labels "org.opencontainers.image.revision"}}',self.image)==os.environ["GITHUB_SHA"]
        assert docker("image","inspect","--format","{{.Config.User}}",self.image)=="11001:11001"
        cfg=dict(config)
        cfg.update(listen_host="0.0.0.0",listen_port=8443)
        for field,filename in (
            ("server_tls_cert_file","api.crt"),("server_tls_key_file","api.key"),
            ("trusted_bff_ca_file","bff-ca.crt"),("bff_rs256_public_key_file","bff-public.pem")):
            shutil.copyfile(cfg[field],self.secrets/filename)
            cfg[field]="/run/secrets/"+filename
        for field in ("history_dsn","revoke_dsn"):
            opts=psycopg.conninfo.conninfo_to_dict(cfg[field])
            assert opts["host"]=="127.0.0.1" and opts["dbname"]=="history_ci_f3_signed"
            if not (self.secrets/"pg-ca.crt").exists():
                shutil.copyfile(opts["sslrootcert"],self.secrets/"pg-ca.crt")
            cfg[field]=psycopg.conninfo.make_conninfo(cfg[field],host="f3-pg",port="5432",
                sslmode="verify-full",sslrootcert="/run/secrets/pg-ca.crt")
        (self.secrets/"phase3-app-only.json").write_text(json.dumps(cfg))
        for f in self.secrets.iterdir():f.chmod(0o600)
        self.secrets.chmod(0o700)
        sudo("chown","-R","11001:11001",self.secrets)
        try:
            docker("network","create","--internal",self.network)
            self.attach_pg(source_pg)
            self.launch()
            self.relay=Relay(("127.0.0.1",port),Handler)
            self.relay.target=self.ip
            self.thread=threading.Thread(target=self.relay.serve_forever,daemon=True)
            self.thread.start()
        except BaseException:
            self.close()
            raise

    def attach_pg(self,container):
        assert self.pg is None
        docker("network","connect","--alias","f3-pg",self.network,container)
        self.pg=container

    def detach_pg(self):
        if self.pg:
            docker("network","disconnect","-f",self.network,self.pg)
            self.pg=None

    def launch(self):
        docker("run","-d","--name",self.name,"--network",self.network,"--network-alias","f3-api",
               "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
               "--pids-limit","128","--memory","512m","--cpus","1.0",
               "--env","API_CURSOR_KEY","--env","API_CURSOR_TTL_SECONDS",
               "--mount","type=bind,src="+str(self.secrets)+",dst=/run/secrets,readonly",
               self.image_id)
        assert docker("inspect","--format","{{.Image}}",self.name)==self.image_id
        assert docker("inspect","--format","{{.Config.User}}",self.name)=="11001:11001"
        assert docker("inspect","--format","{{.HostConfig.ReadonlyRootfs}}",self.name)=="true"
        assert docker("network","inspect","--format","{{.Internal}}",self.network)=="true"
        bindings=json.loads(docker("inspect","--format","{{json .HostConfig.PortBindings}}",self.name))
        assert not bindings
        mounts=json.loads(docker("inspect","--format","{{json .Mounts}}",self.name))
        assert len(mounts)==1 and mounts[0]["Destination"]=="/run/secrets" and mounts[0]["RW"] is False
        self.ip=docker("inspect","--format","{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",self.name)
        assert self.ip
        if self.relay:self.relay.target=self.ip

    def reload(self):
        archive=self.root/"signed-image.tar"
        start=time.monotonic()
        docker("save","-o",archive,self.image)
        with archive.open("rb") as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
        docker("rm","-f",self.name)
        docker("image","rm",self.image)
        assert docker("image","inspect",self.image_id,check=False)!=0
        docker("load","-i",archive)
        assert docker("image","inspect","--format","{{.Id}}",self.image)==self.image_id
        self.launch()
        self.roundtrip={"local_oci_id":self.image_id,"archive_sha256":digest,
            "removed_image_id_then_reloaded":True,"archive_bytes":archive.stat().st_size,
            "archive_roundtrip_seconds":round(time.monotonic()-start,3)}
        archive.unlink()

    def close(self):
        if self.relay:
            self.relay.shutdown()
            self.relay.server_close()
        docker("rm","-f",self.name,check=False)
        if self.pg:
            docker("network","disconnect","-f",self.network,self.pg,check=False)
            self.pg=None
        docker("network","rm",self.network,check=False)
        sudo("rm","-rf",self.secrets)


# The Web test image keeps the existing CI-only localhost-origin checks.
# A byte-only TCP relay connects them to the actual private network, never
# terminates mTLS, rewrites headers, or fabricates responses.
WEB_RELAY = """
import net from 'node:net';
import {spawn} from 'node:child_process';
const ports=[
 [Number(process.env.F3_LAB_PRODUCT_PORT),'f3-api',8443],
 [Number(process.env.F3_LAB_BOOTSTRAP_PORT),process.env.F3_LAB_BRIDGE_GATEWAY,Number(process.env.F3_LAB_BOOTSTRAP_PORT)]
];
const servers=[];
for(const [port,host,target] of ports){
 const s=net.createServer(client=>{
  const upstream=net.connect(target,host);
  client.on('error',()=>upstream.destroy());
  upstream.on('error',()=>client.destroy());
  client.pipe(upstream); upstream.pipe(client);
 });
 await new Promise((ok,fail)=>{s.once('error',fail);s.listen(port,'127.0.0.1',ok);});
 servers.push(s);
}
const child=spawn('./node_modules/.bin/next',['start','-H','0.0.0.0','-p','3000'],{stdio:'inherit'});
for(const sig of ['SIGTERM','SIGINT'])process.on(sig,()=>{child.kill(sig);for(const s of servers)s.close();});
child.on('exit',code=>process.exit(code??1));
"""

class WebImageLab:
    def __init__(self,api,root,env,shared,bootstrap_port,product_port):
        assert os.getenv("F3_BROWSER_WEB_IMAGE")=="1" and api is not None
        self.api=api
        self.root=root
        self.shared=shared
        self.image=os.environ["F3_WEB_IMAGE_TAG"]
        self.name=api.name.replace("signed-api","web")
        self.image_id=docker("image","inspect","--format","{{.Id}}",self.image)
        assert docker("image","inspect","--format",'{{index .Config.Labels "org.opencontainers.image.revision"}}',self.image)==os.environ["GITHUB_SHA"]
        assert docker("image","inspect","--format","{{.Config.User}}",self.image)=="11003:11003"
        self.secret_dir=root/"web-container-secrets"
        self.secret_dir.mkdir(mode=0o700)
        self.env_file=root/"web-container.env"
        self.boot_relay=None
        self.web_relay=None
        self.roundtrip=None
        # BFF-only keys, no API server key or privileged database DSN.
        values={k:v for k,v in env.items() if k.startswith("AUTH_CI_") and k not in
                {"AUTH_CI_TLS_CERT","AUTH_CI_TLS_KEY"}}
        for field in ("AUTH_CI_BOOTSTRAP_SIGN_KEY","AUTH_CI_BOOTSTRAP_CA",
                "AUTH_CI_BOOTSTRAP_CERT","AUTH_CI_BOOTSTRAP_KEY","AUTH_CI_PRODUCT_SIGN_KEY"):
            filename=field.lower()
            shutil.copyfile(values[field],self.secret_dir/filename)
            values[field]="/tmp/f3-ci-web/"+filename
        (self.secret_dir/"relay.mjs").write_text(WEB_RELAY)
        for p in self.secret_dir.iterdir():p.chmod(0o600)
        sudo("chown","-R","11003:11003",self.secret_dir,self.shared)
        gateway=docker("network","inspect","--format","{{(index .IPAM.Config 0).Gateway}}",api.network)
        assert gateway and gateway!="127.0.0.1"
        values.update(CI="true",PHASE3_APP_MODE="APP_ONLY",AUTH_CI_SHARED_STORE_DIR="/tmp/f3-aliases",
            F3_LAB_PRODUCT_PORT=str(product_port),F3_LAB_BOOTSTRAP_PORT=str(bootstrap_port),
            F3_LAB_BRIDGE_GATEWAY=gateway)
        assert all("\n" not in v and "\r" not in v for v in values.values())
        self.env_file.write_text("".join(k+"="+v+"\n" for k,v in sorted(values.items())))
        self.env_file.chmod(0o600)
        try:
            self.boot_relay=Relay((gateway,bootstrap_port),Handler)
            self.boot_relay.target="127.0.0.1"
            self.boot_relay.target_port=bootstrap_port
            threading.Thread(target=self.boot_relay.serve_forever,daemon=True).start()
            self.launch()
            self.transport_preflight()
            self.web_relay=Relay(("127.0.0.1",3000),Handler)
            self.web_relay.target=self.ip
            self.web_relay.target_port=3000
            threading.Thread(target=self.web_relay.serve_forever,daemon=True).start()
        except BaseException:
            self.close()
            raise

    def launch(self):
        docker("run","-d","--init","--name",self.name,"--network",self.api.network,
            "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
            "--pids-limit","128","--memory","768m","--cpus","1.0",
            "--tmpfs","/tmp:rw,nosuid,size=32m,uid=11003,gid=11003",
            "--tmpfs","/srv/release/apps/web/.next/cache:rw,nosuid,size=64m,uid=11003,gid=11003",
            "--env-file",self.env_file,
            "--mount","type=bind,src="+str(self.secret_dir)+",dst=/tmp/f3-ci-web,readonly",
            "--mount","type=bind,src="+str(self.shared)+",dst=/tmp/f3-aliases",
            self.image_id,"node","/tmp/f3-ci-web/relay.mjs")
        assert docker("inspect","--format","{{.Image}}",self.name)==self.image_id
        assert docker("inspect","--format","{{.Config.User}}",self.name)=="11003:11003"
        assert docker("inspect","--format","{{.HostConfig.ReadonlyRootfs}}",self.name)=="true"
        assert not json.loads(docker("inspect","--format","{{json .HostConfig.PortBindings}}",self.name))
        mounts=json.loads(docker("inspect","--format","{{json .Mounts}}",self.name))
        binds=[m for m in mounts if m["Type"]=="bind"]
        assert {m["Destination"]:m["RW"] for m in binds}=={"/tmp/f3-ci-web":False,"/tmp/f3-aliases":True}
        self.ip=docker("inspect","--format","{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",self.name)
        assert self.ip
        if self.web_relay:self.web_relay.target=self.ip

    def transport_preflight(self):
        # Run from the actual nonroot Web namespace, with the exact files
        # the existing server-side CI guards accept. Never print their bytes.
        script = """
const fs=require('node:fs'),https=require('node:https'),assert=require('node:assert/strict');
const files=['AUTH_CI_BOOTSTRAP_SIGN_KEY','AUTH_CI_PRODUCT_SIGN_KEY',
'AUTH_CI_BOOTSTRAP_CA','AUTH_CI_BOOTSTRAP_CERT','AUTH_CI_BOOTSTRAP_KEY'];
for(const name of files){
 const p=process.env[name],st=fs.statSync(p);
 assert(p.startsWith('/tmp/')&&!p.includes('..'));
 assert.equal(st.uid,process.getuid());assert.equal(st.mode&0o777,0o600);
 assert(fs.readFileSync(p).length>0);
}
const ca=fs.readFileSync(process.env.AUTH_CI_BOOTSTRAP_CA);
const cert=fs.readFileSync(process.env.AUTH_CI_BOOTSTRAP_CERT);
const key=fs.readFileSync(process.env.AUTH_CI_BOOTSTRAP_KEY);
function get(origin,path,withCert){
 return new Promise((resolve,reject)=>{
 const req=https.get(origin+path,{ca,...(withCert?{cert,key}:{}),rejectUnauthorized:true,agent:false},res=>{
  res.resume();res.on('end',()=>resolve(res.statusCode));});
 req.setTimeout(5000,()=>req.destroy(new Error('timeout')));req.on('error',reject);
 });
}
(async()=>{
 assert.equal(await get(process.env.AUTH_CI_BOOTSTRAP_ORIGIN,'/__fixture_health',true),200);
 assert.equal(await get(process.env.AUTH_CI_PRODUCT_ORIGIN,'/internal/ready',true),200);
 await assert.rejects(get(process.env.AUTH_CI_PRODUCT_ORIGIN,'/internal/ready',false));
 console.log('F3_WEB_CONTAINER_MTLS_BOTH_UPSTREAMS_AND_SECRET_MODES_PASS');
})().catch(()=>process.exit(1));
"""
        for _ in range(25):
            try:
                assert docker("exec",self.name,"node","-e",script)=="F3_WEB_CONTAINER_MTLS_BOTH_UPSTREAMS_AND_SECRET_MODES_PASS"
                print("F3_WEB_CONTAINER_MTLS_BOTH_UPSTREAMS_AND_SECRET_MODES_PASS",flush=True)
                return
            except RuntimeError:
                time.sleep(.5)
        raise AssertionError("WEB_CONTAINER_MTLS_OR_SECRET_PREFLIGHT_FAILED")

    def read_alias(self,name):
        assert name.startswith("alias-") and name.endswith(".json") and "/" not in name
        return subprocess.check_output(["sudo","cat",str(self.shared/name)],text=True,timeout=5)

    def reload(self):
        archive=self.root/"web-image.tar"
        start=time.monotonic()
        docker("save","-o",archive,self.image)
        with archive.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        docker("rm","-f",self.name)
        docker("image","rm",self.image)
        assert docker("image","inspect",self.image_id,check=False)!=0
        docker("load","-i",archive)
        assert docker("image","inspect","--format","{{.Id}}",self.image)==self.image_id
        self.launch()
        self.transport_preflight()
        self.roundtrip={"local_oci_id":self.image_id,"archive_sha256":digest,
            "removed_image_id_then_reloaded":True,"archive_bytes":archive.stat().st_size,
            "archive_roundtrip_seconds":round(time.monotonic()-start,3)}
        archive.unlink()

    def close(self):
        for relay in (self.web_relay,self.boot_relay):
            if relay:
                relay.shutdown()
                relay.server_close()
        docker("rm","-f",self.name,check=False)
        sudo("rm","-rf",self.secret_dir,self.shared)
        self.env_file.unlink(missing_ok=True)
