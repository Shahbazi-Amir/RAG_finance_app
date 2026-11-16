# API_F3 — Private staging initial OIDC Bootstrap (implementation handoff)

STATUS: SOURCE ONLY. NO Arvan service, real Code exchange, DB GRANT or migration, Gateway, Runner or public IdP login was executed in this task.
User reports Arvan PostgreSQL Clone PASS; the distinct primary staging database and its role/privilege inventory are not thereby proven ready.

## Entrypoint and exact callback

- Executable: apps/api/private_staging_bootstrap_asgi.py
- Core: src/phase3/auth/bootstrap_oidc.py
- Verified TLS boundary: src/phase3/auth/staging_transport_mtls.py
- Full dependency-backed tests: tests/phase3/integration/api/test_staging_bootstrap_asgi.py and test_staging_bootstrap_network.py
- CI static guard: tests/phase3/api/test_staging_bootstrap_source.py

The new core runtime_profile=private_staging enforces a REAL HTTPS non-loopback Keycloak issuer ending in /realms/<realm>, with fixed authorization, token and JWKS endpoints under its /protocol/openid-connect/ namespace. The only allowed redirect is the exact public URL https://ragfinance.ir/api/auth/callback. The identical redirect goes to authorization and Code+PKCE/S256 token exchange. IdP token/JWKS TLS verifies an Ops CA; neither endpoint follows redirects, JWKS bounded to 64KiB. Legacy runtime_profile=loopback_fixture with a local /callback is retained ONLY for old isolated tests; no CI emulation is a staging deployment.

Private listener (not public Nginx) exposes exactly 5 POST-only routes:
- /internal/auth/oidc/v1/start
- /internal/auth/oidc/v1/complete
- /internal/auth/oidc/v1/status
- /internal/auth/oidc/v1/ack
- /internal/auth/oidc/v1/abort

Direct Uvicorn 0.48.0 TLS/H11 to loopback 127.0.0.1 only. ssl.CERT_REQUIRED enforces actual BFF client-chain trust. Its transport SSLObject supplies DER, the SHA256 of its client leaf must match a separately pinned Ops fingerprint, and only a process-local capability can deliver peer DER to BootstrapOIDC._auth. No X-Forwarded-Client-Cert, X-SSL-Client-Cert, X-Forwarded-Proto or browser parameter is trusted for mTLS. Independently require short-lived Bootstrap RS256 assertion from pinned issuer/audience/kid, exact raw method/path/empty query/body hashes and matching attempt/initiator. M005 durable JTI and 009/010 function-only transaction and Commit gate Code exchange; UNKNOWN never triggers an automatic second send. 8KiB bounded HTTP body and no-store replies.

## Proposed Ops systemd launch; not yet installed or approved

Service must run as a *nonroot, approved runtime UID* from the immutable integrated release root that contains the new API code. The Python venv below is a proposal, NOT an observed on-host path.

    ExecStartPre=/opt/rag-finance-staging/phase3/.venv-api/bin/python -m apps.api.private_staging_bootstrap_asgi --config /etc/rag-finance-staging/bootstrap-private.json --preflight-only
    ExecStart=/opt/rag-finance-staging/phase3/.venv-api/bin/python -m apps.api.private_staging_bootstrap_asgi --config /etc/rag-finance-staging/bootstrap-private.json

