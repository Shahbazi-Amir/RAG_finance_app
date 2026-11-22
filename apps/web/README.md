# AGENT-UI-01 — Next.js L1 chat (SYNTHETIC)

This is a Next.js + TypeScript **mock-only** consumer of the repository's shared `product.v1` fixtures. No backend, model, database, Auth, persistent history, Feedback, Deletion, or deployed service is involved. The adapter is deliberately inside `apps/web/src/mock/transport.ts` and reads the **unchanged** `../../packages/contracts/fixtures/product.v1.cases.json` registry.

## Local setup (ONLY in isolated task workspace with registry access)

    cd apps/web
    NEXT_TELEMETRY_DISABLED=1 npm install --ignore-scripts --no-audit --no-fund
    NEXT_TELEMETRY_DISABLED=1 npm run typecheck
    NEXT_TELEMETRY_DISABLED=1 npm run lint
    NEXT_TELEMETRY_DISABLED=1 npm test
    NEXT_TELEMETRY_DISABLED=1 npm run build
    NEXT_TELEMETRY_DISABLED=1 npm run dev

Visit **http://127.0.0.1:3000**. Stop the temporary process with Ctrl+C.

Exact dependency versions are pinned in `apps/web/package.json`. The unused `vitest` dependency was removed: unit tests use Node's built-in `node:test` runner.
For optional genuine DOM/keyboard security checks, see `tests/phase3/ui/browser_check.py` (requires a running Next UI; not a substitute for renderer tests). The assigned executor could not reach npm's registry (DNS EAI_AGAIN), and its offline cache did not include the required metadata (ENOTCACHED). Therefore **install, complete npm lockfile, Next build, full typecheck, ESLint, actual browser run and genuine screenshot are NOT VERIFIED/NOT AVAILABLE.** Do **not** fabricate a partial lockfile or claim `npm ci` works; create and commit a complete `apps/web/package-lock.json` with the npm resolver in an authorized isolated environment before a clean build/acceptance. The machine's observed Node 22.16.0 is not a mandated installation target and has not been security-cleared for production.

