# SPEC-P3-04 — Browser History and accessibility

**Status: PARTIALLY ACHIEVED.** Chromium desktop/mobile checks passed after fixing a stale History refresh alert. The complete cross-engine and real private-History journey remains pending.

## Scope and exact source

- Branch `phase3/completion`, baseline `a9157d643a8edd99e04c5c2e8235251810675fe8`. Scoped to M14 and the UI slices of M13/M15, per [P3-00](SPEC-P3-00-phase3-audit.md) and [P3-03](SPEC-P3-03-oidc-session-history-boundary.md). Allowed paths are `apps/web/app/history/`, `apps/web/src/ui/`, `tests/phase3/ui/` and `tests/phase3/integration/ui/`, plus this report.
- Activity inventory: P3M14-A01–A12. Primary checks cover A01–A03 and A09–A12 (session/logout, list, responsiveness, recovery, basic a11y, target browsers and debug boundaries). Relevant UI slices are P3M13-A03/A04/A08/A09 (error/paging/authorization/contract), and P3M15-A03/A07 (paging and account boundary). The new fixture exercises two conversations within one owner plus a 401. Durable two-owner isolation requires the signed backend environment. A04–A08 (stream/cancel, citation, attribution, confidence and no-answer) retain their independent evidence requirements.
- Changed paths: `apps/web/src/ui/product-chat.tsx` (tested Git blob `2a9aaedbd78aeec18d3cf228d2e3bee9b689aba5`), `tests/phase3/integration/ui/history_accessibility_browser.mjs` (tested Git blob `a019bba55328f3a7908db30e82650c12879a4b98`), and this report. No authentication, role, service or database code changed. No live Arvan or engine repository access occurred.

## Bug and correction

The Chromium fixture reproduced a stale error after History returned from a 503. The list request had written to the shared action-error state as well as setting the list status. On recovery only the list status changed. The alert now derives from list failure state, while action errors keep their existing independent behavior. Failed revalidation still clears the rendered messages and disables Send, and recovery waits for a successful owner-bearing list before refetching messages. The fixture verified restoration of the selected conversation with zero writes and a subsequent 401 purge.

The first browser attempt also failed because its two new fixture rows tied on timestamps and did not respect the API's descending ID tie-break. The fixture now has distinct newest-first timestamps. A second attempt reproduced the stale alert. The new assertion targets the History alert and excludes Next's route announcer. All checks below passed after the correction.

## Verification

Commands ran against the listed source and test blobs on macOS with Node 24.19.0 and Chrome 150.0.7871.125.

| Command or environment | Result |
| --- | --- |
| In `apps/web`: `npm run lint`, `npm run typecheck` | Both exit 0 before and after the fix. |
| In `apps/web`: `TMPDIR=/tmp npm test` | 143 pass, 0 fail, 0 skipped both runs. |
| In `apps/web`: `npm run build` | Exit 0 before and after fix. Both reported the two existing Turbopack auth tracing warnings. |
| `node --check tests/phase3/integration/ui/history_accessibility_browser.mjs` | Exit 0. |
| Local History fixture in Chrome, command below | Final exit 0, four checkpoints passed. Desktop RTL and Persian language, keyboard skip link and focused heading, selected History after browser Back from the anchor, disabled Send and contrast 16.73:1. Recovery preserves selection and clears stale alert. At 390px: modal role/name, inert background, visible keyboard outline, focus trap, Escape and focus restoration, no root overflow. Revocation fixture hides messages on 401 and the test observes zero writes. |
| `PLAYWRIGHT_MODULE=/private/tmp/rag-ux-browser/node_modules/playwright-core/index.mjs CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node tests/phase3/integration/ui/sidebar_logout_browser.mjs` | Exit 0, three checkpoints. Desktop and mobile denied bad CSRF (403), denied GET logout (405), accepted one-click POST (303) and removed fixture cookies. Mobile theme check passed. |
| `HISTORY_BROWSER_ENGINE=firefox` and `HISTORY_BROWSER_ENGINE=webkit` with the same Playwright module and History script | Both launch attempts stopped before a browser assertion. Playwright Firefox 1572 and WebKit 2388 executables were absent. Installed desktop Firefox/Safari were not used as Playwright bundle substitutes. |
| `/private/tmp/rag-arvan-pytest/bin/python -B -c 'import importlib.util; print(importlib.util.find_spec("playwright") is not None)'` | False. Existing Python browser suites require their separate environment. |

Local History reproduction, from the repo root, after a successful build:

```bash
node apps/web/node_modules/next/dist/bin/next start apps/web -H 127.0.0.1 -p 32194
```

Once Next responds on loopback, run in another shell:

```bash
HISTORY_BROWSER_BASE=http://127.0.0.1:32194 \
PLAYWRIGHT_MODULE=/private/tmp/rag-ux-browser/node_modules/playwright-core/index.mjs \
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
node tests/phase3/integration/ui/history_accessibility_browser.mjs
```

The History script intercepts browser API routes with versioned fixtures. The logout script uses real local HTTPS and a synthetic mTLS revoke peer. ARIA and contrast assertions are bounded browser checks. Screen-reader audio, full WCAG conformance, real IdP login and signed database History remain unverified.

## Gate reconciliation

| Gate | Before | After | Remaining evidence |
| --- | --- | --- | --- |
| P3M14-GATE | PARTIAL | PARTIAL | Firefox/WebKit and full real Login→Chat→Citation→History. Real citation/attribution and live stream/cancel depend on producer evidence, `EXTERNAL_DEP (Codex-2)`. Advanced PWA remains separately scoped. |
| P3M13-GATE (UI) | PARTIAL | PARTIAL | Signed backend/OpenAPI/authorization and producer-backed streaming, `EXTERNAL_DEP (Codex-2)` for the latter. |
| P3M15-GATE (UI) | PARTIAL | PARTIAL | Real owner A/B PostgreSQL/Keycloak journey, durable History and policy-dependent lifecycle behavior. Verified producer Answer remains `EXTERNAL_DEP (Codex-2)`. |

Overall **DONE 0, PARTIAL 22, PENDING 4** across 26 independent Gates. `PROJECT_STATE.md` was not changed. No browser bundle or dependency download occurred.

## Proposed SPEC-P3-05 — Offline adapter, safety and provenance contract

App-only slices of M00, M07–M12, M13–M15 and M17. Allowed paths in the audit are `src/phase3/rag_runtime/`, `apps/api/`, `packages/contracts/`, `tests/phase3/api/` and `tests/phase3/contracts/`, with the frozen runtime read-only. Pass requires mismatch rejection, no-dispatch with zero external calls, schema/fixture checks, and guards against fabricated locators and attribution. Upstream Release and live producer acceptance stay external.
