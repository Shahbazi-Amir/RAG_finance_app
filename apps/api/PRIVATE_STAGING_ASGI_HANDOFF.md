# API_F3 — private staging ASGI executable handoff (C018 NO_DISPATCH_ONLY)

**Status: source candidate, not an installed/approved service.** No server action,
DB Grant, migration, Gateway, `--dispatch`, Product T3, or C023 process
operation is performed by this source. An earlier successful Arvan Next build
of integrated SHA 9d4cf5dc6cb86b5cc174b71b9ed08c42f57d77de does NOT include
the new API entrypoint and is NOT proof of staging API readiness.

## Source, module, and trust topology

- Entrypoint **`apps/api/private_staging_asgi.py`**, launched via
  **`python -m apps.api.private_staging_asgi --config <OPS_0600_FILE>`**;
  it is deliberately **not** a plain `uvicorn apps.api.product_session_api:app`.
- TLS boundary **`src/phase3/auth/staging_transport_mtls.py`** uses
  the actual Python `SSLObject` obtained from the underlying Uvicorn
  transport (pinned **Uvicorn 0.48.0 / H11 HTTP/1.1**).
- Direct loopback HTTPS listener: **127.0.0.1 only**, port supplied by
  the approved Ops configuration. `ssl.CERT_REQUIRED` enforces actual
  BFF client-cert verification using an explicitly named private client CA.
  After the TLS handshake, the certificate's DER SHA256 MUST match the
  approved exact BFF leaf fingerprint; a different client under the same CA
  is rejected. Missing cert fails TLS handshake; mismatched cert closes
  connection before ASGI.
- Only then an **object-identity capability** (never a request header,
  cookie, ordinary string, or caller-provided TLS validation claim) is injected
  into the one connection's ASGI scope. The `PrivateStagingProfile.peer_verifier`
  requires the same process-local capability + `scheme=https` on EACH
  protected HTTP request. Forwarded headers, `X-SSL-Client-Cert`,
  `X-Forwarded-Client-Cert`, `X-Forwarded-Proto`, and
  `X-Client-Cert` are NEVER authentication evidence.
  Config sets `proxy_headers=False`, `workers=1`,
  `reload=False` and disables WebSockets/access logs.
- Independently validate signed BFF RS256 assertion against the Ops-installed
  RSA public key and fixed issuer/audience/kid, exact method/raw_path/raw_query/
  body bytes, one-time JTI and actual server-side session owner+epoch+generation
  via committed PostgreSQL 005/004. Neither TLS nor JWT alone grants ownership.
- TLS private server key, BFF public key, CA file and mode-0600 bootstrap JSON
  checked before listen. The BFF HTTPS origin configured in UI #54 MUST use
  an address/hostname covered by the API server certificate's SAN and Ops CA;
  `https://127.0.0.1:<OPS_PRIVATE_PORT>` is only valid if the SAN
  explicitly includes that IP. It cannot be a public API endpoint.
- **No network reverse proxy certificate headers** are part of this design.
  If Ops chooses Nginx termination / UDS instead, a DIFFERENT reviewed verifier
  and signed, OS-peer-authenticated transport bridge is required; do NOT
  silently replace this TLS implementation with header-based trust.

## Runtime startup and failure modes

1. Load the 0600 real config (absolute path, exact closed fields, root or service
   user-owned; unknown config fields and any non-loopback bind denied).
   All `*_file` paths must be absolute, non-symlink, protected;
   server TLS private key MUST have no group/other permissions.
2. Require `API_RUNNER_EXECUTION_MODE=NO_DISPATCH_ONLY` and
   `CI != true`, `GITHUB_ACTIONS != true`.
   Env is only from Ops' restricted systemd service, never a browser.
3. Strict pinned C018 `RunnerLayout.pinned()`: engine Python
   `/opt/rag-finance-staging/.venv-onnx-probe/bin/python`,
   repository `/opt/rag-finance-staging/RAG_finance`,
   artifacts `/opt/rag-finance-staging/_RAG_finance_NB22E_v4_outputs`,
   offline HF `/opt/rag-finance-staging/hf/hub`. Require full
   `rag_engine.py` SHA256
   **93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d**.
   Env `HF_HUB_CACHE`, `HF_HUB_OFFLINE=1`,
   `TRANSFORMERS_OFFLINE=1` must match exactly.
4. Validate server/client CA/cert/private key via OpenSSL context, validate
   real RS256 signing public key, then **connect read-only** as actual
   `history_app` and `auth_revoker` (non-SUPERUSER,
   non-BYPASSRLS) and verify function-only 005/004 Execute:
   `auth_l1.consume_service_assertion(text,bigint)`,
   `auth_l1.admit_session_fenced(text,text,bigint,integer)`,
   plus `auth_l1.revoke_one(text,bigint)` for the revoker.
   This is SELECT-only inspection, not SQL GRANT; missing actual DB or
   permissions denies startup. Actual DB #57 target and grant approval
   are still separate external Ops/DB gates.
5. Verify private persistent ledger **parent directory owned by runtime UID,
   mode 0700**, and existing SQLite regular file 0600; then
   **`install_private_staging_no_dispatch(profile, engine)`** runs
   BEFORE opening a socket, calling
   `build_private_no_dispatch_handler` with exact Runner digest,
   offline preflight and NoDispatchLedger. It installs both verified BFF Auth
   and C018 NoDispatchHandler atomically into the API app. No Runner is invoked
   during startup/preflight.
