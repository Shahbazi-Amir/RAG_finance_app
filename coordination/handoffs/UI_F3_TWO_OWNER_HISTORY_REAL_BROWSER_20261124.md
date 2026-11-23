# UI F3 handoff — REAL A/B History browser, signed-only, app-only — 2026-11-24

**UI owner delivery to Foundation candidate [#84](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/84).** Separate UI [Draft PR #89](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/89), branched from **exact original #84 HEAD `0fd1066945ef91a3913e040ab4c350bb645ea502`**, branch `agent/ui-f3-real-two-owner-history-20261124`, base `integration/f3-app-only-four-pr-candidate-20261124`. Apply this UI patch only after comparing **actual current Foundation #84 HEAD**, no force-push, no default branch/Mac/demo mutation, no Engine or Runner. Source-candidate CI runs are **not** real connected A/B target acceptance.

## First actual boundary, source and HTTP evidence

On an isolated `CI=true, PHASE3_APP_MODE=APP_ONLY` Web built from the exact candidate, a REAL production Next server and real Playwright Chromium **without route interception or cookie injection** requests:
- `GET http://127.0.0.1:3100/history` → rendered product page; its ordinary browser `GET /api/history/conversations?limit=2` → **503**; `history-state` displays unavailable and zero conversation/message DOM rows. This is the expected first unavailable History trust boundary, **NOT** an Owner A login. Evidence script: `tests/phase3/integration/ui/app_only_entry_baseline_real_browser.py` at desktop 1280px and mobile 390px.
- `GET http://127.0.0.1:3100/login` → **503**, because the unconfigured lab lacks authorized HTTPS reverse proxy proof. No `__Host-rag-*` cookie is issued. This is the FIRST blocking boundary for a real login, before IdP; do not fake HTTPS or inject headers to convert it to 200.
- The actual BFF `POST /api/history/messages` from a normal browser `fetch` → **503 `ENGINE_NOT_AVAILABLE`** with zero React submit POST; disabled Send is enforced server-side, not only a disabled HTML button.
- `product-chat.tsx` now truthfully states that History is only available **after secure login and server connection**. Previously it promised `History can be viewed` even while the real source returned 503.
- Updated real-browser locators `data-testid=more-conversations` and `more-messages` on the **same existing real product UI buttons**, enabling deterministic next-page assertions, not test-only routes. Underlying ownership/response handling remains unchanged.

**Baseline exact-SHA CI:** pin actual latest `UI F3 exact-candidate real browser History baseline` GitHub run in PR #89 once final delivery SHA is tested; early verified run [45276543670](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45276543670) on `d0e82bfe9adfe177341126f9d77fd196acd86efb`: 136/136 Node, build/lint/typecheck, real Chromium normal GET 503 on desktop/mobile, explicit direct POST 503. Further updated baseline also measures login 503; do **not** attribute its success to the earlier SHA without rerunning.

## True A/B test added, but NOT YET EXECUTED on signed integration

File: `tests/phase3/integration/ui/real_signed_two_owner_history_journey.py`.

Only when Foundation/API/DB have actually started a **single disposable, persistent CI stack** does this script:
1. Start two separate **fresh Chromium browser contexts**; navigate the real `/login` page, submit native BFF login, follow actual Keycloak OIDC authorization form, enter ephemeral A/B credentials through the IdP form; wait for real BFF callback/session Cookie, then demand `GET /api/history/conversations?limit=2` **200** and actor-scoped owner ID matching an independent **PG-generated** seed manifest.
2. Verify A's ordered list rows and **cursor page 2** from actual BFF/API/PG; navigate A's first long thread and actual message cursor page 2 (31+ seeded messages). Compare **exact PG-record IDs and order** against DOM. Refresh and demand the exact same IDs again; never create or duplicate a message.
3. Have authenticated B use a **real same-origin browser GET** on the exact A conversation URL; demand **404** with no foreign ID in the error. B's list must never contain any A record.
4. Probe direct Send **once** through an ordinary in-browser `fetch` with a valid `product.v1` payload; demand **503 `ENGINE_NOT_AVAILABLE`**; SQL owner separately proves no new `history_l1.send_receipts`, T1/T2, child or generation. Never enable Engine to pass this test.
5. Revoke A with a **native same-session Logout form** in a second tab; require 303 and committed server receipt. The old browser tab's real GET must become **401** and remove **every A conversation/message DOM node**. B's own authenticated GET remains 200.
6. Repeat on 1280px and 390px. Emits **sanitized only** receipt (SHA and record ID digest, test booleans); never records token/password/cookie/PG DSN. **No `route.fulfill`, `route.fetch`, `context.add_cookies`, fake actors, upstream override, `storage_state`, preview or synthetic API**.

**Preflight deliberately fails closed** without actual approved CI/IdP/PG evidence. Source syntax and negative preflight success are **NOT** an A/B journey success.

### One-replay prerequisites for Foundation/API/DB

Foundation keeps the one candidate #84 branch and adds this UI patch; API configures real signed BFF HTTPS→mTLS API→PG History, Bootstrap OIDC and revoked session checks, all in the **same job and same Docker network/Runner**. Prior #84 `apps/api/app_only_asgi.py` has **`SIGNED_HISTORY_NOT_CONFIGURED` 503**; don't route tests to that no-op listener and mistake it for signed History. API should inspect #80 actual mTLS listener and integrate the real signed data route without importing Engine. Preserve `PHASE3_APP_MODE=APP_ONLY`, Send 503 and /health/ready 503 on failed DB/issuer/dependency; 200 only when truly ready.

DB creates a **brand-new** PG17.11 TLS volume with exact migrations 001–010 (no 011), two real distinct mapped Keycloak subjects, A **at least three distinct ordered conversations** and **31+ real PG user messages in A's newest conversation**, plus B at least one distinct conversation. DB independently queries list/detail and orders using the restricted `history_app` role (not a forged browser owner); records IDs/owners and expected exact page order in a sanitized JSON fixture file **in that same disposable CI job**, never checked into Git. Minimum strict schema:

```json
{
  "kind": "ui_f3_actual_pg_two_owner_seed",
  "contract_version": "ui.pg_two_owner_seed.v1",
  "integrated_sha": "<current candidate 40-hex commit>",
  "pg_cluster_id_sha256": "<sha256 of real fresh cluster identifier>",
  "users": {
    "A": {
      "owner_id": "<real mapped PG owner A>",
      "conversation_ids": ["<newest first A>", "<A second>", "<A third>"],
      "message_ids": {"<newest first A>": ["<oldest first message 1>", "<... at least 31>"]}
    },
    "B": {
      "owner_id": "<real mapped PG owner B>",
      "conversation_ids": ["<newest first B>"],
      "message_ids": {"<newest first B>": []}
    }
  }
}
```

The placeholders above are **schema documentation, not generated evidence or accepted IDs**. DB must independently measure before/after browser Refresh/Send and after independent new-volume Restore. User supplied owner/session/query/body headers may NEVER be accepted by BFF/API. SQL receipt and browser JSON need the **same exact Git SHA and disposable cluster digest**. A false JSON can satisfy schema; only genuine DB/CI run and authorized owner review support final acceptance.

CI environment **only** (ephemeral 127.0.0.1, never Arvan/Mac; provision credentials as masked ephemeral job secrets, don't echo):

```bash
export CI=true GITHUB_ACTIONS=true PHASE3_APP_MODE=APP_ONLY
export UI_REAL_BROWSER_APPROVED=true
export UI_REAL_BROWSER_ORIGIN=https://127.0.0.1:3443
export UI_REAL_IDP_ORIGIN=http://127.0.0.1:<actual-keycloak-port>
export UI_REAL_PG_SEED_RECEIPT=/tmp/<generated-in-this-job>/pg-two-owner-seed.json
export UI_REAL_A_USERNAME=<ephemeral-a-email>
export UI_REAL_A_PASSWORD=<ephemeral-a-password>
export UI_REAL_B_USERNAME=<ephemeral-b-email>
export UI_REAL_B_PASSWORD=<ephemeral-b-password>
export UI_REAL_BROWSER_RECEIPT_DIR=/tmp/<prepared-private-receipt-directory>
python -u tests/phase3/integration/ui/real_signed_two_owner_history_journey.py
```

The script checks `git rev-parse HEAD == seed.integrated_sha`. It does not create IdP users, schemas or secrets, so it is safe for UI-owner execution and leaves setup with the actual API/DB/Foundation owners. The CI-specific TLS warning: Playwright ignores the **ephemeral lab's self-signed public proxy cert**; that is not proof of valid Mac/production PKI. API must separately prove pinned client certificate mTLS and issuer/audience/nonce/owner, and PostgreSQL RLS.

### Same-SHA results register

| Step | Current observed source-only baseline | Real connected two-user expected | Owner |
|---|---|---|---|
| 1. Startup | Next HTTP exists but login HTTPS proxy 503 | private Web/BFF + TLS OIDC/IdP + API signed + PG started on same CI network | Foundation |
| 2. Login | no signed subject; /login 503 | distinct Keycloak A/B sessions and BFF signed cookies; A logout verified | Foundation/API/UI |
| 3. History | ordinary GET History 503; zero DOM items | exact real PG ID list/detail + cursor and B 404, A/B DOM segregation | DB/API/UI |
| 4. Refresh/Send/failure | Send 503, no owner revalidation | stable PG IDs after refresh, zero direct Send T1/T2, revoked 401, missing cert and dead PG fail closed | API/DB/UI |
| 5. Restore | DB isolated backup receipt in separate prior CI only | fresh new-volume restore + same browser→API→SQL owner/IDs on the same candidate | DB/Foundation/UI |

**Observed target travel steps = 0/5**; 503 denial is a measured safety boundary, **not** step-3 success. **Official UI accepted 0/14; no new final Gates**. The existing 393-entry registry and 16 cross-branch owner decisions are managed by Foundation and remain unchanged by this UI patch.

**One-line for coordination:** `UI: History GET/HTTPS login 503 → exact-source ordinary Chromium 503/Send-deny safety verified; signed A/B 200/404/revoke runner prepared but blocked on real OIDC+PG | Draft PR #89 | 136 Node + real desktop/mobile browser (negative only) | missing signed shared stack + fresh DB seed/restore`.

Stop conditions: No signed backend, mismatched SHA/PG receipt, unknown credentials or broken TLS ⇒ stop with named failing assertion; **never** mark A/B accepted or reroute into synthetic History to obtain green CI.
