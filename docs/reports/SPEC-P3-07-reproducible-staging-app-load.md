# SPEC-P3-07 — Reproducible staging and app-only load

**Status: PARTIALLY ACHIEVED.** Deployment source checks and bounded local HTTP timing passed. The isolated signed stack, workload and release gates remain open.

## Scope and exact source

- Repository `RAG_finance_app`, branch `phase3/completion`, base `94eec83220f6a093e724d9393cb88a1ff4a96462`. Scope per the [P3-00 audit](SPEC-P3-00-phase3-audit.md) and [P3-06 baseline](SPEC-P3-06-audit-rate-limits-security-evidence.md) is the App-only slice of M18–M20 and M23. The exact module inventories are M18-A01–A10, M19-A01–A11, M20-A01–A11 and M23-A01–A10. The scoped work checks template/script reproducibility, configuration integrity, expected HTTP boundaries, stable App-only startup and bounded concurrency. Release approvals and provider-backed workload criteria remain separate.
- Changed files: `infra/arvan-staging/deploy-arvan.sh` (tested Git blob `ff3dd23ef18ef88176b54fd41f567d5f876ed500`), `tests/phase3/integration/api/spec_p307_loopback_probe.py` (tested Git blob `98a551f54de0f10ce4d8fedba761449f8ac75658`), and this report. The Next.js build used the unchanged application sources at the baseline. No live Arvan or engine repository access took place.
- Source review covered the same-domain and legacy deny-only Nginx routes, systemd service templates, strict RS256 and PKCE S256 realm checks, and the private mTLS smoke verifier. The template, systemd, application and frozen engine runtime paths compare unchanged to the baseline. Live #143 evidence remains the historical [SPEC-01B receipt](SPEC-01B-arvan-live-deploy.md).

## Fix and verification

A local HTTP fixture returned 302 and received exit 0 from the legacy `curl -f` check. The deployment smoke now verifies exact HTTP 200 for capabilities, login and the actual discovery response before validating its issuer, RS256 and S256 JSON. The same helper requires 404 on blocked routes (including a non-staging realm) and 405 for GET logout. Existing service activity, discovery policy and mTLS requirements still apply.

| Command or method | Actual result |
| --- | --- |
| `git ls-files -z -- 'infra/arvan-staging/*.sh' \| xargs -0 -n1 bash -n` | 3 scripts parsed, 0 failures. |
| `infra/arvan-staging/deploy-arvan.sh --dry-run` | Exit 0 before and after correction. Two post-change runs produced identical plans. The plan covers offline build, units, theme, realm, Nginx and smoke. |
| `python3 -B -m unittest discover -s tests/phase3/integration/api -p 'test_f3_lab_*.py'` | 90 pass, 0 fail, covering lab read-load/overlap, health receipts, log/trace and architecture harnesses. These are harness tests. |
| `python3 -B scripts/f3_source_supply_chain.py --repo . --out /private/tmp/rag-p307-source` | Exit 0. 499 tracked source files scanned, zero high-confidence secret matches, SBOM inventory of 28 Python and 407 Web components. New files were separately reviewed from disk before staging. |
| `F3_PROJECT_NAME=f3-app-only-local-p307 F3_RELEASE_TAG=p307 F3_SOURCE_SHA=94eec83220f6a093e724d9393cb88a1ff4a96462 docker compose -f infra/phase3_l1/compose.app-only.internal.yml config --format json` with JSON assertions | Pass, exactly API/Web, both read-only, no published ports, internal network and source pin on both build definitions. No containers started. |
| In `apps/web`: `npm run build` | Exit 0, 5/5 static pages. Two existing Turbopack dynamic tracing warnings in the auth server modules. |
| `python3 -B tests/phase3/integration/api/spec_p307_loopback_probe.py` | Exit 0. The exact-status helper rejected 302 (exit 1) and accepted local 200 (exit 0). The discovery branch rejected 302 before inspecting JSON. Actual Next loopback benchmark passed all 21 timed capability reads with status 200, `no-store`, and disabled generation. One independent unauthenticated History GET returned expected fail-closed 503 with `no-store`. |
| `docker version --format '{{if .Server}}{{.Server.Version}}{{end}}'`; command discovery for nginx, systemd-analyze, postgres, psql and shellcheck | Docker daemon unreachable on normal and approved checks, latter exit 1. The other tools were absent from PATH. No local Linux runtime validation or image/PG witness produced. |

### Measured loopback HTTP

The probe uses a fresh localhost port, a production Next build, App-only environment, 3 waves per tier and independent HTTP connections. Durations include each local HTTP response body; wall durations include wave overhead. Both temporary servers are stopped at cleanup. This workload only measures the public capabilities response and makes no mutating requests.

| Concurrent clients | HTTP 200 / attempted | Median request (ms) | Max request (ms) | Tier wall (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 3 / 3 | 6.44 | 10.04 | 28.60 |
| 2 | 6 / 6 | 14.18 | 24.05 | 55.83 |
| 4 | 12 / 12 | 16.43 | 27.49 | 72.57 |

Signed user History throughput, real peak load and SLO compliance were not measured.

## Gate reconciliation

| Gate | Before | After | Pending evidence |
| --- | --- | --- | --- |
| P3M18-GATE | PARTIAL | PARTIAL | Pinned clean image build, image scan and restart/persistence in isolated Linux Docker. |
| P3M19-GATE | PARTIAL | PARTIAL | Same-SHA signed receipts, migration/rollback, image digest/scan and approval. Existing historical registry reconciliation remains open. |
| P3M20-GATE | PARTIAL | PARTIAL | Repeatable test deployment with real signed A/B OIDC/PG, restart and restored data, nginx/systemd preflight, rollback and UAT. Full live-engine path remains `EXTERNAL_DEP (Codex-2)`. |
| P3M23-GATE | PARTIAL | PARTIAL | Authenticated History load/soak/outage on an isolated stack, an approved SLO and workload, and measured representative peaks. Live retrieval/provider load remains `EXTERNAL_DEP (Codex-2)`. |

Overall **DONE 0, PARTIAL 22, PENDING 4** of 26 independent Gates. `PROJECT_STATE.md` was left untouched. Preconditions for a complete lab receipt include pinned Docker/Linux image and tooling, PostgreSQL/Keycloak isolation, clean restore and signed two-owner data, plus approved load targets. No 100-user load result or fresh live gate PASS is claimed.

## Proposed SPEC-P3-08 — Production readiness and handoff evidence

Scope: local readiness for M24–M25. Allowed paths: `docs/operations/`, `docs/reports/` and `tests/phase3/integration/` under the [audit](SPEC-P3-00-phase3-audit.md). Collect Go/No-Go, rollback/backup, UAT, monitoring and a named owner for hypercare, with an approved Phase 4 handoff. Production acceptance waits for the full server and engine evidence, workload and owner approvals.
