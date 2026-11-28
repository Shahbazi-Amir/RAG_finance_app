# SPEC-P3-03 — OIDC session and history boundary

**Status: PARTIALLY ACHIEVED.** Local browser and App-only source checks passed. The full signed OIDC/History chain requires a provisioned isolated environment.

## Baseline and scope

- Branch `phase3/completion`, tested source `cbaa12dd8ef85fba1b809c59ec7d3af25f3039b0`. Scope and prior PostgreSQL prerequisite from [P3-00](SPEC-P3-00-phase3-audit.md) and [P3-02](SPEC-P3-02-postgres-migrations-isolation.md). Only this report changes. No runtime, tests, coordination or project-state edits. No connection to live Arvan or the engine repository.
- Audit ownership for this Spec: `apps/api/`, `apps/web/app/api/auth/`, `apps/web/src/auth/`, `src/phase3/auth/`, `tests/phase3/integration/api/` and `tests/phase3/contracts/`. The broader Web and Playwright suites were run for verification.
- Exact module activity inventory: P3M05-A01–A10, P3M13-A01–A10 and P3M15-A01–A10. Within the inventory, this execution covered the App-only OIDC/History/Health slice. M05-A02 has the owner's N/A approval for password hashing. Live streaming (M13-A05), producer-backed Answer and Citation evidence (M15-A01/A06), and deferred privacy mutations/feedback/export (M15-A04/A05/A08/A09) were outside the verified slice. The local evidence does not resolve the production lockout, durable idempotency/race, revocation or expiry criteria.
- Local macOS environment used the installed Node dependencies and an existing Python 3.11 venv. PostgreSQL executables were absent from PATH. Docker client could not connect to the local daemon. There was no disposable Keycloak/PG stack. The venv has psycopg but lacks PyJWT, cryptography and uvicorn. The inspected local wheelhouse did not contain PyJWT, cryptography or the required uvicorn 0.48.0. No dependencies were downloaded.

## Gate reconciliation

| Gate | Before | After | Verified slice and residual gap |
| --- | --- | --- | --- |
| P3M05-GATE | PARTIAL | PARTIAL | Web session store, CSRF and RS256 signing checks, source checks for the private OIDC callback/transport, desktop and mobile logout. Real Code+PKCE exchange, database-backed revocation, expiry and revoke-all, and Python service verification remain pending. |
| P3M13-GATE | PARTIAL | PARTIAL | App-only ASGI Health, Send stopped at 503 before reading the body with zero inner dispatch/job/replay, forged owner header denial, and Web-side disabled Send and History contracts. Full signed HTTP/PG and complete OpenAPI/authorization validation remain pending. Real producer/streaming: `EXTERNAL_DEP (Codex-2)`. |
| P3M15-GATE | PARTIAL | PARTIAL | History and lifecycle contracts, read-only/privacy boundaries and owner-binding checks. Real two-owner signed DB comparison, revoked-session 401, owner-masked 404, durable consistency and race behavior, and approved retention/mutation policies remain pending. Verified producer provenance/History answers: `EXTERNAL_DEP (Codex-2)`. |

Overall **DONE 0, PARTIAL 22, PENDING 4** across 26 independent Gates. The existing external-dependency count remains 16.

## Verification results

Run npm commands from `apps/web`. Other commands ran at repository root. `PY` is `/private/tmp/rag-arvan-pytest/bin/python`.

| Exact command | Observed outcome |
| --- | --- |
| `npm run lint` | Exit 0. |
| `npm run typecheck` | Exit 0. |
| `TMPDIR=/tmp npm test` | Exit 0, **143 pass, 0 fail, 0 skipped**. Includes OIDC state, encrypted alias/ACK, HTTPS/Origin/CSRF, RS256, History owner/fence, disabled Send, and realm cookie expiry. |
| `npm run build` | Exit 0, 5/5 static pages produced, with two dynamic filesystem tracing warnings in the existing auth server modules. |
| `PLAYWRIGHT_MODULE=/private/tmp/rag-ux-browser/node_modules/playwright-core/index.mjs CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node tests/phase3/integration/ui/sidebar_logout_browser.mjs` | Approved local browser run exited 0. Desktop and mobile each passed GET 405, invalid-CSRF POST 403 with zero revoke calls for that request, single-click POST 303, active alias revocation, and BFF/Keycloak realm cookie removal. Theme CSS smoke also passed. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_app_only_asgi.py` | Exit 0, 9 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_app_only_privacy_contract_boundary.py` | Exit 0, 11 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_staging_bootstrap_source.py` | Exit 0, 6 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_full_binding_fence.py` | Exit 0, 5 pass. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_staging_service_profile.py` | Exit 0, 8 pass. |
| `$PY -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` | Exit 0, 71 pass. |
| `env -i PATH="$PATH" "$PY" -B -m unittest discover -s tests/phase3/integration/api -p test_bootstrap_oidc_010.py` | Exit 1, one loader error for missing PyJWT, zero test cases executed. |
| `env -i PATH="$PATH" "$PY" -B -m unittest discover -s tests/phase3/integration/api -p test_product_session_011.py` | Exit 1, one loader error for missing PyJWT, zero test cases executed. |
| `env -i PATH="$PATH" "$PY" -B -m unittest discover -s tests/phase3/integration/api -p test_app_only_mtls_network.py` | Exit 1, one loader error for missing uvicorn, zero test cases executed. |
| `command -v postgres psql` and `docker version --format '{{if .Server}}{{.Server.Version}}{{end}}'` | No PostgreSQL executable or reachable Docker server. |

The browser ran real Chrome and Next.js and used a localhost HTTPS proxy and synthetic mTLS revoke peer. Its seeded session and Keycloak cookies were synthetic, so it supplies browser boundary evidence while the real IdP exchange and durable peer behavior remain unverified. The passing App-only ASGI test counts also do not replace signed HTTP or PostgreSQL behavior.

## Pending and proposed SPEC-P3-04 — Browser History and accessibility

Restore the pinned local test dependencies and isolated PostgreSQL/Keycloak fixture, then execute the signed transport, Code+PKCE, owner A/B, 401/404, expiry and revoke-all paths. SMTP, full reset and deferred mutations retain their separate approvals. No reproducible source defect requiring a code or assertion change was observed in this run.

Proposed P3-04 scope is M14 and the UI portions of M13/M15. Allowed paths are `apps/web/app/history/`, `apps/web/src/ui/`, `tests/phase3/ui/` and `tests/phase3/integration/ui/`. Pass requires Chromium/Firefox/WebKit and mobile evidence for RTL, keyboard and ARIA, login/logout and private History. Real citations, stream/cancel and advanced PWA keep their separate gates. See the [P3-00 audit](SPEC-P3-00-phase3-audit.md).
