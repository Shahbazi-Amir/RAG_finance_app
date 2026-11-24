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
            with socket.create_connection((self.server.target,8443),timeout=5) as upstream:
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
        docker("run","-d","--name",self.name,"--network",self.network,
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
