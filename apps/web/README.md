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
