# DATABASE_F3 — Physical ERD, active data dictionary, policy design contract v2
**Recorded:** 2026-11-23. **Status:** DRAFT — API/DB/Security/Owner approval required. Absolutely NO 012+ migration authorization or product acceptance.

## Source of truth and physical vs design boundary

The actual PG17.11 catalog is from [GitHub Actions 45202743968](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968), exactly tested source SHA 996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba, [artifact 14831408848](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968/artifacts/14831408848), file physical_erd_data_dictionary.jsonl, SHA256 03f1fba468680edad84e8901effc64f0b58c74ba8f4a3cbc0ecbffdf5bc74c8f. That source enumerates EVERY column/type/nullability, PK/FK/CHECK/UNIQUE constraint, index definition, policy USING/WITH CHECK and exact schema owner. This document groups the verified facts into a reviewable ERD and distinguishes proposed models, without pretending they already exist. 14 actual tables, 17 FKs, 38 indexes, 14/14 FORCE RLS, 8 auth_l1 and 6 history_l1 tables. Migration/bridge ledgers under db55_audit are internal and not counted among these tables.

## Actual physical 001–010 dictionary (all PG17.11, all FORCE RLS)

| Real table | Primary key and essential fields | Security and relationships |
|---|---|---|
| auth_l1.owners | owner_id TEXT PK, state, session_epoch BIGINT, reset_gate, created_at | private deny-direct RLS; owner lifecycle and monotonic epoch |
| auth_l1.identity_links | (issuer, subject) PK, owner_id UNIQUE, created_at | FK owner_id to owners; immutable link trigger; private deny-direct; sub alone is NOT a global identity |
| auth_l1.sessions | digest_sha256 PK, owner_id, session_epoch, generation, status, created_at, last_activity_at, idle_expires_at, absolute_expires_at, idle_seconds | FK owner; active/rotated/revoked/PENDING_BINDING; no raw bearer tokens; private deny-direct |
| auth_l1.service_assertion_replays | issuer_jti_sha256 PK, expires_at, consumed_at | hashed JTI + private deny-direct; durable replay fence |
| auth_l1.reset_c1_authorizations | authorization_sha256 PK, owner_id, kind, purpose, expected_epoch, session digest/generation, issued/expiry/consumed timestamps | FK owner; only recovery or authenticated reset; deny-direct |
| auth_l1.reset_c1_operations | operation_id UUID PK, owner_id, authorization_sha256, kind, purpose, expected_epoch, revoked_epoch, status, active, created_at | FKs owner/authorization, unique authorization, one active operation owner index; deny-direct |
| auth_l1.reset_idp_attempts | attempt_id UUID PK, operation_id, owner_id, authorization_sha256, revoked_epoch, outcome, outcome_code, times | FKs reset operation/authorization/owner; UNIQUE operation; UNKNOWN may not auto retry |
| auth_l1.initial_login_attempts | attempt_id UUID PK, BFF principal, start_key, state/initiator/request hashes, encrypted PKCE+nonce envelopes, state, owner_id, session_digest, receipt_id, epochs/timestamps | FKs owner+session; unique BFF principal+attempt/start_key, receipt/digest/state; deny-direct |
| history_l1.conversations | (owner_id, id) PK, title, state, created_at, updated_at | owner_only RLS; state active/deletion_requested; conversation_order_idx |
| history_l1.messages | (owner_id, id) PK, conversation_id, role, body, answer_id, created_at | composite FK owner+conversation, compound unique owner+conversation+id; message_order_idx; immutable event intent |
| history_l1.create_receipts | (owner_id, client_conversation_id, idempotency_key) PK, payload_sha256, conversation_id, snapshot | compound FK owner+conversation, owner_only RLS |
| history_l1.send_receipts | (owner_id,id) PK, requested/resolved conversation, user_message_id, client_message_id, idempotency_key, payload_sha256, request/trace, created_at | FKs owner+conversation and owner+conversation+user-message, unique NULLS NOT DISTINCT composite key, dedupe |
| history_l1.execution_attempts | (owner_id,id) PK, send_receipt_id, attempt request/trace, reserved_answer_id, state, error_code, created_at | compound FK owner+send; unique owner+attempt+reserved answer and one_attempt_per_send_receipt |
| history_l1.answers | (owner_id,id) PK, conversation_id, message_id, attempt_id, payload JSONB, created_at | compound FKs to owner+conversation+message and owner+attempt+reserved answer; unique owner+attempt and owner+message. JSON payload alone does NOT prove real Citation provenance |

