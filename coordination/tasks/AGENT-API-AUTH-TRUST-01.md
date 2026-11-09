# AGENT-API-AUTH-TRUST-01 — cumulative authorized execution checkpoint

**Status:** IMPLEMENTED=LIMITED_SOURCE_PREPARED; TESTED=NEW_CI_PENDING; ACCEPTED=NONE. Proposed deliverable READY_FOR_REVIEW — API_SERVICE_TRUST_SLICE only after real passing CI. Product Auth/History integration/Production/M05 Gate remain BLOCKED.

## TRUST-01-A — 2026-11-09 baseline and mission limits

- Live repository: Shahbazi-Amir/RAG_finance_app; only writable target. Read-only other repos RAG_finance and parent AI-Agent-projects. **Starting main HEAD confirmed** `1e95ba52f726e4cff7da07cbdbb2b771887d3848`. New branch `agent/api-auth-trust` created from exactly this commit; branch absent before creation, no active competing PR. No merge or force push.
- Read AGENTS.md, coordination/ownership.md, [ADR 0005](../../docs/adr/0005-auth-session-boundary.md), [AUTH_SESSION_INTERFACE.md](../../src/phase3/storage/postgres/AUTH_SESSION_INTERFACE.md), Migration 003/004 SQL and accepted Python DB wrapper, db-auth-session.yml and existing tests. [PR #15](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/15) accepted 003 synthetic owner/opaque session/owner epoch, merge `8c33cc45b7934b28b4ca39974ae621fab600a8a8`; [PR #16](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/16) accepted **session-aware outer-transaction** Migration 004 and restricted `auth_sessions` EXECUTE, merge `1e95ba52f726e4cff7da07cbdbb2b771887d3848`. Neither is BFF issuer/signature verification, HTTP/Auth, product History or real Reset/reauth.
- Traceability (source `references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md`): **P3M03-A01/A03/A08** identity domain boundary, request/trace and contracts; **P3M05-A03/A07/A08/A09/A10** secure session/revoke/expiration/log-redaction/replay (service proof subset ONLY); **P3M06-A03/A05/A07** same-transaction owner fencing and negative cross-user SQL; **P3M13-A03/A07/A08/A09/A10** stable denied errors, trace scope, API endpoint authorization, regression/abuse. Operational P3OP03-R01/R02/R05 are *non-counting* overlays. No Gate checked; canonical checklist Foundation-owned and NOT edited.
- Allowed and ONLY changed files: `src/phase3/auth/service_proof.py`, `src/phase3/auth/transactional_admission.py`, `src/phase3/auth/SERVICE_TRUST_INTERFACE.md`, `tests/phase3/api/proof_fixture.py`, `tests/phase3/api/test_service_proof.py`, `tests/phase3/integration/api/test_auth_trust_postgres.py`, `.github/workflows/api-auth-trust.yml`, THIS cumulative task file. NO apps/web, apps/api/history_api.py, DB repository or migration, root, common contracts or canonical checklist modification.

## TRUST-01-B — selected implementation and exact trust boundary

- Real service proof verification uses **PyJWT[crypto] 2.15.1** (PyPI version verified 2026-11-09; not independently installed outside CI) and `cryptography` RSA public key parser. No hand-rolled JWT or signature. Only RS256/2048-bit+ explicitly configured static public key allowlist, exact `iss` and `aud`; no JWKS URL/jku/x5u/IdP JWT, fallback or assertion from browser owner header. Test-only RSA signer in unit/integration fixture independently generates keys in RAM, no signer in runtime module. Header and claims strict, unknown/duplicate/forbidden owner headers fail closed. Integration consumer is isolated in-process FastAPI fixture, NOT product History.
- `iat,nbf,exp` mandatory exact integers, `exp-iat<=30s`, zero leeway, positive age, jti 20..128 URL-safe; exact method, ASGI raw_path, raw query including order/% casing, *raw body bytes* SHA256 and body_len (not parsed JSON). Bound server-only session_ref, owner UUID, epoch and generation. No Cookie or IdP token in JavaScript/log/artifact. HTTP test fixture deny with generic 401 or 503 no body.
- `protected_operation` verifies proof then opens a single explicit PostgreSQL primary `conn.transaction()` on `auth_trust_api` restricted role; consumes JTI through `INSERT...ON CONFLICT DO NOTHING` on synthetic `auth_trust_ci.replay_jti` with a UNIQUE digest, calls **UNCHANGED** `auth_session.admit_session_fenced(conn, same server-side opaque, signed owner,epoch,generation)` from 004, requires exactly True, and then invokes test-only INSERT in **same connection and outer transaction**. Any SQL error/rejected session aborts all writes. DB 004 handles Owner→Session locks, DB time/status/epoch/expiry; NOT duplicated as Python checks. Role can only call 004, insert JTI/marker; no issue, revoke, reauth, History privilege, direct Auth tables or BYPASSRLS. Trusted fixture roles create synthetic owner/issued session **only in GitHub CI**.
- **JTI semantics:** consumed iff outer transaction COMMIT; if protected write raises and TX ROLLBACKs, JTI insert also rolls back and the same still-unexpired assertion MAY retry. Concurrent same-JTI across DB connections allows at most one committed successful operation. New JTI for an HTTP retry is **not** Product Create/Send idempotency and must preserve its original idempotency key. The in-memory fixture/Signer is NOT a durable multi-worker replay guarantee. Test-only real PostgreSQL table provides durability *only during disposable DB lifetime*. Future production replay store & role grants require DB-owner migration/approval; absence fails closed.
- **Limitations:** same PostgreSQL transaction only, not HTTP/external side effects cancellation after admission or natural expiration; no production BFF issuer, mTLS, secret management/rotation, CSRF/cookie, fresh reauthentication, reset external, IdP tokens, two OIDC user identities, real product Auth/RLS/History Gate, Production. BFF-side protected server session-ref transport still needs explicit separate UI/API design review. Keycloak PR13 measured reset surviving old IdP browser SSO/refresh/UserInfo, not resolved here.

## TRUST-01-C — CI setup, exact tests and expected checks (PENDING at first Push)

`ubuntu-24.04` free GitHub Actions, `postgres:17.11` one disposable service at CI loopback, Python 3.13. CI pip: `python -m pip install --no-cache-dir --index-url https://pypi.org/simple -r apps/api/requirements-ci.txt 'PyJWT[crypto]==2.15.1'`; existing API pins FastAPI 0.162.2, httpx 0.28.1, psycopg[binary] 3.3.8, jsonschema 4.26.0 unchanged. Real installed Python/cryptography subversion MUST come from actual run output.

CI applies unmodified 001+002 History, 003+004 Auth migrations to disposable history_ci; separate history_api_ci 001+002 for unchanged API regression. CI-only disposable `auth_trust_ci.replay_jti`, `auth_trust_ci.protected_actions` and grant EXECUTE(004) to auth_trust_api, no Migration changes. CI-only existing `auth_fence_ci.protected_actions` fixture reused for DB 004 regression; no real users. Role credentials are fixed synthetic-only ephemeral CI strings; NOT production secrets. No installation on Mac, Keycloak start, outbound email, model, deploy, paid/real external service.

Exact CI commands in new workflow:
1. `python -m compileall -q src/phase3/auth tests/phase3/api tests/phase3/integration/api`
2. `python -m unittest discover -s tests/phase3/api -p 'test_*.py' -v`
3. `python -m unittest discover -s tests/phase3/integration/api -p 'test_auth_trust_postgres.py' -v`
4. `python -m unittest discover -s tests/phase3/database -p 'test_auth_session_fence.py' -v`
5. `python -m unittest discover -s tests/phase3/contracts -p 'test_history.py' -v`
6. `python -m unittest discover -s tests/phase3/integration/api -p 'test_http_postgres.py' -v`

Expected checks (ALL new NOT_RUN at first Push): TRU01..10 static RSA/keys/issuer/audience/time/jti/byte binding/spoof/size; TRI01..13 true synthetic SQL permit, direct/forged denial, sequential/concurrent replay, wire tampering, signed mismatches, rotate/revoke-one/revoke-all/suspend/idle/absolute, actual DB lock wait vs revoke, transaction rollback/no partial effect, missing replay/role denial and real in-process HTTP; unchanged DB session fence, History API & contract regressions. Real outcomes only after CI.

**Potential dependencies/open decisions:** approved production durable replay store + role grants must be designed/implemented by DB owner, not silently into auth_trust_ci; BFF public key distribution, private signer custody, HTTPS/mTLS/path normalization and provider credential reset revocation remain future work. If CI fails, append failure/stage, root cause, fix and new SHA to THIS checkpoint in the very next related working Push, never replace historical records.

## TRUST-01-D — review handoff policy

For every meaningful Push update THIS SAME file in the same atomic commit, keep branch and Draft PR unmerged; report source tested SHA and documentary final SHA separately. New code and tests do not authorize real Auth, History, reset/reauth or Module Gate acceptance. Proposed final label **READY_FOR_REVIEW — API_SERVICE_TRUST_SLICE** is conditional on observed green real CI.


## TRUST-01-E — first REAL CI failure and least-privilege SQL fix (2026-11-09)

SOURCE SHA 423f360fab95f7765737e3bf3bcbaa5526709874; [GitHub Push Run 42678132169](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42678132169) **COMPLETED FAILURE**. PostgreSQL 17.11 service started and migrations 001-004 applied; pinned Python 3.13.18, PyJWT 2.15.1, cryptography 50.0.2, psycopg 3.3.8 installed successfully. Compileall and **10/10 pure Trust Unit tests PASS**. Initial 13 integration tests: 3 PASS, 9 FAIL, 1 ERROR. Failed real SQL stage had actual server diagnostic `permission denied for table replay_jti` on positive admission. Cause: `INSERT ... ON CONFLICT (jti_sha256) DO NOTHING` under deliberately INSERT-only role requires more table privileges in PostgreSQL 17.11. This is NOT an assertion/DB 004 failure; initial positive proof never entered protected SQL. No positive concurrency/revoke claims from that run.

**Narrow correction:** replace targeted ON CONFLICT with ordinary INSERT into the existing unique indexed fixture table; catch `psycopg.errors.UniqueViolation` and return False, forcing the outer coordinator to raise TrustRejected and roll back the aborted TX. Every other SQL error still fails closed. Keep **INSERT-only** auth_trust_api and **NO SELECT/UPDATE/DELETE** on replay table; no schema or role broadening and no DB migration. The test's direct SELECT-denial remains mandatory. Changed code only src/phase3/auth/transactional_admission.py, linked service-proof interface doc and this cumulative checkpoint. No test relaxation. Test after fix **PENDING actual new SHA CI**.

Additional precision: JTI is NOT persisted on failed/rolled-back protected operation, but remains consumed on a committed operation; unique constraint is real PostgreSQL across all connections, unlike process-only memory. Assertion signing secrets never in report. If second run fails, record error and follow-up in next atomic push.


## TRUST-01-F — real new-slice ALL PASS, unchanged History regression harness config correction

Exact source SHA 9129782b89d12adc0719ccd67477919b025bcc08, [Push CI Run 42678454139](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42678454139): **COMPLETED FAILURE overall**, but ALL new and prior DB trust cases passed:
- **TRU01–TRU10:** 10/10 PASS on real pinned PyJWT 2.15.1 RSA signature/config/time/path/query/body/owner negatives.
- **TRI01–TRI13:** 13/13 PASS on actual PostgreSQL 17.11 with dedicated INSERT-only auth_trust_api, synthetic in-process FastAPI HTTP, real same-session 004 transaction fencing, concurrent JTI unique conflict, revoke race/lock wait, expiry, rotation, revoke all, suspension, missing replay store, rollback/no partial effect.
- **BND16–BND25 existing DB Session-aware fence:** 10/10 PASS, unchanged test/source.
- **Existing History product contract:** 17/17 PASS unchanged.
- **Existing History HTTP/PostgreSQL:** 18/20 PASS, *two failures only*: test_09 Conversation Cursor and test_10 Message pagination returned **503 CURSOR_CONFIGURATION** because the new Workflow's separate history_api_ci fixture omitted existing `API_CURSOR_KEY` (and TTL) from the already accepted `.github/workflows/api-history.yml`. No product code changed; no evidence of Auth/DB 004 regression.

**Narrow correction, WORKFLOW ONLY:** set exact CI synthetic `API_CURSOR_KEY=ci-only-cursor-signing-not-production-2026-verified-unit-test` and `API_CURSOR_TTL_SECONDS=300`, as in existing accepted API History CI. These are nonsecret synthetic configuration, NOT product keys; CI environment only, no production credential. This checkpoint updated atomically in same Push; no tests softened or migrated. Expected next Run exact new SHA must prove all six real commands green. Version evidence from actual CI: Python 3.13.18, psycopg 3.3.8, PyJWT 2.15.1, cryptography 50.0.2, FastAPI 0.162.2, httpx 0.28.1, PostgreSQL 17.11. Last source remains unaccepted until overall green; acceptance stays NONE.


## TRUST-01-G — first full GREEN CI and follow-up DB-down hardening (2026-11-09)

SOURCE SHA 932bedd026a8bd94551299a10266494b27a0a9ed,
[actual GitHub Push Run 42678700135](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42678700135) **COMPLETED SUCCESS**. All CI steps successful. Real counts:
- TRU01..TRU10 pure static RSA/byte-bound service proof **10/10 PASS**;
- TRI01..TRI13 real PostgreSQL 17.11 synthetic FastAPI/JTI/session SQL **13/13 PASS**;
- unchanged BND16..BND25 004 DB admission fence **10/10 PASS**;
- unchanged History contracts **17/17 PASS**;
- unchanged API History/PostgreSQL HTTP suite **20/20 PASS**.
**Total 70/70 tests**, with real PostgreSQL, true concurrent replay/revoke lock waits, rollback and denied privileges, not static claim. Versions from Run: Python 3.13.18, PostgreSQL 17.11, PyJWT 2.15.1, cryptography 50.0.2, psycopg 3.3.8, FastAPI 0.162.2, httpx 0.28.1. No product file or migration changes. Earlier failures recorded above remain part of audit.

**Extra fail-closed audit discovery:** preflight `conn.autocommit` and `conn.info.transaction_status` was outside the psycopg.Error handling. Under a closed/disconnected session store connection an exception could bypass the generic TrustRejected boundary, even though no protected SQL would run. Narrow correction: include the connection preflight inside existing psycopg.Error catch; new **TRI14** uses genuinely closed PostgreSQL connection to require TrustRejected and no protected writes. Existing positives, roles and assertions stay intact. Extra updated source SHA is NOT_TESTED until its own GitHub Actions run. This is not a mock proof of every partial infrastructure outage or reconnect behavior.

Implemented=SOURCE_PLUS_DB_DOWN_GUARD; tested=70_GREEN_PREVIOUS_SHA, NEW_TRI14_PENDING; accepted=NONE / SUPERVISOR_PENDING. Any new working Push includes this same ledger. Do not merge, do not enable Product Auth.


## TRUST-01-H — FINAL exact-source real CI evidence and review handoff (2026-11-09)

**TESTED SOURCE SHA:** `57415cee5f80f5bfc3251f7745780a65ccc6e2bd`.
[GitHub Actions Push Run 42679069622](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42679069622): **COMPLETED SUCCESS on this exact SHA**, all job steps PASS, PostgreSQL temporary 17.11, Python 3.13.18, PyJWT[crypto] 2.15.1 + cryptography 50.0.2, FastAPI 0.162.2, psycopg 3.3.8, httpx 0.28.1.

Exact real verification matrix from unmodified `.github/workflows/api-auth-trust.yml` and GitHub logs:
- `python -m compileall -q src/phase3/auth tests/phase3/api tests/phase3/integration/api` → PASS;
- `python -m unittest discover -s tests/phase3/api -p 'test_*.py' -v` → **10/10 PASS**, RSA signature and header/key allowlist, forbidden algorithm/remote key, issuer/audience, exp/iat/nbf 0s skew + ≤30s lifetime, missing/bad jti, encoding/path/query/body/method/owner tamper, duplicate/forwarded headers and bounds;
- `python -m unittest discover -s tests/phase3/integration/api -p 'test_auth_trust_postgres.py' -v` → **14/14 PASS**, including TRI14 genuine closed connection rejected and zero protected write; real in-process HTTP, correct signature+session, altered signed CAS claims, missing/wrong Direct API/IdP service header, rotated/expired/revoked/all/suspended, exactly one concurrent committed JTI, rollback retry/no incomplete protected side-effect, actual PostgreSQL Lock wait against revoke;
- `python -m unittest discover -s tests/phase3/database -p 'test_auth_session_fence.py' -v` → **10/10 PASS** unchanged 004 DB regression;
- `python -m unittest discover -s tests/phase3/contracts -p 'test_history.py' -v` → **17/17 PASS** unchanged synthetic contracts;
- `python -m unittest discover -s tests/phase3/integration/api -p 'test_http_postgres.py' -v` → **20/20 PASS** unchanged History product HTTP/PostgreSQL suite.
**Total: 71/71 PASS on real CI source SHA.** No failures or skipped test claimed PASS. Earlier original failures and their minimal CI corrections remain recorded in E/F; previous Run 42678700135 was 70/70 green on earlier code SHA before TRI14.

The `auth_trust_api` role in disposable CI had only USAGE on auth_l1, EXECUTE on function 004 and INSERT on `auth_trust_ci.replay_jti` plus `auth_trust_ci.protected_actions`; it had NO direct session/owner/history read, mapping, issue, reauth, revoke or BYPASSRLS grants. Test fixture roles create owners/sessions, not the API role. JTI is stored SHA256 only, not a raw signed JWT; sensitive verifier/session material is never logged, returned to JS or stored in Artifact. No CI artifact was uploaded; official GitHub job output includes IDs/status and sanitized test names only. Service proof is NOT an IdP authentication of the human actor, and signed server-only session_ref itself remains a privileged secret for the future BFF transport design.

**Delivery label:** READY_FOR_REVIEW — API_SERVICE_TRUST_SLICE, with supervisor acceptance pending. This task is an API service assertion + same-transaction synthetic protected SQL proof ONLY. Product FastAPI History/Next.js BFF integration, durable production replay schema and role/migrations, real IdP OIDC, fresh reauth after Reset, outside-product Reset coverage, CSRF/Cookie, TLS/mTLS and production deployment remain NOT_IMPLEMENTED/NOT_RUN/NOT_ACCEPTED.

**Source tested SHA differs from eventual final HEAD if this checkpoint is a documentation-only last commit.** Report Final SHA separately; any auto-triggered CI on documentary head must be checked before claiming it succeeded. Keep PR Draft/Unmerged, main at Starting SHA unless independently advanced. Do not merge.


## TRUST-01-I — requested temporal TOCTOU correction (source push pending CI)

**Mission continuation:** AGENT-API-AUTH-TRUST-01, source P3M03-A01/A03/A08, P3M05-A03/A07/A08/A09/A10, P3M06-A03/A05/A07, P3M13-A03/A07/A08/A09/A10 (Module03/05/06/13); P3OP overlays not counted. Verified real HEAD of agent/api-auth-trust at start: `3190bddcf9ef52165f7fef79206e1dad9dbef075`, exact user-provided Starting HEAD, main unchanged at `1e95ba52f726e4cff7da07cbdbb2b771887d3848`. PR #17 open Draft and unmerged, no duplicate/new PR. Earlier 71/71 green evidence remains on Run 42679484645 / 42679069622, on the old code/doc HEAD. No rebuild of product Auth or working BFF.

**Defect and fix:** the pre-transaction proof verification was valid at HTTP arrival, but JTI uniqueness wait and Migration004 Owner+Session lock wait could last beyond assertion `exp`. The old code allowed new action immediately after the lock released. Narrow service-proof change carries previously verified signed `iat` and `nbf` (and `exp`) in a redacted VerifiedServiceProof. After replay consumption and exact-True 004 session admission but before action, the same primary PostgreSQL connection samples ONE current wall clock using `clock_timestamp()` in MATERIALIZED CTE, requires signed iat/nbf <= clock < exp and age<=30 seconds. Rejection atomically rolls back pending JTI and any SQL. Does not reimplement 004 Session admission or modify DB Migration; holds Owner/Session locks until transaction ends. If an action has already begun before expiration, no automatic cancellation on clock progression is claimed. Documentation in same existing internal `src/phase3/auth/SERVICE_TRUST_INTERFACE.md` appended with precise final time decision.

**New real PostgreSQL CI-only cases** (new test paths only under tests/phase3/integration/api/**):
- TRI15 signed proof valid at initial check, real Owner row `FOR UPDATE` held by disposable migrator without epoch/status modification; pg_stat_activity must observe SQL `Lock` on 004, PostgreSQL clock must show expiry crossed before release; afterwards deny and rollback zero protected writes and zero committed JTI; fresh independent proof succeeds.
- TRI16 first proof consumes JTI and starts action while valid, second same-JTI attempt blocks on UNIQUE INSERT; actual PG wait + clock crossing exp observed, first intentionally rolls back after expiry; second now-unblocked attempt must deny with zero JTI/writes; a freshly signed assertion must succeed. No 'cancel already-started operation' claim.
- TRI17 real held Owner lock released while token still valid; pg_stat_activity must observe lock, DB clock verifies before exp; admitted action and JTI commit successfully.
All former 71 test cases retained and not weakened; expected count **74**. Tests and CI results NOT_RUN on this new source revision yet, to be updated from actual Actions logs. No workflow, DB repository/migrations, apps/web or apps/api/history_api, root/shared schema or checklist edits. Synthetic PostgreSQL 17.11, no Mac install/email/model/deploy, no raw token/secret in logs. With each Push this same cumulative ledger is updated atomically.

**Proof of correctness intentionally limited:** PostgreSQL primary trusted clock is the final local admission time; not global synchronized clock guarantee or external side-effect cancelation. Existing Production BFF, durable replay migration and reset/reauth are still unimplemented; Accepted=NONE/SUPERVISOR_PENDING.


## TRUST-01-J — static harness review correction, no security-policy loosening

Immediate post-Push read-back of added PostgreSQL contention tests identified
two mistakes in NEW test helper only: TRI15/TRI17 accidentally nested
`ThreadPoolExecutor` inside a `FOR UPDATE` holding transaction, so
Executor.__exit__ could join a blocked worker while the same test still
held the lock (deadlock until timeout); change nesting so the real holder
commits/releases before joining the worker. The JTI observer helper used a
literal backslash-x00 separator instead of the database store's actual
NUL byte; compute digest with `bytes([0])` explicitly. This tightens
the evidence: a committed JTI can no longer be missed due to wrong observer
digest, and a test scheduler cannot pretend to be a genuine SQL lock
timeout. No production code, tests asserted outcomes, migration, CI setup,
role grants or checkout/main files are changed.

First test-bearing SHA bd04a0e22ab5df0a471f335e996abd76dfa7bfed
started GitHub Push Run 42681098826; review discovered the harness error
while that Run was still in progress. Actual eventual result remains
separately verifiable and is NOT claimed PASS. New corrected SHA CI
will be authoritative for TRI15–TRI17. Expected all historical 71
regressions preserved; final count 74.


## TRUST-01-K — FINAL verified post-lock temporal admission, real CI handoff (2026-11-09)

**STARTING HEAD confirmed live:** `3190bddcf9ef52165f7fef79206e1dad9dbef075` on `agent/api-auth-trust`. Existing PR #17 remains Draft Open Unmerged, main remains `1e95ba52f726e4cff7da07cbdbb2b771887d3848`. Correction only in five allowed paths: `src/phase3/auth/service_proof.py`, `src/phase3/auth/transactional_admission.py`, `src/phase3/auth/SERVICE_TRUST_INTERFACE.md`, `tests/phase3/integration/api/test_auth_trust_postgres.py` and THIS same cumulative checkpoint. No migration, DB repository, product API History, UI, workflow, shared contract, root or checklist edits.

**EXACT TESTED CODE SHA:** `370335efd5b0e5170841a1b6bbf4805defae50ef` (the first version after harness lock/digest corrections). Both actual independent GitHub Actions runs completed SUCCESS on exactly that SHA:
- [Push Run 42681400476](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42681400476) — completed/success;
- [PR Run 42681409972](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42681409972) — completed/success.

**Real measured CI breakdown on each run:** pure RSA proof unit TRU01..TRU10 **10/10 PASS**, real PostgreSQL integration TRI01..TRI17 **17/17 PASS**, unchanged DB 004 fence BND16..BND25 **10/10 PASS**, unchanged History contracts **17/17 PASS**, unchanged History HTTP/PostgreSQL **20/20 PASS**. **74/74 PASS in each run**, plus compileall PASS. Existing protected SQL, privilege denials and concurrent revoke tests stayed unchanged and PASS.

**Independent new negative/positive evidence:**
- TRI15 **PASS:** signed 5-second proof successfully passed initial RSA/time validation BEFORE blocking. Disposable migrator held a pure Owner `FOR UPDATE` lock (no Owner epoch/state or Session mutation). CI observed PostgreSQL `pg_stat_activity.wait_event_type='Lock'` on `admit_session_fenced` before expiry, *and* independently observed real primary `clock_timestamp() >= exp` while locked. After release, operation was denied, `auth_trust_ci.protected_actions` had zero rows for the marker, durable `auth_trust_ci.replay_jti` had zero rows for exact SHA256(issuer + NUL + jti). Owner epoch stayed unchanged and reset_gate stayed open. Fresh assertion succeeded.
- TRI16 **PASS:** first transaction consumed its JTI and entered the SQL action BEFORE expiry; a concurrent duplicate assertion actually blocked on the same JTI UNIQUE INSERT, observed as a PostgreSQL Lock wait BEFORE expiry. After independent DB clock crossed `exp`, the first *deliberately* raised test exception and rolled back; the waiting second resumed after the uniqueness conflict vanished, but its NEW post-admission time decision denied it. Zero committed JTI / protected writes after both; a new signed assertion succeeded. First already-started action was not automatically cancelled by expiration; it was deliberately rolled back by the test.
- TRI17 **PASS:** equivalent real Owner row lock with proof still valid when released; actual lock wait observed, DB time verified before `exp`, protected SQL committed and exactly one JTI digest consumed.

**Exact final admission decision:** after signature and initial time check, replay INSERT may wait; after that, Migration 004 obtains owner/session FOR SHARE and checks Session status/expiry/epoch. Only when exact-True is returned, on the SAME PostgreSQL connection and outer transaction a MATERIALIZED-CTE samples current primary `clock_timestamp()` ONCE, accepts strictly `iat <= checked_at`, `nbf <= checked_at < exp` and `checked_at-iat <=30s`. Only then **action starts**. Expired or other invalid time → generic TrustRejected; outer transaction rollback removes even an inserted JTI. This does NOT cancel an action already admitted and started before expiry or an external side effect. DB 004 handles Session idle/absolute expiry at its separate admission point, not application-level JWT proof expiry.

**Audit of pre-green attempt:** initial revision `bd04a0e22ab5df0a471f335e996abd76dfa7bfed` exposed test harness nesting that could join a worker while retaining the very Owner lock it needs; JTI observer used an escaped literal instead of the NUL separator. Both were corrected on next working commit and recorded under TRUST-01-J. The initial attempt's GitHub Runs [42681086160](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42681086160) and [42681098826](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42681098826) were STILL IN PROGRESS during final evidence collection (not claimed as FAIL/PASS; likely block until job timeout). Distinguish those obsolete runs from independently green latest SHA. No force-push, merge, relaxed assertion or deleted previous tests.

**Versions and execution:** unchanged [api-auth-trust.yml](../../.github/workflows/api-auth-trust.yml) on GitHub-hosted ubuntu-24.04, Python 3.13, PostgreSQL `postgres:17.11`, PyJWT[crypto] 2.15.1, cryptography 50.0.2, psycopg 3.3.8, FastAPI 0.162.2; no secret/test signers uploaded. Actual commands unchanged: `python -m compileall -q src/phase3/auth tests/phase3/api tests/phase3/integration/api`; unittest discover pure api, synthetic test_auth_trust_postgres, DB session fence, contract History and unchanged real HTTP History. Temporary fixture roles and tables only in CI, never product schema.

**Scope/ownership:** Source roadmap Modules03/05/06/13: P3M03-A01/A03/A08, P3M05-A03/A07/A08/A09/A10, P3M06-A03/A05/A07, P3M13-A03/A07/A08/A09/A10; limited evidence, no Gate accepted. This is NOT a working BFF/IdP login, product Auth/History integration, complete remote reset/reauth, Production durable JTI or HTTP cancellation; all remain separate DB/UI/API/Integration work. No installs on Mac, public email, model, purchase, service or deployment.

**Implemented:** POST_LOCK_TEMPORAL_AUTHORIZATION. **Tested:** TWO_REAL_GREEN_74_TEST_RUNS_ON_EXACT_SHA. **Accepted:** NONE / SUPERVISOR_PENDING. **Disposition:** READY_FOR_REVIEW — API_SERVICE_TRUST_SLICE. Preserve same Draft PR #17; no merge. A subsequent doc-only Final HEAD differs from tested source SHA and must be reported separately; its auto CI status must be checked before attributing SUCCESS.


## TRUST-01-M — API durable replay integration plan and source checkpoint (2026-11-09)

**Mission:** continuation of AGENT-API-AUTH-TRUST-01, not a second task file. **Requested starting commit and verified live `main` SHA:** `cee65c5af00f43556fba6b588338bc2273793653`; **new branch:** `agent/api-durable-replay` created from exactly that SHA. Prior [PR #17](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/17) already merged at `7f319e097ec6f4f754a782f4b56216cbd83b89ca` (API Trust: 74 real green synthetic tests with post-lock proof time); [PR #18](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/18) merged at exact starting main `cee65c5af00f43556fba6b588338bc2273793653` (DB-owned BND-DB-03 durable replay 005, 49 scoped synthetic PG tests, original source `667fdc92d884490e1aeb514acb62b4346a1ef5f0`, CI [42689689919](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42689689919)). This is **accepted limited DB interface**, not API signing/Auth integration or production role.

**Inputs actually read:** AGENTS.md, coordination/ownership.md, ADR 0005; `src/phase3/auth/SERVICE_TRUST_INTERFACE.md`, `src/phase3/storage/postgres/SERVICE_REPLAY_INTERFACE.md`, `AUTH_SESSION_INTERFACE.md`, existing accepted `auth_session.py` and `service_replay.py`, unmodified migration 001/002/003/004/005 sources, existing API Trust `test_service_proof.py` + synthetic `test_auth_trust_postgres.py`, unchanged `test_service_replay.py`, `test_auth_session.py`, `test_auth_null_fence.py`, `test_auth_session_fence.py`, History contract and HTTP regression suites, workflow `.github/workflows/api-auth-trust.yml`. No other repo write or root contract edit.

**Traceability, NOT new Gate PASS:** original canonical `P3M03-A01/A03/A08`, `P3M05-A03/A07/A08/A09/A10`, `P3M06-A03/A05/A07`, `P3M13-A03/A07/A08/A09/A10`, and non-counting `P3OP03-R01/R02/R05` overlays, same mapping as TRUST-01-A. Scope only BFF-to-API trusted service proof + JTI durability and concurrent admission. `coordination/phase3_checklist.md` remains Foundation-owned, untouched and unaccepted.

**Authorized path diff for current branch (exactly 5 intended):**
1. `src/phase3/auth/transactional_admission.py`: remove the former `PostgresCiReplayStore` SQL/digest implementation; enforce explicit instance of accepted DB-owned `PostgresDurableReplayStore`; keep pre-TX verified signed bytes, one outer PG transaction, exact-True replay, exact-True 004 admission, primary `clock_timestamp()` post-lock check and synthetic action. Sanitize `psycopg.Error`, adapter `ValueError`/`RuntimeError`/`TypeError` to generic `TrustRejected`, no proof/SQL leakage. No fallback table/memory/duck-typed store.
2. `tests/phase3/integration/api/test_auth_trust_postgres.py`: replace test default with DB adapter, use DB-owned digest helper only for test observer, 005 replay queries, 005 SQL Lock observation for TRI16; preserve TRI01..TRI17; extend TRI18 actual 005 despite absent legacy replay table, TRI19 isolated missing-005 and missing EXECUTE, TRI20 manual expired-only cleanup with stale proof denied, TRI21 ValueError/RuntimeError/False secure errors.
3. `.github/workflows/api-auth-trust.yml`: branch trigger `agent/api-durable-replay`; apply **unchanged** 001..005 to history_ci on disposable `postgres:17.11`; separate disposable history_no005_ci with 003+004 only; restricted auth_trust_api via 005 standard grants (no auth table SELECT, no BFF signer/issuance/reauth/revoke/History/BYPASSRLS). Only synthetic `auth_trust_ci.protected_actions` and `service_replay_ci.protected_actions` INSERT fixtures, NO `auth_trust_ci.replay_jti`. Separate auth_replay_cleaner role for manual-only cleanup in DB regression test, and denied role for absence of replay EXECUTE. Additional unchanged DB 001-004 suites and existing History regressions.
4. `src/phase3/auth/SERVICE_TRUST_INTERFACE.md`: replace obsolete legacy replay claim with 005 adapter and exact role/exception/final time contract. No change to DB-owned `SERVICE_REPLAY_INTERFACE.md`.
5. **THIS existing cumulative task file**, appended in same working commit, no parallel report.

**Security decisions:** No API-owned SHA/SQL/unique insertion; 005 DB role/SECURITY DEFINER handles digested issuer:JTI namespacing, durable UNIQUE and own pre/post-lock clock; API final DB clock check after the 004 Session locks still mandatory. Any signed request with valid RSA but stale Session, duplicate committed JTI, lost 005/EXECUTE, broken DB, adapter errors or absent real DB store must fail closed and rollback. A new JTI does not mutate product message idempotency semantics. JTI deletion after expiry never revives an already expired proof. DB persistence across new connections/adapters is NOT a PostgreSQL server-process restart proof.

**Reproducible tests commanded by new workflow (NEW SOURCE NOT_RUN UNTIL REAL CI):**
- `python -m compileall -q src/phase3/auth tests/phase3/api tests/phase3/integration/api`;
- `python -m unittest discover -s tests/phase3/api -p 'test_*.py' -v` (10 prior pure RSA);
- `python -m unittest discover -s tests/phase3/integration/api -p 'test_auth_trust_postgres.py' -v` (17 existing + TRI18–TRI21 = 21 unique API/PG integration methods);
- `python -m unittest discover -s tests/phase3/database -p 'test_*.py' -v` (all unchanged DB Owner/Session 003, 004 fencing, 005 service replay; 12+3+10+11=36 methods expected);
- `python -m unittest discover -s tests/phase3/contracts -p 'test_history.py' -v` (17 unchanged history contracts);
- `python -m unittest discover -s tests/phase3/integration/api -p 'test_http_postgres.py' -v` (20 unchanged History HTTP/PG).
**Expected unique total if all complete: 10 + 21 + 36 + 17 + 20 = 104 methods.** The unchanged BND DB replay tests are counted only in the 36-method DB command, NOT again as API Trust tests. 74 prior PR17 methods retained (10+17+10+17+20); new 4 API cases and extra 26 DB regressions in this workflow. Exact results and versions PENDING real GitHub Actions.

**Limits and next handoff:** no real BFF signer/IdP/OIDC login/mTLS/private transport, Fresh Reauthentication, external Reset, Product History Auth wiring, live DB migration, real user, production cleanup/retention, Module 03/05/06/13 Gate or `AUTH_PRODUCT_ACCEPTED`. No local Mac install, real email/model/public service/cost/deploy. `main` and parent/main RAG_finance stay read-only. If first CI fails, record actual stage/cause, narrow fix, and re-run on new commit with THIS ledger updated per Push.

**Status on first Push:** IMPLEMENTED=API_DURABLE_REPLAY_SOURCE_PREPARED; TESTED=NEW_INTEGRATION_NOT_RUN; ACCEPTED=NONE / SUPERVISOR_PENDING.


## TRUST-01-N — first real CI bootstrap failure, exact fix (2026-11-09)

**SOURCE SHA:** `91ba89a684d3a6c6a841d74e214e213ed945d1b2`, [GitHub Push Run 42693852913](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42693852913) completed **FAILURE** before test execution. PostgreSQL 17.11 runner service, Python dependencies and unmodified migrations 001-005 applied successfully; the new CI-only restricted roles/schema and legacy-table-free `auth_trust_ci.protected_actions` were created successfully. Failure stage: **Apply UNCHANGED migrations 001 through 005 to ephemeral PostgreSQL**, Bash syntax error near `(` at shell line 44. The script carried literal escaped double-quote characters `\\\"` around SQL passed to `psql -c`, causing Bash to parse `to_regclass(` outside an actual quote. This is a workflow-only shell quoting bug; NO tests were run and there is no PASS claim.

**Fix (same restricted path, same cumulative checkpoint):** remove the three unintended backslashes so `-c "SELECT to_regclass(...)"` and `-c "SELECT to_regprocedure(...)"` remain valid Bash command-substitution arguments in the post-migration assertions. **No** SQL migrations, role privileges, assertion validation, code adapter or tests changed. Re-run full CI and retain failed Run as audit history. No live database touched; `main` unchanged.
