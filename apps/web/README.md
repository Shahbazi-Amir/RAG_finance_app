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

Exact dependency versions are pinned in `apps/web/package.json`. The assigned executor could not reach npm's registry (DNS EAI_AGAIN), and its offline cache did not include the required metadata (ENOTCACHED). Therefore **install, complete npm lockfile, Next build, full typecheck, ESLint, actual browser run and genuine screenshot are NOT VERIFIED/NOT AVAILABLE.** Do **not** fabricate a partial lockfile or claim `npm ci` works; create and commit a complete `apps/web/package-lock.json` with the npm resolver in an authorized isolated environment before a clean build/acceptance. The machine's observed Node 22.16.0 is not a mandated installation target and has not been security-cleared for production.

The isolated Node mock regression command (can run without Next):
    node --experimental-strip-types --test tests/phase3/ui/*.test.mjs

## UI behavior and boundaries

- Persian RTL/responsive chat, accessible labels/keyboard-focus, functional scenario selector and buttons.
- Sends `requested_conversation_id=null` for new thread; reconciles only from Mock receipt. Replays preserve original payload/key and stable message/conversation IDs; conflicts never claim success.
- Original streaming whitespace/newline is preserved; `completed` does not imply complete answer (`final_state=partial`). Display cancellation is NOT server stop. Mock server stop needs explicit confirmation.
- Synthetic claim-citation drawer shows actual fixture metadata with separate source resolution and attribution; optional title/origin does not prove provenance. No made-up locator, page, timestamp, or link. Unknown source anchors are not openable.
- React escapes text and metadata, no `dangerouslySetInnerHTML`, no unsafe raw Markdown parser, explicit HTTPS URL gate, generic technical errors and no prompt, stack trace, secrets or telemetry.
- Only local in-memory conversations. L1 mock checks cannot be used as real engine, source provenance, safety, DB, Auth, L2 or Module 14 Gate evidence.
