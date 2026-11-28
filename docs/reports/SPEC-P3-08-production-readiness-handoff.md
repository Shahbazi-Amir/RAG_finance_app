# SPEC-P3-08 — Production readiness and handoff evidence

**Status: PARTIALLY ACHIEVED. Local Spec sequence closed for supervisor review. Production: NO-GO.**

## Scope and baseline

- Branch `phase3/completion`, baseline `c63099476b2e95b90c700d84390303726f34844a`. The [P3-00 audit](SPEC-P3-00-phase3-audit.md) ends at SPEC-P3-08. The [P3-07 receipt](SPEC-P3-07-reproducible-staging-app-load.md) supplies the preceding source and loopback evidence.
- M24-A01–A11 covers Go/No-Go, exact image/DB/Release pins, predeploy backup, controlled rollout, migration/health, smoke, invite activation, monitoring, rollback, decision record and acceptance. M25-A01–A11 covers named hypercare owner, incident SLA, daily monitoring, feedback, Phase 3 stabilization, baseline freeze, runbook, knowledge transfer, Phase 4 contract, debt and closure. The audit permits local readiness evidence in `docs/operations/`, `docs/reports/` and `tests/phase3/integration/`.
- Changed paths: `docs/operations/phase3-production-readiness-handoff.md`, `docs/PROJECT_STATE.md` and this report. No runtime, configuration, tests, protected notebook, live Arvan or engine checkout changes. No command was sent to live Arvan.
- Operational documentation gap: the historical rollout still instructs readers to use legacy IdP discovery and old vhosts, which conflicts with the frozen same-domain deployment. The [production decision runbook](../operations/phase3-production-readiness-handoff.md) identifies the correct sources and separates legacy rollout context from the current ingress instructions. It also gives a future operator the evidence and ownership checklist for Go, containment, rollback and hypercare.

## Verification and Gate disposition

| Exact command or reproducible check | Result |
| --- | --- |
| `python3 -B -m unittest discover -s tests/phase3/integration/api -p 'test_f3_lab_*.py'` | Exit 0. 90 pass, including architecture, evidence collection, log and read-load harnesses. |
| `/private/tmp/rag-arvan-pytest/bin/python -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` | Exit 0, 71 pass. |
| `/private/tmp/rag-arvan-pytest/bin/python -B -m unittest discover -s tests/phase3/foundation -p 'test_*.py'` | Exit 0, 42 pass. Fail-closed diagnostic markers were expected in negative tests. |
| `git ls-files -z -- 'infra/arvan-staging/*.sh' \| xargs -0 -n1 bash -n`; `infra/arvan-staging/deploy-arvan.sh --dry-run` | 3 syntax passes, dry-run exit 0. No service or configuration action executed. |
| Extract all fenced `sh`/`bash` blocks from `infra/arvan-staging/ROLLOUT.md` and pipe each to `bash -n`. Check the six explicit tracked SQL/script/Compose/lock paths via `git ls-files --error-unmatch -- "$path"`. | 11/11 syntax passes, 6/6 path checks. This proves syntax and local path existence only. The old-host mismatch was identified by comparing rollout prose to the current realm check and vhost templates. |
| Reload changed Markdown files and resolve relative repository links, including the rollout stop-condition anchor. Run `git diff --check` and inspect file modes, tracked scope and secret patterns. | Local paths and anchors passed. External vendor URLs were outside this offline check. No code or configuration changed, so no Web rebuild was necessary. |
| `command -v postgres psql`; `docker version --format '{{if .Server}}{{.Server.Version}}{{end}}'` | PostgreSQL binaries absent from PATH, Docker daemon unreachable. No new runtime receipt. |

| Gate | Before | After | Decision |
| --- | --- | --- | --- |
| P3M24-GATE | PENDING | PENDING | Pilot freeze and #143 do not provide production artifact, migration, restore, signed UAT, workload, P0 and approval evidence. Production NO-GO. |
| P3M25-GATE | PENDING | PENDING | Local runbook and handoff exist. Named owners, agreed incident response targets, actual hypercare, stable metrics, training and signed Phase 4 contract are pending. |

Final count across 26 independent Gates: **DONE 0, PARTIAL 22, PENDING 4**. The original 16 `EXTERNAL_DEP (Codex-2)` labels overlap those statuses. Historical 9 limited App-only lab Gate acceptances and 64 activity acceptances carry their original tested scope. No Gate advanced here.

