"""Bounded operational measurements through actual authenticated browser BFF.

Only the disposable CI lab; no production SLO, capacity/retention policy,
engine metrics, deployment or human incident exercise is asserted.
"""
from __future__ import annotations
import asyncio
from collections import Counter
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

def summary(samples, seconds):
    assert samples and seconds>0
    values=sorted(x[1] for x in samples)
    counts=Counter(str(x[0]) for x in samples)
    def pct(p):return round(values[math.ceil(p*len(values))-1],3)
    return {"requests":len(samples),"status_counts":dict(counts),
            "duration_s":round(seconds,3),"requests_per_second":round(len(samples)/seconds,3),
            "http_5xx":sum(1 for x in samples if 500<=x[0]<600),
            "p50_ms":pct(.5),"p95_ms":pct(.95),"p99_ms":pct(.99),"max_ms":round(max(values),3)}

def resource_snapshot(names,connect):
    result={}
    for kind,name in names.items():
        raw=json.loads(subprocess.check_output(["docker","inspect",name],text=True))[0]
        host=raw["HostConfig"]
        assert raw["State"]["Running"]
        # No raw env, mounts, command, network addresses or container names.
        result[kind]={"memory_limit_bytes":host["Memory"],"nano_cpus":host["NanoCpus"],
                      "pids_limit":host["PidsLimit"],"oom_killed":raw["State"]["OOMKilled"]}
    # Docker stats returns only numeric percentages/PIDs here; no container id.
    rows=subprocess.check_output(["docker","stats","--no-stream","--format",
        "{{.CPUPerc}}|{{.MemPerc}}|{{.PIDs}}",*names.values()],text=True,timeout=20).splitlines()
    assert len(rows)==len(names)
    for kind,row in zip(names,rows):
        cpu,mem,pids=row.split("|")
        assert re.fullmatch(r"\d+(\.\d+)?%",cpu) and re.fullmatch(r"\d+(\.\d+)?%",mem)
        assert pids.isdigit()
        result[kind].update(cpu_pct=float(cpu[:-1]),memory_pct=float(mem[:-1]),pids=int(pids))
    with connect() as c:
        row=c.execute("SELECT count(*) FILTER (WHERE state='active'), count(*) FROM pg_stat_activity WHERE datname=current_database()").fetchone()
        max_conn=int(c.execute("SHOW max_connections").fetchone()[0])
    result["postgres"]={"active_connections_including_probe":row[0],"database_connections":row[1],
                        "max_connections":max_conn}
    return result

