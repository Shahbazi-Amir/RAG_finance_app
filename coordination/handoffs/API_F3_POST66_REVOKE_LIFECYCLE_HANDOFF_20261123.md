# API_F3 → Foundation / DB / UI / CENTRAL — tested revoke peer fence and pending lifecycle contract

**2026-11-23 | DRAFT | NO NEW MODULE ACCEPTANCE | NO MAC L2 | NO PAID MODEL**

## Version/source matrix (do not confuse environments)

| Owner/source | Baseline | Tested SHA | Current relevant PR SHA (observed) | Actual Mac deployed |
|---|---|---|---|---|
| API runtime #61 | `5fe21e922b5e6570e319cf528fc481a96a4c8e9e` | `c02ba7896edb78febd2042f7afb1243f2a6aca34` / 275 historic L1 | #61 `c02ba7896edb78febd2042f7afb1243f2a6aca34` | NOT_OBSERVED |
| API patch #66 | #61 `c02ba7896edb78febd2042f7afb1243f2a6aca34` | `d6d36bd078266f2e1f21ebd54b23011f6ee17c5a` / [run 45209235334](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209235334) | SHA may change with evidence-only handoff commits; inspect PR #66 | NOT_OBSERVED |
| UI #65 | #62 `86bf2c2f1a0491d20496c704dbdfe3f9f1696d85` | not re-executed by API owner | `ac0e7159e6c7d673fb5607c0b7824a0981f7ceef` | NOT_OBSERVED |
| DB #59 | intermediate handoff `996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba` | not re-executed by API owner | `5b0f14d06bf37b8b20926a3db491344b22daac05` (latest 2 commits docs-only) | NOT_OBSERVED |
| Foundation #64 | `c2edbbf87f02ff2cfb8ba12a0a9594533324fd28` | `d6dc01df5835cca8a97a778b091b769496646abb` / [source CI 45201093424](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45201093424) | #64 SHA above; not integrated with API #66 | NOT_OBSERVED |

All listed Green CI relates to its own source and environment only. Foundation #64 already reconciles **262 numbered P3M activities, 26 independent Gates, 105 P3OP operational aliases**, including the extra two P3OP01-R06/R09; do not redo counts. The 91 API-owned starting rows (61 PARTIAL, 30 NOT_VERIFIED) are mapped individually in [API 91-row CSV](API_F3_91_ROW_L1_SOURCE_MATRIX_20261123.csv). The only new direct mock-L1 test coverage from this PR is a **subcase** of `P3M05-A07` and `P3M13-A08`; neither entire row nor its Module Gate is accepted.

## Exact API security fix and tests

- File: `apps/api/product_session_api.py::session_revoke_one`. Before parsing proof or touching PG `auth_revoker`, require `_PRIVATE_STAGING_PROFILE.allowed_peer(request.scope)` if private staging is installed, matching `_signed_history`. Reject with 401 on absence. Forged `X-Forwarded-Client-Cert` headers do not influence the accepted transport scope.
- Test: `tests/phase3/api/test_revoke_peer_boundary.py`, three cases: untrusted HTTP peer/spoofed headers 401 with ZERO Auth/DB access; simulated trusted peer signed/fenced revoke 200; same mock signed path but DB refusal 401.
- CI [45209235334](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209235334): **3/3 targeted PASS, 137/137 full API PASS (includes targeted 3), 38/38 shared contract PASS; `pip --require-hashes`, `pip check`, `compileall` PASS.** Real TLS and PG/IdP were not exercised.
- Existing `api.no_dispatch_status.v1` and `api.retrieved_sources.v1` unchanged; no Runner, Gate, Gateway, T3, migrations, PII, secret or Product answer change.

## Single versioned lifecycle-contract decision request — PENDING, not yet implemented

**CENTRAL/Product/privacy owner must make the one authoritative decision for DB, API and UI** on consent/withdrawal, feedback, report-a-source, deletion/retention/restore and conditional Export. Freeze the decisions with approval SHA/date before API publishes a binding schema or DB creates 012+.

