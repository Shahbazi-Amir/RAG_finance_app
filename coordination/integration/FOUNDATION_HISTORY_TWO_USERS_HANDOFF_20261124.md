# FOUNDATION_F3 shared candidate — First two-user History journey

**Candidate root**: PR #84 HEAD `0fd1066945ef91a3913e040ab4c350bb645ea502` (fresh isolated branch `integration/f3-foundation-history-two-users-20261124`). Owner transfer is exact Git blobs from PR #80 `cc04bef906d827c20dcdf5da49897246c7f2a7dd`, **not** a copy of #80's default API Dockerfile or CI identity claim.

Imported private signed ASGI entrypoint, mTLS socket liveness probe, strict config sample, 2 source/transport test suites, #80 runbook and a separate signed API Dockerfile. Original `apps/api/app_only_asgi.py` and original `Dockerfile.api` remain unchanged; the regular APP_ONLY Send deny and History 503 remain fail-closed until the real private BFF, Postgres, Bootstrap and IdP are wired.

**Run the imported L1 tests**:
```bash
python -m unittest discover -s tests/phase3/api -p test_app_only_no_engine.py -v
python -m unittest discover -s tests/phase3/integration/api -p test_app_only_mtls_network.py -v
```
The imported HTTPS/mTLS test uses an in-memory inner ASGI app and a patched DB readiness verifier: it is **not** proof of a real Browser→SQL History journey. Do not promote the five user-specified journey steps until witnessed in a single namespace with authenticated A/B and restored DB.

**Verified source witness before any execution**: #84 report `SIGNED_HISTORY_NOT_CONFIGURED` at GET /v1/conversations and 503 readiness, no token accepted from browser header. No Mac demo/011/Qdrant/Engine/server deployment allowed. The signed API path must be explicitly Ops-configured, with strict 0600 private file and real mTLS BFF fingerprint, RS256 issuer/audience and restricted PG roles. The #80 runtime deliberately refuses `CI=true` and `GITHUB_ACTIONS=true` environment flags; a real lab profile requires separate correctly bounded changes, not disabling trust checks.

**Next barriers**: assemble genuine standard OIDC IdP two subjects → signed BFF → real API/Bootstrap → TLS PG17.11 001–010 History with A/B RLS; replay after fresh-volume restore. Evidence must include SHA, HTTP/SQL IDs, screenshot/browser trace, migration ledger digest and strict negative Send/revoke/peer probes. Until then Gate 0/26; 0/5 full journey steps independently passed.

## 16 unresolved #84 three-way variants — impact triage, not unreviewed merge

Ground truth: `coordination/integration/FOUR_PR_58_PATH_THREE_WAY_AUDIT_20261124.json` at parent SHA `0fd1066945ef91a3913e040ab4c350bb645ea502`, `summary.retained_pending = 16`. Each decision below **retains the #84 file** while the first browser-to-SQL journey is tested. The owner must review exact Blob SHA + behavior before replacing it. `P0` denotes the five-step journey dependency, **not a new canonical Gate acceptance**.

| Source path (the identity of the open variant) | Journey ID / effect | Narrow action |
|---|---|---|
| `.github/workflows/foundation-integration-staging-candidate.yml` | P0-1: runner topology / exact SHA | Keep original, use a separate single-runner workflow on this branch |
| `apps/api/product_session_api.py` | P0-2/3: signed actor, session and PG transactions — **security-critical** | Preserve #84 behavior, compose via #80 private ASGI; test real A/B negative matrix |
| `apps/web/app/history/page.tsx` | P0-4: real History DOM and pagination — **critical** | Preserve #84 UI; browser must assert persisted IDs rather than synthetic responses |
| `apps/web/app/layout.tsx` | P0-2/4: browser layout/CSP and authentication navigation | Preserve; require real callback and CSRF regression |
| `apps/web/app/page.tsx` | P0-4: landing-to-History route and state | Preserve; verify navigation after real callback |
| `apps/web/README.md` | P0-5: deployment guide only | No runtime import; update after witness |
| `apps/web/src/history/client.ts` | P0-4: bounded API pagination + Refresh — **critical** | Preserve; correlate each owner ID with server and PG |
| `coordination/open_decisions.md` | P0-6: policy/release decisions only | Retain open approvals; no silent acceptance |
| `coordination/phase3_checklist.md` | P0-6: canonical status source | Do not reclassify activities without exact receipts |
| `coordination/tasks/AGENT-API-AUTH-BOUNDARY-01.md` | P0-2: trust ownership documentation | Keep until API owner signs BFF/mTLS/actor contract |
| `coordination/tasks/AGENT-FOUNDATION-01.md` | P0-1/5: Foundation boundaries | Keep and append current SHA evidence only |
| `coordination/tasks/AGENT-UI-01.md` | P0-4: UI/AT acceptance criteria | Keep and request real browser test owner |
| `src/phase3/rag_runtime/retrieved_sources.py` | Engine-dependent future slice, **outside first History** | Never import Runner/Engine to clear History gate |
| `tests/phase3/api/test_retrieved_sources_gate3.py` | Engine source/authority tests, outside first History | Keep out of app-only live witness; retain offline tests |
| `tests/phase3/ui/product-chat-client.test.mjs` | P0-4: UI Send-Disabled client regressions | Preserve; test direct BFF POST 503 and zero DB writes |
| `tests/phase3/ui/README.md` | P0-4 documentation only | No behavior changed |

