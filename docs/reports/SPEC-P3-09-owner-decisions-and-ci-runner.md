# SPEC-P3-09 — Owner decisions and isolated CI runner

**Status: PARTIALLY ACHIEVED.** Decisions and the manual evidence workflow are recorded. Hosted execution and evidence acceptance are pending. **Production: NO-GO. Phase 4: LOCKED.**

## Baseline and decisions

Branch `phase3/completion`, starting commit `1865994a81bcf37706636d9892f2ae313d125c7b`. The user supplied six approved decisions for 2026-11-27. The signed record names امیر شهبازی آراللو (Primary Owner) for Ops, Security, DBA, UAT, Release and Hypercare until team formation. Targets are 99.5% monthly availability, non-engine API p95 ≤500 ms, 5xx <1%, 100 invited users and at most 10 concurrent. PostgreSQL RPO is ≤24 h with daily backup and ≤15 min after PITR/WAL activation, with RTO ≤2 h. Hypercare is 14 days, with initial P0/security response ≤30 min and P1 ≤4 h. Change window is Thursday/Friday 02:00–05:00 Tehran time, with immediate rollback on a #143 smoke failure or 5xx >2%. Verification is hosted and isolated. SMTP and the corpus correction remain deferred. [Signed owner record](../../coordination/OWNER_DECISIONS_20261127.md)

The [handoff](../operations/phase3-production-readiness-handoff.md) and [project state](../PROJECT_STATE.md) carry the same decisions. The live pilot tag `v0.1-arvan-100users-live` still points to `4edadd3e784e1f9500dd9da8d4b6f6e40833cd13`. No server, engine, security configuration or existing test assertion changed.

## Workflow

[Phase 3 isolated evidence](../../.github/workflows/phase3-isolated-evidence.yml) uses `workflow_dispatch`, `contents: read`, `ubuntu-latest`, checkout without persisted credentials and an explicit SHA/ref check. It contains no production credential or server target. Each job runs independently.

| Job | Configured checks |
| --- | --- |
| `postgres-migrations-rls` | Disposable PostgreSQL 16 with no published ports and SQL via Docker exec, hashed Python lock, 001–011 with explicit roles, 011 one-shot replay and owner denial, 001–010 reverse/reapply in a separate DB, and real logical backup/restore with post-restore owner tests. Migration 011 has no DOWN in this repository. Dump remains inside the disposable service. |
| `python-security-and-api` | Hashed Python runtime including PyJWT, cryptography and uvicorn, pinned pytest dependencies, contracts, Foundation, API discovery, HTTP 429, mTLS and Bootstrap. A separate disposable, loopback-bound PG 17.11 service supports the existing real local Keycloak Bootstrap and Product Session suites. Trust authentication is confined to ephemeral test services. No engine is mounted. |
| `web-playwright-cross-browser` | Clean Web dependency install, type generation, lint/typecheck/test/build and the existing History fixture on Chromium, Firefox and WebKit. The separate logout smoke runs on Chromium because that entrypoint selects Chromium internally. |
| `staging-and-image-check` | Bash syntax, deploy dry-run, App-only API/Web Dockerfiles, revision label and local image IDs. Artifact contains build/dry-run logs and image metadata only. The engine, signed deployment and browser-lab images are outside this App-only build. |

Local result: PyYAML 6.0.3 loaded the workflow, validated all four hosted jobs, three matrix engines, manual trigger and read-only permissions; all 18 embedded shell bodies passed `bash -n` and referenced checkout paths were present. `git diff --check`, document link checks and the file-mode/secret-pattern review passed. No hosted job was started by this task. These checks validate repository wiring; successful runtime execution is still required before counting evidence. Gate counts remain **DONE 0 / PARTIAL 22 / PENDING 4**.

## Manual dispatch

GitHub requires the workflow to exist on the default branch before a manual dispatch can select a non-default ref. The observed default is `main`, and the file is absent there. The request excludes writes to `main`. A separately authorized registration is pending. [GitHub manual dispatch documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)

After registration, from a GitHub account authorized to dispatch:

```bash
gh workflow run phase3-isolated-evidence.yml --repo Shahbazi-Amir/RAG_finance_app --ref phase3/completion
```

Record the run URL and tested commit SHA, review each job and accept only the evidence actually produced. Hosted smoke or lab receipts do not authorize production promotion or unlock Phase 4.
