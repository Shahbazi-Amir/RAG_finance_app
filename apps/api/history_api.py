"""History L1 HTTP adapter: product.v1, existing PostgreSQL repository, NO Auth/engine.

No production actor is configured. Only in-process tests override get_trusted_actor.
Never expose repository owner or T2/T3 controls through an HTTP endpoint.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from jsonschema import ValidationError
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/phase3/storage/postgres"))
from repository import (  # noqa: E402 - existing single storage implementation
    SCHEMA, VALIDATOR, Conflict, IntegrityAnomaly, NotFound, check_wire,
    create_conversation, list_conversations, list_messages, read_status,
    scoped, send_t1, uid,
)

API_VERSION = "product.v1"
MAX_JSON_BYTES = 8192
MAX_QUESTION_BYTES = 4096
CURSOR_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,512}$")
CURSOR_FIELDS = {"v", "owner", "resource", "conversation_id", "limit",
                 "anchor", "last", "exp"}


class ApiFailure(Exception):
    def __init__(self, status: int, code: str, category: str = "technical"):
        self.status, self.code, self.category = status, code, category


def get_trusted_actor():
    """Default is DENY; a separately reviewed Auth provider is NOT installed.

    TestClient only: dependency_overrides[get_trusted_actor] supplies an
    in-process synthetic actor. No header/query/body/env switch enables it.
    """
    raise ApiFailure(401, "AUTH_REQUIRED", "authorization")


def _fresh_context(actor):
    if not isinstance(actor, dict):
        raise ApiFailure(401, "AUTH_REQUIRED", "authorization")
    try:
        VALIDATOR.validate(actor)
        if actor["kind"] != "trusted_actor_context" or actor["principal_source"] != "server_auth_context":
            raise ValueError("invalid server actor")
        issued = datetime.fromisoformat(actor["authenticated_at"].replace("Z", "+00:00"))
        if issued.tzinfo is None:
            raise ValueError("naive authentication timestamp")
    except (ValidationError, ValueError, KeyError, TypeError):
        raise ApiFailure(401, "AUTH_REQUIRED", "authorization") from None
    return {"owner": actor["owner_user_id"], "request_id": uid(), "trace_id": uid()}


def _session(actor=Depends(get_trusted_actor)):
    ctx = _fresh_context(actor)
    dsn = os.getenv("API_HISTORY_DSN")
    if not dsn:
        raise ApiFailure(503, "TEMPORARILY_UNAVAILABLE")
    try:
        with psycopg.connect(dsn, autocommit=True, row_factory=dict_row,
                             connect_timeout=5) as conn:
            role = conn.execute("""SELECT rolname, rolsuper, rolbypassrls
                FROM pg_roles WHERE rolname=current_user""").fetchone()
            if (not role or role["rolname"] != "history_app"
                    or role["rolsuper"] or role["rolbypassrls"]):
                raise ApiFailure(503, "TEMPORARILY_UNAVAILABLE")
            yield {**ctx, "conn": conn}
    except psycopg.Error:
        # No DSN, SQL, traceback or row content ever reaches the caller.
        raise ApiFailure(503, "TEMPORARILY_UNAVAILABLE") from None


def _safe_error(status: int, code: str, category: str, message: str):
    response = {
        "kind": "error_response", "contract_version": API_VERSION,
        "request_id": uid(), "trace_id": uid(),
        "error": {"category": category, "code": code, "message": message},
    }
    VALIDATOR.validate(response)
    return JSONResponse(status_code=status, content=response)


def _exception_code(exc):
    if isinstance(exc, ApiFailure):
        return exc.status, exc.code, exc.category
    if isinstance(exc, NotFound):
        return 404, "NOT_FOUND", "authorization"
    if isinstance(exc, Conflict):
        return 409, "IDEMPOTENCY_CONFLICT", "validation"
    if isinstance(exc, (ValidationError, ValueError, RequestValidationError)):
        return 422, "INVALID_REQUEST", "validation"
    if isinstance(exc, IntegrityAnomaly):
        return 503, "TEMPORARILY_UNAVAILABLE", "technical"
    return 503, "TEMPORARILY_UNAVAILABLE", "technical"


async def _read_body(request: Request, kind: str):
    length = request.headers.get("content-length")
    if length and (not length.isdecimal() or int(length) > MAX_JSON_BYTES):
        raise ApiFailure(413, "REQUEST_TOO_LARGE", "validation")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise ApiFailure(415, "UNSUPPORTED_MEDIA_TYPE", "validation")
    # Count actual ASGI-delivered bytes, not only the advisory Content-Length.
    # Never request another chunk after the first that exceeds the limit.
    received = 0
    pieces = []
    try:
        async for piece in request.stream():
            received += len(piece)
            if received > MAX_JSON_BYTES:
                raise ApiFailure(413, "REQUEST_TOO_LARGE", "validation")
            pieces.append(piece)
    except ClientDisconnect:
        # Connection ended before the final ASGI request frame. No write ran.
        raise ApiFailure(422, "INVALID_REQUEST", "validation") from None
    if length is not None and received != int(length):
        # A caller can understate length while remaining below the size cap.
        raise ApiFailure(422, "INVALID_REQUEST", "validation")
    raw = b"".join(pieces)

    def no_duplicate_keys(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out
    try:
        body = json.loads(raw, object_pairs_hook=no_duplicate_keys)
        if not isinstance(body, dict):
            raise ValueError("JSON object required")
        check_wire(body, kind)  # exact shared product.v1, never a copied DTO
        if kind == "send_message_request" and len(body["question"].encode("utf-8")) > MAX_QUESTION_BYTES:
            raise ApiFailure(413, "REQUEST_TOO_LARGE", "validation")
    except (UnicodeError, json.JSONDecodeError, ValueError, ValidationError, KeyError):
        raise ApiFailure(422, "INVALID_REQUEST", "validation") from None
    return body


def _query(request: Request, kind: str, **values):
    raw = request.query_params
    allowed = {"limit", "cursor"} if kind.endswith("list_request") or kind == "conversation_messages_request" else {
        "requested_conversation_id", "client_message_id", "idempotency_key"}
    if any(key not in allowed or len(raw.getlist(key)) != 1 for key in raw.keys()):
        raise ApiFailure(422, "INVALID_REQUEST", "validation")
    if "limit" in allowed:
        value = raw.get("limit", "20")
        if not value.isdecimal():
            raise ApiFailure(422, "INVALID_REQUEST", "validation")
        values.update(limit=int(value), cursor=raw.get("cursor"))
    else:
        original = raw.get("requested_conversation_id")
        values.update(requested_conversation_id=original if original not in (None, "") else None,
                      client_message_id=raw.get("client_message_id"),
                      idempotency_key=raw.get("idempotency_key"))
    item = {"kind": kind, "contract_version": API_VERSION, **values}
    try:
        check_wire(item, kind)
    except (ValidationError, ValueError):
        raise ApiFailure(422, "INVALID_REQUEST", "validation") from None
    return item


def _cursor_config():
    secret = os.getenv("API_CURSOR_KEY", "")
    ttl = os.getenv("API_CURSOR_TTL_SECONDS", "")
    try:
        duration = int(ttl)
        if len(secret.encode("utf-8")) < 32 or not 1 <= duration <= 3600:
            raise ValueError("invalid server cursor config")
    except (UnicodeError, ValueError):
        raise ApiFailure(503, "CURSOR_CONFIGURATION") from None
    return secret.encode("utf-8"), duration


def _key_part(key):
    if key is None:
        return None
    if (not isinstance(key, (list, tuple)) or len(key) != 2
            or not isinstance(key[1], str)):
        raise ApiFailure(503, "TEMPORARILY_UNAVAILABLE")
    when = key[0]
    if isinstance(when, datetime):
        when = when.astimezone(timezone.utc).isoformat()
    if not isinstance(when, str):
        raise ApiFailure(503, "TEMPORARILY_UNAVAILABLE")
    return [when, key[1]]


def _cursor_encode(data, ctx, resource, conversation_id, limit, anchor, last):
    secret, ttl = _cursor_config()
    doc = {
        "v": 1, "owner": ctx["owner"], "resource": resource,
        "conversation_id": conversation_id, "limit": limit,
        "anchor": _key_part(anchor), "last": _key_part(last),
        "exp": int(time.time()) + ttl,
    }
    msg = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(msg + hmac.new(secret, msg, hashlib.sha256).digest()).rstrip(b"=").decode()
    if len(token) > 512:
        raise ApiFailure(503, "CURSOR_CONFIGURATION")
    return token


def _cursor_decode(raw, ctx, resource, conversation_id, limit):
    secret, _ = _cursor_config()
    if not isinstance(raw, str) or not CURSOR_PATTERN.fullmatch(raw):
        raise ApiFailure(422, "INVALID_CURSOR", "validation")
    try:
        encoded = base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True)
        if len(encoded) < 33:
            raise ValueError()
        body, signature = encoded[:-32], encoded[-32:]
        if not hmac.compare_digest(hmac.new(secret, body, hashlib.sha256).digest(), signature):
            raise ValueError()
        decoded = json.loads(body)
        if (not isinstance(decoded, dict) or set(decoded) != CURSOR_FIELDS
                or type(decoded["v"]) is not int or decoded["v"] != 1
                or type(decoded["exp"]) is not int):
            raise ValueError()
        for k in ("anchor", "last"):
            if (not isinstance(decoded[k], list) or len(decoded[k]) != 2
                    or not all(isinstance(v, str) for v in decoded[k])):
                raise ValueError()
            decoded[k][0] = datetime.fromisoformat(decoded[k][0].replace("Z", "+00:00"))
            if decoded[k][0].tzinfo is None:
                raise ValueError()
        if decoded["owner"] != ctx["owner"]:
            raise ApiFailure(404, "NOT_FOUND", "authorization")
        if (decoded["resource"] != resource or decoded["conversation_id"] != conversation_id
                or type(decoded["limit"]) is not int or decoded["limit"] != limit):
            raise ApiFailure(422, "INVALID_CURSOR", "validation")
        if decoded["exp"] <= time.time():
            raise ApiFailure(422, "CURSOR_EXPIRED", "validation")
        return decoded["anchor"], decoded["last"]
    except ApiFailure:
        raise
    except (ValueError, KeyError, TypeError, OverflowError, UnicodeError):
        raise ApiFailure(422, "INVALID_CURSOR", "validation") from None


def _initial_anchor(conn, owner, resource, conversation_id):
    # Owner bound, readonly query for upper keyset watermark. This is NOT
    # an MVCC snapshot across requests or protection from privileged backdating.
    with conn.transaction():
        scoped(conn, owner)
        if resource == "conversations":
            row = conn.execute("""SELECT created_at,id FROM history_l1.conversations
                WHERE owner_id=%s AND state='active'
                ORDER BY created_at DESC,id DESC LIMIT 1""", (owner,)).fetchone()
        else:
            row = conn.execute("""SELECT created_at,id FROM history_l1.messages
                WHERE owner_id=%s AND conversation_id=%s
                ORDER BY created_at DESC,id DESC LIMIT 1""",
                (owner, conversation_id)).fetchone()
        return [row["created_at"], row["id"]] if row else None


def _send_success(doc, status):
    try:
        VALIDATOR.validate(doc)
    except ValidationError:
        raise IntegrityAnomaly("INVALID_PRODUCT_V1_OUTPUT") from None
    return JSONResponse(status_code=status, content=doc)


def _page(kind, ctx, content, limit, anchor, resource, conversation_id=None):
    items = content["items"]
    if len(items) > limit or any(
        obj["owner_user_id"] != ctx["owner"] for obj in items
    ):
        raise IntegrityAnomaly("OWNER_OR_PAGE_MISMATCH")
    if resource == "conversations":
        if any(obj["state"] != "active" for obj in items):
            raise IntegrityAnomaly("INACCESSIBLE_HISTORY")
    else:
        if any(obj["conversation_id"] != conversation_id for obj in items):
            raise IntegrityAnomaly("FOREIGN_MESSAGE")
        matches = {m["answer_id"]: m["message_id"] for m in items if m["role"] == "assistant"}
        answers = content["answers"]
        if (any(a["answer_id"] not in matches
                or a["message_id"] != matches[a["answer_id"]]
                or a["conversation_id"] != conversation_id for a in answers)
                or len(answers) != len(matches)):
            raise IntegrityAnomaly("ANSWER_PAGE_MISMATCH")
    next_cursor = (_cursor_encode(content, ctx, resource, conversation_id, limit,
                                  anchor, content["last"]) if content["has_more"] else None)
    page = {"limit": limit, "has_more": content["has_more"], "next_cursor": next_cursor}
    result = {"kind": kind, "contract_version": API_VERSION, "items": items, "page": page}
    if resource == "conversations":
        result["scope_user_id"] = ctx["owner"]
    else:
        result.update(owner_user_id=ctx["owner"], conversation_id=conversation_id,
                      answers=content["answers"])
    return _send_success(result, 200)


# OpenAPI references the exact existing product schema, without parallel DTOs.
def _schema_ref(name):
    return {"$ref": "#/components/schemas/ProductContract/$defs/" + name}


def _output_doc(kind, success_code="200", request_kind=None, replay_code=None):
    err = {"description": "Versioned sanitized product.v1 error",
           "content": {"application/json": {"schema": _schema_ref("error_response")}}}
    response = {"responses": {
        success_code: {"description": kind, "content": {
            "application/json": {"schema": _schema_ref(kind)}}},
        **{str(n): err for n in (400, 401, 404, 409, 413, 415, 422, 503)},
    }, "x-product-contract-version": API_VERSION}
    if replay_code:
        response["responses"][replay_code] = response["responses"][success_code]
    if request_kind:
        response["requestBody"] = {"required": True, "content": {
            "application/json": {"schema": _schema_ref(request_kind)}}}
    return response


app = FastAPI(title="RAG Finance History L1 (Auth and engine unavailable)",
              version="1.0.0-l1",
              description="Synthetic PostgreSQL History L1. No authentication provider or model.")


@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception):
    status, code, category = _exception_code(exc)
    # Standard messages never include underlying DB/API details or user text.
    messages = {
        "AUTH_REQUIRED": "Authentication required.",
        "NOT_FOUND": "Resource not found.",
        "INVALID_REQUEST": "Invalid request.",
        "INVALID_CURSOR": "Invalid cursor.",
        "CURSOR_EXPIRED": "Invalid cursor.",
        "IDEMPOTENCY_CONFLICT": "Idempotency conflict.",
        "REQUEST_TOO_LARGE": "Request too large.",
        "UNSUPPORTED_MEDIA_TYPE": "Unsupported media type.",
        "CURSOR_CONFIGURATION": "History temporarily unavailable.",
        "TEMPORARILY_UNAVAILABLE": "History temporarily unavailable.",
    }
    return _safe_error(status, code, category, messages.get(code, "History temporarily unavailable."))


for _error_type in (ApiFailure, NotFound, Conflict, IntegrityAnomaly, ValidationError,
                    ValueError, RequestValidationError, psycopg.Error):
    app.add_exception_handler(_error_type, on_error)


@app.post("/v1/conversations",
          openapi_extra=_output_doc("create_conversation_receipt", "201", "create_conversation_request", "200"))
async def create(request: Request, ctx=Depends(_session)):
    payload = await _read_body(request, "create_conversation_request")
    # _session owns a distinct connection and closes it on request teardown.
    result = await run_in_threadpool(
        create_conversation, ctx["conn"], ctx["owner"], payload,
        ctx["request_id"], ctx["trace_id"])
    return _send_success(result, 201 if result["disposition"] == "created" else 200)


@app.post("/v1/messages",
          openapi_extra=_output_doc("send_message_receipt", "202", "send_message_request", "200"))
async def send(request: Request, ctx=Depends(_session)):
    payload = await _read_body(request, "send_message_request")
    # T1 ONLY. No start_t2(), mark_attempt(), finalize_t3() or model calls.
    # T1 only; synchronous psycopg work must not block the ASGI event loop.
    result = await run_in_threadpool(
        send_t1, ctx["conn"], ctx["owner"], payload,
        ctx["request_id"], ctx["trace_id"])
    return _send_success(result, 202 if result["disposition"] == "created" else 200)


@app.get("/v1/conversations",
         openapi_extra=_output_doc("conversation_page"))
def conversations(request: Request, ctx=Depends(_session)):
    query = _query(request, "conversation_list_request")
    limit = query["limit"]
    anchor, last = (_cursor_decode(query["cursor"], ctx, "conversations", None, limit)
                    if query["cursor"] else (None, None))
    if not query["cursor"]:
        anchor = _initial_anchor(ctx["conn"], ctx["owner"], "conversations", None)
    response = list_conversations(ctx["conn"], ctx["owner"], limit=limit,
                                  anchor=anchor, last=last)
    return _page("conversation_page", ctx, response, limit, anchor, "conversations")


@app.get("/v1/conversations/{conversation_id}/messages",
         openapi_extra=_output_doc("conversation_messages_page"))
def messages(conversation_id: str, request: Request, ctx=Depends(_session)):
    query = _query(request, "conversation_messages_request",
                   conversation_id=conversation_id)
    limit = query["limit"]
    anchor, last = (_cursor_decode(query["cursor"], ctx, "messages", conversation_id, limit)
                    if query["cursor"] else (None, None))
    if not query["cursor"]:
        anchor = _initial_anchor(ctx["conn"], ctx["owner"], "messages", conversation_id)
    response = list_messages(ctx["conn"], ctx["owner"], conversation_id,
                             limit=limit, anchor=anchor, last=last)
    return _page("conversation_messages_page", ctx, response, limit, anchor,
                 "messages", conversation_id)


@app.get("/v1/message-requests/status",
         openapi_extra=_output_doc("message_request_status"))
def status(request: Request, ctx=Depends(_session)):
    query = _query(request, "message_request_status_query")
    response = read_status(ctx["conn"], ctx["owner"], query,
                           ctx["request_id"], ctx["trace_id"])
    if response["owner_user_id"] != ctx["owner"]:
        raise IntegrityAnomaly("OWNER_MISMATCH")
    return _send_success(response, 200)


def openapi():
    if app.openapi_schema is not None:
        return app.openapi_schema
    document = get_openapi(title=app.title, version=app.version,
                           description=app.description, routes=app.routes,
                           openapi_version="3.1.0")
    # Embed the exact single contract, adjusting ONLY references in the
    # generated OpenAPI view (never edit product.v1 source or make DTO forks).
    contract = copy.deepcopy(SCHEMA)
    def references(node):
        if isinstance(node, dict):
            for k, value in node.items():
                if k == "$ref" and isinstance(value, str) and value.startswith("#/$defs/"):
                    node[k] = value.replace("#/$defs/", "#/components/schemas/ProductContract/$defs/")
                else:
                    references(value)
        elif isinstance(node, list):
            for element in node:
                references(element)
    references(contract)
    document.setdefault("components", {}).setdefault("schemas", {})["ProductContract"] = contract
    for path, item in document["paths"].items():
        if path.endswith("/messages") and path.startswith("/v1/conversations/"):
            item["get"]["parameters"] = [
                {"in": "path", "name": "conversation_id", "required": True,
                 "schema": SCHEMA["$defs"]["conversation_messages_request"]["properties"]["conversation_id"]},
                {"in": "query", "name": "limit", "required": False,
                 "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
                {"in": "query", "name": "cursor", "required": False,
                 "schema": {"type": "string", "minLength": 1, "maxLength": 512}},
            ]
        elif path == "/v1/conversations" and "get" in item:
            item["get"]["parameters"] = [
                {"in": "query", "name": "limit", "required": False,
                 "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
                {"in": "query", "name": "cursor", "required": False,
                 "schema": {"type": "string", "minLength": 1, "maxLength": 512}},
            ]
        elif path == "/v1/message-requests/status":
            props = SCHEMA["$defs"]["message_request_status_query"]["properties"]
            item["get"]["parameters"] = [
                {"in": "query", "name": field, "required": field != "requested_conversation_id",
                 "schema": props[field]}
                for field in ("requested_conversation_id", "client_message_id", "idempotency_key")
            ]
    app.openapi_schema = document
    return document


app.openapi = openapi