| Domain | Proposed HTTP/API boundary (NOT implemented or approved) | Required source of truth | Decision needed |
|---|---|---|---|
| Consent / withdrawal | Versioned owner-scoped signed POST of current consent policy, read-only GET of effective current state; one idempotency key for each transition | DB-owned immutable policy-version event and effective state in same valid Product session transaction | Consent text/version, scope(s), time semantics, refusal/withdrawal impact on in-flight T1/T2 |
| Feedback | Signed POST of positive/negative plus approved error taxonomy tied to an existing verified owner-specific `answer_id`; GET own feedback | DB owner/Answer FK and unique idempotency with sanitized event | Feedback categories, retention/PII limits, handling no real T3 Answer |
| Citation/attribution issue | Signed report bound to approved source + claim/Answer, never turning technical C018 `source_id` into a verified locator | Only accepted Product Answer claim/citation relationships | Reporter scope, attribution dispute category and moderation lifecycle |
| Delete/retention | Owner-only signed delete request with idempotent status polling and irreversible tombstone/revocation policy | DB lineage + backup restore anti-resurrection, audited status and actual TTL scheduling | Soft vs hard delete deadlines, legal holds, restore reconciliation, session/revoke policy |
| Export | Explicitly **CONDITIONAL**, not prerequisite to deletion | DB/Privacy approved data classes and audit | Include/exclude Export in current MVP, format/TTL/signed download expiry |

**Suggested candidate behavior for review, not a version freeze:** errors 401 (invalid session), 404 (cross-owner masking), 409 (same key/different semantic payload), 422 (closed schema), 503 or explicit unknown (uncertain transaction). Exact DTO names, endpoint names, state values, retention time, scopes and DB migration number **remain TBD** until the above approval. Never treat a Source ID as a Verified citation or permit an unattested synthetic Answer to receive a real-feedback event. Export may be deferred independently of deletion.

### Required cross-team acceptance tests AFTER decisions

1. Same valid Product owner+session/epoch and PostgreSQL fenced transaction for every write; replay of identical idempotency key returns same receipt, payload conflict 409; B user masks 404 without information leaks; stale/revoked old epoch 401.
2. A real committed Answer must be verified against accepted T3 Producer/provenance before feedback/citation claim; no fixture or raw C018 source can become an authoritative Answer.
3. Withdrawal racing with send must have a specified, tested linearization point; retries after ambiguous commit never silently duplicate a destructive write.
4. Backup restore must preserve deletion tombstone and prevent reappearance; retention TTL and encrypted audit must match approved policy with sanitized trace and no user PII in public logs.
5. Browser UI #65 must consume exact public versioned schemas, distinguish PENDING/UNKNOWN/COMPLETED states and be safe on Refresh, owner switch, 401, 404 and malicious strings.
6. Regenerate Version/Schema and integration CI on exact combined API+DB+UI SHA; Mac L2 with real mTLS, OIDC and role grants is separately required.

## One precise Foundation/Ops real Mac no-dispatch request

Required input: **authorized isolated** candidate compose/project/network/volumes/ports, pinned API #66 + UI #65 + DB #59 integration SHA/OCI digests, actual redacted Ops startup traceback (no invented cause), approved service UID/C011/C018 hash and DB role/verify-full credentials delivered via secure runtime secret pointers (never in PR), real signed BFF and Keycloak OIDC A/B sessions.

Required sanitized receipt after explicit Mac operations approval: HTTPS 202 first POST + durable same-owner T1/T2, OS **one and only one** attested C018 child, `CONTEXT_READY`, top10=10, generation_calls=0, dispatch=false, answer=null, same Attempt/Trace GET-only Refresh (POST2=0, OS2=0), replay200 same T2, B404, revoked401, timeout/UNKNOWN no resend. Capture timestamps/SHAs, pseudonymized identifiers, exact test failures and no secrets. If C018 cannot run, mark its subsection NOT_RUN; do not fake it from archived Q2.

## Separate Generation/Gateway hold

`API_RUNNER_EXECUTION_MODE=NO_DISPATCH_ONLY` remains. Phase2 Release/NB23 Gate00, C019 producer and typed member locators, authorized DB011 claim, model/provider/price/token budget, privacy/retention and CENTRAL signoff are still prerequisites for *any* real Generation or Product T3. No paid API or Arvan deployment has occurred in this branch.

**Next status:** PR #66 L1 source fix **TESTED**, Mac L2 **NOT_RUN**, 91 API rows **not all individually accepted**, 26 Gates **NOT_ACCEPTED**; acceptance progress cannot be calculated from the 137+38 test count.
