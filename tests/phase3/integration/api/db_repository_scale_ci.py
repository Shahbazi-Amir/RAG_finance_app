"""CI-only bounded synthetic load: actual repository over restricted TLS PG.

Runs in the already-owned fresh preflight volume, before any browser login.
It is not an OIDC, HTTP latency, representative workload, or approved SLO test.
No production rows, engine, schema changes or grant changes.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from src.phase3.storage.postgres import repository

ROOT=Path(__file__).resolve().parents[4]
OWNERS=("scale-ci-a","scale-ci-b")
N=6000
HOT=604
LIMIT=100
SESSIONS=8
REPO_BLOB="14f97dd680425b74f8e12fa1696d423a20bf7d76"

def require(ok,code):
    if not ok:
        raise RuntimeError(code)

def fence(demo,dsns,pg_id):
    require(os.environ.get("CI")==os.environ.get("GITHUB_ACTIONS")=="true","SCALE_CI_ONLY")
    require(re.fullmatch(r"[0-9]+",os.environ["GITHUB_RUN_ID"]),"RUN_ID")
    require(re.fullmatch(r"[a-f0-9]{64}",pg_id),"EXACT_PG_ID")
    require(not pg_id.startswith(os.environ["API_F3_ISOLATED_PG_CID"]),"INSTALLER_FORBIDDEN")
    demo.assert_restore_pg_binding(pg_id)
    info=json.loads(demo.ci_command("docker","inspect",pg_id))[0]
    require(info["Id"]==pg_id and info["State"]["Running"],"OWNED_PG_REQUIRED")
    require(re.fullmatch(r"[a-f0-9]{32}",info["Config"]["Labels"]["rag.finance.ci.restore"]),"RESTORE_LABEL")
    opts={k:conninfo_to_dict(dsns[k]) for k in ("DB_APP_DSN","DB_MIG_DSN")}
    for key,role in (("DB_APP_DSN","history_app"),("DB_MIG_DSN","history_migrator")):
        x=opts[key]
        require(x["host"]=="127.0.0.1" and int(x["port"])==demo.restore_pg_port and int(x["port"])!=5432,"PG_PORT_FENCE")
        require(re.fullmatch(r"history_browser_restore_ci_[a-f0-9]{16}",x["dbname"]),"DB_NAME_FENCE")
        require(x["dbname"]==opts["DB_APP_DSN"]["dbname"] and x["user"]==role and x["sslmode"]=="verify-full","TLS_ROLE_FENCE")
    require(subprocess.check_output(["git","hash-object",str(ROOT/"src/phase3/storage/postgres/repository.py")],text=True).strip()==REPO_BLOB,"REPOSITORY_BLOB_DRIFT")
    require(subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==os.environ["F3_EXACT_SHA"],"SHA_DRIFT")

def seed(demo,dsns,pg_id):
    fence(demo,dsns,pg_id)
    with psycopg.connect(dsns["DB_MIG_DSN"],autocommit=True) as c:
        require(c.execute("SELECT current_user,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())").fetchone()==("history_migrator",True),"SEED_ROLE_TLS")
        with c.transaction():
            require(c.execute("SELECT count(*) FROM history_l1.conversations WHERE owner_id=ANY(%s)",(list(OWNERS),)).fetchone()[0]==0,"FIXTURE_COLLISION")
            for owner in OWNERS:
                c.execute("""INSERT INTO history_l1.conversations(owner_id,id,title,created_at,updated_at)
                  SELECT %s, %s||'-c-'||lpad(i::text,5,'0'),'synthetic scale',
                  '2026-01-01T00:00:00Z'::timestamptz+((i-1)/3)*interval '1 second',
                  '2026-01-01T00:00:00Z'::timestamptz+((i-1)/3)*interval '1 second'
                  FROM generate_series(1,%s) i""",(owner,owner,N))
                c.execute("""INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
                  SELECT %s,%s||'-m-'||lpad(i::text,5,'0')||'-'||lpad(j::text,3,'0'),
                    %s||'-c-'||lpad(i::text,5,'0'),'user','synthetic no PII',
                    '2026-01-01T00:00:00Z'::timestamptz+((j-1)/3)*interval '1 second'
                  FROM generate_series(1,%s) i CROSS JOIN generate_series(1,4) j""",(owner,owner,owner,N))
                c.execute("""INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
                  SELECT %s,%s||'-m-00001-'||lpad(j::text,3,'0'),%s||'-c-00001','user',
                    'synthetic no PII','2026-01-01T00:00:00Z'::timestamptz+((j-1)/3)*interval '1 second'
                  FROM generate_series(5,%s) j""",(owner,owner,owner,HOT))
            require(c.execute("SELECT count(*) FROM history_l1.conversations WHERE owner_id=ANY(%s)",(list(OWNERS),)).fetchone()[0]==N*2,"SEED_CONVERSATIONS")
            require(c.execute("SELECT count(*) FROM history_l1.messages WHERE owner_id=ANY(%s)",(list(OWNERS),)).fetchone()[0]==(N*4+HOT-4)*2,"SEED_MESSAGES")
        c.execute("ANALYZE history_l1.conversations")
        c.execute("ANALYZE history_l1.messages")
        c.execute("ANALYZE history_l1.answers")
    print("DB_SCALE_12000_CONVERSATIONS_49200_MESSAGES_SEEDED_OWNED_TLS_CLONE=PASS",flush=True)

def connect(dsn):
    c=psycopg.connect(dsn,autocommit=True,row_factory=dict_row)
    c.execute("SET statement_timeout='10s'")
    c.execute("SET default_transaction_read_only=on")
    flags=c.execute("""SELECT current_user AS role,rolsuper,rolbypassrls,rolinherit,
      rolcreaterole,rolcreatedb,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS tls
      FROM pg_roles WHERE rolname=current_user""").fetchone()
    require(flags=={"role":"history_app","rolsuper":False,"rolbypassrls":False,"rolinherit":False,
                    "rolcreaterole":False,"rolcreatedb":False,"tls":True},"RESTRICTED_TLS_LOGIN")
    return c

def assert_unset(c):
    for table in ("conversations","messages","create_receipts","send_receipts","execution_attempts","answers"):
        # Identifier is a fixed in-tree allowlist; no user-controlled SQL.
        require(c.execute("SELECT count(*) AS n FROM history_l1."+table).fetchone()["n"]==0,"TX_OWNER_LEAK")

def indexes(plan):
    result=[]
    if plan.get("Index Name"):
        result.append(plan["Index Name"])
    for child in plan.get("Plans",[]):
        result.extend(indexes(child))
    return sorted(set(result))

def plans(dsn):
    with connect(dsn) as c:
        owner=OWNERS[0]
        with c.transaction():
            c.execute("SET TRANSACTION READ ONLY")
            repository.scoped(c,owner)
            # Exact repository query shape, including detail's Answer join
            # and keyset bounds. No enable_seqscan override.
            maxkey=c.execute("""SELECT created_at,id FROM history_l1.conversations
                  WHERE owner_id=%s AND state='active' ORDER BY created_at DESC,id DESC LIMIT 1""",(owner,)).fetchone()
            hot=owner+"-c-00001"
            msgmax=c.execute("""SELECT created_at,id FROM history_l1.messages WHERE owner_id=%s
                    AND conversation_id=%s ORDER BY created_at DESC,id DESC LIMIT 1""",(owner,hot)).fetchone()
            queries={
              "conversations":("""EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT * FROM history_l1.conversations
                   WHERE owner_id=%s AND state='active' AND (created_at,id)<=(%s,%s)
                   ORDER BY created_at DESC,id DESC LIMIT %s""",(owner,maxkey["created_at"],maxkey["id"],LIMIT+1)),
              "messages":("""EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT m.*,ans.payload AS answer_payload
                   FROM history_l1.messages m LEFT JOIN history_l1.answers ans
                   ON ans.owner_id=m.owner_id AND ans.id=m.answer_id AND ans.message_id=m.id
                   WHERE m.owner_id=%s AND m.conversation_id=%s AND (m.created_at,m.id)<=(%s,%s)
                   ORDER BY m.created_at ASC,m.id ASC LIMIT %s""",(owner,hot,msgmax["created_at"],msgmax["id"],LIMIT+1))}
            out={}
            for name,(query,params) in queries.items():
                val=next(iter(c.execute(query,params).fetchone().values()))[0]
                require(val["Plan"]["Actual Rows"]==LIMIT+1,"PLAN_ROW_COUNT")
                used=indexes(val["Plan"])
                require(("conversation_order_idx" if name=="conversations" else "message_order_idx") in used,"NATURAL_ORDER_INDEX_NOT_USED_"+name)
                out[name]={"actual_rows":val["Plan"]["Actual Rows"],"indexes":used,
                           "execution_ms":val["Execution Time"],"shared_hit_blocks":val["Plan"].get("Shared Hit Blocks",0)}
        assert_unset(c)
        return out

def observe(demo,dsns,pg_id,phase):
    require(phase in ("BEFORE_RESTART","AFTER_RESTART"),"PHASE")
    fence(demo,dsns,pg_id)
    dsn=dsns["DB_APP_DSN"]
    barrier=threading.Barrier(SESSIONS,timeout=20)
    def read(index):
        owner=OWNERS[index%2]
        foreign=OWNERS[1-index%2]
        hot=owner+"-c-00001"
        latencies=[]
        def timed(fn,*args,**kwargs):
            start=time.perf_counter_ns()
            result=fn(*args,**kwargs)
            latencies.append((time.perf_counter_ns()-start)/1e6)
            return result
        with connect(dsn) as c:
            pid=c.execute("SELECT pg_backend_pid() AS pid").fetchone()["pid"]
            assert_unset(c)
            barrier.wait()
            convs=[]
            last=anchor=None
            for _ in range(math.ceil(N/LIMIT)):
                page=timed(repository.list_conversations,c,owner,limit=LIMIT,anchor=anchor,last=last)
                items=page["items"]
                require(items and all(x["owner_user_id"]==owner for x in items),"CONV_OWNER")
                if anchor is None:
                    anchor=(datetime.fromisoformat(items[0]["created_at"]),items[0]["conversation_id"])
                convs.extend(items)
                last=page["last"]
                require(page["has_more"]==(len(convs)<N),"CONV_HAS_MORE")
            require([x["conversation_id"] for x in convs]==[f"{owner}-c-{n:05d}" for n in range(N,0,-1)],"CONV_FULL_ORDER")
            assert_unset(c)
            with c.transaction():
                repository.scoped(c,owner)
                maxkey=c.execute("""SELECT created_at,id FROM history_l1.messages WHERE owner_id=%s AND conversation_id=%s
                  ORDER BY created_at DESC,id DESC LIMIT 1""",(owner,hot)).fetchone()
                require(c.execute("SELECT count(*) AS n FROM history_l1.messages WHERE owner_id=%s",(foreign,)).fetchone()["n"]==0,"FOREIGN_SQL_VISIBLE")
                require(c.execute("SELECT count(*) AS n FROM history_l1.messages").fetchone()["n"]==N*4+HOT-4,"OWNER_MSG_COUNT")
                for table in ("create_receipts","send_receipts","execution_attempts","answers"):
                    require(c.execute("SELECT count(*) AS n FROM history_l1."+table).fetchone()["n"]==0,"NONZERO_SIDE_EFFECT")
            anchor=(maxkey["created_at"],maxkey["id"])
            messages=[]
            last=None
            for _ in range(math.ceil(HOT/LIMIT)):
                page=timed(repository.list_messages,c,owner,hot,limit=LIMIT,anchor=anchor,last=last)
                require(page["answers"]==[] and all(x["owner_user_id"]==owner and x["conversation_id"]==hot for x in page["items"]),"MESSAGE_OWNER")
                messages.extend(page["items"])
                last=page["last"]
                require(page["has_more"]==(len(messages)<HOT),"MESSAGE_HAS_MORE")
            require([x["message_id"] for x in messages]==[f"{owner}-m-00001-{n:03d}" for n in range(1,HOT+1)],"MESSAGE_FULL_ORDER")
            for cid in (foreign+"-c-00001","scale-ci-nonexistent"):
                try:
                    repository.list_messages(c,owner,cid,limit=1)
                except repository.NotFound as exc:
                    require(str(exc)=="NOT_FOUND","ENUMERATION_ERROR_DRIFT")
                else:
                    raise AssertionError("FOREIGN_OR_UNKNOWN_DETAIL_ALLOWED")
            assert_unset(c)
            digest=hashlib.sha256(json.dumps([convs,messages],ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            return {"owner":owner,"pid":pid,"hash":digest,"latencies":latencies}
    with ThreadPoolExecutor(max_workers=SESSIONS) as pool:
        results=list(pool.map(read,range(SESSIONS)))
    require(len({r["pid"] for r in results})==SESSIONS,"DISTINCT_SESSIONS_REQUIRED")
    parity={}
    for owner in OWNERS:
        values={r["hash"] for r in results if r["owner"]==owner}
        require(len(values)==1,"CONCURRENT_ROW_PARITY")
        parity[owner]=values.pop()
    latency=sorted(x for r in results for x in r["latencies"])
    expected=SESSIONS*(math.ceil(N/LIMIT)+math.ceil(HOT/LIMIT))
    require(len(latency)==expected and min(latency)>0,"SAMPLE_COUNT")
    result={"phase":phase,"distinct_tls_logins":SESSIONS,"full_conversation_rows_per_session":N,
            "hot_message_rows_per_session":HOT,"repository_page_samples":len(latency),
            "p50_ms":round(latency[math.ceil(len(latency)*.5)-1],3),
            "p95_ms":round(latency[math.ceil(len(latency)*.95)-1],3),
            "row_parity":parity,"query_plans":plans(dsn),"foreign_and_unknown_denials":SESSIONS*2,
            "no_owner_after_transaction":True,"zero_send_attempt_answer":True}
    print("DB_SCALE_"+phase+"_EIGHT_TLS_LOGINS_FULL_KEYSET_NATURAL_INDEX_NO_LEAK=PASS",flush=True)
    return result

def receipt(before,after):
    require(before["row_parity"]==after["row_parity"],"RESTART_ROW_DRIFT")
    # Do not export per-owner row hashes or backend PIDs.
    for r in (before,after):
        del r["row_parity"]
    p=ROOT/"ci_receipts/db_repository_scale.json"
    p.parent.mkdir(exist_ok=True)
    with p.open("x",encoding="utf-8") as f:
        json.dump({"source_sha":os.environ["F3_EXACT_SHA"],"repository_blob":REPO_BLOB,
          "scope":"DISPOSABLE_PREFLIGHT_TLS_CLONE_REPOSITORY_ONLY","synthetic_conversations":N*2,
          "synthetic_messages":(N*4+HOT-4)*2,"before":before,"after":after,
          "exact_restart_parity":True,"approved_workload":False,"http_latency":False,
          "operational_slo_attested":False,"target_verified":False,"accepted":False,
          "engine_calls":0,"sql_011":False},f,indent=2)
        f.write("\n")
    print("DB_SCALE_RESTART_EXACT_PARITY_1072_REPOSITORY_PAGE_SAMPLES=PASS",flush=True)
