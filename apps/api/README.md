# FastAPI History L1 (provisional)

Consumes **the merged** `packages/contracts/product.v1.schema.json` and the existing `src/phase3/storage/postgres/repository.py`. No forked DTO, Schema, DB or migrations. Only five endpoints are implemented, with OpenAPI **3.1.0** backed by product.v1 JSON Schema `$defs`.

| Route | Request / successful response | Exact HTTP outcomes |
|---|---|---|
| `POST /v1/conversations` | `create_conversation_request` → `create_conversation_receipt` | 201 created; 200 replayed; 409 conflict |
| `GET /v1/conversations` | Query `limit=20&cursor=` normalized to `conversation_list_request` → `conversation_page` | 200; 422 invalid query/cursor; 404 foreign cursor |
| `GET /v1/conversations/{id}/messages` | Query normalized to `conversation_messages_request` → `conversation_messages_page` | 200; 404 missing/foreign/deleted; 422 invalid cursor |
| `POST /v1/messages` | Existing `send_message_request` → existing `send_message_receipt` | 202 **T1 committed only**; 200 replayed; 409 conflict |
| `GET /v1/message-requests/status` | Query normalized to `message_request_status_query` → `message_request_status` | 200; 404 missing/foreign; NEVER invokes T2/T3 |

All failures use the existing `error_response` Schema with server-generated current `request_id`/`trace_id`. Codes: `AUTH_REQUIRED` 401; `NOT_FOUND` 404; `INVALID_REQUEST` 422; `INVALID_CURSOR`/`CURSOR_EXPIRED` 422; `IDEMPOTENCY_CONFLICT` 409; `REQUEST_TOO_LARGE` 413; `UNSUPPORTED_MEDIA_TYPE` 415; `CURSOR_CONFIGURATION`/`TEMPORARILY_UNAVAILABLE` 503. Generic text only; never SQL/DSN/stack trace, owner details or raw user input. Validation reuses JSON Schema Draft 2020-12 with `FormatChecker`, rejects extra JSON body/query keys and duplicate JSON object members. Entire request JSON max 8192 bytes; question UTF-8 max 4096 bytes; keyset page limit 1–100 (default 20).

**No Production Auth is implemented.** The default `get_trusted_actor` dependency always rejects 401; there is no public owner/header/query/body selector, fixed actor or environment flag for test Auth. Only a separately authorized in-process `TestClient.dependency_overrides` may inject a synthetic, schema-valid `trusted_actor_context`; each real HTTP adapter request mints fresh current request/trace IDs. This must not be deployed until the employer approves real Auth/session/revocation and associated threat review. The `history_app` PostgreSQL role is explicitly checked to be neither superuser nor BYPASSRLS, and is the only API role supported by this L1 adapter. `API_HISTORY_DSN` is a server-only setting with no fallback; unavailable configuration fails closed.

**Cursor:** HMAC-SHA256, URL-safe, version 1, max 512 chars, bounded by owner, resource, Conversation ID, page limit, immutable first-page keyset high-watermark (anchor), exclusive last key, and expiry. `API_CURSOR_KEY` (min 32 UTF-8 bytes) and `API_CURSOR_TTL_SECONDS` (1–3600 for this L1 test harness) must both be explicitly provided server-side; **no default secret, key rotation or Production TTL is chosen**. Invalid signature/scope/limit/expiry fails; other-user owner scope is generic 404. Timestamps are UTC-aware. This anchor is a **keyset upper bound**, NOT a persistent MVCC snapshot against deleted rows or privileged backdated inserts. The existing Repository supplies limit+1, ordering and anchor/last consumption; the API only finds the initial owner-scoped upper bound and signs cursors. Cursor key never appears in API response or log.

