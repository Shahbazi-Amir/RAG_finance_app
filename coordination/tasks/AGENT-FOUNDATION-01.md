# AGENT-FOUNDATION-01 checkpoint

**Status: REVIEW (foundation documentation); NOT ACCEPTED.** Branch `prep/foundation`, initial `main@bd5e365e9ad3f39ba4c1e5a44f1d9e217b613158`. Read-only source `RAG_finance@7c74783c3dcda897b010ba9ea358d113f172ed1f`.

## Completed

- Initial repository only README; created foundation branch. Prior commits `05d3062` and `660566e` copied five roadmaps, two Draft schemas and C011 selected guide.
- **Historical checkpoint (superseded; prior to manifest completion):** User had paused source transfer. At that time SHA-256 manifest and Mac transfer decision were still pending. Both were resolved in Checkpoint B; current manifest is complete and eight copies remain unchanged.
- Read five roadmaps, NB23 request/response, selected C011 guide, C012 saved output, metrics and execution/guardrail context.
- Prepared shared README, AGENTS, ignore, architecture/ADRs, ownership, 26-module + 11-package single-count canonical checklist, open decisions and draft product contract boundary.

## Checks and gaps

- Actual GitHub branch and initial HEAD verified; no local Mac Git inspection.
- NB23 C012 `upstream_release_accepted=false`, `accepted_for_phase3=false`, `formal_readiness=BLOCKED`. Tests in notebook are Draft fixture tests, not live runtime verification.
- 26 module IDs, 11 operational cross-references and all checklist entries unaccepted. Product code and integration tests: NOT_RUN.
- **Historical pending items (superseded in part):** Transfer method and the source manifest were resolved; specialist UI/DB checklists are now recorded. Still pending: Foundation supervisory acceptance, accepted Phase 2 Release/Module00, employer scope/auth/privacy/SLO decisions and specialist execution authorization.

**Implemented:** documentation and prior reference copies only. **Tested:** document/source structural checks only. **Accepted:** no; supervisor pending.

## Checkpoint B — Source provenance verification (2026-11-05)

- User reports the `660566e` reference bundle is received on their Mac and working tree is clean; direct local verification was not available to this agent.
- Manual transfer is canceled. No new source copies created or existing references rewritten.
- Created `references/phase2/source_manifest.json` with all eight copy source paths, pinned commit, exact matching Git Blob SHAs, independently calculated SHA-256 and byte lengths.
- Verified SHA-256 helper against published test vector and checked C011/request/response hashes against NB23 saved outputs. GitHub remote source/copy equivalence verified. This is a documentation integrity check, not Module 00 acceptance.
- Pending: governance/checklist wording cleanup; final PR review.

## Checkpoint C — operational gates and provenance documentation

- Source transfer restriction lifted: user confirms `660566e` obtained on clean Mac checkout; no files copied again. The eight copies are pinned by Git Blob SHA and copy SHA-256 in `references/phase2/source_manifest.json` (remote GitHub verification only).
- Replaced synthesized operational summary with 11 real source-package acceptance records, quoting source Gate text and listing actual package activities and mapped modular IDs. Canonical Module 00–25 items remain unchecked, and no progress is counted twice.
- Updated governance/docs to distinguish confirmed user-local status from independently verified GitHub status. Phase 2 and NB23 remain BLOCKED for formal Module 00.
- Checks: 26 Module IDs, 11 operational IDs, none checked; source package Gate present in all 11. No product code, tests, API, model download, deploy, paid operations or migration.
- Next: verify changed paths/Markdown/JSON, update Draft PR and submit for supervisory review.

## Final foundation handoff — READY_FOR_REVIEW (not accepted)