6. Server listens on loopback HTTPS with direct client cert verification.
   NO Gateway client is installed. No 011 Claim necessary for first
   NO_DISPATCH smoke. Start with **one** worker; shared ledger is single-host.
   Stop with sanitized `PRIVATE_STAGING_STARTUP_DENIED` on any
   pre-start exception; never print DSN, config data, private key, question.

## Proposed service paths (NOT observed as installed)

This is a template for Foundation/Ops **only after their approved window**.
Do not assume the guessed API Python venv, username, group, config directory,
port, unit name, or release SHA exists yet. Ops must provision and check each.

    [Service]
    Type=simple
    User=<OPS_APPROVED_NONROOT_API_USER>
    Group=<OPS_APPROVED_API_GROUP>
    WorkingDirectory=/opt/rag-finance-staging/phase3/releases/<FOUNDATION_APPROVED_INTEGRATED_SHA>
    Environment=API_RUNNER_EXECUTION_MODE=NO_DISPATCH_ONLY
    Environment=HF_HUB_CACHE=/opt/rag-finance-staging/hf/hub
    Environment=HF_HUB_OFFLINE=1
    Environment=TRANSFORMERS_OFFLINE=1
    ExecStartPre=/opt/rag-finance-staging/phase3/.venv-api/bin/python -m apps.api.private_staging_asgi --config /etc/rag-finance/phase3-api-private.json --preflight-only
    ExecStart=/opt/rag-finance-staging/phase3/.venv-api/bin/python -m apps.api.private_staging_asgi --config /etc/rag-finance/phase3-api-private.json
    Restart=no
    NoNewPrivileges=yes

**ExecStart (copy after Ops provisions exact paths; NOT run now):**

    /opt/rag-finance-staging/phase3/.venv-api/bin/python -m apps.api.private_staging_asgi --config /etc/rag-finance/phase3-api-private.json

API venv is NOT the pinned C018 engine venv. Python 3.13, FastAPI,
Uvicorn **0.48.0**, psycopg3 (+ binary or system libpq), PyJWT, cryptography,
jsonschema, Starlette, h11, and project DB modules must be available.
Foundation must pin actual versions and output the installed Python path.

The server-owned JSON includes EXACT required fields (no unapproved extras):

    {
      "contract_version": "api.private_no_dispatch_asgi.v1",
      "listen_host": "127.0.0.1",
      "listen_port": 8443,
      "server_tls_cert_file": "/etc/rag-finance/private-api-server.crt",
      "server_tls_key_file": "/etc/rag-finance/private-api-server.key",
      "trusted_bff_ca_file": "/etc/rag-finance/private-bff-client-ca.crt",
      "bff_leaf_cert_sha256": "<64 lowercase hex digest from the actual BFF TLS client leaf DER>",
      "bff_issuer": "urn:<BFF signing issuer>",
      "bff_audience": "urn:<API accepted audience>",
      "bff_kid": "<exact BFF key ID>",
      "bff_rs256_public_key_file": "/etc/rag-finance/private-bff-signing.pub.pem",
      "history_dsn": "<OPS server-only approved history_app DSN>",
      "revoke_dsn": "<OPS server-only approved auth_revoker DSN>",
      "engine_version": "NB23.C018",
      "ledger_file": "/var/lib/rag-finance-api/no-dispatch.sqlite3"
    }

**The displayed JSON is NOT runnable:** placeholders must be replaced by
authorized Ops; the real filled config with DSNs/private details MUST never
be committed or posted to PRs. The example port 8443 and file paths are
proposals, not observed ports or files.

## Initial authorized private Smoke (later, NOT_RUN)

1. On a separately approved, C023-safe Ops window, verify deployed integrated
   SHA includes this API source, actual service unit + nonroot UID/GID and
   genuine TLS/Keycloak/PG permissions, and pass preflight. Do not launch
   without host read-only inventory and DB #57 authority.
2. Invited A signs exactly one POST `/v1/messages` with a fresh
   `requested_conversation_id=null`,
   `client_message_id` and `idempotency_key`.
   Expected 202 committed T1/T2; record request_id/trace_id and Attempt.
3. Independent BFF signed GET
   `/v1/message-requests/engine-status` with the same original
   three correlators (nullable requested_conversation_id may be omitted
   per existing product.v1 parser). Poll only via GET until
   `preflight_state=CONTEXT_READY`,
   `generation_calls=0`,
   `top10_count=10`,
   `question_sha256_matches=true`,
   `dispatch_performed=false`, `answer=null`.
   One actual C018 process; no model generation or Gateway transport.
4. Same A POST replay gives **200**, no second Runner subprocess;
   Refresh/GET polls preserve persisted Attempt/trace and zero additional
   Runner calls. Valid independently authenticated B signed GET of A's
   tuple gets masked **404**, never answers or history.
5. If any layer lacks physical proof, mark BLOCKED with exact first error,
   do not set CI/demo flags, do not assert LIVE_VERIFIED/T3 and do not
   rerun Claim011. Arvan deployment is a separate Foundation/Ops decision.

## Test evidence scope

API-owned tests `tests/phase3/api/test_staging_private_asgi.py` use
real locally generated CA, server and two distinct client leaf certificates,
OpenSSL in-memory TLS handshake and negative forged-header, missing client cert,
same-CA wrong-leaf, invalid scope, config mode, and CI bypass tests.
These are SOURCE-level tests, not an authorized Arvan service or signed
PostgreSQL HTTP smoke. Foundation must perform additional exact-SHA isolated
TLS/H11 real network + signed PG/004/005 tests before pinning or activation,
then return Run/Job/evidence, without editing original API-owned source.
