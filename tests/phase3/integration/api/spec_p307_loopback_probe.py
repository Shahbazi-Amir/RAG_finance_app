"""Read-only loopback smoke and bounded Next.js capability timing. Run from repo root."""
import concurrent.futures as cf
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import socket
import statistics
import subprocess
import threading
import time

class Redirect(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()
    def log_message(self,*args):
        pass

with ThreadingHTTPServer(("127.0.0.1",0),Redirect) as redirect:
    worker=threading.Thread(target=redirect.serve_forever)
    worker.start()
    try:
        url=f"http://127.0.0.1:{redirect.server_port}/"
        old=subprocess.run(["curl","-qfsS",url],capture_output=True)
        script=Path("infra/arvan-staging/deploy-arvan.sh").read_text()
        helper=re.search(r"^expect_status\(\) \{.*?^\}",script,re.M|re.S)[0]
        shell='fail() { printf "%s\\n" "$1" >&2; exit 1; }\n'+helper
        new=subprocess.run(["bash","-c",shell+'\nexpect_status 200 "$1"','fixture',url],capture_output=True,text=True)
        assert old.returncode==0 and new.returncode==1 and "received 302" in new.stderr
        print("Redirect regression: legacy curl exit=0, exact-status helper exit=1 (302)",flush=True)
        discovery=script[script.index("discovery=$(curl"):script.index("blocked=(/internal/")]
        discovery=discovery.replace("https://ragfinance.ir/realms/finance-staging/.well-known/openid-configuration",url)
        readback=subprocess.run(["bash","-c",shell+"\n"+discovery],capture_output=True,text=True)
        assert readback.returncode==1 and "discovery status" in readback.stderr
        print("Discovery fixture: reject 302 before inspecting JSON",flush=True)
    finally:
        redirect.shutdown()
        worker.join()

if any(Path("apps/web").glob(".env*")):
    raise RuntimeError("Use a Web checkout without local environment files")

with socket.socket() as reserve:
    reserve.bind(("127.0.0.1",0))
    port=reserve.getsockname()[1]
env={"PATH":os.environ["PATH"],"PHASE3_APP_MODE":"APP_ONLY","NEXT_TELEMETRY_DISABLED":"1"}
next_process=subprocess.Popen(["node","apps/web/node_modules/next/dist/bin/next","start","apps/web","-H","127.0.0.1","-p",str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
path="/api/product-capabilities"
def get(endpoint):
    start=time.perf_counter()
    conn=HTTPConnection("127.0.0.1",port,timeout=5)
    try:
        conn.request("GET",endpoint)
        response=conn.getresponse()
        raw=response.read(8193)
        elapsed=(time.perf_counter()-start)*1000
        assert len(raw)<=8192
        return response.status,response.getheader("Cache-Control"),json.loads(raw),elapsed
    finally:
        conn.close()
try:
    for _ in range(75):
        if next_process.poll() is not None: raise RuntimeError("Next exited")
        try:
            code,*_=get(path)
            if code==200: break
        except OSError: pass
        time.sleep(.1)
    else: raise RuntimeError("Next did not become ready")
    checked=subprocess.run(["bash","-c",shell+'\nexpect_status 200 "$1"',"fixture",f"http://127.0.0.1:{port}{path}"],capture_output=True)
    assert checked.returncode==0
    print("Exact-status helper: accepted loopback 200",flush=True)
    expected={"kind":"ui_runtime_capabilities","contract_version":"ui.runtime_capabilities.v1",
              "send_mode":"DISABLED","engine_available":False,"generation_available":False}
    for width in (1,2,4):
        samples=[]
        wall=time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=width) as pool:
            for _ in range(3):
                barrier=threading.Barrier(width)
                def call():
                    barrier.wait(timeout=5)
                    return get(path)
                futures=[pool.submit(call) for _ in range(width)]
                for future in futures:
                    code,cache,body,ms=future.result()
                    assert code==200 and cache=="no-store" and body==expected
                    samples.append(ms)
        elapsed=time.perf_counter()-wall
        print(f"width={width} requests={len(samples)} status200={len(samples)} p50_ms={statistics.median(samples):.2f} max_ms={max(samples):.2f} wall_ms={elapsed*1000:.2f}",flush=True)
    code,cache,_,_=get("/api/history/conversations?limit=2")
    assert code==503 and cache=="no-store"
    print("Unauthenticated History GET: status=503, cache=no-store",flush=True)
finally:
    if next_process.poll() is None:
        next_process.terminate()
        try: next_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            next_process.kill()
            next_process.wait()