- **Starting head:** `main@bd5e365e9ad3f39ba4c1e5a44f1d9e217b613158`. **Working branch:** `prep/foundation`; Draft PR #1 targets main and remains unmerged. Final commit is the HEAD of that PR once this checkpoint update lands.
- **Implemented:** governance, README, proposed architecture/ADRs, contract separation, ownership, canonical Phase 3 checklist and source integrity manifest. No running product stack.
- **Checks performed:** complete GitHub tree inspection; eight reference Git Blob SHA pairs match upstream; SHA-256 recorded for eight pinned copy contents; three NB23 content digests cross-checked; JSON manifest parsed; module IDs P3M00–P3M25 present exactly once; operational IDs P3OP01–P3OP11 present exactly once; all reference links in checklist resolve; 39 checklist items unchecked, zero checked.
- **Not executed:** app build, unit/integration/security/end-to-end, notebook replay, live API/model, migrations, paid operations or deploy.
- **Acceptance:** supervisor review pending; no Phase 2 release acceptance, no NB23 formal readiness, no Module 00/01 pass.
- **Open:** accepted Phase 2 handoff, finalized auth/privacy/retention/export/hosting/budget/SLO, role assignment for production operations and specialist integration contracts. UI/DB/API planning can proceed in separate task records without duplicated checklist credit.

## Checkpoint D — supervisor correction package (approved UI v1.1 / DB v2)

- Confirmed branch HEAD before changes as `dffc16146418b78c8b36be3e1610f34a731e6c2b`, Draft PR #1 open and unmerged. The original reference files and manifest were not rewritten or recopied.
- Added `coordination/tasks/AGENT-UI-01.md` (14 unchecked specialist acceptance tasks) and `coordination/tasks/AGENT-DB-01.md` (18 unchecked tasks); each links to canonical P3M IDs and keeps onboarding approval strictly separate from implementation/Gate approval.
- Defined non-overlapping UI/API/PostgreSQL/shared document/test paths. DB owns product PostgreSQL, not Qdrant or Object Storage; final human operations ownership remains assignment pending.
- Removed P3M00 circular dependency; classified P3OP02 Phase 4 entities as reserved/deferred, not active MVP tables. Kept all modular Gates while making operational packages and cross-cutting items non-counting overlays. Kept Streaming/Cancellation requirements while distinguishing Mock testing from unverified live runtime.
- Marked illustrative SLO figures proposed/nonbinding inside the relevant checklist rows. Deletion remains independent of Export scope approval. Historical transfer/manifest notes explicitly labeled superseded.
- **Implemented:** foundation documentation only. **Checks:** structural Markdown, ID/link/Gate and Git tree checks (see PR description); product tests NOT_RUN. **Accepted:** specialist onboarding checklist revisions only; no activity executed, no Module 00 or Phase 2 Gate acceptance.
- **Next:** submit the updated same Draft PR #1 for supervisor review. UI/DB executable work still awaits Foundation acceptance and separate specialist assignments.


## Checkpoint G — FND-ADR0005-OPTIONB-01 / Supervisor initial-login binding decision (2026-11-13)

