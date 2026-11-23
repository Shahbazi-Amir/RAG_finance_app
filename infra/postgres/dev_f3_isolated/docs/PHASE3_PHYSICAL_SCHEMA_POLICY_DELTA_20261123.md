# DB-F3 | Proven physical schema vs Phase3 scope — decision-bound delta (2026-11-23)

**Status:** PROVEN_BASE_001_010 / UNAPPROVED_NEW_SCHEMA / NO_012_CREATED. This is a schema-contract gap analysis, **not** a request to relax Owner/RLS guarantees, accept live Mac, or assume employer privacy policy. Foundation remains sole editor of the canonical `coordination/phase3_checklist.md`.

## Verified physical baseline

Source chain is immutable `001–008@d93dcf7cbf9290acd4cd3aa0164ef05689049da4`, `009@656604356dadea953031fcdb74650a5d42df4e9b`, `010@1678e87b7984094b74ec995383b8d4383e5f5ae7`, with 20-row Manifest SHA256 `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7`.

**History (`001_history_l1.up.sql`, blob `b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5`):** `history_l1.conversations`, `create_receipts`, `messages`, `send_receipts`, `execution_attempts`, `answers` = **6 active tables**, common `owner_id`, composite owner FKs, `UNIQUE NULLS NOT DISTINCT` for original requested Conversation, scoped `history_app`, owner-only RLS using trusted transaction `app.owner_id`, FORCE RLS.

**Auth:** `auth_l1.owners`, `identity_links`, `sessions` (003 blob `3eec77219a2462136b71b65dcae6e6a2b7998e90`); `service_assertion_replays` (005 blob `2899613dfc5ccac82733e35a5885635c969d99a5`); `reset_c1_authorizations`, `reset_c1_operations` (006 blob `98879f4dea04c49db5a4a0e429ef169c6823154d`); `reset_idp_attempts` (008 blob `a94183aeac661476d4462e4a2f766a84e1dd8d32`); `initial_login_attempts` (009 blob `2a694f871bf45aa5540b458bcaea1b2bd343036d`). **8 Auth tables**. 010 is function-only; `claim_initial_login_exchange_material` is function-only scoped role, not a table.

**CI:** Run `45082326382` (source `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74`): PG17.11 14 tables/30 routines, TLS 9/9, scoped role privilege negative 72/72, DB55, both original App DB preflight functions, independent restore with same 10-row migration ledger and different cluster ID PASS. Run `45108041850` (source `fcdc8e2de69684f3a5cd804f58a564e7772ba10a`): isolated `009/010` rollback with live attempt evidence refused, empty clean DOWN/UP revalidated DB55; synthetic owner FK, NULL dedupe and read/write RLS negatives PASS. **This proves neither real user deletion nor live ASGI HTTP.**

## Exactly what is missing (do not silently create DDL)

| Capability | Current actual DB/API source | Decision and acceptance gate before a versioned additive migration |
|---|---|---|
| Consent version + withdrawal | No dedicated `consents` table in 001–010. Provisional ERD only in `AGENT-DB-01.md`; real OIDC Auth may set owner but does not define consent persistence. | **Owner+Privacy+API:** consent types, effective text/version, withdrawal consequences, identity owner, audit event, enforcement endpoint. Test withdraw blocks access and survives restore without resurrecting permission. |
| Feedback + idempotent submit | `product.v1.schema.json` contains `feedback_submit_request/receipt` and kind `feedback`, but deployed `apps/api/history_api.py` routes only Create/Send/List/Message/Status, `apps/api/product_session_api.py` has no feedback route. No feedback table in 14. | **API+UI+DB:** stable answer-to-owner join, payload/rating/reason enums, request uniqueness, conflict/replay, failed transport UNKNOWN, security/PII policy. Only then decide `feedback`, `feedback_submission_idempotency` etc in 012+. |
| Delete/retention/tombstone | Conversation `state='deletion_requested'` is a scoped lifecycle state; NOT hard/soft purge, export, or backup-resurrection protection. `product.v1` `delete_command/delete_status` are provisional wire kinds; no standalone `deletion_requests` table in 14. | **Owner+Security+API:** soft/hard/delete legal hold, post-revocation status, proof of erasure, tombstone lineage and restore delta reconciliation; test absent rows remain absent after backup restore. No speculative cascade/delete SQL. |
| Audit/security events | Auth replay, reset and one-time SQL ledgers are real but not general `audit_events`/`security_events` tables; private DB Ledger is for migration attempts not user activity. | **Security/Ops+API:** event schema, actor and target, PII/trace redaction, TTL, alert, access/no administrator blanket SELECT and post-deletion evidence. |
| Citation and version lineage | No `citations`, `retrieval_runs`, `model_runs` or `knowledge_releases` table in 001–010; `answers.payload` is JSON, not verified citation or version storage. API #61 source IDs are explicitly unverified and non-clickable. | **Engine+API:** true C018 Q2 source/chunk/locator authority, versioned knowledge/model/policy, complete T3 output, retention/access; no fabricated provenance. |
| `user_id` vs `owner_id` | Schema uses trusted `owner_id` on History and Auth owner mappings. Phase3 roadmap says `user_id`/tenant. | **API+Security+DB:** declare canonical equivalence, forbid client-controlled owner, align any future aggregate FK and RLS. A schema column rename without review is not allowed. |
| RPO/RTO and encrypted backups | Logical `pg_dump -Fc`, sha256 and independent restore tested, but ephemeral lab secrets/CA, not encrypted cross-environment backup/PITR; no numeric goals. | **Owner+Ops/Security:** RPO/RTO numeric window, encryption/KMS/key escrow, backup retention/rotation, Qdrant consistency and realistic data volume; measure end-to-end after decision. |
| Phase4 namespace | Approved **design-only**, `financial_profiles`, `assessments` etc must NOT become active Phase3 tables. | No SQL before separate Phase4 acceptance. |

## New-Migration decision

`011_external_dispatch_claim` is tested in a **separate disposable DB and branch**; do not add to `private_no_dispatch`. Its provider-safe Claim/UNKNOWN logic does not establish a live paid Gateway.

`012+`: **NOT_AUTHORIZED_AS_IMPLEMENTATION**, because no final API endpoint/retention/consent/full Answer production contract exists. When owner inputs arrive, require new versioned `UP/DOWN` files, correctly pinned Git Blob + SHA256 manifest extension, FK and owner checks, grant/force RLS matrix, explicit rollback policy that refuses erasure of user evidence, SQL tests on **empty and populated disposable DB**, backup/restore and downstream API contract test, only then request merger.

## Precise handoff / acceptance split

- Source and CI evidence: Draft PR #59, plus `docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md`.
- Required Foundation/Ops **real Mac** receipt: integrated immutable SHA, actual Product/Bootstrap HTTP processes + BFF mTLS/OIDC, selected TLS/SAN and seven+two database roles used by those processes, database/Volume fingerprint, A/B isolation and real C018 one spawn/no dispatch. Mac tools not accessible here.
- Existing accepted Mac DB `rag_finance_f3_demo`, volume `rag_finance_f3_demo_pg17_20261121` are untouched. DB55 exception regarding missing historical migration ledger **does not create a historical Ledger**.
- `foundation.dba_admission.v1` for the demo is separate from CI/dev ephemeral ledger. No rewriting either receipt is authorized.
