# SPEC-P3-11 — App-only Gate evidence and NB23-v4 baseline

**Production: NO-GO. Phase 4: LOCKED.**

## Scope and owner decision

Starting SHA `09883e2049860ccd660f6c6c80d5339038244bfc` on `phase3/completion`. The [owner addendum](../../coordination/OWNER_DECISIONS_20261127.md#spec-p3-11-addendum--app-only-governance-and-engine-baseline) records approval of App-only governance and release policy and the selection of NB23-v4. The App-side tree `ed2df0b52510e9ec58e50f86d73fcf8fde1077bf` matches at the starting SHA and at the frozen pilot commit `4edadd3e784e1f9500dd9da8d4b6f6e40833cd13`, as verified with `git rev-parse v0.1-arvan-100users-live:infra/nb23-v4 HEAD:infra/nb23-v4`. Upstream release identity and asset integrity still require authoritative evidence.

## App-only Gates

Each row uses the [P3-10 reconciliation](SPEC-P3-10-ci-evidence-reconciliation.md) for its prior status and the owner addendum for governance. The isolated run is linked below. Operational rollout, production enforcement and supervisor acceptance remain separate.

| Gate | Before | After | Evidence and remaining criterion |
| --- | --- | --- | --- |
| P3M01-GATE | PARTIAL | PARTIAL | Owner approved architecture, scope, SLO and ADRs for the baseline. M00 release acceptance is open. |
| P3M02-GATE | PARTIAL | PARTIAL | Clean builds and pinned dependency installs cover part of the baseline. HIGH/CRITICAL dependency findings, full exact-source SBOM, complete secret/dependency review and M01 acceptance remain open. |
| P3M03-GATE | PARTIAL | PARTIAL | Contract and Foundation runs cover schema and fixture checks. Full circular-dependency evidence and M01/M02 acceptance remain open. |
| P3M04-GATE | PARTIAL | PARTIAL | Clean and populated migration, idempotency, rollback and restore are checked in separate isolated jobs. Migration 011 is forward-only. Target 011 recovery evidence and upstream M03 acceptance remain open. |
| P3M05-GATE | PARTIAL | PARTIAL | Disposable Keycloak Bootstrap, signed Product Session, mTLS and Chromium logout cover bounded auth/revoke paths. Target endpoint coverage, log audit and M04 acceptance remain open. |
| P3M06-GATE | PARTIAL | PARTIAL | Isolated RLS paths include two owners and restored data. Target role/runtime matrix and M04/M05 acceptance remain open. |
| P3M16-GATE | PARTIAL | PARTIAL | Lab audit, log guards, health alert transitions and quota/429 checks exercise policy contracts. Complete operational trace, alert delivery and redaction evidence remain open. |
| P3M18-GATE | PARTIAL | PARTIAL | App-only images are built and scanned. HIGH/CRITICAL findings block this Gate. Release reproducibility across builds and restart with durable state remain open. |
| P3M19-GATE | PARTIAL | PARTIAL | Owner signed mandatory release controls. Evidence CI checks its SHA and records image identity. Target production denial when any release prerequisite is missing remains open. |
| P3M21-GATE | PARTIAL | PARTIAL | Private mTLS, signed auth, RLS and vulnerability scan cover bounded security checks. HIGH/CRITICAL findings, target security/privacy assessment, incident runbook acceptance and M20 remain open. |

## Producer-dependent Gates and SPEC-P3-12

Category A covers all 16 Gates with acceptance work that can target the selected NB23-v4 baseline. The work remains conditional on the evidence indicated below. The baseline choice does not certify the producer, authorize contact with live Arvan or grant launch.

| Gate | Status | SPEC-P3-12 evidence to collect on the pinned baseline |
| --- | --- | --- |
| P3M00-GATE | PENDING | Obtain and verify authoritative release manifest, hashes, contracts, real locators and attribution, and record upstream acceptance. |
| P3M07-GATE | PENDING | Verify readiness denial for incompatible release and rollback to an approved manifest without reindexing. |
| P3M08-GATE | PARTIAL | Run baseline retrieval regression against accepted reference and tolerance, including misattribution. |
| P3M09-GATE | PARTIAL | Check real gateway schema and failure behavior and approved provider/cost controls. |
| P3M10-GATE | PARTIAL | Verify actual Answer envelope, request and release traces, citations, safety and fail-closed outcomes. |
| P3M11-GATE | PARTIAL | Verify real baseline citation/attribution scores, sources and locators against accepted targets. |
| P3M12-GATE | PARTIAL | Run approved real safety and no-answer suite against baseline acceptance thresholds. |
| P3M13-GATE | PARTIAL | Verify producer-backed OpenAPI, authorization and error contracts. |
| P3M14-GATE | PARTIAL | Run full login/chat/citation/history journey with baseline citations across approved browsers and mobile. |
| P3M15-GATE | PARTIAL | Verify real-product owner isolation, retention/deletion and feedback lineage. |
| P3M17-GATE | PARTIAL | Verify rate/cache isolation and cache behavior across accepted release changes. |
| P3M20-GATE | PARTIAL | Rebuild isolated staging, capture signed UAT, critical producer-backed E2E and defect disposition. |
| P3M22-GATE | PARTIAL | Time authorized full DB and knowledge-asset recovery against RPO/RTO and record restore sign-off. |
| P3M23-GATE | PARTIAL | Measure representative E2E load, soak and failure against the signed SLO and workload. |
| P3M24-GATE | PENDING | Assemble migration, backup, rollback, UAT, monitoring, P0 and Go/No-Go receipts. Separate authorization is required for release. |
| P3M25-GATE | PENDING | After authorized Go-Live, collect actual Hypercare, incident closure, stable metrics, training and signed handoff evidence. |

Category B has **zero whole Gates**. The waiver covers prospective Recall/knowledge-quality uplift in the scope of **P3M08-GATE** (retrieval) and **P3M11-GATE** (knowledge attribution quality), as applicable. Existing retrieval/citation thresholds remain in category A. The waiver adds zero `WAIVED-TO-TRACK4` Gates to the matrix.

## Verification and disposition

- SPEC-P3-11B started at `246dbe4d9583cade45f7de112833d1981bfb365d`. [Run 46100686641](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46100686641) stopped at `STOP_M04_A07_CONSISTENCY_MISSING`. The exporter at line 280 requires the receipt produced by `23_m04_migration_full_cycle.sh`. The workflow now runs that probe after the populated pre-009 upgrade, along with the required `24_m10_idempotency_concurrency_probe.sh` and `25_pg_crash_recovery_probe.sh` before export. The restore checks follow the ordering of the standalone DB workflow.
- PyYAML `yaml.safe_load`, `bash -n` for embedded shell steps, and `git diff --check` passed. [Run 46102067648](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46102067648) finished at tested SHA `aff653f8492f212aa602779a3c325e685b642f2f` with 6/7 jobs successful and overall conclusion `failure`.

| Job | Result |
| --- | --- |
| postgres-populated-recovery | PASS. Export validated `M04_A07_14TH_SANITIZED_CONSISTENCY_RECEIPT=PASS` and emitted `P311_POPULATED_MIGRATION_RLS_RESTORE_PASS`. |
| postgres-migrations-rls | PASS. Isolated 001–011, 001–010 rollback/reapply, owner RLS and logical restore. |
| python-security-and-api | PASS. Includes audit log guards, operational alert transition contracts, policy/HTTP 429, and isolated Keycloak and signed Product Session. |
| web-playwright-cross-browser (chromium) | PASS. Web checks, History/accessibility and sidebar logout. |
| web-playwright-cross-browser (firefox) | PASS. Web checks and History/accessibility. |
| web-playwright-cross-browser (webkit) | PASS. Web checks and History/accessibility. |
| staging-and-image-check | FAIL at Trivy after building both App-only images. API 2 CRITICAL / 49 HIGH. Web 1 CRITICAL / 48 HIGH. These match the earlier run. Raw scan evidence is attached to the run. |

**DONE 0 / PARTIAL 22 / PENDING 4 / WAIVED-TO-TRACK4 0.** No App-only Gate was promoted. The scan findings keep P3M02, P3M18 and P3M21 PARTIAL. Remediation of the affected image and dependency versions requires a separate change within the appropriate source/configuration scope. The PostgreSQL evidence closes the isolated receipt-export gap while the remaining acceptance criteria above still apply.
