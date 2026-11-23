# UI_F3 → API/DB candidate contracts — **PROPOSED v0.1; NOT a shipped wire schema**

**Status:** `CANDIDATE / OWNER_REVIEW_REQUIRED / NOT_API_CONTRACT / NOT_DB_MIGRATION`. Dedicated consumer draft only. Nothing here enables production UI buttons, routes, model dispatch, or legal consent. Supersedes no `product.v1`, `api.retrieved_sources.v1`, or signed `NO_DISPATCH_ONLY` envelope. API/DB/Product/Legal and Foundation must return approved **schema/blob SHA, endpoint, authorization design, error codes and tests** before UI imports any field in shipping paths.

## Roles and cross-cutting invariants (all 3 consumers)

- **Actor:** signed BFF server authenticates one active, revocable Owner/session from HttpOnly cookie via OIDC; API verifies BFF RS256+mTLS, epoch/generation, audience, method/path/body hash and independent DB row ownership. `owner_id`, `session_id`, `actor`, `scope` in an untrusted body/query MUST NOT override identity. Support/admin role and audit scope are a separate Product/security decision.
- **Transport:** HTTPS same-origin Browser→BFF with CSRF on mutations and a server-signed BFF→API call; `Cache-Control: no-store`; correlation IDs are server-issued; log redacted. Do not add synthetic proxy adapters in shipping UI.
- **Idempotency:** opaque client operation key bound to owner+action+resource+payload hash+policy-version, backed by transactional unique record. Same key and same payload returns original receipt (not a second write); same key different payload returns 409; retry on network UNKNOWN is **status GET only**. Session revocation may produce 401 rather than expose another account's receipt. Browser tab sessionStorage stores only non-secret operation correlators if and only if policy approves.
- **Common errors to approve:** 400 malformed, 401 no/expired/revoked session, 403 role or policy denial, 404 foreign/absent resource (never enumerate other owner), 409 idempotency/version conflict, 412 stale precondition, 422 semantic validation, 429 rate, 503 unavailable/unknown. No UI may render `success` on 202, timeout, 503 or unverified receipt. Timeouts do not authorize repeated POST.
- **Exact correlation and rollback:** API/DB must return owner-signed scope, server receipt ID, server UTC timestamp, request/trace IDs and terminal status; UI only trusts schema-validated owner-bound receipt and must discard it after logout, owner change or a stale epoch. State transitions and storage must be tested under concurrency, revoke, restore and repeat key.

## UI-04 — Consent / Privacy candidate `ui.consent.candidate.v0_1`

| Item | Candidate requirement / unresolved owner decision |
|---|---|
| Actor | Valid owner, current OIDC session; user action only, never pre-checked, background-only or inferred from login |
| Precondition | Product/Legal publishes immutable `policy_id`, `policy_sha256`, `locale`, effective time and approved exact Persian text. API/DB has agreed version-to-owner persistent ledger. |
| Read | Proposed owner-scoped `GET /v1/account/consents/current` returns current version/status. Missing/read failure means `UNKNOWN` not implicitly granted. |
| Write | Proposed `POST /v1/account/consents/decisions`, body `policy_id + policy_sha256 + decision=ACCEPT/WITHDRAW + idempotency_key`; no owner fields. Require CSRF and consent-specific replay fencing. |
| Status | Proposed `GET /v1/account/consents/operations/{receipt_id}`, owner-bound; 202 `PENDING`, terminal `ACCEPTED_COMMITTED` / `WITHDRAWN_COMMITTED` or `REJECTED`. Exact version conflict 409/412; 401/404 after revoked/foreign owner. |
| Consequences | Withdraw and policy-version change must reflect new legal gating: which actions are blocked and whether existing History remains readable require Product decision; no fabricated deletion or tokens revoked just because consent withdrew. |
| Persistence | DB append-only versioned decision+actor+UTC hash+consent text hash; retention period and deletion exceptions must be approved; access audit without PII; restore must preserve effective withdrawal. |
| UI now | `/account` only read-only **blocked shell**; no checkbox/accept button and no legal statement of current consent. |

## UI-09 — Feedback / Answer issue report candidate `ui.feedback.candidate.v0_1`

| Item | Candidate requirement / unresolved owner decision |
|---|---|
| Actor and precondition | Same authorized owner of a **validated and persisted LIVE_VERIFIED** Answer; `answer_id`/claim/citation IDs must all belong to that Answer and session; synthetic retrieval observations and `answer=null` cannot create Feedback. |
| Write | Proposed `POST /v1/answers/{answer_id}/feedback` with `idempotency_key`, `rating` (POSITIVE/NEGATIVE), `reason_code` (including BAD_CITATION/BAD_ATTRIBUTION/OTHER), optional policy-bounded text and evidence IDs. No owner selector and no arbitrary URL. |
| Read | `GET /v1/answers/{answer_id}/feedback/operations/{receipt_id}`; 202 pending `NOT_SAVED`, only committed server receipt `FEEDBACK_COMMITTED` means saved, 409 conflicting duplicate, 401/404 owner mismatch. |
| Race | Duplicate click, same answer in two tabs, parallel approval, revoked session and deletion-in-progress must be atomic; error/timeout must not silently double insert or claim accepted. |
| Persistence | DB unique dedupe on owner+answer+operation key, immutable Answer foreign key, category, consent/legal basis, bounded text and redacted audit. Retention/deletion cascades, evaluation export excluding PII need explicit policy and backup restore tests. |
| UI now | Only disabled/read-only status, **no feedback write or receipt**; blocked pending API+DB+validated live producer. |