**High-impact unresolved variants: 5** (Product API, History page/client, app layout, client Send test); **others are CI/docs/landing or deferred engine**. This is prioritization, not a claim that the five are defective or require copying owner files. A failing exact behavior assertion, not the other PR's filename, selects any future change.

## Current execution proof

- Base #84: `0fd1066945ef91a3913e040ab4c350bb645ea502` — original exact-SHA Actions 45271111946 success, but original signed History on standard App path returned 503.
- Imported #80 owner files: `2df91a15b0bb428dc273a4ee65f3428b35775580` (source #80 `cc04bef906d827c20dcdf5da49897246c7f2a7dd`).
- Reproducible signed-after-independent-volume-restore test and single-job Actions: `865a9b79f73c4c7390051804798ee420325b9ff8` (subsequent exact SHA corrections visible in PR #88).
- Original signed API BFF→PG Keycloak-style CI flow is **test harness**; it is not the user's requested **standard, independently configured Keycloak service with two full browser OIDC sessions**. Even a green recovered SQL receipt is only P0-3 and API subset evidence; never mark browser P0-2/4 or complete P0-5/restore E2E accepted.
- Non-acceptance: 0/26 signed Phase-3 Gates; 0/5 complete **user journey steps** until same-SHA actual browser→SQL and post-restore browser are witnessed. No Mac/engine/destination mutations.

## Foundation transfer from tested API checkpoint

Base of this working branch: #84 `0fd1066945ef91a3913e040ab4c350bb645ea502`; previous Foundation SHA `71c5e13366bec9b3101188f49b0dcf4fff197537`. Selected tested API source #87 `23db3da6367e6a8279072ee96b56a2bd4b7f0fbc` (runs 45392028003 and 45392028018). No owner approval or release. Exact imported blobs:

- `apps/api/app_only_socket_probe.py` — `bbc803942b0d59a674f116a78c6b9a5786ab14d6`
- `apps/api/private_app_only_asgi.py` — `5a4807dbb725e9474676b21be221aed4b7a52d38`
- `apps/api/private_staging_asgi.py` — `0f87572041cf179db6de004a41cc266a16994b67`
- `apps/api/product_session_api.py` — `32d6148e1eb9f014ee62a4e607516547e510c7ec`
- `src/phase3/auth/service_proof.py` — `63f85aa2f15a435faa44e9f41d25df8e7f2e43be`
- `src/phase3/auth/staging_service_profile.py` — `bfc45cfcc1989c4fbe1bef9df975eb3c13733c97`
- `tests/phase3/api/test_app_only_no_engine.py` — `9514d9ac21b3f45542a3bcdeaf689168f1096912`
- `tests/phase3/api/test_service_proof.py` — `cc6368349602ce1e358a0e8efd4152a219fd7b85`
- `tests/phase3/integration/api/app_only_signed_pg_ci_h11.py` — `50131268814dd39e9de2b0e2d7744ed9dd4189a6`
- `tests/phase3/integration/api/test_app_only_browser_journey.py` — `52e0f1632cb8573a80911e0b1c8dfba8ff2055e4`

Existing #88 deny-only image and four regression workflows retained. Dedicated same-runner browser/real signed OCI API/restored TLS PG workflow uses the existing separate signed Dockerfile, now with explicit PHASE3_APP_MODE. Web and Bootstrap remain host CI processes; full private Compose topology and owner decisions remain open. No 011, provider, target or main change. Do not count pending CI as acceptance.
