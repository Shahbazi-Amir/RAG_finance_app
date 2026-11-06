# RAG_finance_app — Product contract v1 (provisional)

**Scope:** machine-readable **product-owned** interface for API, UI and PostgreSQL persistence. **Status:** `PROPOSED / NOT_FROZEN`; this does **not** approve Module 00, freeze Module 03 or confirm a running RAG engine. This document supersedes the earlier *documentation-only* placeholder in this directory, not the read-only NB23 schemas.

## Single source of machine-readable definitions

- [`product.v1.schema.json`](product.v1.schema.json) — JSON Schema **Draft 2020-12**, `$id: urn:ragfinance:product:v1`, `contract_version: product.v1`. It contains **one `$defs` registry** shared by all 14 wire-document kinds; only `kind` dispatches the relevant shape. Schema draft validation does not verify source semantics or server identity.
- [`fixtures/product.v1.cases.json`](fixtures/product.v1.cases.json) — 62 **SYNTHETIC** cases: 22 positive and 40 negative, explicitly expected and labeled. No real person, real source, production release, provider output or historical engine behavior is represented.
- [`../../tests/phase3/contracts/test_contracts.py`](../../tests/phase3/contracts/test_contracts.py) and [`semantics.py`](../../tests/phase3/contracts/semantics.py) — executable schema, positive/negative and cross-reference checks. Install only into an isolated environment if this Python container does not already have the pinned dependency; do not alter the user's Mac/global or Phase 2 environment.

### Documents and consumers

| Wire `kind` | Ownership boundary / key invariants |
|---|---|
| `conversation`, `message`, `answer`, `feedback`, `conversation_snapshot` | Server-owned `owner_user_id`, stable IDs; snapshot checks conversation/message/answer/feedback ownership, assistant-message link, citation cross-references, and feedback target. DB defines storage/index/RLS, not this document. |
| `send_message_request` | Browser sends `conversation_id` (nullable for a new thread), `client_message_id`, `question`, `idempotency_key`; **never a user identity**, trusted context, NB23 history or authority/source/context filters. |
| `trusted_actor_context` | **Internal server-generated** identity context only: `principal_source=server_auth_context`. No login, session, cookie or token strategy is selected; the backend must not deserialize this type from untrusted browser input. |
| `send_message_receipt` | Server returns `owner_user_id`, `request_id`, `trace_id`, idempotency disposition, message ID or explicit conflict. Rejects inconsistent client/trusted-server ownership in relational checks. |
| `conversation_page` | Opaque cursor, limit 1–100, `next_cursor` required only when `has_more=true`; product must authorize all returned conversations to the authenticated owner, also independently tested. |
| `stream_event`, `stream_session` | Backend-reported phases, ordered sequence, request/trace IDs and explicit end/error/unknown/server-cancel semantics. The schema is **provisional**: not a verified NB23 event stream. |
| `delete_command`, `delete_status` | User confirmation, `requesting→processing→succeeded/failed` consumer vocabulary; only backend confirmation may set `succeeded`. Optional Export is *not* a prerequisite for deletion. |
| `error_response` | Distinct technical/validation/authorization/policy error envelope; not a `no_answer` outcome. |

## Product-level invariants beyond JSON Schema

The runnable cross-checks reject orphan/duplicated claim/citation IDs and asymmetric **two-way** links, answer-to-assistant-message mismatch, cross-user snapshots, feedback for an unknown answer, unauthorized pagination results, skipped or duplicated event sequences, missing/repeated terminal events, synthetic source verification and inconsistent request receipts. These checks are **local synthetic contract checks**, not live services, database RLS tests, or real source accuracy tests.

**Attribution:** `credited_author_name`, `editorial_supervisor_name` and `speaker_name` are separate nullable fields. `content_authority_type`/`attribution_status` do not authorize inventing identity, page, URL or timestamp. For `SYNTHETIC` examples, citation `resolution_status=unresolved`, `locator=null`, and every attribution field is `null`; synthetic data must **never** be presented as verified source evidence. Future `verified` source claims require independent server-side provenance and actual resolver checks; schema acceptance alone is insufficient. `speaker`/`speaker_name` mapping to NB23 is pending.

**Confidence:** `null` means **unmeasured**, not a measured value of zero. If a value is genuinely measured, it must be an object with `value` in `[0,1]` plus nonempty `meaning` and `calibration_scope`. A synthetic example with numeric value is not evidence of actual calibration.

**Answer status:** `error` is a technical failure (`state=failed`, error object and no successful claims); `no_answer` is an ordinary abstention (`state=completed`, `error=null`); `partial`, `unknown` and `cancelled` remain distinct. Never transform an unknown backend state into completed or no-answer. A partial answer is not fully validated success.

## Send-message idempotency policy — no Exactly-once model claim

