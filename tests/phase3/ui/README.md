# UI L1 targeted checks

- Node Mock regression with the **unchanged complete shared** `product.v1.regression.2` registry from the same checkout:

  `node --experimental-strip-types --test tests/phase3/ui/mock.test.mjs`

- Genuine browser/DOM/keyboard check (requires Next.js installed and **actually running** on `127.0.0.1:3000`, and separately available Python Playwright/Chromium):

  `UI_L1_BASE_URL=http://127.0.0.1:3000 python tests/phase3/ui/browser_check.py`

  This script tests dialog Escape/Tab/Shift+Tab, focus return, untrusted text rendered as DOM text (no injected script/svg/img), disabled unsafe links, local Replay/Conflict, basic mobile viewport and takes real desktop/mobile screenshots in `/tmp/ragfinance-ui-l1-screenshots`. It must **not** be called PASS until actually executed against the running Next UI.

Mock tests are independent L1 checks, not evidence of actual server persistence, NB23 response, real Source verification, Safety, L2 or Gate approval.
