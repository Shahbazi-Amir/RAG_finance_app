# SPEC-P3-13 — App-only Gate reconciliation

**Production: NO-GO. Phase 4: LOCKED.**

## Scope and baseline

`phase3/completion` started at `20c408039cd13a226bc27daac87059ad2fbd449c`. Sources are the [canonical checklist](../../coordination/phase3_checklist.md), [P3-10 reconciliation](SPEC-P3-10-ci-evidence-reconciliation.md), [P3-11 Gate and owner mapping](SPEC-P3-11-app-gates-closure-and-nb23-pin.md), [P3-12 image evidence](SPEC-P3-12-image-hardening-and-ci-green.md) and [owner decisions](../../coordination/OWNER_DECISIONS_20261127.md). The owner addendum approves architecture, governance and release policy. Technical Gate acceptance, upstream prerequisites and supervisor acceptance retain their separate criteria.

The [baseline run 46103757931](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46103757931) covers migration, recovery, lab audit and 429, isolated Keycloak and signed Product Session, three browser engines, staging syntax/dry-run and both image scans at 0 CRITICAL / 0 HIGH. P3-13 exercises evidence that can be collected with the isolated services. The 16 NB23-v4-dependent Gates remain assigned to SPEC-P3-14. Their dispositions and frozen engine references are unchanged.

## Ten independent Gates

| Gate | Before | After | Prior evidence and P3-13 scope | Remaining criterion |
| --- | --- | --- | --- | --- |
| P3M01 | PARTIAL | PARTIAL | Owner approved App-only architecture, scope, SLO and ADRs. | The checklist requires accepted M00 and formal Gate acceptance. |
| P3M02 | PARTIAL | PARTIAL | Clean image builds, hashed API dependencies, Web tests, clean HIGH/CRITICAL scans. P3-13 adds exact-SHA source SBOM, tracked-text credential scan and built-image SBOM. | Full target environment/security baseline, broader credential/dependency review and accepted M01. |
| P3M03 | PARTIAL | PARTIAL | Contract and Foundation schema/fixture suites. | Full dependency-cycle verification and accepted M01/M02. |
| P3M04 | PARTIAL | PARTIAL | Prior 001–011 and populated 001–010 rollback, FK and query-plan receipts. P3-13 applies forward-only 011 to populated History and verifies same-cluster restart and restore with owner checks. | Target recovery on the supported 011 baseline and accepted M03. |
| P3M05 | PARTIAL | PARTIAL | Isolated Bootstrap and signed Product Session, replay/revoke, mTLS and Chromium logout. | Target protected-route and auth/log coverage on the approved topology, and accepted M04. |
| P3M06 | PARTIAL | PARTIAL | Forced RLS, signed two-owner History, populated owner A/B role probes and logical restore. P3-13 repeats owner read and claim replay checks after restart. | Full target protected table and role matrix on the approved topology, and accepted M04/M05. |
| P3M16 | PARTIAL | PARTIAL | Log guards, health alert transitions, API audit tests and 429 policies. | End-to-end trace coverage, delivery of critical alerts to the approved destination, and policy-complete target PII/secret log audit. |
| P3M18 | PARTIAL | PARTIAL | Pinned base digests, real image build and Trivy 0/0 in P3-12. P3-13 checks non-root cold-start and restart on isolated API/Web images and durability on the separate DB service. | Cross-build reproducibility and durability of the complete target stack with its mounted storage. |
| P3M19 | PARTIAL | PARTIAL | Owner approved release prerequisites; isolated CI records exact SHA, tests, migration probes and image identity. | Enforced production deny paths for absent test report, immutable registry digest, migration check or approval. This workflow runs in a separate evidence environment. |
| P3M21 | PARTIAL | PARTIAL | Image vulnerability threshold, isolated mTLS and signed RLS/auth checks. Historical #143 applies to the frozen pilot. | Complete target security/privacy assessment, approved incident runbook and accepted M05/M06/M20. |

## Verification

- Changed executable path: `.github/workflows/phase3-isolated-evidence.yml`. Tested SHA `225cd29a5451f61b20581a22143067ac4559ae6a`. PyYAML loading, `bash -n` on embedded steps and `git diff --check` passed.
- Local Web from `apps/web`: `npm run lint`, `npm run typecheck` and `TMPDIR=/tmp npm test` passed, with 143 tests. The hosted Web checks also built the application. Local Python used `/private/tmp/rag-arvan-pytest/bin/python -B -m unittest discover` with `-s tests/phase3/contracts -p 'test_*.py'` (71), `-s tests/phase3/foundation -p 'test_*.py'` (42), and `-s tests/phase3/integration/api -p 'test_f3_lab_*.py'` (90). All three passed.
- [Run 46104453013](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013) completed with **7/7 PASS** at the tested SHA. Verified with `gh run view 46104453013 --repo Shahbazi-Amir/RAG_finance_app --json status,conclusion,headSha,url,jobs` and matching job log markers.

| Job | Result and evidence |
| --- | --- |
| [postgres-migrations-rls](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951713) | PASS. Populated 011, owner isolation and persisted claim replay after restart. Marker `PG16_POPULATED_011_AND_RESTART_OWNER_REPLAY_PASS`. |
| [postgres-populated-recovery](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951712) | PASS. Populated upgrades, rollback, owner and restore probes with sanitized receipts. |
| [python-security-and-api](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951469) | PASS. Contract, Foundation, API, log/alert and policy suites, private transport and isolated signed-session checks. |
| [web-playwright-cross-browser (Chromium)](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951655) | PASS. Web build/tests, browser History and logout. |
| [web-playwright-cross-browser (Firefox)](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951726) | PASS. Web build/tests and browser History. |
| [web-playwright-cross-browser (WebKit)](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951686) | PASS. Web build/tests and browser History. |
| [staging-and-image-check](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46104453013/job/140853951667) | PASS. Source inventory reported 28 API and 407 Web lock components. The bounded tracked-text scanner found zero high-confidence matches across 509 files. Non-root cold-start and restart passed. Built-image SBOMs were generated after the unchanged scan assertions. Trivy reported API 0 CRITICAL / 0 HIGH (50 MEDIUM, 5 LOW) and Web 0 CRITICAL / 0 HIGH (39 MEDIUM, 5 LOW). |

**DONE 0 / PARTIAL 22 / PENDING 4** across 26 Gates. Zero of the ten App-only Gates advanced to DONE. This report and `docs/PROJECT_STATE.md` record the new evidence. The mandatory Qdrant Snapshot Reuse and UI-polish queue remains in [Project State](../PROJECT_STATE.md).
