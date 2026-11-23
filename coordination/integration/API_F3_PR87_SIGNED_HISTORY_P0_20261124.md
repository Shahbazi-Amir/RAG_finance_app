# API specialist handoff — PR #87: real signed app-only History on #84

**Date:** 2026-11-24. **Owner:** API. **Source base:** PR #84 `0fd1066945ef91a3913e040ab4c350bb645ea502`; no changes were pushed to #84, main, Mac or destination server. **Dedicated Draft:** [#87](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/87), branch `agent/api-f3-pr84-signed-history-20261124`. Built from actual GitHub file blobs, not the reported 14/32-test local packages. Current HEAD and exact Actions need to be rechecked at final integration.

## Earliest reproducible defect — no tests-only shortcut

Original #84 `apps/api/app_only_asgi.py` is **deny-only**: `GET /v1/conversations` returns **503 `SIGNED_HISTORY_NOT_CONFIGURED`** and `GET /health/ready` 503. Its original `infra/phase3_l1/Dockerfile.api` starts `uvicorn apps.api.app_only_asgi:app --port 8080`. BFF has a real mTLS+RS256 client source and `product_session_api.py` has genuine 004/005 transactional Session→Owner→History, but **the container entrypoint did not use them**. This is a real composition gap, not missing CSV documentation.

## Changed Product behavior in the API-owned branch

- Transplanted exact #80 `apps/api/private_app_only_asgi.py`, `app_only_socket_probe.py`, its 10+ negative tests and actual OpenSSL/Uvicorn mTLS network test; existing original `product_session_api.py` / Product.v1 / original migrations remain unchanged.
- Replaced the *actual container default process* with `python3 -m apps.api.private_app_only_asgi --config /run/secrets/phase3-app-only.json` on private TLS port **8443**, non-root UID11001, fail-closed **exit 78** on missing/untrusted 0600 Ops secret. Docker health is socket liveness only, never readiness. Original #84 deny-only module remains for compatibility tests; it is NOT the new container CMD.
- Requires BOTH `PHASE3_APP_MODE=APP_ONLY` and `API_RUNNER_EXECUTION_MODE=APP_ONLY`, valid owned TLS server key+CA, pinned BFF client leaf cert, public RSA signer with fixed issuer/audience/kid, restricted `history_app` and `auth_revoker` DB roles/execute functions. Rejects CI fixture flags for live startup. Malformed signer exits 78 with sanitized fixed stderr; no engine imports or dispatch.
- `GET /v1/conversations?limit=N[&cursor=...]`, `GET /v1/conversations/{id}/messages?limit=N[&cursor=...]`, `GET /v1/message-requests/status?... `, `POST /internal/auth/session/v1/revoke-one` pass to the **original Product signed HTTP/PG transaction**, with exact URL/query/body assertion, no browser-selected identity. A200, foreign B404, revoked A401/B200 are covered by disposable Keycloak/PG CI.
- `POST /v1/messages` and encoded aliases such as `/v1/%6dessages` are **503 ENGINE_NOT_CONFIGURED before body read**, with original SQL `T1=0,T2=0,T3=0` delta and no Runner/model/Qdrant/Gateway. Every private response is no-store/nosniff.
- `GET /internal/ready` is a **mTLS-only PG-role/grant metadata probe**; **strict `GET /health/ready` requires a fresh BFF RS256 signed assertion on this exact path, a real active session, 004/005 owner-bound PostgreSQL transaction**, then returns 200 `signed_actor_pg:verified`. No/incorrect signature, signed replay, cross-owner, revoked session or lost PG EXECUTE privilege returns **503**. It explicitly emits `bootstrap_idp:not_probed`; this 200 **is not** full browser/IdP end-to-end readiness.
- Stable **Ops-owned `API_CURSOR_KEY` (≥32 byte secret) and `API_CURSOR_TTL_SECONDS` (1–3600)** now required BEFORE listener startup to support genuine page-2 pagination. Missing/invalid cursor authority denies startup instead of failing only for a real customer. Cursor secret must not be committed or regenerated on every request.

## Live synthetic-CI evidence — source SHA must be matched

