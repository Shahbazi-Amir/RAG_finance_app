# SPEC-P3-05 — Offline adapter, safety and provenance contract

**Status: PARTIALLY ACHIEVED.** Offline checks and the controlled-denial regression passed. Full API verification and producer-dependent Gate criteria remain open.

## Baseline and scope

Branch `phase3/completion`, baseline `b8ce7bf994bd27eb25b97bd0c104f3786e61a380`. The [P3-00 audit](SPEC-P3-00-phase3-audit.md) and [P3-04 handoff](SPEC-P3-04-browser-history-accessibility.md) authorize local work in `src/phase3/rag_runtime/`, `apps/api/`, `packages/contracts/`, `tests/phase3/api/` and `tests/phase3/contracts/`. Web suites were read-only verification. The activity ranges below are the enclosing module inventories. This execution covers only their adapter, safety and provenance slices.

Reviewed [frozen worker](../../infra/nb23-v4/worker.py), [worker Compose](../../infra/nb23-v4/compose.arvan-worker.yml) and [worker startup state](../../infra/nb23-v4/worker_startup_state.py) as source. The worker verifies the bundled engine digest. Compose declares no networking, a read-only root and read-only engine/artifact inputs. The check `git diff --exit-code HEAD -- infra/nb23-v4 apps/web` exited 0. No Runner, real provider, external engine checkout or Arvan service was used. The zero-generation assertion is specific to the no-dispatch fixture path, and tests exercising generation use stubs.

Changed paths:

- `src/phase3/rag_runtime/result_contract_gate.py` (tested blob `26a6d715408cacca1f8c13ad76f43817ac1b6406`).
- `tests/phase3/api/test_staging_result_gate.py` (tested blob `6ad3c6881a5e515283f4942a44f33b77d76dabcd`).
- This report. No Gate qualified for promotion, so project state was left in place.

## Fix and verification

The focused regression injects a decoder depth error with a mock. Before the fix, the suite ran 10 tests and returned 1 error because the exception escaped the standard result-denial boundary. The schema digest and the two result validators now handle `RecursionError` through the same sanitized `PreflightDenied` path used for other validation errors. The test checks both C018 and schema-pinned result paths. The fresh focused run passed all 10 tests. Existing version, identity binding, digest, field, size and zero-generation checks were kept.

Web commands were run from `apps/web`. Python commands ran from repo root using `PY=/private/tmp/rag-arvan-pytest/bin/python`.

| Exact command or reproducible method | Observed result |
| --- | --- |
| `npm run lint`, `npm run typecheck` | Exit 0 each. |
| `TMPDIR=/tmp npm test` | Exit 0, 143 pass, 0 fail and 0 skipped. Covers unverified source display, no fabricated locator, author/editor/speaker separation, unknown confidence and GET-only recovery. Web build was conditional on Web code edits. |
| `$PY -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` | Exit 0, 71 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p 'test_*.py'` | Exit 1 both runs. Before fix: 179 reported, 8 errors, 10 skips. After fix: 180 reported, 8 errors, 10 skips. Seven errors were caused by missing PyJWT/cryptography, including the graph/HTTP suite loader. One was private-ASGI certificate fixture setup on the local LibreSSL 2.8.3 toolchain with the OpenSSL `-addext` invocation. |
| `$PY -B -m unittest discover -s tests/phase3/api -p "$p"` for each module below | Targeted rerun exited 0 for each module with applicable cases: 104 passes and 1 skip. |
| `$PY -B -m pytest -q -p no:cacheprovider tests/phase3/api/test_arvan_turn_policy.py` | Exit 1, 16 pass, 1 fail at Product API import for missing PyJWT. The earlier unittest invocation discovered zero tests because this module uses pytest functions. |
| Pure graph probe using `inspect_answer_citation_graph` and `valid_answer_unresolved_source` from `packages/contracts/fixtures/product.v1.cases.json` | Exit 0. Five checks: reciprocal synthetic graph stays unverified, zero-graph no-answer cannot authorize T3, dangling claim rejected, duplicate claim rejected, and unresolved self-declared LIVE_VERIFIED rejected. Reproduce by copying the fixture per case and invoking the pure validation helper without importing the ASGI layer. |

Targeted rerun inventory: `test_staging_result_gate.py` 10; `test_staging_no_dispatch.py` 15 pass / 1 skip; `test_staging_preflight.py` 6; `test_retrieved_sources_gate3.py` 36; `test_stream_event_integrity.py` 15; `test_arvan_live_dispatch.py` 7; `test_staging_claim_bridge.py` 8; `test_staging_invited_schema.py` 7. The no-dispatch skip still requires its independent runtime prerequisites.

## Gate reconciliation

| Gate and activity range | Before | After | Offline evidence and pending criteria |
| --- | --- | --- | --- |
| P3M00-GATE / A01–A08 | PENDING | PENDING | Rejection guards cover local shape/version/digest. Accepted release, hashes, compatibility and producer smoke are external. |
| P3M07-GATE / A01–A10 | PENDING | PENDING | Worker source shows digest/readonly configuration. Live Release readiness and rollback across real assets are external. |
| P3M08-GATE / A01–A10 | PARTIAL | PARTIAL | C018 zero generation and pinned chunk evidence with synthetic inputs. Real retrieval parity and source authority remain external. |
| P3M09-GATE / A01–A10 | PARTIAL | PARTIAL | Stub generation and review-required cases passed. Provider/toolchain and policy/cost verification are pending. |
| P3M10-GATE / A01–A10 | PARTIAL | PARTIAL | Exact C018 identity ownership and schema-pinned result denial. Real proof chain and T3 with verified producer remain external. |
| P3M11-GATE / A01–A11 | PARTIAL | PARTIAL | Structural graph, locator and attribution fixture guards. Typed authoritative real locators, verified source and attribution accuracy remain external. |
| P3M12-GATE / A01–A10 | PARTIAL | PARTIAL | Fixture no-answer, review filtering and safe denial. Actual producer safety suite and No-answer F1 are pending. |
| P3M13-GATE / A01–A10 | PARTIAL | PARTIAL | Offline contracts and no-dispatch checks. Signed API integration and real stream/cancel remain pending. |
| P3M14-GATE / A01–A12 | PARTIAL | PARTIAL | UI contracts reject unverified locators and fallback author claims. Real citation journey and browser matrix remain pending. |
| P3M15-GATE / A01–A10 | PARTIAL | PARTIAL | Provenance gate denies fixture authorization for live T3. Signed DB and real owner-bound Answer retention remain pending. |
| P3M17-GATE / A01–A10 | PARTIAL | PARTIAL | Turn-policy/cache tests covered available local paths. HTTP quota 429 test is blocked by PyJWT. Real versioned cache, approved cost and producer behavior remain pending. |

Producer-dependent parts of all rows above retain the audit's **EXTERNAL_DEP (Codex-2)** classification. Python dependency and certificate-toolchain failures are local prerequisites. No full Gate advanced. Overall **DONE 0, PARTIAL 22, PENDING 4** across 26 independent Gates.

## Proposed SPEC-P3-06 — Audit, rate limits and security evidence

M16, M17 and M21. Allowed paths: `apps/api/`, `src/phase3/`, `infra/phase3_l1/`, `tests/phase3/api/`, `tests/phase3/integration/`, and `docs/operations/` per [P3-00](SPEC-P3-00-phase3-audit.md). Verify trace and redaction, quota/cache isolation and replay controls, alert and scan receipts, and resolution or owner disposition of security findings before production. Keep #143 mTLS/RS256/S256/404 and the frozen/runtime and live-server boundaries in force.
