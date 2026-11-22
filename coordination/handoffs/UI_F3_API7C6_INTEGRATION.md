# UI_F3 + API_F3 Gate3 — isolated integration handoff

Date: 2026-11-23 (Asia/Baku date not assumed; source timestamps are GitHub UTC).
**DRAFT — NOT APPROVED for Mac deployment, C018 Gate3, Gateway or merge.**

## Immutable inputs and ownership

- UI source: Draft [PR #58](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/58), \`agent/ui-f3-gate3-retrieval-evidence-20261122@6a92d0c719f2a31e459f49b2a18782fe92a08094\`.
- API source: \`agent/api-f3-gate3-retrieval-isolated-20261122@7c6b5c62817f4f06201718781a00c62e0b4c17e0\`.
- Isolated shared candidate: \`agent/ui-f3-api7c6-integration-20261123\`, stacked **only** on API commit and copying identified UI #58 evidence/CI blobs. Neither input branch nor the frozen Mac demo is modified.
- Authoritative DTO: \`packages/contracts/api.retrieved_sources.v1.schema.json\`, blob \`ed6044b194ea597ddcded4c3a63077b4cd83c3e1\`.
- API BFF sends signed, session-owned \`GET /v1/message-requests/retrieved-sources\` with exactly the three original send correlators, not question/owner/body. The API stores a sanitized same-Attempt receipt. This GET is read-only; it does **not** trigger C018.
- Wire contract is **technical retrieval evidence only**: \`PARTIAL_UNVERIFIED\` rows contain rank, pinned-chunk ID and an *observed* source ID; \`source_validation=UNVERIFIED\`, \`locator_validation=PENDING_STRUCTURE\`, \`verified_locators=[]\`. These are neither approved attribution nor Product \`LIVE_VERIFIED\` nor answer citations.
- Separate older \`retrieval-evidence-panel\` verified-link preview remains CI-only, host/CI/fixture gated and **must never receive these unverified API rows**. Product shows a different, intentionally link-free \`retrieved-sources-panel\`.

## Verified source paths and safeguards

- \`apps/web/src/history/client.ts\` from pinned API: validates exact DTO keys, enum/hex T2 identifiers, ordered 1..10 rows, chunk/source bounds, no locator/extra fields and pinned SHA; 401 invalidates session, 404 does not create evidence.
- \`apps/web/src/history/proxy.ts\` from pinned API: exactly one signed \`retrieved-sources\` GET route, existing trusted public origin, auth, CSRF POST guards and signed service-request path preserved.
- \`apps/web/src/ui/product-chat.tsx\`: status + engine GET + retrieval GET checked against the same independently read T2 Attempt. On Refresh only original persisted correlators are read. Invalid/mismatched receipts are not displayed; old observations are cleared on later errors, preventing stale citations.
- \`apps/web/src/ui/retrieved-sources-panel.tsx\`: technical observations only, no anchor/URL/Citation, explicit absent/malformed/invalid/unknown states, RTL identifier isolation. The prior gated synthetic verified destination / missing locator / unverified destination / unverified source UI preview remains separate.
- \`tests/phase3/ui/retrieved-sources-client.test.mjs\`: valid matching GET after Refresh, no POST, strict negative schema/unsafe locator and 401/404.
- \`tests/phase3/integration/ui/product_chat_browser.py\`: Chromium intercepted fixture, same original POST once and signed-correlator GET before/after refresh; forbidden locator triggers list purge, 401 clears session. **Fixture-only, not a real signed API or Mac.**
- \`tests/phase3/integration/ui/retrieval_evidence_preview_browser.py\`: desktop 1280x800/mobile 390x844 isolated preview with conspicuous synthetic marker, not engine evidence.
- \`.github/workflows/ui-f3-api7c6-integration.yml\`: push-branch-only CI: pinned npm install, Typecheck, Lint, all Node, Next Build, Chromium. No model, Docker, staging, Mac, deployment or Gateway.
- No modification to \`scripts/phase3-demo/**\`, SQL, API server source, OIDC private staging configurations, or frozen machine.

## Canonical 14 UI activities — separate implementation, L1 and L2 status

**Do not tick canonical UI-01..14 on partial evidence.** A design acceptance is not Phase3 Gate acceptance; mock Chromium is L1 only. Links to actual successful/failed **exact-SHA** CI runs belong in the integration PR body.

| ID | Implemented / scope | L1 status & evidence | L2 / dependency that still blocks full activity |
|---|---|---|---|
| UI-01 | Journey/Frontend shell and boundaries documented, original design accepted only | Source shell + UI tests; final new-SHA CI must be linked | Supervisor/architectural Gate and live approved stack |
| UI-02 | API \`api.retrieved_sources.v1\` strict client + signed BFF GET integrated | Contract negative Node/CI in branch | Real API + approved owner/session/Source DTO deployment and contract-level L2 |
| UI-03 | OIDC callback/login/logout/401 session clearing inherited, not rewritten | Existing fixture/Auth tests and browser logout/401 checks | Real Keycloak + signed BFF/API session A/B + macOS stack |
| UI-04 | Consent deliberately not falsified or auto-accepted | No backend Consent versioned payload to implement; NOT_RUN | Product policy, versioned Consent DTO, authenticated signed endpoint |
| UI-05 | History list/thread/refresh/cursor + per-owner fenced proxy maintained | Node and fixture browser checks | Actual persistent PG History owner-isolated L2 |
| UI-06 | Persian RTL composer and same-send receipt flow retained | Desktop/mobile Chromium and Node once-only POST | Real user browser/device and signed POST/GET |
| UI-07 | Technical Pending/Ready/Failed/Unknown and verified Answer gating retained | State/test fixtures only | C018 real status + model/Confidence/outcome producer mapping (not a fabricated answer) |
| UI-08 | Retrieval rank, chunk IDs and observed source IDs visible only as **unverified**. Verified links limited to gated synthetic UI preview | New strict receipt tests + separate view tests, CI Chromium | Reviewed member_locators typed contract, actual approved Q2 provenance/permission and valid claim citation |
| UI-09 | Feedback UI not enabled (safe absence) | NOT_RUN due to missing approved contract | Versioned Feedback DTO/ID, auth and persistence endpoint |
| UI-10 | Stable client ID/key, one POST, polling, unknown/Refresh recovery | Client Node + intercepted Chromium refresh | Streaming/cancel contract and real server end-state, no accidental re-dispatch |
| UI-11 | RTL responsive CSS + accessible status/labels preserved | Synthetic Chromium 1280x800 and 390x844; no full WCAG audit | Real Mac/mobile browser + keyboard/focus/contrast/screen reader acceptance |
| UI-12 | CI + source-pinned evidence and explicit L1/L2 division | Node, Typecheck, Lint, Build, fixture Chromium on final SHA only | Real OIDC→C018→same Attempt GET→Refresh→logout end-to-end on Mac |
| UI-13 | Deletion/account erase not falsely declared successful | NOT_RUN pending contract | Approved deletion policy, request/status/transaction + authorization |
| UI-14 | React escaped source IDs, HTTPS-only verified preview, no source URL from unverified API; invalid receipt cleared | Strict schema and unsafe-link negative Node, fake UI browser | Final signed/API/real browser security, XSS/abuse and leakage audit |

**Canonical checkbox and supervisor approval:** unchanged (no claims of 14/14 completed). **Real C018 Mac:** NOT_RUN. **Real Q2 captured and displayed:** NOT_VERIFIED. **Exact one OS spawn/no extra on Refresh:** NOT_VERIFIED. **Production/Staging:** NOT_DEPLOYED. **Gateway paid calls:** NONE in this UI workflow.

## Foundation / Ops unblock receipt (external, not synthetic)

On separately authorized and already configured Mac Docker/OIDC/DB stack, with an invited account:
1. Preserve frozen demo and unrelated services. Record exact image/source digests, API/Next SHA, TLS/IdP health and verified C018 no-generation config; do **not** infer Mac availability from Ubuntu CI.
2. Execute one actual UI send. Capture only sanitized \`client_message_id\`, \`idempotency_key\`, \`attempt_id\`, \`attempt_trace_id\`, signed status/engine/retrieved-sources reads, Q2 row rank/chunk and observed source ID, authorization-safe DB/OS audit receipt.
3. Verify source GET receipt matches **that** T2, model generation calls 0, OS spawn audit shows exactly one C018 process for the Attempt and no second process on page Refresh; record request counts (one POST total, GET after Refresh), and desktop/mobile real browser screenshots without secrets.
4. If Source locator is not authorized, remain nonclickable and mark Source attribution \`UNVERIFIED\`; never label it \`LIVE_VERIFIED\` or a Citation. Record typed locator/resolver absence explicitly.
5. Sign Ops/Foundation receipts with access context, timestamps, SHA and test status. Until then mark Gate3 **BLOCKED**, do not merge/deploy or trigger Gateway.

## Conflict preservation

The UI #58 \`product-chat.tsx\` originally lacked source GET; the API commit adds it. The integrated code **retains API source GET/correlation, session and original once-only POST** while layering UI #58 synthetic preview as a separate bounded path. No replacing API client/proxy with stale UI variants, and no merging whole divergent histories.