All six History tables use owner_only policies. All eight Auth tables use deny-direct policies and trusted definer functions. Exact grants and role-to-function signatures: contracts/FOUNDATION_API_DB_CONTRACT.md and the physical catalog. NO physical FK between History owner_id and Auth owners is asserted; trusted identity mapping is a cross-service authorization contract, not an automatic FK.

### Actual foreign-key ERD (not future tables)

~~~mermaid
erDiagram
  AUTH_OWNERS ||--o| AUTH_IDENTITY_LINKS : has_mapping
  AUTH_OWNERS ||--o{ AUTH_SESSIONS : owns
  AUTH_OWNERS ||--o{ AUTH_RESET_C1_AUTHORIZATIONS : authorizes
  AUTH_OWNERS ||--o{ AUTH_RESET_C1_OPERATIONS : revokes
  AUTH_RESET_C1_AUTHORIZATIONS ||--o| AUTH_RESET_C1_OPERATIONS : token
  AUTH_RESET_C1_OPERATIONS ||--o| AUTH_RESET_IDP_ATTEMPTS : records
  AUTH_OWNERS ||--o{ AUTH_INITIAL_LOGIN_ATTEMPTS : initiates
  AUTH_SESSIONS ||--o| AUTH_INITIAL_LOGIN_ATTEMPTS : binds
  HISTORY_CONVERSATIONS ||--o{ HISTORY_MESSAGES : owner_conversation
  HISTORY_CONVERSATIONS ||--o{ HISTORY_CREATE_RECEIPTS : owner_conversation
  HISTORY_CONVERSATIONS ||--o{ HISTORY_SEND_RECEIPTS : owner_conversation
  HISTORY_MESSAGES ||--o{ HISTORY_SEND_RECEIPTS : owner_conversation_message
  HISTORY_SEND_RECEIPTS ||--o| HISTORY_EXECUTION_ATTEMPTS : owner_send
  HISTORY_EXECUTION_ATTEMPTS ||--o| HISTORY_ANSWERS : reserved_answer
  HISTORY_MESSAGES ||--o| HISTORY_ANSWERS : owner_conversation_message
~~~

AUTH_SERVICE_ASSERTION_REPLAYS exists physically but has no FK edge. This is a readable relationship diagram, not an exhaustive cardinality enforcement claim: use the exact catalog for nullable/unique constraints.

## Owner and session fence — joint API+Security decision still OPEN

Current SQL maps trusted external (issuer,subject) to immutable owner_id. The canonical roadmaps demand user_id or tenant_id on user data, but literal column rename is NOT approved. Preferred proposed equivalence is a stable internal logical owner, with server-controlled mapping, and explicit signature and version in API contract; NEVER take owner_id from untrusted client payload. Real transaction must validate signed product session digest+epoch/generation, reset_gate and trusted actor within the SAME History SQL read/write transaction; a previous independent GET-only session check does not prevent revoke races. SET LOCAL app.owner_id is an implementation aid, not independently trusted authorization; test malicious GUC, stolen session, worker privileges and cross-user guessing.

Owner A cannot read/update/delete Owner B rows or infer their IDs; foreign HTTP resources masked 404, revoked/expired session 401. Product runtime has two disjoint roles (history_app, auth_revoker), Bootstrap seven scoped roles, real TLS sslmode=verify-full and CA/SAN. Nine-role DB client verification over SSL in CI is NOT an authenticated HTTP/Mac runtime witness.

## Draft-only future domain relations — deliberately NOT created by 001–010

| Capability, unimplemented | Proposed candidate schema/invariant (NOT committed DDL) | Needed authoritative input |
|---|---|---|
| Consent and withdrawal | owner, consent_scope, consent_version, policy_version, granted_at, withdrawn_at, event state; grant/withdraw must be audited, withdrawals must fence future operations according to approved scope | API + Security + Owner select granularity, cutoff instant, propagation, revoked-session behavior and retention policy |
| Feedback to actual Answer | composite (owner_id,answer_id) FK to an owned COMMITTED Answer; rating/category with approved enum, payload hash, idempotency key, created time, concurrency uniqueness | API+UI+Owner decide whether multiple ratings/revisions possible; deny pending/foreign/nonexistent Answers and replay conflicts |
| Citation discrepancy report | FK to trusted Answer and to verified citation/locator only, owner scope | ENGINE+API provide real Q2 verified source locator and permission semantics; raw source_id is NOT validated Citation |
| Knowledge/retrieval/model/policy lineage | immutable versions and run IDs linked to one Attempt and Answer, with source permission/retention rules | ENGINE+API give accepted NB23 release and T3 lineage schema, proven real source authority |
| Audit and security events | owner/actor, server request/trace, event code, timestamp and redaction classification; no raw cookie, financial text or token | Security+Ops approve audit/event matrix, retention, alert and secret leakage tests |
| Deletion requests / tombstones | owner-scoped durable monotonic deletion authority independent of an old backup; request/effective/complete states and approved holds | Owner+Security+Ops approve real hard/soft erasure rules, legal holds, backup handling, cross-store propagation |
| Export | separate explicit owner-approved categories, downloadable lifetime, redaction/authorization and audit | Owner+API: Export is conditional; deletion is independent and must not be gated on Export |
| Backup catalog and retention | release/config pointers, schema manifest, source/restore PG system IDs, encrypted dump identity + checksum, key custody, retention and PITR/watermark | Ops+Security: numeric RPO/RTO, real workload, encrypted-at-rest/off-host key KMS/escrow, rotation, WAL/PITR and Qdrant safe snapshot |
| Phase4 financial profile/assessment/goal/action plan | RESERVED / DESIGN ONLY | No active Phase3 namespace, migration, API authorization or disguised scope expansion |

**Data resurrection is NOT solved** by a soft-state restoration test. A pre-hard-delete dump contains erased rows. A proposed acceptable recovery design stores authoritative deletion watermark/tombstones OUTSIDE the rollback snapshot, quarantines a restored DB until all later deletion obligations are reconciled, then runs source+HTTP+SQL negative tests; legal holds and permitted retention need signed policy. Test fixture: Owner A/B → backup → approved hard-delete A → restore old snapshot in independent cluster → replay signed deletion authority before startup → prove deleted A invisible, B intact, including interrupted reconciliation. No hard-delete SQL implemented in this scope.

## Evidence, performance, recovery and 011 boundary

- Run 45202743968 source cluster ID 7711385358965735485; restored second system ID 7711385478295212091; backup SHA256 24e01ee55b371a2611056f639de4f6c831b17aa5593c64ccf85872b6ba3f99e2. Restored Ledger entries retain SOURCE origin and timestamps, NOT a fictional re-run in restore cluster. DB55 profile private_no_dispatch PASS.
- Real EXPLAIN ANALYZE uses synthetic two-owner 2400 conversations / 4800 messages, Owner A 1200 visible, conversation_order_idx and message_order_idx. 0.050 ms/0.047 ms observed on fixture only; no approved production SLO, RPO/RTO or saturation claim.
- pg_dump -Fc with SHA256 and 0600 permissions + independent lab restore are NOT encrypted/off-host operational backup, key-custody policy, PITR, Qdrant snapshot, or full-app failover. Operations requires real-sized signed RPO/RTO and rotation decision.
- Optional 011 remains wholly separate from 001–010 NO_DISPATCH_ONLY; it does not prove paid Gateway. No source-verified T3 or Citation; no 012+ implementation until contract ratified.

## Reviewer acceptance inputs and exact regression gates

| IDs | Scoped CI evidence | Still required for acceptance |
|---|---|---|
| P3M04-A01/A02/A06/A07 | 14-table full catalog, 17 FK,38 index; fresh/preserved-populated upgrade and independent PG restore, guarded rollback/fault tests | DB+API sign actual ERD and conceptual gaps; test approved rows/volume and migration policy |
| P3M04-A03/A04/A05/A08 | trusted existing owner_id and opaque Answers | owner_id/user_id mapping, verified Citation/versions and delete/retention policy |
| P3M06-A01/A02/A03/A05/A09 | 14 FORCE-RLS, role-negative 72/72; synthetic two-owner SQL | signed Mac A/B same-session fence, GUC/worker/IDOR/HTTP 401/404 suite |
| P3M15-A01/A03/A04/A05/A07/A08/A09/A10 | History and soft deletion_requested preserved in independent restore | live Answer/Feedback, hard-delete anti-resurrection, export and replay policy |
| P3M22-A01/A04/A05/A06/A07/A08/A09/A10 | independent PG restore+checksum and Ledger fault injection | real encrypted + rotating off-host backup, Qdrant snapshot, PITR, approved RPO/RTO and failure drill |

**Next single joint API+Security+Owner contract required:** immutable owner/session fence; Consent version/withdrawal, Feedback FK/rating/idempotency, deletion+tombstone post-restore, Citation and version lineage, Audit/Export, numeric RPO/RTO and backup encryption/custody. After signed choices, DB can propose separately pinned 012+ changes and tests on fresh/populated disposable PG, negative RLS/grants, and encrypted restore. Until then PROPOSAL ONLY; GATES NOT ACCEPTED.