Full server-side bootstrap config must be an absolute regular non-symlink JSON file, root/service-owned 0600, not a .env or browser setting. Keys and DSNs never enter PR/artifacts. All required keys (placeholders below are NOT runnable):

    {
      "contract_version": "api.private_oidc_bootstrap_asgi.v1",
      "listen_host": "127.0.0.1",
      "listen_port": 8444,
      "server_tls_cert_file": "/etc/rag-finance-staging/secrets/bootstrap-server.crt",
      "server_tls_key_file": "/etc/rag-finance-staging/secrets/bootstrap-server.key",
      "trusted_bff_ca_file": "/etc/rag-finance-staging/secrets/bff-client-ca.pem",
      "bff_leaf_cert_sha256": "<64 lowercase hex from actual BFF leaf DER>",
      "bff_issuer": "urn:<Ops approved bootstrap BFF issuer>",
      "bff_audience": "urn:<Ops approved bootstrap API audience>",
      "bff_kid": "<Ops approved bootstrap signer kid>",
      "bff_rs256_public_key_file": "/etc/rag-finance-staging/secrets/bootstrap-bff-signing.pub",
      "seal_key_file": "/etc/rag-finance-staging/secrets/initial-oidc-fernet.key",
      "seal_key_kid": "<Ops approved key version>",
      "idp_ca_file": "/etc/rag-finance-staging/secrets/oidc-trusted-ca.pem",
      "oidc_issuer": "https://<IDP-HTTPS-HOST>/realms/<REALM>",
      "oidc_authorization_endpoint": "https://<IDP-HTTPS-HOST>/realms/<REALM>/protocol/openid-connect/auth",
      "oidc_token_endpoint": "https://<IDP-HTTPS-HOST>/realms/<REALM>/protocol/openid-connect/token",
      "oidc_jwks_uri": "https://<IDP-HTTPS-HOST>/realms/<REALM>/protocol/openid-connect/certs",
      "oidc_client_id": "<exact configured public PKCE client>",
      "oidc_redirect_uri": "https://ragfinance.ir/api/auth/callback",
      "dsn_replay": "<auth_trust_api DSN>",
      "dsn_bootstrap": "<auth_login_bootstrap DSN>",
      "dsn_claim_reader": "<auth_login_claim_reader DSN>",
      "dsn_issuer": "<auth_login_issuer DSN>",
      "dsn_mapper": "<auth_mapper DSN>",
      "dsn_binder": "<auth_login_binder DSN>",
      "dsn_reader": "<auth_login_reader DSN>"
    }

Example port/path/IdP are PROPOSED, NOT observed. The private server leaf certificate SAN must match the Node BFF bootstrap_origin hostname/IP; the public domain is for Next callback only. All 7 database roles are checked at startup using actual restricted non-SUPERUSER / non-BYPASS credentials, exact 005/009/010 function-only EXECUTE, auth_l1 USAGE and negative direct SELECT checks. Missing target database/role/function or unapproved CI flag must deny startup. Preflight-only performs no IdP HTTP or login and no SQL writes, migrations, grants, or listen.

## CI separation and required Foundation evidence

The existing minimal-dependency API53 workflow runs only syntactic/static source guards and offline C018 tests. It does not have cryptography/FastAPI/psycopg dependencies for real OIDC tests. Its earlier failed import was due solely to missing cryptography, not a five-route execution failure; the dependency-heavy tests were moved out of that workflow's discovery into API-owned tests/phase3/integration/api.

Foundation must prepare a separate isolated job with Python3.13, openssl, FastAPI, Starlette, uvicorn==0.48.0, h11, cryptography, PyJWT, httpx, psycopg[binary], jsonschema:
    PYTHONPATH="$PWD/tests/phase3/integration/api:$PWD" python -m unittest discover -s tests/phase3/integration/api -p 'test_staging_bootstrap_asgi.py' -v
    PYTHONPATH="$PWD/tests/phase3/integration/api:$PWD" python -m unittest discover -s tests/phase3/integration/api -p 'test_staging_bootstrap_network.py' -v

Fixture tests generate a real ephemeral OpenSSL CA/server and BFF+wrong-leaf client certificates, use signed RS256 JWT for five ASGI POST routes, and NEGATIVES for expiry, method/path/body binding, spoofed headers, no certificate, wrong same-CA leaf, callback/Issuer mismatch, and JWKS redirect. 005/009/010 SQL calls are MOCKED in these particular tests, so these are NOT real PostgreSQL or live HTTPS-IdP signoff. Real staging login requires independent Keycloak issuer/callback configuration, actual signed mTLS transport, approved primary staging PostgreSQL 001–010 roles/grants, and cross-account auth/browser tests.

## Integration rule

Existing integrated #55 86ae7884dd9bad64ef051adf90a52471c0fff24a has the old loopback-only Bootstrap path and must not be treated as if it already contained this code. After full-dependency CI PASS, Foundation must repin exact immutable API code and test blobs into its existing Draft #55, run combined UI/API verification, and retain the prior Next build/DB clone as separate evidence. No permission to merge/deploy or invoke an Arvan service follows from this handoff.
