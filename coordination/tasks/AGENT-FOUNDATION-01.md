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


## Checkpoint H — FND-COMPAT-3113-01: exact Python 3.11.3 on isolated branch (initial source, CI PENDING)

- **Preflight:** real main SHA d93dcf7cbf9290acd4cd3aa0164ef05689049da4, compat branch starting SHA 51cbf7a4beaef70365729c8682d6464ef7c45a01 from #49. #49's source-tested shell launcher was f3c0f6cab0147c8aa903cffe4e1fb02dcef32fa5, [Linux Python3.13 Run 43490639433](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43490639433) SUCCESS. Existing #49 Draft and all other branch heads not modified; RAG_finance repo read only. User-reported NB22E-v4:C011 Python3.11.3 is historical notebook runtime evidence, NOT evidence for Phase3.
- **Pinned sources reused unchanged in a disposable worktree by #49 launcher:** UI fee20cc0992f4c26f76757e670cd6425400441cc, API50 62d40f4b4ed254de0aa0dfc21c17d809e24423db, API48 1998b31c86155a972b11ea745d6bb37e09549392, API36 99a917c2f2c519027d0e71643bbbf6973a6c8ac3, SQL009 656604356dadea953031fcdb74650a5d42df4e9b, SQL010 1678e87b7984094b74ec995383b8d4383e5f5ae7. Exactly those SHA pins, migrations 001–010 and existing source tests are used; no User DB, IdP or nonowned Docker resources touched.
- **Minimal launcher-only Python guard correction:** demo.sh accepts optional RAG_PHASE3_PYTHON explicit path, then prefers python3.11, then retains python3.13 fallback; launcher.py accepts EXACT 3.11.3 **or existing 3.13** and expects this named compat branch. Prior unconditional Python 3.13 guard was a **launcher constraint**, not proof of a Python 3.11 package failure. Next still Node24, not Python.
- **Linux CI planned and pending initial push:** dedicated .github/workflows/phase3-python-3113-compat.yml on Ubuntu22.04, actions/setup-python v6 exact 3.11.3; fresh isolated venv with apps/api/requirements-ci.txt, tests/phase3/contracts/requirements.txt, PyJWT[crypto]==2.15.1, uvicorn==0.34.3 and playwright==1.64.1. Actual Python/sys/installed package versions printed. Runs 3.11.3 compile+API pure+History contracts, Next Node24 and real Chromium dependencies, Docker Postgres17.11, #49 local demo.sh preflight/start/reset/stop with real Keycloak, A/B History and Logout, and original API/DB shared test matrix in tests/phase3/integration/cross_component/python311_compat_matrix.py (7 suites on temporary PG: History contracts, API service proof, DB Session, DB NULL fence, DB 004 fence, DB 005 Replay, API HTTP History). Fails closed on any missing marker.
- **Host constraints partition:** this agent's available host is Linux with Python3.13.5, Node22, no Docker or network for new Python download. It cannot locally verify CPython3.11.3 or Intel macOS12.7.6; Linux GitHub Actions is the actual 3.11.3 executable authority. Mac 12.7.6 remains NOT_RUN, independent of Linux success. Node24 official macOS binary requires >= macOS 13.5 per https://nodejs.org/en/blog/migrations/v22-to-v24; so the full Next/Chromium stack on macOS12.7.6 is an **upstream OS/Node blocker, NOT a CPython test failure**. Mac-local Python/venv check remains separate.
- **Discipline:** initial test commit leaves .python-version at 3.13 and all existing 3.13 workflows untouched. Only after complete Linux3.11.3 green, a follow-up commit may propose .python-version=3.11.3, update scripts/phase3-demo/README_FA.md, re-run a new CI on resulting source SHA, and include the exact Mac Intel command/failure boundaries. No blanket replacement of Node24, removal of Python3.13 tests, merge/deploy or Gate/Release acceptance.
- **Status at source creation:** IMPLEMENTED=ISOLATED_3113_COMPAT_TEST_SOURCE, TESTED=NEW_CI_PENDING, ACCEPTED=NONE/SUPERVISOR_PENDING. Later result must append exact SHA/Run/Job/versions, Linux API/DB/UI outcomes, Mac NOT_RUN, and classify any failure by interpreter, package, Linux runner, Docker, Node or Playwright separately.
