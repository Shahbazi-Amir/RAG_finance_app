# SPEC-P3-10 — CI evidence reconciliation

**Production: NO-GO. Phase 4: LOCKED.**

## Baseline and method

- Branch `phase3/completion`, tested SHA `42b58e5e6f8a256d65dc11841737496d16b44b89`. [Run 46098376958](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958) completed with `success`. All four job definitions completed successfully, including the three browser matrix entries.
- Reconciled the 26 independent Gates in the [P3-00 audit](SPEC-P3-00-phase3-audit.md) and [canonical checklist](../../coordination/phase3_checklist.md) against the P3-00–08 receipts summarized in the [P3-08 handoff](SPEC-P3-08-production-readiness-handoff.md), the [signed owner decisions](../../coordination/OWNER_DECISIONS_20261127.md) and the hosted execution of the [P3-09 workflow](SPEC-P3-09-owner-decisions-and-ci-runner.md). Historical receipts retain their original SHA and scope. The frozen pilot #143 receipt applies to the frozen pilot.
- Read run metadata and job steps via `gh run view 46098376958 --repo Shahbazi-Amir/RAG_finance_app --json status,conclusion,headSha,url,jobs` and filtered runtime summaries from the same command with `--log` in place of `--json ...`. Mapped successful steps to commands in the [tested workflow](../../.github/workflows/phase3-isolated-evidence.yml).
- CI success records test execution at the tested SHA. Gate acceptance requires the complete criteria and formal approval. The owner decisions approve roles, targets, the isolated runner and deferrals. Supervisor Gate acceptance remains separate.

## Observed CI results

| Job | Result and scope |
| --- | --- |
| [postgres-migrations-rls](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958/job/140834940291) | PASS. Hashed Python lock and pinned migration bytes verified. Disposable PG16 applied 001–011, checked 011 replay/owner semantics, reversed and reapplied 001–010 separately, verified forced RLS and owner A/B, and ran logical `pg_dump`/`pg_restore` with post-restore checks. Runtime marker `PG16_MIGRATION_001_011_ROLLBACK_001_010_RLS_RESTORE_PASS`. 011 has no DOWN in the repository. |
| [python-security-and-api](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958/job/140834940392) | PASS. Hashed dependencies, pinned pytest, 71 contracts, 42 Foundation and 19 policy/429 cases passed. API discovery ran 241 cases (240 passed, one skipped). Private transport suites passed 1 mTLS network, 13 Bootstrap ASGI and 1 Bootstrap network case. Real isolated Keycloak/PG17.11 passed 10 Bootstrap and 5 Product Session cases, with signed History, replay, owner A/B and revoke markers. |
| [web-playwright-cross-browser (chromium)](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958/job/140834940400), [web-playwright-cross-browser (firefox)](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958/job/140834940043), [web-playwright-cross-browser (webkit)](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958/job/140834940453) | PASS on each engine. Clean install/type generation, lint, typecheck, 143/143 Web tests per job and Next build. Loopback browser History/accessibility script succeeded on all three engines. Chromium also ran the sidebar logout script. |
| [staging-and-image-check](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958/job/140834940443) | PASS. Bash syntax and deploy dry-run. App-only API/Web Docker images built for linux/amd64 and revision labels matched the SHA. Artifact upload succeeded for build/dry-run logs, source SHA and local image IDs. Image scanning, registry publication and deployment remain outside this receipt. |

## Gate matrix