## UI-13 — Deletion/Account request candidate `ui.deletion.candidate.v0_1`

| Item | Candidate requirement / unresolved owner decision |
|---|---|
| Actor and precondition | Authenticated owner with **fresh step-up challenge**, server-side anti-CSRF and explicit confirmation for the exact target; no support/admin scope assumption. Concurrent active jobs or History visibility must have a declared policy. |
| Write | Proposed `POST /v1/account/deletion-requests`, `idempotency_key` plus server-issued confirmation challenge token, no user_id in body; 202 only means recorded `DELETE_REQUESTED` not `deleted`. |
| Read | `GET /v1/account/deletion-requests/{receipt_id}`; scoped status `DELETE_REQUESTED → DELETING → DELETED_COMMITTED`, or `REJECTED/UNKNOWN`. Revoked session requires explicit separate limited status mechanism approved by policy; never leak foreign status. |
| Terminal | Only verified `DELETED_COMMITTED` with DB transaction, storage purge inventory, downstream job cancellation, session alias invalidation and restore-tombstone attestation may show success. A partial failure remains `PENDING/UNKNOWN`; do not claim full purge after 202. |
| Recovery | DB tombstone/high-watermark must survive restore: no resurrected deleted history/feedback, no old session reactivation; test in isolated PG restores and racing pagination. |
| Retention | Specify legal hold, backup retention, minimal privacy-preserving audit, delayed erasure notice; Product/Legal/DB decision required. |
| Export | Independently approved product scope and separate typed signed endpoint. If unapproved, UI remains disabled while deletion is still handled by its own approved policy. |
| UI now | `/account` only read-only blocked shell; **zero** delete/export POST. |

## UI-07/08/10 producer/stream/citation interface review — separate candidate

- **Existing current wire**: `product.v1` for persisted History and Answer, pinned `api.retrieved_sources.v1` for observed technical chunk/source IDs with `source_validation=UNVERIFIED`, `verified_locators=[]`, `generation_calls=0`. **No** verified Citation, generation or promised Source URL follows from the technical receipt. Original three correlators and T2 Attempt remain fixed; owner B gets 404, expired alias gets 401, wrong Attempt/Trace invalidates rendered evidence.
- **Answer/Claim**: API+Phase2 must deliver a real producer whose `answer_id` is pinned to the same persisted T2 and whose Claim→Citation links and permissions are independently attested by authorized resolver. Distinct site/book/Transcript source kind, page/time, direct author vs editorial supervisor vs speaker, displayed title origin and URL safety; no client guess or fabricated confidence score. `confidence=null` stays uncalibrated; Producer supplies calibration method/version and evaluation receipts before numeric confidence.
- **Streaming proposal:** `ui.stream.candidate.v0_1` `GET /v1/message-requests/events?{original_three_correlators}`, owner/signed T2, non-secret monotonically increasing `sequence`, bounded resume cursor; producer states `QUEUED/RETRIEVING/GENERATING/PARTIAL/COMMITTED/FAILED/UNKNOWN/CANCELLED`, out-of-order/duplicate rejects, and terminal payload only after validated Answer/Claim. Cancel is a separate idempotent authorized POST `/v1/message-requests/cancel` keyed to same T2, with `CANCEL_REQUESTED` distinct from actual server `CANCELLED`; `COMMITTED_BEFORE_CANCEL` is a valid race outcome. Closing EventSource or the tab is not server cancel. Refresh GET only; no resend after UNKNOWN. **No producer endpoint exists in the approved UI transport today; this is review-only.**
- **Fixture rules:** `tests/phase3/ui/fixtures/ui-f3-contract-candidates.v0_1.json` is deliberately `fixture_only:true` and `approved:false` with no real URL, owner or legal content. Positive/negative Node tests only check that draft candidates cannot be mistaken for shipped contracts. A real implementation must replace these fixtures with API-signed contracts, DB writes, and L2 Mac actor receipts, not merely enable buttons.

### Acceptance request — API/DB/Product/Phase2/FOUNDATION

API: decide whether these route shapes, state enums, version and error code semantics can be frozen; provide **repository branch, exact 40-hex SHA, JSON Schema/OpenAPI paths, signed ownership negative tests, duplicate/unknown/cancel/revoke cases**. DB: same for migration/table/RLS/persistent idempotency/tombstone/restore, PG17 URL policy and receipt SHA. Product/Legal: signed Persian consent text/version, effective gating & retention, deletion/Export policy, feedback labels and step-up. Phase2: real Claim/Citation/Locator producer with accepted upstream release. Foundation: signed integrated candidate SHAs and actual Mac HTTPS A/B C018 one-child same-T2/zero-post-refresh receipt; stage only after separate authorization. All Gate/14 UI acceptance remain **NO** until target tests and owner decision.
