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

## Checkpoint F — FND-H1-X01 isolated cross-component Chromium/PostgreSQL matrix (SOURCE / CI PENDING)

- **Stable ID / source:** FND-H1-X01; Phase 3 Modules 05/06/13/14/15. Canonical links P3M05-A07, P3M06-A03/A05/A07, P3M13-A04/A08, P3M14-A02, P3M15-A03/A07/A10. P3OP03 is a non-counting overlay; no Gate accepted.
- **Verified preflight:** main@d93dcf7cbf9290acd4cd3aa0164ef05689049da4. Separate branch agent/foundation-h1-cross-component-chromium, never PR #35. PRs #35/#36/#37/#38 all Open/Draft before this batch.
- **Reused exact tested product code WITHOUT edits:** src/phase3/auth/transactional_admission.py from PR #36 tested SHA 99a917c2f2c519027d0e71643bbbf6973a6c8ac3, [API Run 43299642520](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43299642520); apps/web/app/history/page.tsx from PR #38 tested SHA 3faf98728d3ddf2e1d243d5a6fa92223713a9cc2, [UI Run 43309050166](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43309050166) / [Job 131499933316](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43309050166/job/131499933316). Historical green evidence does not equal a new cross-component PASS.
- **Only NEW paths:** tests/phase3/integration/cross_component/h1_revocation_chromium.py and .github/workflows/foundation-h1-cross-component.yml, plus this pre-existing cumulative coordination/tasks/AGENT-FOUNDATION-01.md. No new modification of product code beyond copying the exact source blobs above. No SQL migration, Auth production routing, UI proxy, Checklist, shared contract or Reset/C2 change.
- **Execution topology, fixture-only:** real Chromium -> existing Next History page on 3000/3001 -> fixed synthetic signer gateways on loopback 8111/8112 -> the registered FastAPI GET /v1/conversations on 8120 -> one actual PostgreSQL 17.11 history_app connection with signed RSA BFF proof + durable 005 JTI + 004 same-session/owner/epoch fence kept across original History Repository LIST. This is achieved by a CI-only FastAPI dependency override copied in pattern from PR #36, not by enabling production Auth. Keys, opaque sessions and identity mapping remain CI-only/in memory; the browser cannot pick owner and no responses are fabricated by Playwright.
- **Scoped Chromium acceptance matrix (expected, NOT_YET_RUN):** H1X01 separate A/B synthetic owners each see only own seeded History from real signed LIST 200; H1X02 one already-committed real old A LIST 200 is held before gateway delivery; H1X03 explicit revoke_one of session A commits in a second PostgreSQL connection; H1X04 a newly signed JTI on that SAME A session yields actual API LIST 401 and 005 denial JTI does not commit; H1X05 Chromium forces a second call to the original React LIST callback while Refresh is disabled by an outstanding first LIST, inducing real API LIST 401 that must purge all A private state; H1X06 after a late prior real 200 is delivered A must stay cleared; H1X07 B fresh signed LIST still yields real API 200 and B-only data. Test-only adversarial callback invocation is NOT a normal user click. No other History path is signed by fixture and no Playwright stub issues 401.
- **Independent PostgreSQL concurrency witness from PR #37 (not this integration):** tested SHA a70f65d611cbdf7f14a88675b1c227eb8fdf5a85; actual [Run #43302999997](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43302999997) / [Job #131478822093](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43302999997/job/131478822093): H1DB01/02/03 3/3 OK; actual H1DB02 lock witness reader_backend_pid=119, revoker_backend_pid=120, pg_blocking_pids=[119], wait_event_type=Lock, wait_event=transactionid while read TX held its 004 locks. Do not call this new Chromium/HTTP proof.
- **Reproducible command:** Python 3.13, Node 24, PostgreSQL postgres:17.11, unchanged migrations 001–005, CI-only two-function grant to restricted history_app undone after test, and installed official Chromium. Execute: python -m compileall -q apps/api src/phase3/auth tests/phase3/integration/cross_component ; python -u tests/phase3/integration/cross_component/h1_revocation_chromium.py . CI must emit H1X01..H1X07 and H1_CROSS_COMPONENT_CHROMIUM_REAL_API_PG_PASS before accepting a successful tested source SHA. Real new CI and Run/Job PENDING at this source checkpoint; do not invent a run.
- **Security boundary / open gap:** the current Next History proxy does not itself sign a Product Auth assertion or implement real Cookie/CSRF/OIDC; test-only fixed gateway is required. Temporary mixed 004/005/history role grant is NOT a production privilege policy. If any further test linkage requires modifying product code, STOP with exact missing path/interface. Implemented=ISOLATED_SOURCE, Tested=NEW_CI_PENDING, Accepted=NONE/SUPERVISOR_PENDING, Draft only, no Merge/Deploy/Gate.

- **H1-X01 failed first real attempt (NOT PASS):** original source commit `4f37d6815cfefa888bc426ae141cbf978cf8198b`, [Run #43313249858](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43313249858), [Job #131514520434](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43313249858/job/131514520434), completed **FAILURE**. Python/Node install, real Chromium, Next build, temporary PostgreSQL 17.11, 001–005 migrations and limited reversible 004/005 function grants succeeded. First Chromium assertion reached `browser_scenario` line 315 (B's conversation locator), where the *real* B list item was present in DOM but Playwright said `hidden`: B was configured as a 390px mobile viewport with collapsed side navigation. **Zero** H1X01..07 success markers, no UI/401/revoke test reached. Diagnosis is a wrong Harness visibility assumption, **not** security or DB failure; no Product code fix warranted. Correct in the **same test file only** by putting the independent B verification browser in 1280x800 visible-sidebar mode and removing the mobile-menu toggle before B refresh. New source requires a fresh CI run, no earlier PASS counted.