- **Scope and baseline:** live main `d93dcf7cbf9290acd4cd3aa0164ef05689049da4`; independent branch `agent/foundation-adr0005-optionb-binding`. The existing crosswalk [Draft #35](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/35) stays unmodified; UI [#41](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/41), API [#40](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/40) and DB [#42](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/42) likewise remain on their own Draft branches. Exactly **two Foundation-owned documents** are changed: docs/adr/0005-auth-session-boundary.md and this cumulative checkpoint. No product.v1, canonical checklist, SQL, Route, Workflow, Gate, merge or deployment.
- **Verified source contracts:** API #40 HEAD `ddc2f2f4424f548df50047ce7eb7209584d6bdb7` / API-AUTH-NEXT-PRIVATE-CONTRACT-01; its earlier *code-tested* `59a1ae76c71337cbddbe6759f93a1a7402334b7c` [Run 43318211274](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43318211274) SUCCESS 108/108 (INIT01–04: isolated Keycloak 26.8.2 Code+S256/RS256, two owners and PG issuance), not a product browser login. UI #41 HEAD `babdcfcdef4cf274a2a555a9a2e0bab0ac5cbdc5`: UI-AUTH-BFF-PLAN-01, design and UI-AUTH-P01..P16 NOT_RUN. DB #42 HEAD `4bc1ac42b68996bdabbf94ab942ba367ddfd927c`: DB-AUTH-BOOTSTRAP-REVIEW-01, DBL01..16 NOT_RUN. H1 #39 [Run 43315447479](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43315447479) SUCCESS but only synthetic-signer GET /v1/conversations.
- **Decision and ADR conflict resolved:** prior ADR 0005 allocated Code exchange and IdP validation to Next BFF; supervisor's Option B now places Authorization Code redemption, server-held PKCE S256, JWKS/claims validation, verified issuer+subject mapping and Product Session issuance in **API**. Next BFF owns initiator/browser callback binding and durable encrypted alias/Cookie/CSRF. Private pre-session Next→API service identity is **different** from session-bound BFF→API assertion: independent mTLS plus signed purpose-scoped bootstrap proof and durable JTI replay; no fake Owner/session. Only new **private.auth.bootstrap.v1** start/complete/status/ack/abort spec; public product.v1 unchanged.
- **DB one-issue boundary:** proposed future `009_initial_login_attempt_binding.up.sql/.down.sql` with durable unique attempt/idempotency/receipt/session digest Registry, state INITIATED→EXCHANGE_STARTED→ISSUED_PENDING_BINDING→ACTIVE; Session PENDING_BINDING must remain denied by 003/004 until atomic Owner→Registry→Session ACK. Never hold PG lock across outbound IdP HTTP. Exactly at most one Product Session per Login Attempt even across Worker/restart/ambiguous receipt. No raw Code/IdP token/Product verifier in Registry, logs or STATUS.
- **ACK/ABORT/cookie semantics:** BFF first **durably commits** handle-digest→encrypted verifier/Owner/Epoch in shared store as NOT_SERVE, ACK binds same BFF/attempt/receipt/alias digest, and PostgreSQL commits Pending→Active and Registry state in one transaction. **Only after confirmed ACK may Next send Browser Cookie**; ACK confirms BFF's durable alias-write assertion, **not** Cookie delivery. Pending ABORT uses a dedicated 009 operation, not existing 003 revoke_one (active-only). Identical ACK/ABORT retries idempotent; conflicting terminal transitions 409/deny. Unknown Code exchange/Issue/ACK result never automatically retries Code or mints a second Session; STATUS never returns verifier; orphan pending/unused active Alias cleanup with TTL/revocation and permanent tombstone requires future policy/test. Epoch drift, revoke and reset gates prevent late activation.
- **Open policy deliberately not fabricated:** Production IdP/provider allowlist, verified-email/disabled-account policy, Session idle/absolute/rotation/re-auth and allowed clock bounds, Cookie host flags/SameSite, CSRF/Origin/Fetch Metadata, bootstrap cert trust/key rotation, BFF alias retention, Production role grants/SECURITY DEFINER least privilege, ops approval, RPO/RTO, audit/redaction. Legacy proposed 30m/12h/5m are NOT APPROVED. C2=NOT_PROVEN and PR #33 SECURITY_BYPASS_REPRODUCED persist; C2 only required for reopening *after Reset*, not initial ordinary login.
- **Exactly three successive future owner packages:** 1. **DB owner** new 009 migration + pending/atomic ACK/ABORT/cleanup and real PG17 DBL01..16/role/rollback tests, immutable SHA/Run/Job; 2. **API owner** purpose-scoped mTLS/private START/COMPLETE/STATUS/ACK/ABORT, API IdP verification/unique attempt and crash/replay/epoch/negative multi-worker tests, exact CI; 3. **UI owner** real Next Login/Callback/init Cookie/durable encrypted NOT_SERVE alias then ACK then Cookie/303, Cookie/CSRF/logout/lost-response and two-owner Chromium UI-AUTH-P01..P16 with API/PG evidence. Integration/Gate remain subsequent and separate. No actual implementation authorized by this documentation branch.
- **Checks and status:** source-specific review of exact PR SHA/CI and original ADR sections, revised authoritative section 9 and limited historical §2 clarification. Only static document consistency, no test suite, no operational action. IMPLEMENTED=DOC_DECISION_ONLY; TESTED=SOURCE_REVIEW_AND_STATIC_SCOPE; ACCEPTED=ARCHITECTURE_DECISION_ONLY / PRODUCT_GATE_NONE. READY_FOR_SUPERVISOR_DRAFT_REVIEW. Future merge of this main-derived Foundation ledger with parallel #35 checkpoint needs additive reconciliation; do not overwrite either cumulative history.
