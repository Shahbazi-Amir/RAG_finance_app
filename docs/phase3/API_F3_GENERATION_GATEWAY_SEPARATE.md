# API_F3 — Separate Generation/Gateway track (NOT Gate 3 Mac acceptance)

Baseline of this *separate* branch: `c02ba7896edb78febd2042f7afb1243f2a6aca34`.
This document is a source-grounded dependency gate, NOT approval or a working generated answer.

## Immutable invariants
- Mac Gate 3 must remain `API_RUNNER_EXECUTION_MODE=NO_DISPATCH_ONLY`, with no `--dispatch`, Gateway calls or T3.
- No type, metadata or source link can be invented from C018 `top10` or a stored Fixture.
- `packages/contracts/product.v1.schema.json` and `docs/adr/0006-live-history-provenance.md` prohibit presenting an unverified real answer as `LIVE_VERIFIED`.
- A real pre-release answer must not be persisted in Product History as `product.v1` Answer or disguised as `SYNTHETIC`.

## Already implemented but NOT equivalent to real Gateway
- `src/phase3/rag_runtime/dispatch_claim_bridge.py`: claim inside signed/fenced T2 with DB Migration 011; only a definitive COMMIT winner may perform a single external dispatch, no retries after unknown.
- `src/phase3/rag_runtime/result_contract_gate.py`: requires independently SHA-pinned full `rag_finance.mvp_engine_result.v1` schema and exact engine Attempt request ID; structural validation alone does not prove provenance.
- `apps/api/product_session_api.py`: fixture/CI dispatch branches are strictly separate from private no-dispatch service and cannot be promoted to paid/real dispatch.

## First blockers by owner
1. **ENGINE_F3**: exact audited C019/generation CLI or Gateway contract, full canonical JSON Schema and SHA256, model/producer identification, real error/timeout/unknown semantics, source attribution/Locator provenance, sanitized authenticated result (not synthetic).
2. **DATABASE_F3/DBA**: independently approved migration 011, restricted claim/reporter roles, recovery semantics, idempotent terminal result state, backup/restore and release/version compatibility.
3. **CENTRAL + Security/Contract/Privacy**: explicit generation authorization and cost cap, accepted Phase2 Release or separately approved staging-real versioned DTO, retention/consent/TTL/revoke/deletion, encryption and URL authority.
4. **FOUNDATION + UI**: approved isolated live-dispatch mode and network secrets, UI warning and client schema for an independently authenticated same-Attempt GET; no change to `api.no_dispatch_status.v1` and existing `api.retrieved_sources.v1`.

## Required negative/positive tests before a live dispatch
- Signed Owner A creates exactly one fenced T2 and one durable Claim after a definitively confirmed DB transaction.
- Owner B, stale/revoked sessions, wrong attempt/request/trace, invalid producer/locator/schema, and unapproved Release are denied.
- Timeout, unknown COMMIT, crash and replay never automatically dispatch again; GET/Refresh never calls Gateway.
- Any real paid/model operation and Product T3 run only after a *separate explicit authorization* and same-SHA CI/host evidence.

## Current verdict
`LIVE_GENERATION_IMPLEMENTATION=BLOCKED_UPSTREAM_SCHEMA_AND_APPROVAL`.
`GATE3_MAC_NO_GENERATION_UNCHANGED=YES`.
`REAL_GENERATION_CALLS=0`.
