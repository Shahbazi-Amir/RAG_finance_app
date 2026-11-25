"""Disposable DB-only historical fixture. Never a reachable POST admission path.
Exercise the original repository with restricted TLS role, then let the
unchanged APP_ONLY listener read persisted correlation via signed HTTP GET.
No dispatch, T3, engine, or user-data access.
"""
import concurrent.futures
import json
import threading
import uuid
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from src.phase3.storage.postgres.repository import (
    send_t1, start_t2, mark_attempt, Conflict, InjectedRollback,
)

cfg=json.loads(Path("/run/secrets/phase3-app-only.json").read_text())
dsn=cfg["history_dsn"]
owner="signed-owner-b"
payload={"kind":"send_message_request","contract_version":"product.v1",
         "requested_conversation_id":None,"client_message_id":"m10-historical-client",
         "idempotency_key":"m10-historical-key-001","question":"Disposable historical replay fixture"}
def connect():
    return psycopg.connect(dsn,row_factory=dict_row,autocommit=True)
def rid():
    return uuid.uuid4().hex
def send(p=payload,**kw):
    with connect() as c:
        return send_t1(c,owner,p,rid(),rid(),**kw)
def denied(fn,exc):
    try:
        fn()
    except exc:
        return
    raise AssertionError("expected-denial")
def main():
    denied(lambda:send({**payload,"client_message_id":"m10-rollback-client",
                         "idempotency_key":"m10-rollback-key-001"},rollback=True),InjectedRollback)
    barrier=threading.Barrier(2)
    def race():
        barrier.wait(timeout=10)
        return send()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(race);b=pool.submit(race)
        result=[a.result(timeout=20),b.result(timeout=20)]
    assert sorted(r["disposition"] for r in result)==["created","replayed"]
    assert len({r["message_id"] for r in result})==1
    assert len({r["resolved_conversation_id"] for r in result})==1
    denied(lambda:send({**payload,"question":"changed"}),Conflict)
    replay=send()
    assert replay["disposition"]=="replayed"
    assert replay["message_id"]==result[0]["message_id"]
    with connect() as c:
        args=(c,owner,None,payload["client_message_id"],payload["idempotency_key"])
        t=start_t2(*args,rid(),rid())
        t2=start_t2(*args,rid(),rid())
        assert t["id"]==t2["id"] and t["attempt_request_id"]==t2["attempt_request_id"]
        assert t["attempt_trace_id"]==t2["attempt_trace_id"]
        mark_attempt(c,owner,t["id"],"attempt_unknown")
    print("M10_REAL_REPOSITORY_T1_CONCURRENT_REPLAY_CONFLICT_ROLLBACK_T2_UNKNOWN_PASS")
if __name__=="__main__":
    main()
