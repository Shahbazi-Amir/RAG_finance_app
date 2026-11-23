# F3 app-only isolated API — real listener, deployment is NOT approved

This is the candidate's **non-engine** operational procedure, not permission
to deploy, change existing volumes, enable Qdrant/Runner, or alter Mac/Arvan.

## What ships

- `apps/api/private_app_only_asgi.py`: one-process Uvicorn 0.48.0 real HTTPS
  listener; mutual TLS `CERT_REQUIRED`, pinned BFF client leaf, original
  signed RS256 and PostgreSQL 004/005 admission for History/Revoke.
- `infra/phase3_l1/Dockerfile.api`: non-root UID 11001 real CMD, no engine
  startup or C018 requirement, TCP socket-only Docker liveness. This is NOT
  proof of live PostgreSQL/IdP readiness.
- `GET /internal/ready`: BFF-mTLS-only live PostgreSQL role and function
  permission checks. It responds `history_db=verified`, but explicitly
  `bootstrap_idp=not_probed`, `retrieval=unavailable`,
  `generation=unavailable`. When PG is unavailable, returns sanitized 503.
- `POST /v1/messages`: even with real trusted BFF client certificate,
  sanitized `ENGINE_NOT_CONFIGURED` 503 **before reading the body**, creating
  T1/T2, queueing an OS child, calling the Gateway, or producing any Answer.
- UI #65 independently disables the composer and its BFF POST proxy with a
  `PHASE3_APP_MODE=APP_ONLY` capability. Both fences are required.

## Source-only reproducible checks

```sh
python3 -m unittest discover -s tests/phase3/api -p test_app_only_no_engine.py -v
python3 -m unittest discover -s tests/phase3/integration/api -p test_app_only_mtls_network.py -v
# Next 22.16.0, Python3.13, Chromium fixture:
npm ci --prefix apps/web --no-audit --no-fund
npm --prefix apps/web run test
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run build
PHASE3_APP_MODE=APP_ONLY npm --prefix apps/web run start
# In another shell on isolated loopback:
python3 tests/phase3/integration/ui/app_only_real_browser.py
```

Run `.github/workflows/f3-app-only-runtime-ci.yml` at exact candidate SHA
for source pins, real Docker API/Web builds, actual local network TLS/Chrome
smoke. `api-session-011.yml` separately verifies original signed
HTTPS/Keycloak/PG17 A/B History/revoke with disposable infrastructure.

## External/Ops-only prerequisites for a running container

1. Pick a **new isolated** Docker project/network with NO host-published API
   port or reuse of a legacy volume. Freeze source SHA, image IDs/digests,
   approved base-image digest and DB migration ledger 001–010. Never install
   optional 011 or open a public Gateway from this procedure.
2. Provision real PostgreSQL 17 with separate `history_app` and
   `auth_revoker` restricted roles, 004/005 functions and session-aware
   grants; verify TLS server name and pinned CA, no superuser or BYPASSRLS.
3. Provision real BFF **on a different trust boundary** with its own private
   RS256 signing key and mTLS client key. The API receives **only its public**
   RS256 key, trusted client CA, pinned BFF leaf fingerprint and its server
   certificate/private key. Store in an Ops-only 0600 file owned by UID 11001
   inside the API namespace (or root preflight followed by a privilege drop).
   Never pass credentials in CLI arguments, source files or CI logs.
4. Copy `app-only.config.example.json` to that protected path, replace all
   placeholders with real approval receipts and valid DNS SAN/TLS details.
   The JSON MUST contain exactly the listed fields. No engine, ledger,
   Qdrant or provider fields are permitted. `0.0.0.0` bind is intended
   **only** on an isolated internal container interface; use `127.0.0.1`
   for loopback-only deployments.
5. Start the API image with `PHASE3_APP_MODE=APP_ONLY` and `API_RUNNER_EXECUTION_MODE=APP_ONLY` and
   `--config /run/secrets/phase3-app-only.json`. Missing/unreadable/unsafe
   config must exit **78**, not enable fixture or fall back to anonymous.
   Docker liveness checks loopback socket only; **do not mistake it for**
   session, PostgreSQL or IdP readiness.
6. Start Bootstrap/IdP and Web separately with same approved network DNS,
   CA/SAN and BFF cert. A BFF request to `GET /internal/ready` must observe
   `ready` only after real PG role verification; authorization of History
   requires original mTLS + RS256 signed BFF + active 004/005 session.
