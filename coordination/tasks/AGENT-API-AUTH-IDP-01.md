# AGENT-API-AUTH-IDP-01 — cumulative CI-only Keycloak evaluation ledger

Status at first working push: IMPLEMENTED=ISOLATED_TEST_HARNESS_PREPARED; TESTED=GITHUB_CI_PENDING; ACCEPTED=SUPERVISOR_PENDING.
Delivery target only: READY_FOR_REVIEW — ISOLATED_IDP_EVALUATION, not AUTH_PRODUCT_ACCEPTED or PRODUCTION_READY.
Starting main SHA: 4831ff90470028abab1dd6dd78834fcf3446a716. New branch: agent/auth-idp-ci. Repository Shahbazi-Amir/RAG_finance_app. No other repo is writable.

## IDP-CI-01-A — preflight (2026-11-08)

Read live GitHub main: exact 4831ff90470028abab1dd6dd78834fcf3446a716 and exact merge commit of PR #12, now merged/closed. New branch agent/auth-idp-ci was 404 before creation and was created from this SHA without changing main. Read AGENTS.md and coordination/ownership.md, ADR 0004 §8, coordination/open_decisions.md employer preferences and canonical coordination/phase3_checklist.md. The additional infrastructure/auth_idp integration/workflow permissions were expressly granted by supervisor for THIS evaluation only; Foundation's permanent ownership of shared workflow/infra remains unchanged. All previous DB/API/UI limited PR #9/#10/#11 acceptances remain bounded; no real Auth had been implemented or accepted. No parallel Auth product test fixture or checklist modification.

Actual source: references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md, Module 05 authentication_and_sessions, activities 1-10, L302-L311. Existing canonical IDs:
- P3M05-A01 employer method decision (documented in previously merged ADR; no Keycloak final decision);
- P3M05-A02 conditional password hashing, A03 session token/rotation, A04 HttpOnly/Secure/SameSite Cookie, A05 CSRF policy;
- P3M05-A06 login throttling/controlled lockout, A07 logout/revoke, A08 expiration/refresh, A09 security event redaction, A10 session theft/replay negative tests.
Linked future M06 user isolation, M13 endpoint auth, M14 login UI, M15 no cross-user disclosure remain blocked. This evaluation checks selected IDP-specific behaviors only. All M05 Product Auth activities, full Gate and Module 00 remain NOT_ACCEPTED, regardless of CI result.

Employer target current Iran; preference infrastructure controlled by organization, v1 email/password+email verification/secure reset; Keycloak an evaluation candidate only. No hosting vendor/location/legal approval, production SMTP, budget, real IdP or account approval. Future phone/SMS/username/public OTP, financial/bank data, model, real users and admin/financial panels OUT_OF_SCOPE.

## IDP-CI-01-B — pinned sources and containment choices

Official version review at 2026-11-08:
- Keycloak 26.8.2, released 2026-11-05: https://www.keycloak.org/2026/11/keycloak-2682-released ; official pinned Docker usage https://www.keycloak.org/getting-started/getting-started-docker ; image quay.io/keycloak/keycloak:26.8.2, start-dev only on isolated CI loopback, not a production config.
- PostgreSQL 17.11 (identity-only DB, NEVER product History DB); Keycloak current supported database matrix https://www.keycloak.org/server/db lists 17.x supported, while tested version is 18.
- Mailpit v1.32.0, October 2026, upstream https://github.com/axllent/mailpit/releases ; REST https://mailpit.axllent.org/docs/api-v1/ ; image ghcr.io/axllent/mailpit:v1.32.0. No remote relay or mailbox.
- Pin Python 3.13 / requests 2.32.5 / PyJWT crypto 2.10.1 / pyotp 2.9.0 / Playwright 1.64.1 Chromium. Official Keycloak realm configuration, email/SMTP, required actions, password/brute force, session and TOTP: https://www.keycloak.org/docs/latest/server_admin/ ; OIDC https://www.keycloak.org/securing-apps/oidc-layers ; Admin REST https://www.keycloak.org/docs-api/latest/rest-api/ .
- Docker compose defines only three containers, identity-db, mailpit and keycloak, on one internal Docker network. Identity DB and SMTP publish NO ports. Keycloak port 8180 and Mailpit API port 8025 bind only runner 127.0.0.1. Actual network inspection and an explicit outbound 1.1.1.1:443 TCP probe inside the container MUST prove egress denied; unexpected connection makes CI fail. Browser aborts non-loopback HTTP; Python helper requires loopback. This does not prove github.com runner host network is isolated; it proves ephemeral services cannot send mail/traffic externally. No real SMTP message is sent.
- Synthetic passwords generated in runner temp (0600), users first@example.test, second@example.test, realm-operator@example.test; browser flows are real Keycloak Authorization Code+PKCE, not fake tokens/override. Temp SMTP contents and Keycloak database removed after test, no secrets in logs/artifacts. Sanitized report ONLY includes case IDs/PASS/FAIL, versions and non-sensitive observed revocation types. Workflow minimal permissions contents:read, timeout 30 min, no continue-on-error; fixed images and dependency versions, no Mac install, public service, deploy or provider purchase.

