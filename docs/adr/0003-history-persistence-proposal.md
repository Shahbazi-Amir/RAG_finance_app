# ADR 0003 — permanent conversation history and message persistence (PROPOSAL)

**Status:** **PROPOSED — NEEDS_API_DB_REVIEW**, AGENT-HISTORY-01, 2026-11-07. This is *not* a DB01-02 final decision, production API acceptance, Auth approval, Migration, RLS implementation or Module Gate PASS.

## Context, source and scope

- Same existing `product.v1` contract, including [CT-12 lifecycle](../../packages/contracts/README.md#ct-12--receipt--attempt--message--answer-persistence-lifecycle), [DB01-02 draft](../../coordination/tasks/AGENT-DB-01.md) and [UI Mock-only limitations](../../coordination/tasks/AGENT-UI-01.md). No second schema or service code.
- Mappings: `P3M03` shared DTOs/trace; `P3M04` conceptual data/keys; `P3M05` Auth pending; `P3M06` owner isolation/RLS; `P3M13` API/pagination; `P3M15` immutable messages/history. Module 00 and NB23 source/engine integration remain BLOCKED.
- Problem: a reliable owner-scoped list/message history and recoverable send operation requires stable client and server identities, separate HTTP attempt tracing, consistent ordering/cursor and explicit crash boundaries.

## Proposed logical contract and persistence boundaries

1. **Create empty conversation** with `client_conversation_id`, separate `idempotency_key` and nullable title; short atomic insert + scoped idempotency record. Replays return the original Conversation snapshot, new current HTTP trace, without creating another Conversation. Conflict on same owner/scope/key but different canonical client payload.
2. **Send message** retains old `send_message_request/send_message_receipt` fingerprint and original requested `conversation_id` (possibly null). In **T1 atomic transaction** allocate Conversation if needed, insert one User Message and persist Receipt/Idempotency record; both commit or neither. The response Receipt proves Message persistence, **not** Answer persistence.
3. **T1→T2 durable state:** represent as `persisted` with stable `resolved_conversation_id` and User `message_id`; Attempt fields empty. Read-only status allows deterministic lookup after disconnect. It must not launch a model or create a second Message.
4. **T2 short transaction:** create `attempt_id` tied to trusted owner and initiating Receipt, record `attempt_request_id` and `attempt_trace_id`, reserve `reserved_answer_id` as correlation-only (not an Answer), commit before any future external engine call. **For user message sends, recommend required Receipt→Attempt linkage**; non-message internal run exceptions require separate design. After ambiguous crash/timeout mark `attempt_unknown` and **do not automatically retry provider/model**.
5. **T3 short transaction:** only a genuinely validated terminal result creates **separate assistant Message** and Answer and binds `answer.message_id` to that assistant Message; `answer_id=reserved_answer_id` when committed. A crash before T3 leaves Attempt/status (not phantom Answer); after T3 commit, recovery reads the *existing* Answer. `attempt_unknown→answer_committed` requires authoritative T3 DB evidence; failed/cancelled states have no fabricated Answer.
6. **Identifiers:** stable `client_message_id` vs persisted User Message ID vs assistant Message ID vs Answer ID vs Attempt ID. Each incoming HTTP/status query has a **fresh trusted `request_id/trace_id`**. Historical Attempt `request_id/trace_id` remain separate. No internal id is automatically an NB23 input.
7. **Ordering/query:** Conversation `created_at DESC,conversation_id DESC`; Message `created_at ASC,message_id ASC`; server timestamps, bounded limit 1–100 default 20, `limit+1` has-more check and owner/resource/filter-bound signed opaque Keyset cursor with first-page high-watermark. A mutable `updated_at` is unsuitable as keyset order. Validate expiry/tampering/owner/query mismatch and reauthorize every page. Cursor signing secret lifetime and TTL remain open.
8. **Isolation:** authenticated server context (not client owner) gates all queries; read/write Owner predicates, RLS and relationship FK checks required in future DB task. Nonexistent/foreign or inaccessible IDs must be externally indistinguishable 404 without owner leakage. No unauthenticated/fixed-user production identity. Actual Auth/CSRF/session lifecycle is a separate employer decision.
9. **Deletion:** use existing `delete_command/delete_status`; suppress deletion-requested Conversations from ordinary list. Soft/hard deletion, Retention, backup and post-deletion access remain open; Export remains independent.
10. **Physical constraints to review:** uniqueness with nullable original `requested_conversation_id`, lock/CAS and concurrent first-send, transaction isolation and abort behavior, immutable hash/dedupe, TTL/collision/reuse horizon, Attempt lease/reconcile and crash/outbox policies, User/Answer foreign keys, owner-scoped joins and RLS. **No SQL/DDL or migration is authorized in this proposal.**

## API/DB acceptance questions (none frozen)

| Decision | Recommendation awaiting joint API/DB approval | Required proof |
|---|---|---|
| Conversation create scope | Stable `(trusted_owner,create_conversation,client_conversation_id,key)` + canonical SHA-256 payload | Concurrent 201/200/409 with one Conversation, no owner leakage |
| First send with requested ID null | Preserve literal null in original fingerprint; separately persist allocated resolved ID | Crash/retry and PostgreSQL nullable-key uniqueness |
| T1/T2 boundary and durable gap | T1 Receipt+User Message transaction, then T2 Attempt transaction; status `persisted` | Crash before/after each commit; reconcile without silent model call |
| Receipt/Attempt relation | Required for user message attempts; generic non-message attempts separate | DB ERD/Dictionary alignment and real FK/RLS tests |
| Answer reservation/commit | Reserve ID in T2; create Answer+assistant Message only in T3 | No phantom Answer on crash, exactly one committed pair |
| Cursor / sequence | Owner-bound opaque signed keyset with immutable timestamps+IDs; snapshot anchor | Mixed timestamp ties, concurrent append, forged/expired token |
| TTL/Retention, crash leases | Explicit employer/security policy and expiry/reuse semantics | Dedupe after TTL, deletion/restore and privacy tests |
| Auth | See two options below; **employer decision pending** | Positive/negative real session, revocation, CSRF, cross-user/ID enumeration |

## Auth choices for employer (not enabled)

- **Option A — recommended for evaluation:** standards-based managed OIDC / Authorization Code+PKCE with backend-for-frontend session. Needs vendor/data residency agreement, redirect security, session binding, revocation/consent and MFA policy. **Cost:** possible recurring per-active-user/provider fees plus integration/operations. **Security:** avoids storing application passwords but adds provider, redirect and token-handling risks. No vendor/plan/price authorized.
- **Option B — alternative:** first-party credential processing and server-side sessions. Needs secure password hashing, MFA, verified recovery/reset, brute-force protection, CSRF/session rotation, audit and human operations owner. **Cost:** no mandatory IdP subscription but higher ongoing engineering/security/support burden. **Security:** reduces identity-vendor transfer but materially increases breach/credential responsibility.

**Recommendation:** obtain employer decision on A vs B plus owner mapping, data residency, session expiry/revocation, post-account-deletion status and threat review **before** implementing live Auth/API/DB. Production fixed/anonymous user bypass is prohibited.

## Evidence, acceptance boundary and next packages

- [Contract README HISTORY-01 section](../../packages/contracts/README.md#history-01--executable-permanent-conversation-contract-proposed--needs_api_db_review), additive JSON Schema and SYNTHETIC fixtures. Isolated local `python -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v`: **31 tests PASS** (21 preserved, 10 new). No DB, network, model, service or RLS run. [Mission checkpoint](../../coordination/tasks/AGENT-HISTORY-01.md).
- **Proposed API package, not executed:** `apps/api/**`, `tests/phase3/api/**`, `coordination/tasks/AGENT-API-HISTORY-01.md`: server identity/authorization boundary and Versioned HTTP mapping using mocked Persistence, cursor/Replay/Conflict/Error/Status tests. Needs reviewed DTOs and employer Auth choice; no real NB23 calls.
- **Proposed DB package, not executed:** `src/phase3/storage/postgres/**`, `infra/postgres/**`, `tests/phase3/database/**`, `coordination/tasks/AGENT-DB-HISTORY-01.md`: transaction/RLS/PK/FK/idempotency unique/null/rollback/reconcile validation **after separate DB authorization**, joint API/DB decision and Retention. No physical DB01-02 finality now.
- **Explicit non-acceptance:** Module 00, 03, 04, 05, 06, 13, 14, 15, 19 Gates, live engine/NB23, multi-user DB/Auth, L2, security or product deployment.
