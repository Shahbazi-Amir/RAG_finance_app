# AGENT-API-AUTH-TRUST-01 — internal BFF service assertion & transactional admission

**Status:** CI-only API trust slice, not production Auth/BFF, OIDC verification or History wiring. Authorized files: src/phase3/auth/**, tests/phase3/api/**, tests/phase3/integration/api/**, .github/workflows/api-auth-trust.yml and one cumulative mission checkpoint. This is an **internal Python interface**, not a public Product v1 DTO.

## Trust contracts and ownership

Producer: **future Next.js BFF server only**, owned by UI agent. This package has NO production signer. Synthetic private RSA signer exists ONLY in tests/phase3/api/proof_fixture.py, created fresh in runner RAM and never uploaded. Consumer: API-owned `src.phase3.auth.service_proof.BFFServiceVerifier`; it is independently implemented, depends on audited PyJWT[crypto] RSA verification and cryptography library for validating static RSA public keys. **No hand-rolled JWT parser/signature/PKCE**. Service public PEM key(s) are deployment-injected out-of-band, keyed by explicit allowlisted `kid` (rotation only by config update). **No URI/jku/x5u/remote JWKS**, Keycloak JWT, unsigned assertion or HS256 fallback. Absent/malformed key config immediately fails closed.

Trust preconditions outside this slice: separate service-to-service transport authentication/private network (mTLS or approved equivalent), BFF protection of its signer and raw session reference, reverse proxy preserving ASGI raw_path/query bytes, production durable replay schema + least-privilege dedicated API role and Key rotation/ops approval. These have NOT been installed or accepted. Any direct public request or user-selected identity must be rejected by the eventual wiring. This module is not connected to apps/api/history_api.py.

### Wire shape (fixed internal-only assertion)

HTTP: exactly ONE `Authorization: BFF-Assertion <compact-JWT>` header sent directly from a server BFF to API. No query-string credentials; duplicate authorization and spoofed `X-Owner-ID`, `X-User-ID`, `X-Authenticated-User`, `X-Forwarded-User/Owner` headers denied. Compressed request bodies denied. Responses/statuses contain only generic `401`/status, never assertion/IdP token or cookie.

JWT protected header: **exactly** `{"typ":"JWT","alg":"RS256","kid":"<trusted-configured-kid>"}`. RSA >=2048 public key from a non-empty explicit static key map. Only signed service issuer (synthetic test `urn:rag-finance:synthetic-bff`), audience exactly `urn:rag-finance:api:internal-ci` (string, not list) and strict `iat`/`nbf`/`exp` integers. Maximum `exp-iat` = 30 seconds; `iat<=now`, `nbf<=now`, `now<exp`, `now-iat<=30` using API clock; leeway = zero. Future BFF config issuer/audience must be fixed before deployment. No claim-derived issuer/audience or dynamic key lookup.

Exactly these payload claims, no extra role/owner-selector claim:
`iss, aud, iat, nbf, exp, jti, method, raw_path_sha256, raw_query_sha256, body_sha256, body_len, session_ref, owner_id, epoch, generation`.
`jti` = 20..128 URL-safe ASCII, independently unpredictable and unique per *request attempt*; `method` uppercase ASCII 3..8 chars; owner ID (internal UUID string) 1..128 ASCII `[A-Za-z0-9_-]`; epoch/generation nonnegative **integer** (not bool/string); session_ref 43..256 URL-safe ASCII. The session_ref is the **raw server-only opaque verifier from the trusted session store**, not a browser-supplied owner or a JWT from IdP. It is sensitive bearer material, not a display reference, and must never reach client JS/localStorage, logs, analytics or artifacts. In production the BFF Cookie-to-server-verifier mapping and secured BFF→API transport require a separate authorized UI/API handoff.

### Exact byte-bound canonicalization — no normalization

`raw_path_sha256 = SHA256(ASGI scope["raw_path"] bytes)`, `raw_query_sha256 = SHA256(ASGI scope["query_string"] bytes, without "?")`, `body_sha256 = SHA256(the exact ASGI request body bytes)`, `body_len = byte count`. All SHA256 hashes are lowercase hex length 64. `method` is compared as exact uppercase ASCII. The BFF and API agree on the *same wire bytes* after their reverse proxy; **never** sort query params, decode/recase `%2f/%2F`, normalize Unicode, parse/re-dump JSON, drop duplicate query fields or perform transparent decompression. Different query order, percent case, path and JSON whitespace are DIFFERENT assertions. Body max 8192 bytes; query max 4096, raw_path max 2048, assertion max 4096 chars. Reverse-proxy normalization/rewrite consistency must be integration-tested separately. Only raw ASGI scope supplies trusted binding; `request.url` and parsed query parameters do not.

### Admission protocol (same DB primary connection / outer transaction)

1. FastAPI fixture/integration calls `assertion_from_asgi_headers(scope)`, `wire_request(scope, await request.body())`. Production FastAPI wiring is **not part of this commit**.
2. `BFFServiceVerifier.verify()` uses static RSA key trust, exact iss/aud/time/jti + bytes, returns `VerifiedServiceProof` with redacted repr; invalid config/claim → `TrustRejected`. No fallback to an IdP JWT or identity header. Verified claims are *signed BFF assertions*, not an independently verified IdP user.
3. `protected_operation(conn,...)` requires autocommit primary PostgreSQL connection in IDLE state then opens ONE explicit `conn.transaction()`. In the same outer TX the configured `ReplayStore.consume(conn,proof)` must return EXACT `True`, then calls the accepted DB Python wrapper `auth_session.admit_session_fenced(conn,proof.session_ref,proof.owner_id,proof.epoch,proof.generation)` from Migration 004 and requires EXACT `True`.
4. Only then runs the supplied protected SQL callback on that same connection while Owner+Session row locks are retained until COMMIT/ROLLBACK. The fixture writes ONLY `auth_trust_ci.protected_actions`, an INSERT-only table on disposable PostgreSQL 17.11. Never use `inspect`/standalone `fence_owner` instead of 004 atomic admission.
5. PostgresCiReplayStore is explicitly **CI-only** with `auth_trust_ci.replay_jti(jti_sha256 UNIQUE, expires_at)`. `INSERT` with UNIQUE-jti_sha256 and explicit UniqueViolation rejection enforce single COMMITTED JTI consumption across multiple database connections/workers/restarts while the DB persists. Raw JWT/JTI/session never stored in replay DB: SHA256(issuer + NUL + jti) only. Session table gets the existing DB module's SHA256(opaque) digest, never raw Cookie. API role `auth_trust_api` is CI-only with EXECUTE on 004, schema USAGE and INSERT on two CI tables; **no issuer mapping, session issuance/rotation, reauth gate, owner revocation, History table, RLS bypass or table SELECT**. Fixture-specific grants exist only in .github/workflows/api-auth-trust.yml, NOT migration.
6. If store absent, DB unreachable, replay table missing, DB False, claim mismatch or protected SQL fails, **fail closed** and rollback. On a transaction ROLLBACK, an attempted JTI INSERT rolls back as well; *the same unexpired assertion may retry*, but only one committed use is possible. On successful COMMIT all further repeats fail. A new assertion on retry MUST retain original operation idempotency key; replay deduplication is **not** History Create/Send/Receipt idempotency and does not override that contract. If transaction commits but HTTP response is lost, a fresh assertion MAY repeat operation but product idempotency must handle duplicate semantics in its own later package.
7. DB clock is authoritative for 004 session idle/absolute expiration; 004 checks at admission, not at commit. Mutation arriving AFTER admission waits on Owner+Session locks until current transaction ends. This does **not** cancel admitted SQL when the clock crosses expiry, nor prove cross-database/HTTP streaming revocation.

### CI evidence scope and limitations

Only `ubuntu-24.04` free GitHub runner and `postgres:17.11` service; ephemeral synthetic identities/roles, keys in process only. Pin `PyJWT[crypto]==2.15.1`, read existing `apps/api/requirements-ci.txt` unchanged. Workflow applies unmodified migrations 001-004 to disposable DB; builds temporary role/table fixtures in CI. Run pure tests, actual API in-process HTTP+PostgreSQL tests and unchanged DB Session fence and API History regressions. No external credential, public IdP, real mail, provider/model/deploy/Mac installation, source repository write or production authorization. All assertions/results must be read from real CI and recorded in the SINGLE cumulative checkpoint; unrun = NOT_RUN.

**Remaining requirements:** Production durable replay table/retention and approved grants/migration from DB owner; BFF signer/private key and issuer/audience provisioning by UI/ops; transport mTLS, key rotation and clock sync; proof/session-ref exchange protection; verified fresh reauth/Reset outside product; live Auth→History permission/RLS and CSRF; two-user integration and security Gate. None accepted by this slice.

**Traceability:** P3M03-A01/A03/A08; P3M05-A03/A07/A08/A09/A10; P3M06-A03/A05/A07; P3M13-A03/A07/A08/A09/A10; operational overlay P3OP03-R01/R02/R05, not counted as new Gate.


### Closed PostgreSQL connection fail-closed negative

The coordinator's connection preflight runs inside the same psycopg exception
guard as transaction setup: a genuinely closed/failed primary DB connection
cannot generate an actor or run protected SQL. CI TRI14 closes a real
PostgreSQL connection and asserts TrustRejected + zero synthetic writes.
This does not simulate every multi-node partial outage or Production HA mode.


## TRUST-01-I — final temporal admission after lock wait (limited correction)

**Mandatory second time decision (API/DB slice):** The initial PyJWT
signature + issuer/audience/request binding + `iat/nbf/exp` check occurs
BEFORE the transaction. **This initial check is NOT the final time
authorization.** The replay UNIQUE INSERT and Migration 004
`auth_session.admit_session_fenced()` may block for PostgreSQL locks.

**Precise final point:** in the SAME outer PostgreSQL transaction and
primary Connection, AFTER successful replay INSERT and the exact-True
Migration 004 Session admission (Owner and Session `FOR SHARE` locks
acquired), BEFORE invoking `action`, the API samples exactly ONE
`clock_timestamp()` from that PostgreSQL primary (MATERIALIZED CTE). It
requires `iat <= sampled_at`, `nbf <= sampled_at`, `sampled_at < exp`
(strictly; equality at expiry is denied), and
`sampled_at - iat <= 30 seconds`. All signed numeric claims were
cryptographically verified and validated as nonnegative integers in the
preflight; the final comparison uses the same verified values, not
untrusted clock or an earlier request receipt timestamp.
`TrustRejected` rolls back the entire transaction, including any
inserted JTI; no protected action runs.

**Ordering guarantee only:** an action **first admitted and started before**
`exp` is not auto-cancelled as the clock advances; the product
operation may finish after expiration unless it separately aborts.
This boundary rejects only an operation that tries to **start after**
the post-lock final time check fails. Migration 004 separately enforces
DB Session idle/absolute expiry at its own admission instant; the
checks do not replace one another, nor certify remote/HTTP rollback
or global wall-clock synchronization.

**Real CI adversarial requirement:** TRI15 a valid initial assertion
waits on a real held Owner row lock with unchanged epoch; 
`pg_stat_activity.wait_event_type=Lock` and live PostgreSQL
`clock_timestamp() >= exp` must be independently observed; after
release, reject with zero committed JTI or protected write, then
fresh assertion succeeds. TRI16 a duplicate JTI waits on the first
transaction's real UNIQUE-key SQL lock; the original operation
began before expiry and is intentionally rolled back after the
DB clock crosses expiry; the waiting replay must fail the final
post-lock time gate rather than inherit the removed JTI. Fresh
assertion then succeeds. TRI17 a corresponding Owner lock wait
released BEFORE `exp` must permit action, with actual lock observation
and DB-time evidence. All cases are bounded synthetic CI only.
