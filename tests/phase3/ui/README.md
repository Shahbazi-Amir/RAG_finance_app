# UI L1 targeted checks

- Node Mock regression with the **unchanged complete shared** `product.v1.regression.2` registry from the same checkout:

  `node --experimental-strip-types --test tests/phase3/ui/mock.test.mjs`

- Genuine browser/DOM/keyboard check (requires Next.js installed and **actually running** on `127.0.0.1:3000`, and separately available Python Playwright/Chromium):

  `UI_L1_BASE_URL=http://127.0.0.1:3000 python tests/phase3/ui/browser_check.py`

  This script tests dialog Escape/Tab/Shift+Tab, focus return, untrusted text rendered as DOM text (no injected script/svg/img), disabled unsafe links, local Replay/Conflict, basic mobile viewport and takes real desktop/mobile screenshots in `/tmp/ragfinance-ui-l1-screenshots`. It must **not** be called PASS until actually executed against the running Next UI.

Mock tests are independent L1 checks, not evidence of actual server persistence, NB23 response, real Source verification, Safety, L2 or Gate approval.

## UI-CHAT-013 — Main product and API Attempt recovery (Draft PR #54)

- Source PR #49 pinned `93c4cc00ed03a21c9fe8c20737f45eea8fb7c9bd`; UI branch `agent/ui-product-chat-attempt-013`. Authenticated main `/` and `/history` now use the **same non-Mock** product chat. API #52/#53 are **separate Draft dependencies**. The server-only `AUTH_CI_PRODUCT_CHAT_MODE=NO_DISPATCH_ONLY` opt-in prevents POST in the demo except the reviewed no-dispatch pathway. This is not real model readiness.
- Repro on an isolated authorized checkout with the existing pinned Node engine: `cd apps/web && npm ci --no-audit --no-fund && npm run typecheck && npm run lint && npm test && npm run build`. All tests under `tests/phase3/ui/*.test.mjs` include new checkpoint/protocol cases. **Do not interpret these as L2 tests.**
- L1 browser: start Next locally on `http://127.0.0.1:3000` after the build. Run `python tests/phase3/integration/ui/product_chat_browser.py` from repo root in an isolated Linux environment with `playwright==1.64.1` and installed Chromium. The test's `page.route` interception is synthetic **test-only**, never included in Next/staging. It asserts real rendered RTL Chat, a single POST, Refresh GET-only status on same correlation, private 401 purge. **This test is NOT_RUN until a permitted runner executes it.**
- User-facing source quotes are unavailable in `product.v1` (Claim.text is NOT a verbatim source excerpt). The UI says no direct quotation and displays only source ID/Claim and verified URL Locator. Foundation/API contract decision required before exact source quote support.
- L2 must use actual signed Product API from reviewed #52/#53 plus a permitted real producer. #53 currently has only `NO_DISPATCH_ONLY` and no live Answer, and no independent verified Runner dispatch/Locator. Do NOT claim L2 or live evidence.
