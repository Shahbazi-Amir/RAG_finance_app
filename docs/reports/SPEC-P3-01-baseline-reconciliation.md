# SPEC-P3-01 — App-only exact-SHA baseline and evidence reconciliation

**Status: PARTIALLY ACHIEVED.** The scoped source checks passed where noted below. Historical registry assertions and prerequisites for a clean container witness remain open.

## Baseline and scope

- Repository `RAG_finance_app`, branch `phase3/completion`, tested HEAD `801a76866a4e3ecc98d127559ee40fbbc98fc4b7` and frozen parent `4edadd3e784e1f9500dd9da8d4b6f6e40833cd13` tagged `v0.1-arvan-100users-live`. The initial working tree had only the pre-existing untracked control-notebook directory. Tracked executable source, test, lock, infrastructure and coordination paths were verified unchanged against HEAD after execution.
- [P3-00 audit](SPEC-P3-00-phase3-audit.md#spec-p3-01--app-only-exact-sha-baseline-and-evidence-reconciliation) covers five module Gates and exactly 50 numbered activities below. The only change delivered here is this report. `docs/PROJECT_STATE.md` was reloaded and checked, with its update reserved for a full pass per the Spec. No live Arvan or engine repository access occurred.
- Local witness environment: macOS, Node `v24.19.0`, npm `11.17.0`, Next.js `16.4.5`, Python `3.11.3`. Web checks used the existing local installed dependencies. Docker client was available and its daemon was unreachable. This establishes a source witness on the named SHA, with clean locked container builds, restart/persistence and image scanning still pending.

## Gate reconciliation

| Gate and exact activity range | Before | After | Evidence and remaining acceptance |
| --- | --- | --- | --- |
| P3M01-GATE / P3M01-A01–A10 (10) | PARTIAL | PARTIAL | ADR baseline and the 6-test architecture suite below. Approved architecture/scope/SLO and owner decisions still required. Numeric SLO, capacity and RPO/RTO remain unfrozen. Full ordering through M00 depends on external accepted producer evidence. |
| P3M02-GATE / P3M02-A01–A10 (10) | PARTIAL | PARTIAL | API lock checksum, Web lint/typecheck/build/unit, foundation tests, source SBOM and high-confidence secret scan, and production Web advisory scan. Clean target build, full dependency and image verification and complete baseline acceptance remain pending. |
| P3M03-GATE / P3M03-A01–A09 (9) | PARTIAL | PARTIAL | 71 contract tests, 6 architecture tests, 9 targeted App-only ASGI tests. Full exact-environment API and cross-component evidence still required. |
| P3M18-GATE / P3M18-A01–A10 (10) | PARTIAL | PARTIAL | Exact-SHA Compose configuration verifies only two read-only services, private network and no ports. Clean container build, image SBOM/critical scan, restart with persistence, and target hosting evidence remain pending. |
| P3M19-GATE / P3M19-A01–A11 (11) | PARTIAL | PARTIAL | Registry structure and historical Git object checks below. The current-SHA integrated registry check failed. Same-SHA pipeline artifacts, real image digest/scan, migration validation and approval remain pending. |

The audit's direct external classification for these five scoped Gates stays `None`. The full M01 dependency through M00 and producer-dependent inputs inherited by full M18/M19 remain `EXTERNAL_DEP (Codex-2)` where the audit identifies those upstream producer Gates. The App-only checks here used no engine. Across all 26 independent Gates the count remains **DONE 0, PARTIAL 22, PENDING 4**, with 16 external-dependency flags in the original audit.

## Verification on the tested SHA

Run Web commands from `apps/web`, the checksum command from `locks`, and other commands from repository root. `PY` below is `/private/tmp/rag-arvan-pytest/bin/python`.

| Exact command | Observed result |
| --- | --- |
| `npm run lint` | Exit 0, no findings. |
| `npm run typecheck` | Exit 0. |
| `TMPDIR=/tmp npm test` | Exit 0. 143 pass, 0 fail, 0 skipped. |
| `npm run build` | Exit 0. Compiled and generated 5/5 static pages. Two Turbopack dynamic filesystem tracing warnings in `initial-bootstrap.ts` and `product-session.ts`. |
| `$PY -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` | Exit 0. 71 pass. |
| `$PY -B -m unittest discover -s tests/phase3/foundation -p 'test_*.py'` | Exit 0. 42 pass, including intentional negative receipt checks. |
| `python3 -B -m unittest discover -s tests/phase3/integration/api -p 'test_f3_lab_architecture.py'` | Exit 0. 6 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_app_only_asgi.py` | Exit 0. 9 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p 'test_*.py'` | Exit 1. 179 tests reported, 8 errors and 10 skips. Seven import/test errors require PyJWT or cryptography. One private ASGI setup error occurred in the local OpenSSL certificate fixture command using `-addext`. Full API verification remains pending in the declared CI toolchain. |
| `python3 -B -m unittest discover -s tests/phase3/integration -p 'test_integrated_393_registry.py'` | Exit 1. 5 tests, 1 pass and 4 failures. See historical reconciliation below. |
| `LC_ALL=C shasum -a 256 -c requirements-api.lock.sha256` | Exit 0, lock OK. An initial invocation outside the lock's directory failed to resolve the relative filename. |
| `python3 -B scripts/f3_source_supply_chain.py --self-test` | Exit 0, parser self-test PASS. |
| `python3 -B scripts/f3_source_supply_chain.py --repo . --out /private/tmp/rag-p3-01-supply-chain` | Exit 0. SBOM: 28 Python and 407 Web components. High-confidence source scan: 492 files, zero matches. This is source-level evidence. |
| `npm audit --prefix apps/web --package-lock-only --omit=dev --json --fetch-retries=0` | Exit 0. Parsed using `python3 -B scripts/f3_source_supply_chain.py --npm-audit-json /private/tmp/rag-p3-01-supply-chain/npm-audit-raw.json --out /private/tmp/rag-p3-01-supply-chain`: complete, 0 High and 0 Critical. JSON artifacts were kept outside Git. |
| `docker info --format 'Server={{.ServerVersion}}'` | Docker daemon socket unreachable on normal and approved retry. The Docker client returned 0 for the formatted query but its server value was empty. No real image build, image scan or restart receipt was produced. |
| `F3_PROJECT_NAME=f3-app-only-local-p301 F3_RELEASE_TAG=p301 F3_SOURCE_SHA=801a76866a4e3ecc98d127559ee40fbbc98fc4b7 docker compose -f infra/phase3_l1/compose.app-only.internal.yml config --format json` | Render + Python assertions exited 0. Exactly API/Web, neither declared published ports, both read-only, private network internal, both build args pinned to baseline SHA. Initial command without required variables was rejected. |

Receipt SHA-256, with reproducible commands above:

- Source/Web/API CycloneDX: `96ed4b596cdfbcb110de9228e47382cacef14d012d7e6dd7a04519f6a5017867`
- Source secret scan: `57dd415f77af137649a057c642f63392faca9176dff0aac23cdc64b1ae3b6001`
- Sanitized production Web advisory summary: `a59660e6e8dd726bafe2e9ac73cd6876fd5c16e30417e6ac602095df06747c07`

## Historical evidence reconciliation

- One-to-one 393-ID cardinality passed. The remaining suite assertions failed on historical provenance, acceptance state and working-tree blob equality (two tests). The first observed blob mismatch was `apps/api/history_api.py`. The owner decision records 9 limited Gate and 64 activity acceptances for historical App-only CI SHA `4882df4ba3026ea5ab8ad1c473d50aa0d07ca6b5`. The current ledger has 73 `APP_ONLY_LAB_ACCEPTED` and 320 `NOT_ACCEPTED`. The inherited test still expects 393 `NOT_ACCEPTED` rows.
- Read-only replay method: parse `candidate_tree_selected_changes` and `paths` from the two tracked JSON manifests under `coordination/integration/`. For every path compare `git rev-parse --verify "$ref:$path"` to its `integrated_blob_sha`. The manifest's own commit `d4f800722114a5e4c292f8e5989919f38f1a2030` and tree `dbf1be62ef7e8bf0e2ec891c5bc451376bf2161d` each match 42/42 and 58/58. The owner-accepted historical CI SHA matches 39/42 and 53/58. The tested SHA matches 32/42 and 43/58. Those receipts therefore belong to distinct sources.
- CSV provenance method: join the 393 ledger and the canonical 288-row activity/Gate CSV on IDs, appending `-GATE` to original module IDs, then compare `git_sha` with `registry_sha`. The mismatch is broader than acceptance alone, including activities in all five scoped modules. Foundation needs a criterion-preserving reconciliation with a separate exact-SHA receipt. Historical pins, canonical data, expectations and assertions were left in place.
- Remaining action: run the image workflow with the pinned toolchain and a working isolated Docker daemon, produce source and image evidence separately, resolve the registry discrepancies under Foundation ownership, and obtain owner sign-off for scope/SLO and remaining Gates. No downstream Gate is promoted on these results. [Owner decisions](../../coordination/OWNER_DECISIONS_20261126.md)

## Proposed SPEC-P3-02 — PostgreSQL migrations, isolation and recovery

- **Scope:** M04, M06 and the PG-only slice of M22. Start after baseline prerequisites and explicit assignment.
- **Allowed Paths:** `infra/postgres/`, `tests/phase3/integration/api/`, `tests/phase3/integration/foundation/`, per the audit. Existing path ownership applies.
- **Acceptance:** Exact-SHA isolated PostgreSQL evidence for clean and populated migrations and rollback, two-owner isolation and RLS negatives, and independent backup/restore/PITR. Record measured results against approved RPO/RTO when available. Qdrant, producer artifacts, live infrastructure, paid calls, protected secrets and the engine repository remain outside this proposed scope.
