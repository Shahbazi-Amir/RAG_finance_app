"""Actual direct Repository T1/T2 replay across owner and nullable scope.

Synthetic data in the owned PG preflight volume only, no signed HTTP Send,
dispatch, engine, T3, schema change, grant change or target admission.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
import threading
from pathlib import Path
import uuid

import psycopg
from psycopg.rows import dict_row
from src.phase3.storage.postgres import repository as repo
import db_repository_scale_ci as scale

OWNERS=("db-replay-ci-a","db-replay-ci-b")
EXPLICIT="same-explicit-ci-conversation"
GROUPS=tuple((owner,orig) for owner in OWNERS for orig in (None,EXPLICIT))
WORKERS=4
TABLES=("conversations","messages","create_receipts","send_receipts","execution_attempts","answers")
CLIENT="same_client_message_ci"
KEY="same_idempotency_ci_1234"
def require(ok,code):
    if not ok: raise RuntimeError(code)
def request(orig):
    return {"kind":"send_message_request","contract_version":"product.v1",
            "client_message_id":CLIENT,"question":"Synthetic CI replay only",
            "idempotency_key":KEY,"requested_conversation_id":orig}
def query(orig):
    return {"kind":"message_request_status_query","contract_version":"product.v1",
            "requested_conversation_id":orig,"client_message_id":CLIENT,"idempotency_key":KEY}
def ident():
    return uuid.uuid4().hex
def connect(dsn):
    c=psycopg.connect(dsn,autocommit=True,row_factory=dict_row)
    c.execute("SET statement_timeout='15s'")
    f=c.execute("""SELECT current_user AS role,rolsuper,rolbypassrls,rolinherit,
      rolcreaterole,rolcreatedb,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS tls
      FROM pg_roles WHERE rolname=current_user""").fetchone()
    require(f=={"role":"history_app","rolsuper":False,"rolbypassrls":False,"rolinherit":False,
      "rolcreaterole":False,"rolcreatedb":False,"tls":True},"REPLAY_RESTRICTED_TLS")
    return c
def expect(fn,exc,code):
    try:
        fn()
    except exc as error:
        require(str(error)==code,"ERROR_CODE_DRIFT")
    else:
        raise RuntimeError("REPLAY_EXPECTED_DENIAL_MISSING")
def snapshot(dsn):
    values={}
    for owner in OWNERS:
        with connect(dsn) as c:
            scale.assert_unset(c)
            with c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                repo.scoped(c,owner)
                counts={}
                hashes={}
                for table in TABLES:
                    row=c.execute("SELECT count(*) AS n,coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text AS rows FROM history_l1."+table+" t").fetchone()
                    counts[table]=row["n"]
                    hashes[table]=sha256(row["rows"].encode()).hexdigest()
                require(counts=={"conversations":2,"messages":2,"create_receipts":0,
                                "send_receipts":2,"execution_attempts":2,"answers":0},"REPLAY_ROW_COUNT_DRIFT")
                require(c.execute("SELECT count(*) AS n FROM history_l1.messages WHERE role='assistant'").fetchone()["n"]==0,"ASSISTANT_ROW_FORBIDDEN")
                values[owner]=hashes
            scale.assert_unset(c)
    return values
def race(dsn,phase):
    require(phase in ("INITIAL","AFTER_RESTART","AFTER_RESTORE"),"BAD_PHASE")
    t1_barrier=threading.Barrier(len(GROUPS)*WORKERS,timeout=30)
    t2_barrier=threading.Barrier(len(GROUPS)*WORKERS,timeout=30)
    def worker(group):
        owner,orig=group
        with connect(dsn) as c:
            pid=c.execute("SELECT pg_backend_pid() AS pid").fetchone()["pid"]
            scale.assert_unset(c)
            t1_barrier.wait()
            t1=repo.send_t1(c,owner,request(orig),ident(),ident())
            scale.assert_unset(c)
            t2_barrier.wait()
            t2=repo.start_t2(c,owner,orig,CLIENT,KEY,ident(),ident())
            status=repo.read_status(c,owner,query(orig),ident(),ident())
            require(t1["owner_user_id"]==status["owner_user_id"]==owner,"REPLAY_OWNER_DRIFT")
            require(t1["resolved_conversation_id"]==status["resolved_conversation_id"] and
                    t1["message_id"]==status["message_id"],"T1_STATUS_DRIFT")
            require(t2["id"]==status["attempt_id"] and t2["reserved_answer_id"]==status["reserved_answer_id"]
                    and t2["attempt_request_id"]==status["attempt_request_id"]
                    and t2["attempt_trace_id"]==status["attempt_trace_id"],"T2_STATUS_DRIFT")
            require(status["answer_id"] is None and status["answer"] is None,"REPLAY_ANSWER_FORBIDDEN")
            scale.assert_unset(c)
            return (group,pid,t1["disposition"],
                (t1["resolved_conversation_id"],t1["message_id"],t2["id"],t2["reserved_answer_id"],
                 t2["attempt_request_id"],t2["attempt_trace_id"],t2["send_receipt_id"],t1["payload_sha256"]),
                 status["status"])
    with ThreadPoolExecutor(max_workers=len(GROUPS)*WORKERS) as pool:
        results=list(pool.map(worker,[group for group in GROUPS for _ in range(WORKERS)]))
    require(len({r[1] for r in results})==16,"DISTINCT_TLS_SESSIONS")
    stable={}
    for group in GROUPS:
        rows=[r for r in results if r[0]==group]
        dispositions=[r[2] for r in rows]
        require(dispositions.count("created")==(1 if phase=="INITIAL" else 0)
            and dispositions.count("replayed")==(3 if phase=="INITIAL" else 4),"T1_DUPLICATE")
        keys={r[3] for r in rows}
        require(len(keys)==1,"T1_T2_STABLE_ID_DRIFT")
        stable[group]=keys.pop()
        states={r[4] for r in rows}
        expected="attempt_pending" if phase=="INITIAL" else ("cancelled" if group==(OWNERS[0],None) else "attempt_pending")
        require(states=={expected},"ATTEMPT_STATE_DRIFT")
    # The explicit conversation ID is deliberately shared between owners;
    # durable receipt, message, attempt and reserved-answer IDs must differ.
    for slot in (1,2,3,6):
        require(len({x[slot] for x in stable.values()})==4,"CROSS_SCOPE_ID_COLLISION")
    require(stable[(OWNERS[0],None)][0]!=stable[(OWNERS[1],None)][0],"NULL_SCOPE_OWNER_COLLISION")
    for owner in OWNERS:
        require(stable[(owner,EXPLICIT)][0]==EXPLICIT,"EXPLICIT_SCOPE_DRIFT")
    print("DB_IDEMPOTENCY_"+phase+"_16_TLS_SESSIONS_FOUR_OWNER_NULL_EXPLICIT_SCOPES=PASS",flush=True)
    return stable
def initial(demo,dsns,pg_id):
    scale.fence(demo,dsns,pg_id)
    dsn=dsns["DB_APP_DSN"]
    for owner in OWNERS:
        with connect(dsn) as c:
            scale.assert_unset(c)
            with c.transaction():
                repo.scoped(c,owner)
                require(c.execute("SELECT count(*) AS n FROM history_l1.conversations").fetchone()["n"]==0,"FIXTURE_COLLISION")
                c.execute("INSERT INTO history_l1.conversations(owner_id,id,title) VALUES(%s,%s,'Synthetic scope fixture')",(owner,EXPLICIT))
    stable=race(dsn,"INITIAL")
    # Same owner and key, different payload must fail with no writes.
    for owner,orig in GROUPS:
        with connect(dsn) as c:
            changed=request(orig);changed["question"]="Conflicting synthetic question"
            expect(lambda:repo.send_t1(c,owner,changed,ident(),ident()),repo.Conflict,"IDEMPOTENCY_CONFLICT")
            other=OWNERS[1-OWNERS.index(owner)]
            foreign=stable[(other,None)][0]
            expect(lambda:repo.read_status(c,owner,query(foreign),ident(),ident()),repo.NotFound,"NOT_FOUND")
            expect(lambda:repo.read_status(c,owner,query("nonexistent-ci-scope"),ident(),ident()),repo.NotFound,"NOT_FOUND")
            scale.assert_unset(c)
    owner=OWNERS[0]
    attempt=stable[(owner,None)][2]
    with connect(dsn) as c:
        require(repo.mark_attempt(c,owner,attempt,"attempt_unknown")["id"]==attempt,"UNKNOWN_ID_DRIFT")
        require(repo.mark_attempt(c,owner,attempt,"cancelled")["state"]=="cancelled","CANCEL_STATE_DRIFT")
        expect(lambda:repo.mark_attempt(c,owner,attempt,"attempt_unknown"),repo.Conflict,"TERMINAL_ATTEMPT")
        scale.assert_unset(c)
    baseline=snapshot(dsn)
    print("DB_IDEMPOTENCY_CONFLICT_FOREIGN_UNKNOWN_TERMINAL_DENIAL_ZERO_ANSWER=PASS",flush=True)
    return (stable,baseline)
def prove_independent_restore(source, dsns, pg_id, before):
    """Replay committed synthetic T1/T2 on a new logical PG cluster.

    Use the existing owned-volume clone code and a distinct demo/TLS root.
    No HTTP Send, engine or mutation of the source fixture during restore.
    """
    import sys
    sys.path.insert(0, str(scale.ROOT/"tests/phase3/integration/foundation"))
    from db_common_compose_restored_browser import BothSidesComposeBrowserDemo
    scale.fence(source, dsns, pg_id)
    info=json.loads(source.ci_command("docker","inspect",pg_id))[0]
    require(info["Id"]==pg_id and len(info["NetworkSettings"]["Networks"])==1,
            "REPLAY_RESTORE_SOURCE_NETWORK")
    volumes=[m["Name"] for m in info["Mounts"] if m["Destination"]=="/var/lib/postgresql/data"]
    require(len(volumes)==1,"REPLAY_RESTORE_SOURCE_VOLUME")
    def system_id(demo,cid):
        value=demo.ci_command("docker","exec",cid,"psql","-X","-At","-U","postgres",
            "-d","postgres","-c","SELECT system_identifier FROM pg_control_system()").decode().strip()
        require(value.isdecimal(),"REPLAY_CLUSTER_ID")
        return value
    source_id=system_id(source,pg_id)
    source_dsn=dsns["DB_APP_DSN"]
    require(snapshot(source_dsn)==before[1],"REPLAY_SOURCE_PRE_RESTORE_DRIFT")
    clone=BothSidesComposeBrowserDemo()
    try:
        clone.source_pg_id=pg_id
        clone.source_dsns=dsns
        clone.source_pg_port=source.restore_pg_port
        clone.source_pg_label=info["Config"]["Labels"]["rag.finance.ci.restore"]
        clone.source_network=next(iter(info["NetworkSettings"]["Networks"]))
        clone.source_volume=volumes[0]
        clone.source_pg_image=info["Image"]
        with clone.clone_owned_source() as (target,target_id,_):
            require(target_id!=pg_id and clone.restored_pg_volume!=volumes[0],
                    "REPLAY_RESTORE_NOT_INDEPENDENT")
            require(system_id(clone,target_id)!=source_id,"REPLAY_CLUSTER_ID_REUSED")
            target=clone.configure_restore_pg_tls(target_id,target)
            scale.fence(clone,target,target_id)
            dsn=target["DB_APP_DSN"]
            require(snapshot(dsn)==before[1],"RESTORE_BEFORE_REPLAY_DRIFT")
            require(race(dsn,"AFTER_RESTORE")==before[0],"RESTORE_T1_T2_ID_DRIFT")
            for owner,orig in GROUPS:
                with connect(dsn) as c:
                    changed=request(orig);changed["question"]="Conflicting synthetic question"
                    expect(lambda:repo.send_t1(c,owner,changed,ident(),ident()),repo.Conflict,"IDEMPOTENCY_CONFLICT")
                    other=OWNERS[1-OWNERS.index(owner)]
                    foreign=before[0][(other,None)][0]
                    expect(lambda:repo.read_status(c,owner,query(foreign),ident(),ident()),repo.NotFound,"NOT_FOUND")
                    expect(lambda:repo.read_status(c,owner,query("nonexistent-ci-scope"),ident(),ident()),repo.NotFound,"NOT_FOUND")
                    scale.assert_unset(c)
            with connect(dsn) as c:
                attempt=before[0][(OWNERS[0],None)][2]
                expect(lambda:repo.mark_attempt(c,OWNERS[0],attempt,"attempt_unknown"),
                       repo.Conflict,"TERMINAL_ATTEMPT")
                scale.assert_unset(c)
            require(snapshot(dsn)==before[1],"RESTORE_AFTER_REPLAY_MUTATION")
            require(snapshot(source_dsn)==before[1],"RESTORE_SOURCE_MUTATION")
    finally:
        clone.stop()
    print("DB_IDEMPOTENCY_INDEPENDENT_RESTORE_16_REPLAYS_ZERO_NEW_ROWS_TERMINAL_PRESERVED=PASS",flush=True)
    return {"independent_pg_cluster":True,"independent_volume":True,"distinct_tls_sessions":16,
            "created":0,"replayed":16,"owner_scope_groups":4,"conflicting_payload_denials":4,
            "foreign_unknown_status_denials":8,"exact_t1_t2_ids":True,"exact_six_table_hashes":True,
            "terminal_cancelled_not_reopened":True,"source_unchanged":True,"answer_rows":0,
            "http_send_executed":False,"engine_calls":0,"accepted":False,"target_verified":False}


def after_restart(demo,dsns,pg_id,before):
    scale.fence(demo,dsns,pg_id)
    dsn=dsns["DB_APP_DSN"]
    require(snapshot(dsn)==before[1],"RESTART_BASELINE_DRIFT")
    replay=race(dsn,"AFTER_RESTART")
    require(replay==before[0] and snapshot(dsn)==before[1],"POST_RESTART_REPLAY_MUTATION")
    restored=prove_independent_restore(demo,dsns,pg_id,before)
    path=scale.ROOT/"ci_receipts/db_idempotency_owner_scope.json"
    path.parent.mkdir(exist_ok=True)
    with path.open("x",encoding="utf-8") as f:
        json.dump({"source_sha":os.environ["F3_EXACT_SHA"],"repository_blob":scale.REPO_BLOB,
          "scope":"CI_DIRECT_REPOSITORY_SYNTHETIC_ONLY","distinct_tls_sessions_per_phase":16,
          "owner_scope_groups":4,"workers_per_group":4,"initial_created":4,"initial_replayed":12,
          "restart_created":0,"restart_replayed":16,"same_explicit_id_two_owners":True,
          "null_and_explicit_scopes_independent":True,"exact_t1_t2_ids_after_restart":True,
          "exact_six_table_hashes_after_restart":True,"independent_restore":restored,"conflicting_payload_denials":4,
          "foreign_unknown_status_denials":8,"cancelled_attempt_not_reopened":True,
          "answer_rows":0,"engine_calls":0,"http_send_executed":False,"sql_011":False,
          "accepted":False,"target_verified":False},f,indent=2)
        f.write("\n")
    print("DB_IDEMPOTENCY_RESTART_16_REPLAYS_ZERO_NEW_ROWS_TERMINAL_PRESERVED=PASS",flush=True)


def disconnect_and_terminal_race(demo,dsns,pg_id,phase):
    """Actual PostgreSQL client disconnect before outer COMMIT and retry.

    The Repository's nested transaction has returned; a separate TLS
    connection sees no durable result until the outer commit. No worker
    process, provider, HTTP Send or answer generation is executed.
    """
    require(phase in ("BEFORE_RESTART","AFTER_RESTART"),"DISCONNECT_PHASE")
    scale.fence(demo,dsns,pg_id)
    dsn=dsns["DB_APP_DSN"]
    owners=tuple("disconnect-ci-"+phase.lower()+"-"+x for x in ("a","b"))
    def counts(conn,owner):
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            repo.scoped(conn,owner)
            return tuple(conn.execute("SELECT count(*) AS n FROM history_l1."+table).fetchone()["n"] for table in TABLES)
    def one(owner,foreign):
        req=request(None);q=query(None)
        with connect(dsn) as observer:
            require(counts(observer,owner)==(0,0,0,0,0,0),"DISCONNECT_FIXTURE_COLLISION")
            writer=connect(dsn)
            try:
                writer.execute("BEGIN")
                first=repo.send_t1(writer,owner,req,ident(),ident())
                require(first["disposition"]=="created","T1_UNCOMMITTED_CREATE")
                require(counts(observer,owner)==(0,0,0,0,0,0),"T1_DIRTY_READ")
                expect(lambda:repo.read_status(observer,owner,q,ident(),ident()),repo.NotFound,"NOT_FOUND")
            finally:
                writer.close() # real disconnect with outer transaction open
            require(counts(observer,owner)==(0,0,0,0,0,0),"T1_DISCONNECT_DURABLE_ROWS")
            with connect(dsn) as committed:
                receipt=repo.send_t1(committed,owner,req,ident(),ident())
                require(receipt["disposition"]=="created","T1_RETRY_NOT_CREATED")
            require(receipt["message_id"]!=first["message_id"],"T1_ROLLED_BACK_ID_REUSED")
            require(counts(observer,owner)==(1,1,0,1,0,0),"T1_RETRY_ROWS")
            writer=connect(dsn)
            try:
                writer.execute("BEGIN")
                pending=repo.start_t2(writer,owner,None,CLIENT,KEY,ident(),ident())
                require(counts(observer,owner)==(1,1,0,1,0,0),"T2_DIRTY_READ")
                st=repo.read_status(observer,owner,q,ident(),ident())
                require(st["status"]=="persisted" and st["attempt_id"] is None,"T2_DIRTY_STATUS")
            finally:
                writer.close()
            require(counts(observer,owner)==(1,1,0,1,0,0),"T2_DISCONNECT_DURABLE_ROWS")
            with connect(dsn) as committed:
                attempt=repo.start_t2(committed,owner,None,CLIENT,KEY,ident(),ident())
                require(attempt["id"]!=pending["id"],"T2_ROLLED_BACK_ID_REUSED")
                require(repo.send_t1(committed,owner,req,ident(),ident())["disposition"]=="replayed","T1_POST_COMMIT_REPLAY")
            require(counts(observer,owner)==(1,1,0,1,1,0),"T2_RETRY_ROWS")
            expect(lambda:repo.mark_attempt(observer,foreign,attempt["id"],"cancelled"),repo.NotFound,"NOT_FOUND")
            # All contenders race for one terminal transition using separate
            # restricted TLS sessions. Both valid terminal choices are
            # permitted; the winning value is intentionally not prescribed.
            gate=threading.Barrier(4,timeout=15)
            def contend(index):
                with connect(dsn) as worker:
                    gate.wait()
                    try:
                        result=repo.mark_attempt(worker,owner,attempt["id"],"cancelled" if index%2 else "failed")
                        return ("committed",result["state"])
                    except repo.Conflict as exc:
                        require(str(exc)=="TERMINAL_ATTEMPT","TERMINAL_RACE_CODE")
                        return ("denied",None)
            with ThreadPoolExecutor(max_workers=4) as pool:
                outcomes=list(pool.map(contend,range(4)))
            wins=[x[1] for x in outcomes if x[0]=="committed"]
            require(len(wins)==1 and outcomes.count(("denied",None))==3,"TERMINAL_RACE_DUPLICATE")
            st=repo.read_status(observer,owner,q,ident(),ident())
            require(st["status"]==wins[0] and st["answer"] is None and st["attempt_id"]==attempt["id"],"TERMINAL_RACE_STATUS")
            require(repo.start_t2(observer,owner,None,CLIENT,KEY,ident(),ident())["id"]==attempt["id"],"TERMINAL_REPLAY_REOPENED")
            require(repo.read_status(observer,owner,q,ident(),ident())["status"]==wins[0],"TERMINAL_STATE_REOPENED")
            require(counts(observer,owner)==(1,1,0,1,1,0),"TERMINAL_RACE_ROWS")
            scale.assert_unset(observer)
    for i,owner in enumerate(owners):one(owner,owners[1-i])
    print("DB_IDEMPOTENCY_"+phase+"_AB_DISCONNECT_T1_T2_RETRY_TERMINAL_RACE=PASS",flush=True)
    return {"owners":2,"uncommitted_disconnects":4,"successful_retries":4,
            "terminal_race_sessions_per_owner":4,"terminal_winners":2,"terminal_conflicts":6,
            "foreign_terminal_denials":2,"uncommitted_rows_invisible":True,
            "zero_duplicate_rows":True,"terminal_replay_preserved":True,
            "answer_rows":0,"provider_cancellation_proven":False,"http_send_executed":False}