1. The request comes without a trusted identity. Server derives the **authenticated principal** independently, then scopes the idempotency record by `(trusted_user, operation=send_message, conversation_id, client_message_id, idempotency_key)`. A null conversation ID for a new thread is stabilized by the same `client_message_id` and key, not inferred from a display label.
2. Server computes `payload_sha256` over the exact UTF-8 bytes of JSON with **only** `client_message_id`, `conversation_id`, `question`, sorted keys, compact separators `(',',':')`, `ensure_ascii=False`, no Unicode case/whitespace normalization. The server does not trust a client-provided hash.
3. First request persists one `created` receipt. Same authenticated scope/key and same fingerprint returns `replayed` with the **same persisted `message_id`**. Changed canonical payload under the same scoped key returns `conflict`, no message ID and an explicit validation error (the HTTP status mapping is a separate API decision). Same key in a *different authenticated user scope* is independent.
4. This policy is for **duplicate message persistence/receipt and safe client retry**, **not** a guarantee of exactly-once model/provider execution, server cancellation, transaction retry or external side effects. API, DB and Foundation must agree on transaction boundary, commit/abort, authorization, timeout handling and stable error mapping before runtime integration.

## Streaming and cancellation — proposed events, not provider facts

- `connected`, `retrieving`, `generating`, `delta`, `cancel_requested`, `display_cancelled`, `server_cancelled`, `completed`, `failed`, `unknown`. `retrieving`/`generating` require actual `reported_by=backend`; a frontend must not infer these as internal engine phases merely because it displays a spinner.
- `completed`, `failed`, `server_cancelled`, `unknown` are mutually exclusive **terminal server-result events** for the consumer stream. A complete session has **exactly one final terminal event**, no events after it, contiguous sequence starting at 0 and matching stream/answer/request/trace IDs. `unknown` is a reported *unknown state*, not a proven server success/failure; recovery contract remains provisional.
- `display_cancelled` means **UI display stopped only**. `cancel_requested` means a server stop was *asked for*, not proved. Only `server_cancelled` with explicit server report (`server_stopped=true`, confirmation reference) claims the server stopped; it requires a prior cancel request. A display-cancelled stream does not imply provider execution stopped. Event schemas and recovery algorithm remain `provisional/blocked_by=NB23` for live producer integration.

## Deletion, pagination and trust

- Frontend requests account/conversation deletion with explicit confirmation; successful API dispatch is **not** successful deletion. `delete_status.succeeded` requires `backend_confirmed=true` and completion time; further cache/backup/retention obligations are policy decisions, **not** claimed as implemented.
- A cursor is opaque and cannot authorize another user's data. Source of trusted `owner_user_id` is the backend-authenticated principal (method/provider still undecided), never a user-supplied request field.
- Export availability and policy are **unresolved**, but the deletion contract is independent. Retention duration remains undecided.

## NB23 / module boundary

Read-only upstream schemas are in [`../../references/phase2/contracts/`](../../references/phase2/contracts/) and pinned to source commit `7c74783c3dcda897b010ba9ea358d113f172ed1f`. The **Draft NB23 request** accepts only `question` and `contract_version`. It does **not** accept product history, source/authority filters or context. Do not send product DTOs directly to NB23 or silently add fields. The product `provenance.rag_binding` carries `status=provisional`, `blocked_by=NB23`, `release_id=null`, `adapter_verified=false` until independently evidenced acceptance. A real `release_id`, full Citation locator, streaming semantics and producer outcome mapping have not been supplied or verified.

**Decisions intentionally open:** Auth method and consent text/version storage, user identifier provisioning, privacy/retention, optional Export, real status/error/provider mapping, idempotency expiry and HTTP statuses, cursor expiry, exact API event transport/cancel semantics, timestamp/source resolver, hosting, model, capacity, cost, SLO, owner of Qdrant/Object Storage and final Gate. No migrations, services or APIs were deployed by this package.

## Run actual validation (no model, external API or Secret)

From the repository root:

```bash
python -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v
```

Tests require Python 3 and `jsonschema==4.26.0` (with its own declared transitive dependencies). If not available, create a **separate disposable venv** and install `tests/phase3/contracts/requirements.txt` there; do not install packages globally or into Phase 2 environments. Tests use local JSON fixtures only; no network access is made by test code.

Result for the initial package authoring environment: `12 tests`, `OK` on Python 3.13.5 / `jsonschema==4.26.0` (details in `coordination/tasks/AGENT-CONTRACTS-01.md`). No live integration, RAG compatibility, backend DB policy, accessibility or product Gate claims follow from these results.

## Cumulative mission evidence and handoff

The supervisor-wide rule in [`AGENTS.md`](../../AGENTS.md) applies to all contract changes. **Every working push** affecting the product contracts must include an updated [`AGENT-CONTRACTS-01` mission checkpoint](../../coordination/tasks/AGENT-CONTRACTS-01.md) in the same change, with subtask `CT-xx`, source Module/section, baseline, changed files, rationale, exact commands and actual results, error/recheck record, pending work and links to task-owned evidence. Fixture/Schema artifacts under `packages/contracts/` and executable checks under `tests/phase3/contracts/` are the task-owned reproducible evidence; do not create a report per shell command.

**Handoff to Foundation:** Send `CT-01..CT-08` (and any subsequent mission subtask IDs) mapped to `P3M03`, `P3M04`, `P3M06`, `P3M10`, `P3M11`, `P3M12`, `P3M13`, `P3M14`, `P3M15` and `P3M21`, with check outputs/evidence paths. Specialist owners must not edit `coordination/phase3_checklist.md`. Contract Fixture pass is not acceptance of NB23, the producer, Module 00 or Module 03 Gate.
