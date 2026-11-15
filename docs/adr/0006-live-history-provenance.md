# ADR 0006 — Live answer provenance and History before Release

Status: PROPOSED / REVIEW_REQUIRED / NOT_ACCEPTED (2026-11-15).
Source: Foundation Draft #35 FND-PROVENANCE-PRE-RELEASE-012-v1, strict product.v1; separate from staging operations, Dispatch, NB23 R11/R12 and Module Gates.

## Proposed disposition
Under existing `packages/contracts/product.v1.schema.json`, provenance.origin only allows `SYNTHETIC` or `LIVE_VERIFIED`. SYNTHETIC requires provisional NB23-blocked binding and null Release, producer_reference and source_fingerprint. LIVE_VERIFIED requires verified binding, non-null accepted Release, adapter_verified=true, real producer_reference and valid source_fingerprint. The user-reported Arvan/DeepSeek-generated Answer is not evidence of a verified Release or authentic, authorized Locator. Do not mark it SYNTHETIC or LIVE_VERIFIED without fulfilling exact conditions.

Before release, **only separately authorized redacted operational smoke evidence outside Product History is eligible**; a real answer/citation must NOT be persisted/served as a strict product.v1 assistant row. Decision state: `TEST_REGISTERED_LIVE_ANSWER_IN_HISTORY=WAITING_CONTRACT_DECISION`. Never fabricate Locator, author/page or producer receipt.

If History of pre-Release live text is required, propose a distinct opt-in versioned contract (candidate product.v2 with explicit LIVE_PROVISIONAL) covering no verified Release, bounded source state/receipt, privacy/retention/consent, UI warning, immutable DB event, v1 consumer rejection, API/DB/Contract/UI sign-off. This is NOT approved, implemented or an excuse to silently widen v1.

## Separate eventual LIVE_VERIFIED acceptance
Positive: accepted Phase2 knowledge Release/NB23, pinned engine/model/index/chunk/embedding/resolver digests, producer receipt, source fingerprint, opening an authorized Locator, correct credited_author/editorial_supervisor/speaker, same trusted Owner/Session/Epoch at atomic T3 and one result per attempt. Negative: no accepted Release; missing/spoofed producer/fingerprint; unauthorized or unresolved URL; invented attribution; revoked owner; duplicate/late Gateway receipt; unknown/timeout/cancel and browser refresh -> no forged verified row. A cannot read B. Evidence for R11/R12/Gates is independent and remains blocked until independently satisfied.

NO_GATE_CHANGE / NO_SCHEMA_CHANGE / NO_DEPLOY / NO_PAID_DISPATCH.