The isolated Node mock regression command (can run without Next):
    node --experimental-strip-types --test tests/phase3/ui/*.test.mjs

## UI behavior and boundaries

- Persian RTL/responsive chat, accessible labels/keyboard-focus, functional scenario selector and buttons.
- Sends `requested_conversation_id=null` for new thread; reconciles only from Mock receipt. Replays preserve original payload/key and stable message/conversation IDs; conflicts never claim success.
- Original streaming whitespace/newline is preserved; `completed` does not imply complete answer (`final_state=partial`). Display cancellation is NOT server stop. Mock server stop needs explicit confirmation.
- Synthetic claim-citation drawer shows actual fixture metadata with separate source resolution and attribution; optional title/origin does not prove provenance. No made-up locator, page, timestamp, or link. Unknown source anchors are not openable.
- React escapes text and metadata, no `dangerouslySetInnerHTML`, no unsafe raw Markdown parser, explicit HTTPS URL gate, generic technical errors and no prompt, stack trace, secrets or telemetry.
- Only local in-memory conversations. L1 mock checks cannot be used as real engine, source provenance, safety, DB, Auth, L2 or Module 14 Gate evidence.


## UI-HISTORY-01 — CI-only History alongside independent Mock

The original / route is the local-only Mock and never writes to PostgreSQL. The /history page reads/writes only merged product.v1 History API records and NEVER falls back to Mock on API errors. T1 persists a user message only; an Answer is not generated or a model invoked. Auth is unavailable outside a fixture. Page- and conversation-scoped deduplication, immutable retry payloads, single read-only status recovery, 401, loading/empty/error states and refresh-based DB retrieval are implemented. Unknown in-flight requests are volatile; they do not survive browser refresh because private requests are not stored locally.

The same-origin server route at app/api/history/[...path]/route.ts is strictly CI-only and fails 503 without CI=true and a fixed loopback origin from a narrow port allowlist. The browser may not choose an upstream, user, DSN, signing key or secret. No Cookie/Auth header is forwarded and there is no general-purpose proxy. Real product Auth, trusted proxy and security acceptance require future approval.

Tests/phase3/integration/ui/harness.py imports the existing FastAPI app in two separate loopback processes (one fixed synthetic test actor each) and a third with default deny-401. Separate test-only Repository T2/T3 calls seed an artificial Answer directly into disposable PostgreSQL; NO public seed route exists. Browser E2E tests with real Chromium cover desktop/mobile; screenshots and logs belong to short-lived GitHub Actions artifacts, not to the repo. Original Mock browser/Node checks also run. This is neither production Auth nor model readiness.

## Private staging BFF source profile (Ops-provisioned; NOT deployed)

Draft UI #54 supports a **separate**, explicit `AUTH_RUNTIME_PROFILE=private-staging` run mode. It will **reject** `CI=true`, `GITHUB_ACTIONS=true`, all old `AUTH_CI_LOGIN_MODE` / `AUTH_CI_DEMO_MODE` / `AUTH_CI_PRODUCT_CHAT_MODE` flags, absent files, loose permissions, untrusted proxy or unapproved origin. Never set CI to true to start staging. No default secret/CA/key, no browser-supplied override, no HTTP callback, no public API, no Gateway action. Only a named operator may install the file and start the service after Foundation/API/DB signoff.

Set `AUTH_STAGING_CONFIG_FILE` to an **absolute** server-controlled 0600 JSON file owned by the Next service UID or root. Required fields (all strings, no additional fields):

- `public_origin` exactly `https://ragfinance.ir`; `idp_authorization_origin` pinned exact HTTPS IdP origin from Ops; `bootstrap_origin` and `product_origin` pinned HTTPS private API origins (not public ragfinance.ir)
- `store_dir` pre-created, service-owned 0700 directory on **shared durable filesystem for all BFF workers**; no temporary CI store; coordinate multi-worker atomic alias storage/revocation design with Foundation before horizontal scaling
- File paths, each absolute, regular, owner/root, **0600**: `proxy_proof_file`, `csrf_secret_file`, `alias_key_file` (32-byte base64url), `bootstrap_sign_key_file`, `product_sign_key_file`, `tls_ca_file`, `tls_client_cert_file`, `tls_client_key_file`
- `bootstrap_issuer`, `bootstrap_audience`, `bootstrap_kid`, `product_issuer`, `product_audience`, `product_kid` must exactly match vetted API trust configuration; `send_mode` = `DISABLED` by default or `NO_DISPATCH_ONLY` only after Ops/API/DB approval and installed server-side no-dispatch handler

Ops reverse proxy must terminate a CA-valid public HTTPS certificate on `ragfinance.ir`, **strip inbound** `x-auth-staging-proxy-proof`, `x-forwarded-host`, `x-forwarded-proto`, and inject exact trusted values only on an internal-only Next listener. Never expose BFF directly. The proof value in `proxy_proof_file` is never sent to browsers. Browser cookies use `__Host-` + Secure + HttpOnly + SameSite=Lax, Login and Logout require same-origin CSRF, Callback retains single-use state/Code+S256 and server-side ACK before session cookie. Node HTTPS sender must validate private CA and mTLS certificate and sign exact method/raw path/query/body with JTI and owner-session fence. No bypass via an HTTP client-controlled header is acceptable.

For a recorded staging test, Foundation/Ops must provide **non-secret evidence only**: named service/unit, checked deployed SHA, private socket/UID binding, CA and proxy identity checks, explicit Keycloak redirect and callback trace, 200 private A/B History, one POST 202, same-origin GET Product Status then signed GET `/v1/message-requests/engine-status` (original three IDs), `CONTEXT_READY` with `generation_calls=0` or honest UNKNOWN, Refresh with zero extra POST, committed Logout 200, B isolation. No operator credentials or .env contents may enter this repo. Offline Node tests only exercise local synthetic config and GET-only boundary; **no actual staging host was accessed**.


## Gate3 C018 retrieval evidence — isolated UI preview only

The authenticated Product page currently consumes `api.no_dispatch_status.v1`, which contains only the `top10_count` and `generation_calls` and **NO individual source rows**. It renders a truthful technical count under `شواهد بازیابی`; no source links or claims can be inferred from that number. This is not an approved source-bearing API or `LIVE_VERIFIED` Answer.

New `src/ui/retrieval-evidence-view.ts` and `src/ui/retrieval-evidence-panel.tsx` implement a UI-local, fail-closed presentation policy, **NOT a wire DTO**: API-verified public HTTPS locator → link; verified source with no locator → IDs and no-link message; unverified destination → no link; unverified source → no source claim/IDs; verified book page or transcript time → location text but not a fabricated URL. The panel is intentionally unconnected to product until API_F3 and Foundation approve a signed, independently validated exact-Attempt C018 source endpoint.

Test-only `/ci-evidence-preview` is enabled ONLY by `CI=true`, `GITHUB_ACTIONS=true`, explicit `AUTH_CI_PRODUCT_CHAT_MODE=INVITED_RESULT_STUB_CI_ONLY`, and Host `127.0.0.1:3000`. It prominently labels all sources SYNTHETIC; never use it for a production or staging demonstration. Dedicated `tests/phase3/ui/retrieval-evidence-view.test.mjs` and `tests/phase3/integration/ui/retrieval_evidence_preview_browser.py` verify negative and RTL/mobile states. No real C018, Mac Docker, Keycloak, API, paid Gateway or OS exec count is claimed.