**Persistence boundaries:** Create and Send have independent scoped idempotency. The original `requested_conversation_id=null` survives replay even after a server allocation. POST Send calls **only** `send_t1` (durably recorded User Message + Receipt); it does NOT create Attempt/Answer, call a model or schedule T2/T3. `read_status` uses the Repository's coherent `REPEATABLE READ READ ONLY` primary transaction and keeps prior Attempt trace distinct from current status request trace. T2/T3 may be used **only by internal PostgreSQL test fixture setup**, never through public endpoints. Replay and polling are side-effect-free with respect to Attempt/Answer and models. Missing/foreign/deleted access maps to uniform 404; deletion/Retention/Export remain undecided.

### Reproducible CI-only checks

Runner: free standard `ubuntu-24.04`, ephemeral `postgres:17.11` service on loopback, existing migrations `001_history_l1.up.sql` then `002_one_attempt.up.sql`, independent `history_migrator` and non-BYPASSRLS `history_app` roles with **synthetic credentials only**. Workflow `.github/workflows/api-history.yml` installs direct pins from `apps/api/requirements-ci.txt`, exercises HTTP in-process (HTTPX TestClient, no public listener) and real temporary PostgreSQL; no Mac tool installations.

```sh
python -m pip install --no-cache-dir --index-url https://pypi.org/simple -r apps/api/requirements-ci.txt
python -m compileall -q apps/api tests/phase3/integration/api
python -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v
python -m unittest discover -s tests/phase3/integration/api -p 'test_*.py' -v
```

The integration suite refuses to run without `CI=true`, exact loopback temp DB name, and matching app/migrator roles. Never run it against a user's Mac, live DB or public database. The **simulated dropped response** in a test deliberately discards a successfully completed in-process HTTP response and then retries; it is **not** a real network disconnect, process kill or provider retry. Contract tests and actual test-result status belong in [the cumulative API checkpoint](../../coordination/tasks/AGENT-API-HISTORY-01.md).

**Direct dependency versions:** `fastapi==0.162.2` [official PyPI](https://pypi.org/project/fastapi/0.162.2/), `httpx==0.28.1` [PyPI](https://pypi.org/project/httpx/0.28.1/), `psycopg[binary]==3.3.8` (accepted DB PR #9), `jsonschema==4.26.0` (existing contract). Transitives are NOT pinned/hashes verified in this package; record actual installed versions from CI log. Official [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/) requires HTTPX. All higher Gates, Production security, real Auth, Retention, NB23, L2 and live UI connection remain open.


### APIH-01-D — bounded ingress and event-loop isolation (pending CI/review)

The HTTP adapter consumes ASGI request fragments incrementally and counts actual delivered bytes, never accumulating more than 8192 bytes of application request data. It stops requesting further frames as soon as the limit is crossed and emits the existing product.v1 413 envelope. Content-Length is solely a preflight hint: missing or understated lengths cannot bypass the actual byte limit; a contradictory shorter declared length is rejected (422). Observed ASGI disconnect and malformed/truncated JSON fail validation before database mutation. These are **application-level body collection** guarantees only: buffering limits of the HTTP server, ASGI gateway, reverse proxy, network and client are **not** established.

Create and Send retain async body parsing but dispatch synchronous Repository operations using Starlette run_in_threadpool. The existing per-request synchronous _session dependency opens one restricted PostgreSQL connection per request and closes it during yield-dependency teardown, including errors; no connection is reused by independent concurrent requests. This is not a rewrite of the Repository, nor a claim of end-to-end async I/O, capacity, Auth, engine or production readiness.

New integration tests exercise direct controlled ASGI receive frames (including zero-read Content-Length preflight rejection, absent/lying Content-Length, overflow with unread trailing frames, disconnect and absence of writes). The concurrency test runs simultaneous HTTP operations on a single asyncio event loop via httpx.AsyncClient and ASGITransport; a threading.Event/timeout barrier holds T1 in the worker while a separate GET must finish using another DB connection before release. Independent TestClient worker threads alone do not prove that property. Results require actual CI evidence; no Module Gate is implied.