| Gate | Before | After | Dependency | Evidence observed | Remaining acceptance evidence |
| --- | --- | --- | --- | --- | --- |
| P3M00-GATE | PENDING | PENDING | EXTERNAL_DEP (Codex-2) | P3-00 documented the frozen pilot and draft interface. | Accepted Phase 2 release, authoritative manifest/hash and real contract, locator and attribution checks. |
| P3M01-GATE | PARTIAL | PARTIAL | None | Owner signed SLO, workload, owners and gates for change/rollback. | M00 plus formal approval of architecture, scope and ADRs with security/cost decisions resolved. |
| P3M02-GATE | PARTIAL | PARTIAL | None | Clean Web build and hashed Python installation in hosted CI, plus historical source/SBOM checks in P3-01/P3-06. | Exact-source complete security baseline, SBOM and actionable dependency/secret scan evidence plus M01. |
| P3M03-GATE | PARTIAL | PARTIAL | None | 71 contract and 42 Foundation tests passed. | Complete circular-dependency evidence, upstream M01/M02 and Gate acceptance. |
| P3M04-GATE | PARTIAL | PARTIAL | None | PG16 clean 001–011, rollback/reapply 001–010 and scoped role checks. P3-02 records pinned SQL. | Representative existing-data migration, defined 011 rollback/recovery evidence and explicit FK and main-path query-plan verification. |
| P3M05-GATE | PARTIAL | PARTIAL | None | 10 isolated Keycloak Bootstrap and five signed Product Session tests, private mTLS and Chromium logout. | Target auth policy and protected endpoint coverage, full redacted-log audit and formal sign-off after M04. |
| P3M06-GATE | PARTIAL | PARTIAL | None | PG16 forced-RLS role and owner A/B, restore isolation and signed PG17.11 A/B journey. | Full protected storage and authorization matrix for target roles/runtime plus M04/M05 and Gate sign-off. |
| P3M07-GATE | PENDING | PENDING | EXTERNAL_DEP (Codex-2) | P3-05 records offline adapter evidence. | Accepted Release and runtime readiness rejection for incompatible versions, plus rollback without reindexing. |
| P3M08-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | P3-05 offline fixtures and hosted API discovery suite. | Real retrieval parity against approved tolerance and producer misattribution evidence. |
| P3M09-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | P3-05 offline result rejection and API suite. | Approved provider decision, real gateway invalid-output and cost-guard evidence. |
| P3M10-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | Signed Product Session and hosted contracts plus P3-05 malformed-result denial. | Real producer output and provenance/safety fields on every successful Answer, with accepted M08/M09. |
| P3M11-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | Hosted contract and UI suite plus P3-05 offline citation/attribution checks. | Approved real citation and attribution targets and verified source locators. |
| P3M12-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | 19 policy tests and P3-05 fail-closed fixture evidence. | Approved real safety suite and measured critical-violation and no-answer F1 targets. |
| P3M13-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | 241 API cases collected (240 passed, one skipped), signed Product Session and private transport checks. | Complete accepted OpenAPI, authorization and error-contract suite across producer-backed paths. |
| P3M14-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | History/a11y fixture on three browsers, Chromium logout, P3-04 RTL/focus/recovery evidence. | Full approved browser/mobile login–chat–citation–history journey with real attribution checks. |
| P3M15-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | Signed History refresh, owner A/B and revoke plus three-browser History and P3-04 privacy recovery. | Complete policy deletion and feedback trace evidence across real product conversations. |
| P3M16-GATE | PARTIAL | PARTIAL | None | P3-06/P3-08 structured/redacted lab evidence and hosted API suite. | End-to-end trace coverage, exercised critical alerts and complete secret/PII log verification under approved log policy. |
| P3M17-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | Hosted policy tests and HTTP 429 witnesses, P3-06 quota fix. | Complete bypass/concurrency matrix and cross-user cache/stale citation verification with real release changes. |
| P3M18-GATE | PARTIAL | PARTIAL | None | Two SHA-labelled Linux amd64 image builds and staging dry-run. | Image vulnerability scans, reproducibility witness and restart with durable data. |
| P3M19-GATE | PARTIAL | PARTIAL | None | Exact-SHA job checks and two local image IDs archived, plus P3-07 dry-run. | Enforced production pipeline denial without test report, registry digest, migration check and approval. |
| P3M20-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | Frozen pilot #143, P3-07 public GET probe and hosted dry-run. | Fresh isolated staging rebuild, signed UAT and critical E2E including accepted producer, and critical issue disposition. |
| P3M21-GATE | PARTIAL | PARTIAL | None | Local mTLS and Bootstrap/Product Session, PG16/PG17.11 owner A/B and historical pilot #143. | Current image/security/privacy assessment, Critical/High closure, reviewed incident runbook and target evidence. |
| P3M22-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | PG16 logical dump and restore to a separate database with post-restore owner checks. Owner signed RPO/RTO. | Scheduled backup and timed full restore/recovery including knowledge assets, PITR/WAL evidence when enabled, and operational sign-off. |
| P3M23-GATE | PARTIAL | PARTIAL | EXTERNAL_DEP (Codex-2) | Owner signed workload/SLO and P3-07 records 21/21 loopback capabilities requests. | Representative E2E for 100 invitees/up to 10 concurrent, capacity, error budget, soak and failure measurements. |
| P3M24-GATE | PENDING | PENDING | EXTERNAL_DEP (Codex-2) | P3-08 runbook and owner decisions define change window and rollback thresholds. | Verified release/migration/backup/rollback, monitoring, closed P0s, signed UAT and Go approval. |
| P3M25-GATE | PENDING | PENDING | EXTERNAL_DEP (Codex-2) | P3-08 handoff plus signed named owner, incident SLA and 14-day window. | Go-Live, actual hypercare record, stable metrics, critical incident closure, training and signed Phase 4 handoff. |

## Result and handoff

**DONE 0 / PARTIAL 22 / PENDING 4. EXTERNAL_DEP (Codex-2) 16** overlaps the status counts. No Gate moved to DONE. All ten App-only Gates remain PARTIAL. The 16 producer-dependent Gates comprise 12 PARTIAL and four PENDING.

App-only follow-up is tracked by the ten rows marked None: architecture approvals, exact-source baseline and contract closure, migration/restore and isolation gaps, auth coverage, operational audit/alert evidence, image scans/restart, release enforcement and security sign-off. Independent App-only checks can proceed while Codex-2 supplies the accepted Phase 2 release, authoritative manifest/hashes and real NB23 producer, retrieval, safety and attribution evidence. End-to-end staging/UAT, full restore, representative load and production/hypercare acceptance still require their listed evidence.

Changed paths: this report and `docs/PROJECT_STATE.md`. Canonical Gate acceptance remains with the supervisor.