- [API offline H11/Docker/source CI](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45277628132): PASS on `27c9e729a6de47954c654fbda3eea66c4e7ca718` (earlier exact implementation, not final HEAD); [signer-deny regression](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45277869632): PASS on `907c0dda78c73c7ce4ec99452157990f1675a943`.
- [Keycloak+PG17.11 signed API](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45277627950): **PASS on `27c9e729a6de47954c654fbda3eea66c4e7ca718`**, 10 original Keycloak tests, 8 signed Product-session HTTPS/mTLS/PG tests, 5 full Attempt-binding tests; includes real PG-revoked function grant 503 and re-granted 200, A/B, revoke, Send zero durable write.
- **Pagination**: test `test_API011_08_signed_real_pg_pagination_A_B_cursor_and_detail` added to exercise A/B same HTTP+PG cursor, page 2, refresh, A detail 200, B 404 and independent SQL ID/owner parity; first run found a *test-helper* incorrectly hashing the `?` separator in `raw_query`, now corrected. Full updated exact-head CI still required; this is **not yet a green witness at time of this handoff creation**.
- [API negative test CI workflow](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/agent/api-f3-pr84-signed-history-20261124/.github/workflows/api-f3-pr84-signed-app-only.yml) and [real signed Keycloak/PG17 CI](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/agent/api-f3-pr84-signed-history-20261124/.github/workflows/api-session-011.yml) are source-pinned by actual Actions run HEAD. This is **synthetic isolated lab with genuine H11 mTLS, signed assertions, PostgreSQL and Keycloak; no Mac or original browser BFF**.

## Interface to Foundation / UI / DB (no guessing)

| Contract | Exact path / expected behavior | Owner handoff |
|---|---|---|
| API container | private `https://api.internal:8443` only if the operator provisions matching CA, DNS SAN and private network; 0600 JSON at `/run/secrets/phase3-app-only.json` | Foundation/Ops: replace #84/#85 old plaintext API `8080` and healthcheck; don't retain old Compose health condition |
| BFF signer | existing `productRequest('history'/'messages'/'status'/'revoke')` preserved; mTLS cert must match fingerprint and RSA private signer match API public key and exact issuer/audience/kid | UI/Foundation: use existing *real* signed BFF from browser session; no CI cookie/header override |
| PG | SQL migration `001–010`, DB role and function permissions, real server TLS/SAN/CA, session owner/RLS; API requires stable cursor secret/TTL | DB/Foundation: approved restricted DSNs and independent SQL A/B witness; 011 forbidden |
| API readiness | **GET /health/ready** with fresh exact-path signed BFF proof from active session → 200; absent/bad signer/PG/revoke → 503; `/internal/ready` mTLS-only metadata | Foundation: full Web+Bootstrap+IdP+PG readiness must be checked separately; avoid calling API 200 whole-stack ready |
| disabled Send | `POST /v1/messages` → 503 `ENGINE_NOT_CONFIGURED`, unchanged T1/T2/T3, no engine | UI must keep real browser Send disabled and BFF pre-body defense; DB must independently audit row counts |

**Open before product completion:** full browser A and B (real OIDC callback, cookies and BFF) → real signed API → restricted PG **in same CI job or persistent private network**, exact History IDs, pagination, cross-owner 404, revoke A401/B200, refresh no extra rows, PG backup→new-volume restore→repeat journey. This whole 5-step deliverable belongs to Foundation and is **NOT_RUN/NOT_ACCEPTED**; we cannot claim 0/262 or 0/26 Gates advanced. App-only no model/Runner and no Mac target operations remain unchanged.

## Reproduce without target access

On independently approved private candidate environment: install `API_CURSOR_KEY`, TTL, owned 0600 TLS/config files and restricted PG roles, build `infra/phase3_l1/Dockerfile.api`, run `python3 -m apps.api.private_app_only_asgi --config /run/secrets/phase3-app-only.json`; BFF must sign /health/ready exact path and signed History as described. For reproducible CI, use the two workflows noted above on the **same** commit SHA. Never expose API on a public host/port; no volume deletion/merge/deploy/engine call.
