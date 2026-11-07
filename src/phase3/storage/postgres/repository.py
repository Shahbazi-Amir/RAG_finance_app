"""Synthetic-only PostgreSQL History L1. No network, model, real authentication or HTTP.
Caller-supplied owner is trusted ONLY in the CI test harness. A production API must
authenticate its actor; never expose this repository directly to untrusted callers.
"""
from __future__ import annotations
import hashlib
import json
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SCHEMA_PATH = Path(__file__).resolve().parents[4] / "packages/contracts/product.v1.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

class NotFound(Exception):
    """Uniform inaccessible/missing owner-scoped resource; API should map to 404."""

class Conflict(Exception):
    """Stable scoped key with a different canonical payload."""

class IntegrityAnomaly(Exception):
    """Fail closed: damaged or legacy multiple-attempt state."""

class InjectedRollback(Exception):
    """Test-only injected transaction rollback; not a process crash."""

def uid():
    return uuid.uuid4().hex

def fingerprint(obj, fields):
    blob = json.dumps({k: obj[k] for k in fields}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf8")
    return hashlib.sha256(blob).hexdigest()

def check_wire(doc, kind):
    if doc.get("kind") != kind:
        raise ValueError("wrong document kind")
    VALIDATOR.validate(doc)

def scoped(conn, owner):
    if not isinstance(owner, str) or not owner:
        raise ValueError("owner is only injected by the trusted synthetic CI harness")
    conn.execute("SELECT set_config('app.owner_id', %s, true)", (owner,))

def lock_scope(conn, scope):
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (scope,))