def phase4_negative(connect):
    # Design-only reservation from the canonical roadmap; no migration/table.
    reserved={"financial_profiles","financial_snapshots","assessments","scores","goals",
              "action_plans","risk_flags","human_referrals"}
    with connect() as c:
        names={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')")}
    assert not names.intersection(reserved),"PHASE4_TABLE_ACTIVATED"
    return {"reserved_names_checked":sorted(reserved),"active_reserved_tables":0}

async def error_trace(page,origin,cid):
    r=await page.request.get(origin+"/api/history/conversations/"+cid+"/messages?limit=20")
    assert r.status==404 and r.headers.get("cache-control")=="no-store"
    data=await r.json()
    assert data["kind"]=="error_response"
    req,trace=data["request_id"],data["trace_id"]
    assert isinstance(req,str) and isinstance(trace,str) and req and trace
    # Persist only fingerprints; no owner, question, path, raw trace or response.
    return {"status":404,"request_id_sha256":hashlib.sha256(req.encode()).hexdigest(),
            "trace_id_sha256":hashlib.sha256(trace.encode()).hexdigest()}

async def observe(demo,page_a,page_b,origin,ids_a,ids_b,connect):
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("CI")=="true"
    assert demo.image_lab and demo.web_lab
    names={"api":demo.image_lab.name,"web":demo.web_lab.name}
    pages=[(page_a,demo.owners["A"],ids_a),(page_b,demo.owners["B"],ids_b)]
    traces=[await error_trace(page_a,origin,sorted(ids_b)[0]),
            await error_trace(page_b,origin,sorted(ids_a)[0])]
    assert len({r["request_id_sha256"] for r in traces})==2
    assert len({r["trace_id_sha256"] for r in traces})==2
    async def one(index):
        page,owner,ids=pages[index%2]
        start=time.monotonic()
        resp=await page.request.get(origin+"/api/history/conversations?limit=2",timeout=15000)
        elapsed=(time.monotonic()-start)*1000
        assert resp.headers.get("cache-control")=="no-store"
        assert resp.status in (200,503),"UNEXPECTED_HISTORY_LOAD_STATUS"
        if resp.status==200:
            data=await resp.json()
            assert data["scope_user_id"]==owner
            actual=[x["conversation_id"] for x in data["items"]]
            assert len(actual)==len(set(actual)) and set(actual)<=ids
        else:
            body=await resp.text()
            assert owner not in body and "F3_REAL_POSTGRES_" not in body
        return resp.status,elapsed
    stages=[]
    for concurrency,rounds in ((1,4),(2,4),(4,4),(8,4),(2,12)):
        start=time.monotonic()
        sampler=asyncio.create_task(asyncio.to_thread(resource_snapshot,names,connect))
        samples=[]
        for _ in range(rounds):
            samples.extend(await asyncio.gather(*(one(i) for i in range(concurrency))))
            await asyncio.sleep(.15)
        snapshot=await sampler
        measured=summary(samples,time.monotonic()-start)
        assert measured["status_counts"].get("200",0)>0,"NO_SUCCESSFUL_HISTORY_AT_LAB_STAGE"
        stages.append({"concurrency":concurrency,"rounds":rounds,"measurement":measured,
                       "resource_sample":snapshot})
    return {"scope":"BOUNDED_CI_READ_ONLY_HISTORY_RAMP_AND_SHORT_SUSTAINED_SAMPLE",
            "stages":stages,"error_trace_fingerprints":traces,
            "phase4":phase4_negative(connect),"approved_slo":None,
            "approved_workload":False,"engine_metrics":None,"raw_payloads_retained":False}

async def outage_browser(page_a,page_b,origin):
    # Same authenticated browser contexts during actual PG stop. No fake cookie.
    records=[]
    for page in (page_a,page_b):
        r=await page.request.get(origin+"/api/history/conversations?limit=2",timeout=20000)
        assert r.status==503,"PG_OUTAGE_MUST_FAIL_CLOSED_AT_BFF"
        assert r.headers.get("cache-control")=="no-store"
        body=await r.text()
        assert "F3_REAL_POSTGRES_" not in body and "items" not in body
        records.append({"status":r.status,"private_no_store":True})
    return {"event":"dependency_unavailable","observations":records,"external_notification_sent":False}

def write_dashboard(receipt,path):
    # Offline operational view. Not an authenticated target/admin endpoint.
    rows=[]
    for stage in receipt["operational_probe"]["stages"]:
        m=stage["measurement"];r=stage["resource_sample"]
        rows.append([stage["concurrency"],m["requests"],m["status_counts"].get("200",0),
                     m["http_5xx"],m["p50_ms"],m["p95_ms"],m["p99_ms"],
                     r["api"]["cpu_pct"],r["web"]["cpu_pct"],r["postgres"]["database_connections"]])
    table="".join("<tr>"+"".join("<td>"+html.escape(str(x))+"</td>" for x in row)+"</tr>" for row in rows)
    headers="".join("<th>"+h+"</th>" for h in ("Concurrency","Requests","200","5xx","p50 ms","p95 ms","p99 ms","API CPU %","Web CPU %","PG connections"))
    page=("<!doctype html><html lang='en'><meta charset='utf-8'><title>F3 CI lab health</title>"
          "<style>body{font:16px system-ui;margin:2rem;color:#222}table{border-collapse:collapse}th,td{padding:.6rem;border:1px solid #aaa;text-align:right}</style>"
          "<h1>F3 app-only CI measurements</h1><p>Not target acceptance; no approved SLO or engine metrics.</p>"
          "<p>SHA "+html.escape(receipt["sha"])+"</p><p>Dependency readiness: 200 → 503 → 200; same browser sessions recovered.</p>"
          "<table><thead><tr>"+headers+"</tr></thead><tbody>"+table+"</tbody></table></html>")
    path.write_text(page,encoding="utf-8")
