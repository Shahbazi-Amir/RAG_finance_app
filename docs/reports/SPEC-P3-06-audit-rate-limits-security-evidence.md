# SPEC-P3-06 — Audit, rate limits and security evidence

**Status: PARTIALLY ACHIEVED.** The zero-quota regression and bounded local audit/scan checks passed. Runtime and acceptance criteria remain open.

## Baseline and scope

- Branch `phase3/completion`, baseline `952d78ee400bd390b32076d1a0c1746c0c7fab78`. Scope and known prerequisites from the [P3-00 audit](SPEC-P3-00-phase3-audit.md) and [P3-05 report](SPEC-P3-05-offline-adapter-safety-provenance.md). M16-A01–A10 covers trace/metrics, event integrity/redaction and alerts. M17-A01–A10 covers rate limits, quotas, cache, idempotency, backpressure and costs. M21-A01–A10 covers threat validation, owner isolation, transport, scans and privacy/incident acceptance.
- Changed paths: `src/phase3/rag_runtime/arvan_turn_policy.py` (tested blob `b254d0788e60405e6ed7139fdcdad13a7d6b9a34`), `tests/phase3/api/test_arvan_turn_policy.py` (tested blob `aed510906d30d955c1e610c376c801e6d4a99bbf`), and this report. Infra and Web were verification-only. No live Arvan, external engine checkout, provider or actual user data was used.
- Read-only review checked RS256 restrictions in `src/phase3/auth/service_proof.py`, S256 in bootstrap and realm sync, `CERT_REQUIRED` in the private API, and the 404 rules in both Arvan vhost templates. The [live #143 receipt](SPEC-01B-arvan-live-deploy.md) is historical. No fresh live security result was claimed.

## Quota correction

The API configuration accepts a zero daily override. The quota policy had filtered numeric overrides by truthiness, which discarded zero. It now treats only `None` as unlimited and takes the minimum finite matching limit. Two local regression cases cover an explicit zero and a zero combined with other configured aliases. Both failed before the fix and pass afterward, including reservation rejection and unaffected quota for another owner. Existing Tehran-day, replay, unlimited and cache tests still pass where the local toolchain can execute them.

The Web quota decoder currently accepts only positive finite limits, so the specialized zero-quota message remains a follow-up for the Web client. The API-side quota enforcement change is independent of that display gap. The audit's P3-06 edit-path list excludes the Web client and no Web code was modified.

## Verification

Web commands ran from `apps/web`. Other commands ran from repo root. `PY=/private/tmp/rag-arvan-pytest/bin/python`.

| Command or reproducible method | Result |
| --- | --- |
| `npm run lint`, `npm run typecheck` | Both exit 0. |
| `TMPDIR=/tmp npm test` | Exit 0, 143 pass, 0 fail, 0 skipped. Includes signed-request, auth/CSRF and owner-boundary checks. Web build was conditional on Web source changes and was not needed. |
| `$PY -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` | Exit 0, 71 pass. |
| `python3 -B -m unittest discover -s tests/phase3/integration/api -p 'test_f3_lab_*.py'` | Exit 0, 90 pass. Includes trace/metrics, sanitized log fixture pipeline and read-load harness validation. This suite does not provide a live alert, image or workload receipt. |
| `$PY -B -m pytest -q -p no:cacheprovider tests/phase3/api/test_arvan_turn_policy.py -k zero_quota_override` | Before fix exit 1 with 2 failures. After fix exit 0 with 2 pass and 17 deselected. |
| `$PY -B -m pytest -q -p no:cacheprovider tests/phase3/api/test_arvan_turn_policy.py` | Baseline 16 pass and 1 fail. After fix 18 pass and 1 fail. The remaining test stops at Product API import because PyJWT is missing, so the HTTP 429 assertion was not exercised. |
| `$PY -B -m unittest discover -s tests/phase3/api -p 'test_*.py'` | Both runs exit 1, 180 reported, 8 errors and 10 skips. Seven import/test errors from missing PyJWT/cryptography. Private ASGI certificate setup failed with the local LibreSSL toolchain on `-addext`. Skips include Linux pidfd C018 witnessing. |
| Temporary local SQLite audit probe via `LinuxRunnerSpawnAudit` | Exit 0. Write a synthetic intent, reopen the database, require bounded receipt keys and no observed count, reject duplicate intent and mismatched trace, then record UNKNOWN without claiming an OS child. Temp data removed on exit. |
| `python3 -B scripts/f3_source_supply_chain.py --self-test`; `python3 -B scripts/f3_source_supply_chain.py --repo . --out /private/tmp/rag-p306-scan-post` | Exit 0. Source SBOM reported 28 Python and 407 Web components. High-confidence secret scan: 498 tracked source files with zero matches. Artifacts stayed outside Git. |
| `npm audit --prefix apps/web --package-lock-only --omit=dev --json --fetch-retries=0` followed by `python3 -B scripts/f3_source_supply_chain.py --npm-audit-json /private/tmp/rag-p306-npm/raw.json --out /private/tmp/rag-p306-npm` | Both exit 0, advisory summary complete, 0 High and 0 Critical in scoped production Web dependencies. |
| `bash -n infra/arvan-staging/templates/realm-sync.sh`; `bash -n infra/arvan-staging/deploy-arvan.sh`; `git diff --exit-code HEAD -- infra apps/web` | Exit 0. Read-only #143 source check. |
| `command -v postgres psql trivy syft gitleaks`; `docker version --format '{{if .Server}}{{.Server.Version}}{{end}}'` | Tools absent on PATH and Docker daemon unreachable. No PG-backed owner/replay matrix, fresh image scan or 100-user runtime load result. |

## Gate reconciliation

| Gate | Before | After | Evidence and pending criteria |
| --- | --- | --- | --- |
| P3M16-GATE | PARTIAL | PARTIAL | Trace/metrics/redaction fixtures and durable audit intent checks passed. Live alert receipts, deployed logging verification, complete audit-event chain and Linux OS witness remain pending. |
| P3M17-GATE | PARTIAL | PARTIAL | Zero quota and conflicting-alias cases corrected. Local daily quota, idempotency and cache behavior exercised. HTTP 429, per-user/IP rate bounds, peak workload, real budget and versioned producer cache evidence remain pending. Producer-dependent criteria are `EXTERNAL_DEP (Codex-2)`. |
| P3M21-GATE | PARTIAL | PARTIAL | Local guard and source/advisory checks passed where runnable. Fresh image Critical/High findings, isolated PG/API transport and two-owner evidence, approved privacy/deletion criteria and incident exercise remain pending. Historical lab risk disposition is scoped to its original SHA. |

Overall **DONE 0, PARTIAL 22, PENDING 4** across 26 independent Gates. `PROJECT_STATE.md` was left in place. Unavailable local dependencies and tooling are independent of producer delivery. Recommended prerequisites are a pinned Python/OpenSSL and disposable PostgreSQL/Docker lab, image scanners and approved load/incident targets.

## Proposed SPEC-P3-07 — Reproducible staging and app-only load

App-only slices of M18–M20 and M23. Future allowed paths per the audit: `infra/arvan-staging/`, `infra/phase3_l1/`, `scripts/phase3/`, `tests/phase3/integration/` and `docs/operations/`. Acceptance calls for an isolated exact-source build, two-owner E2E, restore/rollback, and reproducible load evidence against an approved SLO. Production and engine acceptance retain their separate gates. No live promotion or 100-user capacity claim follows from lab load.