Owned file set for this working push:
infra/auth-ci/compose.yml
infra/auth-ci/README.md
tests/phase3/integration/auth_idp/support.py
tests/phase3/integration/auth_idp/network_guard.py
tests/phase3/integration/auth_idp/evaluate.py
.github/workflows/auth-idp.yml
coordination/tasks/AGENT-API-AUTH-IDP-01.md (THIS file)

No changes to apps/api/**, apps/web/**, infra/postgres/**, DB History source, Root, product schemas, shared checklist, ADR 0004 or other task ledgers.

## IDP-CI-01-C — planned executable positive and negative matrix (first push NOT_RUN)

IDP-00 realm policy, password-strength/brute-force, OIDC discovery/issuer on actual Keycloak and PostgreSQL.
IDP-01 two browser email/password self-registrations; verified-email gate with NO OIDC callback before email verification.
IDP-02 real SMTP messages captured locally; verify real action links, test no new privilege from replay.
IDP-03 two independent real browser OIDC authorization code+PKCE logins; separate stable OIDC subjects.
IDP-04 old refresh token succeeds BEFORE revocation.
IDP-05 authorization code one-time exchange, replay 400.
IDP-06 Forgot Password UI -> email reset -> password change, single-use link.
IDP-07/08 old credential denied, new credential accepted.
IDP-09 one-second action token used after expiry rejected.
IDP-10/11 manager required action TOTP enrollment, no password-only bypass for configured manager and wrong OTP rejected.
IDP-12/15 minimum manager role realm-management view-users, ordinary user forbidden Admin REST.
IDP-13 ID token real JWKS signature, issuer/audience/expiry/nonce; malformed signature and nonce rejected.
IDP-14 unregistered redirect refused by IdP.
IDP-16 distinguish old refresh HTTP, UserInfo HTTP and signed-but-not-immediately-expired JWT after real IdP admin-initiated session logout. Do not claim access token or product session revoked by JWT signature alone.
IDP-17 managerial minimal role, explicitly no blanket product access.
All are NOT_RUN until an actual per-SHA GitHub CI succeeds; test IDs are not canonical P3M work counts. Administrator MFA via TOTP on these sampled logins does not prove no post-credential-removal bypass; BFF next package needs explicit security ACR/AMR and admin step-up.

Commands proposed in workflow (no local runtime executed):
docker compose --env-file $RUNNER_TEMP/idp-ci.env -f infra/auth-ci/compose.yml up -d
python tests/phase3/integration/auth_idp/network_guard.py
python -m compileall -q tests/phase3/integration/auth_idp
python tests/phase3/integration/auth_idp/evaluate.py
docker compose --env-file $RUNNER_TEMP/idp-ci.env -f infra/auth-ci/compose.yml down --volumes --remove-orphans

CI evidence and failures MUST be appended under new subheading of THIS cumulative file with Run, actual tested source SHA, exact PASS/FAIL/limitations and artifact. Never call green CI in advance. If CI fails, fix only authorized paths and keep old evidence. No workflow_dispatch, external secrets, paid provider, outbound email, product Auth integration, database migrations or user data.

## IDP-CI-01-D — next package boundary; NOT_IMPLEMENTED

After supervisor review, independent future Next BFF server session/login/logout and CSRF, true trusted BFF→FastAPI identity, stable issuer+subject→immutable internal owner, per-transaction History RLS and real user/admin authorization will require new API/UI/DB/Shared contracts authorization. Keycloak local test success proves only configured candidate capability; does NOT provide app Auth, correct country availability or email delivery, production HA/TLS/backup/monitoring or product access. Logout/reset cannot be assumed to revoke independently issued access JWT or a future BFF session; proposed later tests must separately verify access/refresh/IdP session and explicit product session revocation.

Implemented: CI test harness/source only.
Tested: PENDING_GITHUB_CI at first working push.
Accepted: NONE / SUPERVISOR_PENDING.


## IDP-CI-01-E — initial workflow-level failure before Jobs

Actual first push SHA: 5e0c72d90d8f27a489119f802cd6d68e05749f4e. GitHub Actions Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42521201718 completed FAILURE with ZERO jobs and ZERO check runs. Consequently there is NO actual Docker/Keycloak/Chromium/SMTP test output and no PASS claim for this revision. Likely workflow expression-scope issue: job-level PLAYWRIGHT_BROWSERS_PATH used runner.temp, which is not supported in the job-level env context. Restrict correction to dropping this optional variable and use Playwright's standard runner cache path. No test assertion, product file or scope changed. Real outcome is pending next CI. The failure is retained, not hidden.


## IDP-CI-01-F — real second CI startup failure, no IDP tests executed

Tested config/workflow SHA 2338d2e3a19b351f14ce3d17222699a7da7516e6, GitHub push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42521346176 completed FAILURE. GitHub logs confirm Python/Chromium and test dependency installation succeeded; ephemeral PostgreSQL 17.11, Mailpit v1.32.0 and Keycloak 26.8.2 images all pulled; three containers created and started, DB health check passed. However the combined localhost readiness condition (Keycloak master discovery AND Mailpit REST info) failed after 90 iterations (~270 seconds). No actual per-provider/registration/SMTP/browser test executed; no token or mailbox output in logs/artifacts; teardown executed, artifact upload correctly reported no report.json. This does not distinguish whether one HTTP endpoint was inaccessible or Keycloak startup failed. No success is claimed.

Narrow correction: workflow-only nonsecret readiness diagnostics: numeric HTTP status for fixed loopback discovery and Mailpit info (never response body/URL with bearer token), and Docker container running status only (never logs, image env, passwords or mail). On next Run identify exact failure and adjust isolation topology or readiness check without disabling internal network or opening public ports. Record this failure in the same cumulative mission file; all external/product/Auth gates remain untested.


## IDP-CI-01-G — real host-readiness evidence and internal-network correction

The next real run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42521929869 tested source SHA 978692dcb731611f2239b7d01dad61a15bdf0149 and FAILED at startup. Diagnostic values from actual CI: both Keycloak discovery localhost port 8180 and Mailpit API localhost port 8025 reported HTTP 000 after 90 loops. All three containers (keycloak, mailpit, identity-db) were RUNNING, including previously observed healthy DB. The Docker-only internal network had intentionally eliminated host connectivity to BOTH published ports. No CI integration tests, email operations or browser assertions ran. Teardown PASS. No service or sensitive logs were leaked or uploaded. This is a topology/test placement defect, NOT evidence that Keycloak itself was broken.

Fix preserving *stronger* network isolation: do NOT expose a second egress-connected bridge or relax internal:true. Remove ALL host port publishing. Change Keycloak hostname to internal DNS http://keycloak:8080; Mailpit API reachable only as mailpit:8025. Build a version-pinned Playwright Python container image (mcr.microsoft.com/playwright/python:v1.64.1-noble plus pinned Python packages) on the disposable GitHub runner BEFORE locking service egress; run readiness, actual Chromium and stdlib HTTP callback IN THAT VERY SAME authidpci_authisolated Docker network with no published service port. The callback only binds runner-container loopback 127.0.0.1:8765; no public identity selector or product endpoint. All external TCP/SMTP remain denied; explicit Docker.Internal==true and actual egress probes from BOTH identity DB and browser runner must fail, and host-side network_guard requires exactly zero published ports for all three services. Tool downloads in image build are permitted while building, but runtime is internal-only. Mailpit message bodies and tokens remain unexported; report.json remains the sole sanitized artifact.

New exact run sequence: docker build -f infra/auth-ci/Dockerfile.test-runner -t auth-idp-runner:ci infra/auth-ci; docker compose --env-file "$RUNNER_TEMP/idp-ci.env" -f infra/auth-ci/compose.yml up -d; docker run --rm --network authidpci_authisolated auth-idp-runner:ci python [internal HTTP readiness probe]; python tests/phase3/integration/auth_idp/network_guard.py; docker run --rm --network authidpci_authisolated ... auth-idp-runner:ci python /suite/evaluate.py (readonly mounted tests and credentials; only sanitized report directory writable); unconditional docker compose down --volumes --remove-orphans. No Mac install, code/DB/API/UI/Auth product/Root/shared checklist edit.

Versions: Keycloak 26.8.2, PostgreSQL 17.11, Mailpit v1.32.0 unchanged; official Microsoft Playwright Python image v1.64.1-noble documented https://playwright.dev/python/docs/docker and matched to Python Playwright 1.64.1. Image-runner Python version must be recorded from actual runtime, not guessed. Full IdP tests REMAIN NOT_RUN pending new CI.


## IDP-CI-01-H — real internal-network tests passed; test runner file permission failure

On exact SHA c41d72c4963d48cc3ef80fffb60ca08ff5119293, BOTH GitHub runs https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42522775585 (push) and https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42522780206 (PR) completed FAILURE at Python IdP integration, after successful image build, all three service readiness probes and network checks. CI explicitly printed INTERNAL_IDP_AND_MAIL_READINESS_PASS, ISOLATED_NETWORK_INSPECT_PASS, and NETWORK_GUARD_PASS (all containers internally connected, zero published ports, actual egress denied from DB AND Chromium runner). This fixes the prior topology/readiness failure and validates real connectivity INSIDE the internal network, but NOT OIDC functionality yet.

The Python integration container had no file permission for runner-owned chmod-0600 /run/idp.env and no write permission to runner-owned mode-0700 evidence directory. The root cause is mismatched mounted-file UID/GID combined with --cap-drop=ALL; Python failed at Admin credentials() before an IdP test method, then safe_report also failed with PermissionError. The traceback included only static file paths (no passwords/tokens/cookies), but future errors must remain sanitized. Both runs tore down identity service/network/volumes successfully. No artifact produced, no identity case PASS.

Narrow correction: run test-only Chromium container with explicit --user "$(id -u):$(id -g)" from the host runner (matching the owner of both files), retaining cap-drop=ALL, no-new-privileges, internal-only network and read-only credential/suite bind mounts. Wrap sanitized-report write on failure so no secondary Python traceback is exposed if permissions fail again. No public port, networking exception, credential chmod relaxation, product code or data modified. Next GitHub CI needed; source runtime test status remains PENDING.


## IDP-CI-01-I — actual realm PASS; browser Timeout and safe stage markers

Both runs on exact source SHA 1edde528e0b302899c3e61ca34e6deb85803918f FAILED at Python OIDC/SMTP evaluation, after infrastructure readiness/internal egress denial PASS. Push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42523072557 and PR https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42523076568 uploaded sanitized report.json (artifact IDs 13633513609 and 13634520569) and cleaned up. Real IDP-00-realm-policy-and-OIDC-discovery PASS: actual Keycloak admin realm, temporary identity PostgreSQL, explicit password/brute-force policy and OIDC discovery. Approximately ten seconds later the first browser registration step timed out (Python TimeoutError) without completing IDP-01; no email verify, OIDC login, TOTP, token/logout tests can be called PASS. Not a production Auth defect diagnosis.

Narrow test-only diagnostic: set CURRENT to fixed safe stage names around actual authorization navigation, login form, registration link/form/submit, SMTP capture, action-token visit and database verification state. Report only constant stage labels and exception type, never browser URL/page HTML/action link/token/password/cookie/PII. No original test checks removed and no external network or public endpoint.
