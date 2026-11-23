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
5. Start the API image with `API_RUNNER_EXECUTION_MODE=APP_ONLY` and
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