7. Perform two-owner Login → List/Detail/Pagination/Refresh → B 404 →
   revoke A 401/B 200, and direct BFF/HTTP Send 503 with **zero T1/T2
   writes**, zero OS spawn, zero Gateway, zero T3/Answer. Attach redacted
   request IDs, timestamps, OCI digest and SQL row counts to the exact SHA.
   A fake unit test, synthetic browser route or importing the app is NOT a
   substitute for this signed end-to-end candidate proof.

## Rollback and acceptance

Stop the **new isolated candidate** containers and restore their independently
created new volumes from recorded backups. Verify restore into a second empty
volume and repeat the original two-owner History journey. Do not delete or
restore to an existing production/legacy volume. RPO/RTO are measurements,
never guessed numbers. Ops/CENTRAL must approve real target and credentials
before starting; this repository is only an executable candidate.

Engine and server are separate later missions. No transition to
`NO_DISPATCH_ONLY`, C018, model generation, NB23/C019 or DB011 is allowed
by an app-only image tag or this README.

## API #84 signed-HTTP closure delta (2026-11-24)

**Required stable cursor configuration:** provision `API_CURSOR_KEY` as a
private owner-controlled unpredictable ≥32-byte value in the API process,
with `API_CURSOR_TTL_SECONDS` between `1` and `3600` (suggested lab `300`).
Neither value comes from a browser or URL, and the key must persist across
app restart/replica and prior cursor validity window. The signed listener
fails startup before binding if either value is missing or invalid. Treat
missing cursor authority as readiness 503 / not deployed, never fake a page.


The #84 deny-only `apps/api/app_only_asgi.py` remains as a **safe offline fallback
source test**, not the API container process anymore. The image's actual CMD
is `python3 -m apps.api.private_app_only_asgi --config /run/secrets/phase3-app-only.json`.
Without an Ops-owned config the container returns exit **78**; it cannot
pass Compose's former HTTP liveness. Foundation **must** add the secret mount,
private TLS/CA DNS, actual BFF/Bootstrap/IdP and app-only restricted PG
before marking that Compose job green. There is no anonymous fallback.

Two independent selectors must be `PHASE3_APP_MODE=APP_ONLY` and
`API_RUNNER_EXECUTION_MODE=APP_ONLY`. Disagreeing or CI/GITHUB_ACTIONS
true in production causes startup denial. This does not activate C018.
`GET /internal/ready` remains **mTLS-only, PG role/function metadata** (200 or 503).
`GET /health/ready` is now **stricter**: the BFF must sign this exact GET
path using its real RSA key and a *currently active session*; original
004/005 fenced admission, correct owner and PG commit must all succeed.
It returns 200 only for that transaction and 503 for absent/incorrect
RS256 proof, revoked session, wrong owner or DB failure. No query or body is
allowed. Both probes explicitly state `bootstrap_idp:not_probed` where
applicable; 200 is **API History readiness**, never browser-stack readiness.
The *whole* browser login stack is NOT declared ready by that API-only 200.

### Contract exposed to Foundation/UI/DB

- BFF signed readiness: `GET /health/ready` with a fresh exact-bound
  assertion for a live owner/session; no request body. Failed signature,
  replay or revoked session means 503, not a green Health status.
- BFF signed Product.v1: `GET /v1/conversations?limit=20`, paginated
  `GET /v1/conversations/{id}/messages?limit=20`,
  `GET /v1/message-requests/status?requested_conversation_id=...&client_message_id=...&idempotency_key=...`,
  and `POST /internal/auth/session/v1/revoke-one`.
- Identity sources: exact signed method, raw path/query/body digest, issuer,
  audience, RS256 key ID and JWT, mTLS peer leaf **plus** committed
  session/owner 004+005 transaction under history_app or auth_revoker.
  No caller-provided owner/cert headers. B should see 404 for A's ID;
  revoked A must see 401. Responses are `Cache-Control: no-store`.
- `POST /v1/messages` including percent-encoded path aliases is 503
  `ENGINE_NOT_CONFIGURED` before body read or any T1/T2/T3 mutation.
- API-only CI executable: `.github/workflows/api-f3-pr84-signed-app-only.yml`.
  The signed Keycloak/PG17 job `api-session-011.yml` now launches
  `tests/phase3/integration/api/app_only_signed_pg_ci_h11.py`, which
  puts the **exact same AppOnlyASGI guard** around original real Product
  routes with a verified client-cert H11 protocol. Its profile/DSNs are
  isolated CI-only and do **not** substitute for Ops deployment proofs.
- Next full-system test (Foundation): normal browser A/B OIDC callback,
  same-namespace BFF mTLS+RSA key, API service bound to *real* restricted
  PostgreSQL, SQL receipts, reboot/restore, and negative PG/signing outage.
  This is a separate acceptance criterion and remains NOT_RUN here.