def _conv(row):
    return dict(kind="conversation", contract_version="product.v1",
                conversation_id=row["id"], owner_user_id=row["owner_id"],
                title=row["title"], state=row["state"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat())

def _fetch_conversation(conn, owner, conversation_id, lock=False):
    query = ("SELECT * FROM history_l1.conversations WHERE owner_id=%s AND id=%s"
             + (" FOR SHARE" if lock else ""))
    row = conn.execute(query, (owner,conversation_id)).fetchone()
    if row is None or row["state"] != "active":
        raise NotFound("NOT_FOUND")
    return row

def create_conversation(conn, owner, request, request_id, trace_id, *, rollback=False):
    check_wire(request,"create_conversation_request")
    fp = fingerprint(request, ("client_conversation_id","title"))
    scope = json.dumps([owner,"create_conversation",request["client_conversation_id"],
                        request["idempotency_key"]],ensure_ascii=False)
    with conn.transaction():
        scoped(conn,owner)
        lock_scope(conn,scope)
        r = conn.execute("""SELECT * FROM history_l1.create_receipts
            WHERE owner_id=%s AND client_conversation_id=%s AND idempotency_key=%s""",
            (owner,request["client_conversation_id"],request["idempotency_key"])).fetchone()
        if r:
            if r["payload_sha256"] != fp:
                raise Conflict("IDEMPOTENCY_CONFLICT")
            # Read CURRENT authorized row before releasing immutable original title.
            _fetch_conversation(conn,owner,r["conversation_id"],lock=True)
            return dict(kind="create_conversation_receipt",contract_version="product.v1",
                        owner_user_id=owner,request_id=request_id,trace_id=trace_id,
                        client_conversation_id=request["client_conversation_id"],
                        idempotency_key=request["idempotency_key"],payload_sha256=fp,
                        disposition="replayed",conversation=r["created_snapshot"])
        cid = uid()
        row = conn.execute("""INSERT INTO history_l1.conversations(owner_id,id,title)
            VALUES(%s,%s,%s) RETURNING *""",(owner,cid,request["title"])).fetchone()
        snapshot = _conv(row)
        conn.execute("""INSERT INTO history_l1.create_receipts
          (owner_id,client_conversation_id,idempotency_key,payload_sha256,conversation_id,created_snapshot)
          VALUES(%s,%s,%s,%s,%s,%s)""",(owner,request["client_conversation_id"],
          request["idempotency_key"],fp,cid,Jsonb(snapshot)))
        if rollback:
            raise InjectedRollback("T_CREATE_BEFORE_COMMIT")
        return dict(kind="create_conversation_receipt",contract_version="product.v1",
                    owner_user_id=owner,request_id=request_id,trace_id=trace_id,
                    client_conversation_id=request["client_conversation_id"],
                    idempotency_key=request["idempotency_key"],payload_sha256=fp,
                    disposition="created",conversation=snapshot)

def send_t1(conn, owner, request, request_id, trace_id, *, rollback=False):
    check_wire(request,"send_message_request")
    orig = request["requested_conversation_id"]
    fp = fingerprint(request,("client_message_id","requested_conversation_id","question"))
    scope = json.dumps([owner,"send_message",orig,request["client_message_id"],
                        request["idempotency_key"]],ensure_ascii=False)
    with conn.transaction():
        scoped(conn,owner)
        lock_scope(conn,scope)
        r = conn.execute("""SELECT * FROM history_l1.send_receipts
          WHERE owner_id=%s AND requested_conversation_id IS NOT DISTINCT FROM %s
          AND client_message_id=%s AND idempotency_key=%s""",
          (owner,orig,request["client_message_id"],request["idempotency_key"])).fetchone()
        if r:
            if r["payload_sha256"] != fp:
                raise Conflict("IDEMPOTENCY_CONFLICT")
            _fetch_conversation(conn,owner,r["resolved_conversation_id"],lock=True)
            return _send_receipt(r,request_id,trace_id,"replayed")
        if orig is None:
            cid=uid()
            conn.execute("INSERT INTO history_l1.conversations(owner_id,id) VALUES(%s,%s)",(owner,cid))
        else:
            _fetch_conversation(conn,owner,orig,lock=True)
            cid=orig
        mid=uid()
        conn.execute("""INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
            VALUES(%s,%s,%s,'user',%s)""",(owner,mid,cid,request["question"]))
        rid=uid()
        row=conn.execute("""INSERT INTO history_l1.send_receipts
          (id,owner_id,requested_conversation_id,resolved_conversation_id,user_message_id,
           client_message_id,idempotency_key,payload_sha256,initial_request_id,initial_trace_id)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
          (rid,owner,orig,cid,mid,request["client_message_id"],request["idempotency_key"],
           fp,request_id,trace_id)).fetchone()
        if rollback:
            raise InjectedRollback("T1_BEFORE_COMMIT")
        return _send_receipt(row,request_id,trace_id,"created")

def _send_receipt(r,request_id,trace_id,disposition):
    return dict(kind="send_message_receipt",contract_version="product.v1",
                owner_user_id=r["owner_id"],request_id=request_id,trace_id=trace_id,
                requested_conversation_id=r["requested_conversation_id"],
                resolved_conversation_id=r["resolved_conversation_id"],
                client_message_id=r["client_message_id"],idempotency_key=r["idempotency_key"],
                idempotency_scope="trusted_user+send_message+conversation",
                payload_sha256=r["payload_sha256"],disposition=disposition,
                message_id=r["user_message_id"],error=None)

def _receipt_for(conn,owner,orig,client,key,lock=False):
    r=conn.execute("""SELECT * FROM history_l1.send_receipts
      WHERE owner_id=%s AND requested_conversation_id IS NOT DISTINCT FROM %s
      AND client_message_id=%s AND idempotency_key=%s""" + (" FOR UPDATE" if lock else ""),
      (owner,orig,client,key)).fetchone()
    if r is None:
        raise NotFound("NOT_FOUND")
    _fetch_conversation(conn,owner,r["resolved_conversation_id"])
    return r

def start_t2(conn,owner,orig,client,key,attempt_request_id,attempt_trace_id,*,rollback=False):
    with conn.transaction():
        scoped(conn,owner)
        r=_receipt_for(conn,owner,orig,client,key,lock=True)
        attempts=conn.execute("""SELECT * FROM history_l1.execution_attempts
          WHERE owner_id=%s AND send_receipt_id=%s ORDER BY id""",(owner,r["id"])).fetchall()
        if len(attempts)>1:
            raise IntegrityAnomaly("HISTORY_LEGACY_MULTI_ATTEMPT")
        if attempts:
            return attempts[0]
        att=conn.execute("""INSERT INTO history_l1.execution_attempts
           (owner_id,id,send_receipt_id,attempt_request_id,attempt_trace_id,reserved_answer_id)
           VALUES(%s,%s,%s,%s,%s,%s) RETURNING *""",
           (owner,uid(),r["id"],attempt_request_id,attempt_trace_id,uid())).fetchone()
        if rollback:
            raise InjectedRollback("T2_BEFORE_COMMIT")
        return att

def mark_attempt(conn,owner,attempt_id,state,error_code=None):
    if state not in ("attempt_unknown","failed","cancelled"):
        raise ValueError("invalid failure status")
    with conn.transaction():
        scoped(conn,owner)
        row=conn.execute("""SELECT * FROM history_l1.execution_attempts
            WHERE owner_id=%s AND id=%s FOR UPDATE""",(owner,attempt_id)).fetchone()
        if not row:
            raise NotFound("NOT_FOUND")
        if row["state"] not in ("attempt_pending","attempt_unknown"):
            raise Conflict("TERMINAL_ATTEMPT")
        return conn.execute("""UPDATE history_l1.execution_attempts SET state=%s,error_code=%s
                WHERE owner_id=%s AND id=%s RETURNING *""",
                (state,error_code,owner,attempt_id)).fetchone()

def finalize_t3(conn,owner,attempt_id,answer,assistant_text,*,rollback=False):
    check_wire(answer,"answer")
    if answer["state"] in ("unknown","cancelled","failed") or not assistant_text.strip():
        raise ValueError("not a verified committed answer")
    with conn.transaction():
        scoped(conn,owner)
        row=conn.execute("""SELECT a.*,r.resolved_conversation_id,r.user_message_id
          FROM history_l1.execution_attempts a
          JOIN history_l1.send_receipts r ON r.owner_id=a.owner_id AND r.id=a.send_receipt_id
          WHERE a.owner_id=%s AND a.id=%s FOR UPDATE OF a""",(owner,attempt_id)).fetchone()
        if row is None:
            raise NotFound("NOT_FOUND")
        if row["state"]=="answer_committed":
            existing=conn.execute("""SELECT payload FROM history_l1.answers
               WHERE owner_id=%s AND attempt_id=%s""",(owner,attempt_id)).fetchone()
            if not existing:
                raise IntegrityAnomaly("COMMIT_WITHOUT_ANSWER")
            if existing["payload"]!=answer:
                raise Conflict("FINAL_ANSWER_IMMUTABLE")
            return existing["payload"]
        if row["state"]!="attempt_pending":
            raise Conflict("UNVERIFIED_OUTCOME")
        if (answer["answer_id"]!=row["reserved_answer_id"]
            or answer["conversation_id"]!=row["resolved_conversation_id"]
            or answer["request_id"]!=row["attempt_request_id"]
            or answer["trace_id"]!=row["attempt_trace_id"]
            or answer["message_id"]==row["user_message_id"]):
            raise ValueError("answer/attempt identifiers mismatch")
        conn.execute("""INSERT INTO history_l1.messages
              (owner_id,id,conversation_id,role,body,answer_id)
              VALUES(%s,%s,%s,'assistant',%s,%s)""",
              (owner,answer["message_id"],answer["conversation_id"],assistant_text,answer["answer_id"]))
        conn.execute("""INSERT INTO history_l1.answers
              (owner_id,id,conversation_id,message_id,attempt_id,payload)
              VALUES(%s,%s,%s,%s,%s,%s)""",(owner,answer["answer_id"],
               answer["conversation_id"],answer["message_id"],attempt_id,Jsonb(answer)))
        conn.execute("""UPDATE history_l1.execution_attempts SET state='answer_committed'
            WHERE owner_id=%s AND id=%s""",(owner,attempt_id))
        if rollback:
            raise InjectedRollback("T3_BEFORE_COMMIT")
        return answer

def read_status(conn,owner,query,request_id,trace_id):
    check_wire(query,"message_request_status_query")
    # One coherent, owner-scoped snapshot from primary. No scheduler/provider call.
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        scoped(conn,owner)
        r=_receipt_for(conn,owner,query["requested_conversation_id"],
                       query["client_message_id"],query["idempotency_key"])
        attempts=conn.execute("""SELECT a.* FROM history_l1.execution_attempts a
          WHERE a.owner_id=%s AND a.send_receipt_id=%s ORDER BY a.id""",
          (owner,r["id"])).fetchall()
        if len(attempts)>1:
            raise IntegrityAnomaly("HISTORY_LEGACY_MULTI_ATTEMPT")
        att=attempts[0] if attempts else None
        result=None
        if att and att["state"]=="answer_committed":
            result=conn.execute("""SELECT ans.payload,ans.id,ans.message_id,m.role
             FROM history_l1.answers ans
             JOIN history_l1.messages m ON m.owner_id=ans.owner_id AND m.id=ans.message_id
             WHERE ans.owner_id=%s AND ans.attempt_id=%s AND ans.id=%s
               AND ans.conversation_id=%s""",
             (owner,att["id"],att["reserved_answer_id"],r["resolved_conversation_id"])).fetchone()
            if result is None or result["role"]!="assistant":
                raise IntegrityAnomaly("MISSING_VERIFIED_T3")
        if att and att["state"]!="answer_committed":
            unexpected=conn.execute("""SELECT 1 FROM history_l1.answers
              WHERE owner_id=%s AND attempt_id=%s""",(owner,att["id"])).fetchone()
            if unexpected:
                raise IntegrityAnomaly("PHANTOM_ANSWER")
        status = att["state"] if att else "persisted"
        return dict(kind="message_request_status",contract_version="product.v1",
            request_id=request_id,trace_id=trace_id,owner_user_id=owner,
            requested_conversation_id=r["requested_conversation_id"],
            client_message_id=r["client_message_id"],idempotency_key=r["idempotency_key"],
            status=status,resolved_conversation_id=r["resolved_conversation_id"],
            message_id=r["user_message_id"],attempt_id=att["id"] if att else None,
            attempt_request_id=att["attempt_request_id"] if att else None,
            attempt_trace_id=att["attempt_trace_id"] if att else None,
            reserved_answer_id=att["reserved_answer_id"] if att else None,
            answer_id=result["id"] if result else None,
            answer=result["payload"] if result else None)

def list_conversations(conn,owner,limit=20,anchor=None,last=None):
    if not 1<=limit<=100:
        raise ValueError("limit")
    with conn.transaction():
        scoped(conn,owner)
        q="""SELECT * FROM history_l1.conversations
             WHERE owner_id=%s AND state='active'"""
        params=[owner]
        if anchor is not None:
            q+=" AND (created_at,id) <= (%s,%s)"
            params+=list(anchor)
        if last is not None:
            q+=" AND (created_at,id) < (%s,%s)"
            params+=list(last)
        q+=" ORDER BY created_at DESC,id DESC LIMIT %s"
        params.append(limit+1)
        rows=conn.execute(q,params).fetchall()
        items=rows[:limit]
        return {"items":[_conv(r) for r in items],"has_more":len(rows)>limit,
                "last":(items[-1]["created_at"],items[-1]["id"]) if items else None}

def list_messages(conn,owner,conversation_id,limit=20,anchor=None,last=None):
    if not 1<=limit<=100:
        raise ValueError("limit")
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        scoped(conn,owner)
        _fetch_conversation(conn,owner,conversation_id)
        q="""SELECT m.*,ans.payload AS answer_payload FROM history_l1.messages m
          LEFT JOIN history_l1.answers ans
          ON ans.owner_id=m.owner_id AND ans.id=m.answer_id AND ans.message_id=m.id
          WHERE m.owner_id=%s AND m.conversation_id=%s"""
        p=[owner,conversation_id]
        if anchor is not None:
            q+=" AND (m.created_at,m.id) <= (%s,%s)"
            p+=list(anchor)
        if last is not None:
            q+=" AND (m.created_at,m.id) > (%s,%s)"
            p+=list(last)
        q+=" ORDER BY m.created_at ASC,m.id ASC LIMIT %s"
        p.append(limit+1)
        rows=conn.execute(q,p).fetchall()
        page=rows[:limit]
        if any(r["role"]=="assistant" and r["answer_payload"] is None for r in page):
            raise IntegrityAnomaly("ORPHAN_ASSISTANT")
        def _message(r):
            return dict(kind="message",contract_version="product.v1",
                        owner_user_id=owner,message_id=r["id"],conversation_id=conversation_id,
                        role=r["role"],text=r["body"],created_at=r["created_at"].isoformat(),
                        answer_id=r["answer_id"])
        return {"items":[_message(r) for r in page],
                "answers":[r["answer_payload"] for r in page if r["answer_payload"] is not None],
                "has_more":len(rows)>limit,
                "last":(page[-1]["created_at"],page[-1]["id"]) if page else None}