## App-only evidence matrix

| Spec | Landed change and bounded evidence | Residual |
| --- | --- | --- |
| [P3-00](SPEC-P3-00-phase3-audit.md) | `801a768`: froze pilot tag at `4edadd3`, created completion branch, recorded SMTP and corpus deferrals, audited 26 Gates/262 activities/105 overlays. | No full acceptance inferred from pilot #143. |
| [P3-01](SPEC-P3-01-baseline-reconciliation.md) | `c6f55f6`: report only. Web baseline, contracts, SBOM, scan and Compose rendering. Historical manifest blobs matched their own commit. | Four registry assertions failed on current baseline; pinned image and complete API check open. |
| [P3-02](SPEC-P3-02-postgres-migrations-isolation.md) | `cbaa12d`: report only. 20/20 migration blob matches and 011/DB55 pins, static guards and 87 scoped tests. | No real clean/populated migration, rollback, RLS A/B, independent restore or PITR. |
| [P3-03](SPEC-P3-03-oidc-session-history-boundary.md) | `a9157d6`: report only. 143 Web and 110 Python cases passed. Chrome desktop and mobile logout with synthetic mTLS peer. | Signed PostgreSQL/Keycloak exchange, replay, expiry and revoke-all, Python security dependencies. |
| [P3-04](SPEC-P3-04-browser-history-accessibility.md) | `b8ce7bf`: History error clears on list recovery, plus browser regression. 143 Web; Chromium RTL, keyboard, focus, selection recovery and 401 purge. | Firefox/WebKit, real signed owner History and live citation journey. |
| [P3-05](SPEC-P3-05-offline-adapter-safety-provenance.md) | `952d78e`: JSON decoder depth errors map to the controlled result denial; regression covers both result paths. 104 targeted API pass and 1 skip, 71 contract and 143 Web pass. | Full Python suite, accepted Release and genuine provenance/safety evidence. |
| [P3-06](SPEC-P3-06-audit-rate-limits-security-evidence.md) | `94eec83`: zero daily quota remains restrictive, including conflicting aliases; two regression cases, 90 lab tests and bounded source/advisory receipts. | Complete HTTP 429, Web zero-quota display, DB replay, fresh image scan, operational alert receipts. |
| [P3-07](SPEC-P3-07-reproducible-staging-app-load.md) | `c630994`: deploy smoke rejects redirect success, tests exact HTTP statuses including OIDC, blocked realm and GET logout. Loopback probe under actual Next: 21/21 capabilities 200 across tiers 1/2/4. | Signed A/B, isolated deployment/restart/restore, representative authenticated workload and approved SLO. |
| P3-08 | Local Go/No-Go and rollback/hypercare runbook, consolidated evidence matrix and project-state handoff. 203 tests passed across contract, lab and Foundation suites. | No production or hypercare sign-off. |

## Supervisor decision and prerequisites

- **Local environment** — Use an isolated Linux Docker daemon with the pinned images, PostgreSQL and Keycloak. Supply the pinned Python dependencies (including PyJWT, cryptography, uvicorn and compatible OpenSSL) and Playwright's Firefox/WebKit engines. Reconcile historical registry assertions without repinning evidence. Then rerun exact-source image/security, signed owner A/B, DB migration/recovery, browser, and alert/incident checks. Pilot and local public GET timing do not establish a representative 100-user E2E workload.
- **Owner decisions and server evidence** — Name Ops/Security, DBA, UAT, release and hypercare owners, approve SLO, workload, risk and RPO/RTO, and authorize a future isolated change window. Capture the signed restore and rollback witness before considering production. SMTP and corpus deferrals remain as recorded.
- **EXTERNAL_DEP (Codex-2)** — Accepted Phase 2 Release and manifest/hashes, verified NB23 output/locators/attribution, retrieval parity and provider/safety evidence. These are separate from local toolchain failures and block producer-dependent acceptance.
- **Sequence** — P3-08 is the final Spec in the App-only map. There is no defined SPEC-P3-09. The local documentation/evidence sequence is closed for supervisor decision. Full App-only acceptance and production promotion remain open pending the prerequisites above.
