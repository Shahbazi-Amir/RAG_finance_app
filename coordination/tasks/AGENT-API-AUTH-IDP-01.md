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


## IDP-CI-01-J — confirmed current browser failure and registration locator correction

Preflight 2026-11-09: Actual branch HEAD 34a6d0d2c58efd877ae7f77526c4a50ff513e0c5, existing Draft PR #13 (open/unmerged), main and Starting SHA both 4831ff90470028abab1dd6dd78834fcf3446a716, PR #12 merged. No parallel branch, no task restart and no new unowned file. AGENTS.md, ownership, ADR 0004 and canonical M05 activities A01..A10 read. Only existing mission files touched.

Real failed PUSH Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42523434551 and PR Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42523438805 tested exactly 34a6d0d2c58efd877ae7f77526c4a50ff513e0c5 and both concluded FAILURE. Internal network readiness, actual egress-denial probes, isolated PostgreSQL/Keycloak/Mailpit startup and IDP-00 realm/explicit policy/OIDC discovery PASS. Registration step failed with sanitized stage=browser-registration-link, TimeoutError. The existing test CSS used plural `a[href*="/registrations"]` while the Keycloak login registration action is singular /login-actions/registration and the server_admin guide identifies the registration link. Changed one test-only selector to target `#kc-registration a[href*="registration"]`. No original assertion removed, browser/realm/session/token credentials/URLs never printed. Later IDP-01..17 NOT_RUN on this failed SHA. This is a locator hypothesis until CI validates it, not a blanket claim of Keycloak error.

Official sources checked at 2026-11-09: https://www.keycloak.org/2026/11/keycloak-2682-released (26.8.2 released 2026-11-05); https://www.keycloak.org/server/db (PostgreSQL 17.x supported); https://www.keycloak.org/docs/latest/server_admin/ (self-registration, verification and reset); https://github.com/axllent/mailpit/releases (v1.32.0); test runner Playwright 1.64.1 remains pinned. No external SMTP, product Auth, model, production claim or public host.

Implemented=TEST_LOCATOR_CORRECTION; Tested=CI_PENDING_FOR_NEW_SHA; Accepted=SUPERVISOR_PENDING. GitHub Actions CI runs on the same branch, keep PR Draft and do not merge.


## IDP-CI-01-K — registration link fixed, actual registration form remains unverified

On source SHA 96bb3e2ef4d2f09b90b8a53fdbc0903b52bbecd1, real push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42525431121 and PR Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42525435637 completed FAILURE at CI-only browser stage=browser-registration-form category=TimeoutError. Internal-only topology/egress guard and IDP-00 realm/policy/OIDC discovery remained PASS; unlike prior SHA the registration link did trigger navigation. This is progress in test navigation, but registration/signup, email, code, MFA and revocation are NOT_PASS.

Narrow evidence-gathering correction: inspect only booleans/counts of Keycloak registration action path, known form IDs/actions and generic error container and place them in sanitized report.json; no exact URL/query, HTML, form values, email, passwords, cookies or token. Broaden the registration form selector to an actual form with registration action. Any further diagnosis must be based on next observed GitHub Run; do not invent expected form state. Same strict internal network, pinned candidate versions and cleanup. Implemented=DIAGNOSTIC_ONLY; Tested=NEW_RUN_PENDING; Accepted=SUPERVISOR_PENDING.


## IDP-CI-01-L — actual zero-form registration screen, response-only diagnostics

Push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42525680621 (tested SHA ce4cef6b6166706994055706d41af9f64b4ad36b) completed FAILURE at browser-registration-form after internal network/egress guard and IDP-00 PASS. The actual sanitized report artifact 13635426019 was downloaded and opened: on_registration_action_path=true, kc_register_form_count=0, any_form_count=0, login_form_count=0, registration_form_action_count=0, page_error_box_count=0. This proves browser reached the registration action path but *no HTML form* appeared; merely changing selector cannot fix it. No further identity scenario PASS. No raw page, link, token, email or password was disclosed.

Follow-up test-only safe diagnostic: collect numerical HTTP status of registration-action responses and fixed-class booleans for generic error/register/login/email text after DOM readiness. Report only counts, booleans and body-length bucket, never text/URL/HTML/cookies/codes/PII. Preserve version-pinned Keycloak 26.8.2 / identity PostgreSQL 17.11 / Mailpit 1.32.0 and egress-denied network. A real run is needed to diagnose next. Implemented=DIAGNOSTIC; Tested=NEXT_CI_PENDING; Accepted=SUPERVISOR_PENDING.


## IDP-CI-01-M — distinguish form from visible input

The real GitHub Push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42525984758 tested 9c7b97b96c445c4732c8744d81077713e2268d25 and concluded FAILURE at browser-registration-form after internal egress-denied readiness and IDP-00 PASS. Sanitized artifact 13635481919 was opened: registration HTTP response 200; kc_register_form_count=1 and any_form_count=1; registration path valid, no generic error container, but the assertion that the FORM is visible timed out. No registration/email/OIDC/MFA/revocation success was obtained. New test-only check stores only three booleans (form_visible, email_visible, password_visible), then asserts visibility of the actual email INPUT instead of the form container. No sensitive URL, content, password or token is logged. A new CI run is required, and no functional test can be declared PASS until then. Implemented=TEST_DIAGNOSTIC; Tested=PENDING; Accepted=PENDING. No product/Auth/RLS/other paths touched.


## IDP-CI-01-N — Keycloak 26.8 default verify-first registration flow identified from real evidence

Actual PUSH Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42526300702 tested 6e6702e040e04c1a6c4f5333b1aabf372f1ccacc and completed FAILURE in browser-registration-form. Sanitized artifact 13635675926 was downloaded and inspected. Confirmed real Keycloak 26.8.2 registration response HTTP 200, register form exists and IS visible, email input visible, **password input not visible**, no page/server error. IDP-00 and internal network/egress guard PASS, but IDP-01+ remain untested/failed; zero real verified accounts or MFA/token/revocation success claimed.

Root cause confirmed against OFFICIAL Keycloak 26.8.0 Administration Guide https://www.keycloak.org/docs/26.8.0/server_admin/ section "Clarification on verify email", lines 2633-2637: with self-registration and Verify Email both enabled, password is deliberately omitted from initial registration and user sets it after verifying email. The "Always set password on register form" compatibility option is deprecated and not selected. This explains the absent password input (not outage, hidden CSS or a failed HTTP response).

Narrow scope fix: preserve real browser self-register with email/profile first, keep mandatory SMTP-captured verify-email and no unverified callback, then explicitly require password setup in the post-verification Keycloak browser screen with the same synthetic password; only afterwards may a new independent Code+PKCE login be tested. Retain original replay and identity assertions. No deprecated early-password switch, admin-set password shortcut, product Auth/API, public endpoint, outbound mail, Keycloak version or DB change. New actual CI must confirm that post-email form and subsequent tests work. Implemented=CORRECT_VERIFY_FIRST_FLOW; Tested=NEW_RUN_PENDING; Accepted=PENDING.


## IDP-CI-01-O — verified self-register and email verification, password-setup transition still failing

Push GitHub Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42526628676 tested code SHA a0ac9a5b85933a1d856ffcc853c2e942883a6eb8, completed FAILURE only after actual Keycloak internal discovery, network guard, and real IDP-01 register/unverified gate PASS and IDP-02 verify-email-via-local-SMTP PASS. The actual sanitized report artifact 13635233147 was downloaded/inspected and contains IDP-00/01/02=PASS, then stage post-verification-set-password=FAIL. Registration used the **official verify-email-first Keycloak 26.8 behavior**; no password was collected before verified email. However no visible password-setup form appeared directly on the first verification-link landing screen; no successful password login/OIDC/JWT/OTP/revocation result. No real emails sent, callback never product BFF.

Narrow test follow-up: if the immediately displayed verification page lacks a password form, issue real Keycloak Admin REST execute-actions-email UPDATE_PASSWORD for that same newly verified synthetic user, capture its message in internal-only Mailpit, follow that **second local action email** in Chromium and require password update form. This is a **separately sent password-action email**, NOT proof that the initial verify page automatically completed password setup. Record the method as a sanitized constant, preserve no real SMTP and all negative assertions. This method verifies Keycloak capacity; whether seamless self-service signup can omit the second email remains open for future evaluation. Official Keycloak 26.8 Admin guide https://www.keycloak.org/docs/26.8.0/server_admin/ documents the UPDATE_PASSWORD action email and verification-first flow. Next CI must re-test; no claim of later cases. Implemented=ALTERNATE_LOCAL_ACTION_FLOW; Tested=PENDING_NEW_SHA; Accepted=PENDING.


## IDP-CI-01-P — genuine local UPDATE_PASSWORD case failed, narrowed timing stages

Push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42526901898 tested a141aa3d0a51d4370f6e695ea3e42891a77ae8e6 and concluded FAILURE, sanitized artifact 13635493686 downloaded and read. IDP-00 policy/discovery, IDP-01 self-register and unverified gate, IDP-02 local SMTP verify-email still PASS. Post-verification password setup still FAIL, even after the proposed second real Keycloak execute-actions-email UPDATE_PASSWORD link; no IDP-02A or successful login/OIDC/MFA/logout/revocation. This run did not disclose sensitive data; network egress restriction and teardown remained intact. Next patch records only static stage names for request, SMTP capture, browser link, form visibility, fill and submit so failure can be located without dumping URLs/forms/passwords/links/codes. No assertions removed, no auto-pass, no product changes. Implemented=SAFE_STAGE_DIAGNOSTICS; Tested=NEXT_CI_PENDING; Accepted=PENDING.


## IDP-CI-01-Q — real password-action form and submit selector mismatch

Actual push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42527174208 on exact SHA 33aa68f362242e2336b420da5a50643ebbaed156 completed FAILURE after IDP-00/01/02 all PASS. Last sanitized runtime log: stage=password-action-submit category=TimeoutError, proving Keycloak did return a password update page, both new-password fields were visible and filled via real browser, but old submit locator missed the button. No password-setup completion or later OIDC/MFA/revocation claims. Official Keycloak login-update-password.ftl template (source https://github.com/keycloak/keycloak/blob/main/themes/src/main/resources/theme/keycloak.v2/login/login-update-password.ftl ) uses button id kc-submit rather than input[type=submit] in the v2 theme. Adjust only the submit locator to include #kc-submit/button alongside old input fallback. Original validation and CI-only/network/sanitized boundaries remain. Tested after fix=CI_PENDING, not success yet.


## IDP-CI-01-R — real first OIDC PKCE/refresh/redirect checks passed; admin negative HTTP nuance

Push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42527401876 on exact 0b72352b1e9008b7d68fb2deef72440fcd38a06e reached real OIDC cases and FAILED after: IDP-00/01/02/02A (both synthetic user registration+email-verified password via local-only action email), IDP-03 two independent Authorization Code+S256 PKCE browser logins, IDP-04 refresh before logout, IDP-05 replayed authorization code denied, IDP-13 ID token JWKS signature/iss/aud/nonce negative, IDP-14 unregistered redirect denied: all log PASS. The next source line asserts ordinary user Admin REST status must be EXACT 403, but Keycloak can also deny with 401 if the ordinary-user access token has wrong Admin REST audience; last safe stage remained browser-login-form-render so only assertion-category failure was observable. No manager/MFA/logout/expired/reset success yet. Correct the narrow negative test to require 401 OR 403 (never 200/2xx), record only numeric response status in sanitized report, do NOT disable authorization or create admin grants. Candidate remains CI-only. Test revised source needs a new real CI run. Implemented=NEGATIVE_ADMIN_DENIAL_STATUS_CORRECTION; Tested=NEW_CI_PENDING; Accepted=PENDING.


## IDP-CI-01-S — real OIDC and logout PASS; reset-password stage needs diagnosis

Real Push GitHub Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42527620498 tested 887bf9e34b6d0182c7786d43622ca3e3108a2a38 and concluded FAILURE only later in Python browser suite. Sanitized CI logs show IDP-00, 01, 02, 02A, 03, 04, 05, 13, 14, 15, 16 PASS, for actual Keycloak 26.8.2/identity PostgreSQL 17.11/Mailpit 1.32.0 on internal-only egress-denied CI, including two independent real OIDC logins, verified mail, password setup, successful pre-logout refresh, denied replay, signature and redirect negatives, denied ordinary user Admin REST and distinct logout observations. No later Forgot/Reset, expiry or admin MFA test PASS. After IDP16, reset flow timed out with the stale general marker browser-login-form-render; result must not be relabeled successful.

Narrow correction in same test only: set fixed safe CURRENT stage names around real Keycloak forgot-password link, request screen, SMTP capture, action link, password submit/consumed replay, expired-link and manager MFA/role steps. Also extend two reset-submit selectors to accept the official Keycloak v2 #kc-submit button while preserving old input fallback. No raw action URL/credentials/HTML, no weakened assertion, no product session/CSRF/RLS claims. Await CI for exact cause and behavior. Implemented=RESET_AND_MFA_SAFE_DIAGNOSTICS; Tested=NEXT_CI_PENDING; Accepted=PENDING.


## IDP-CI-01-T — official Keycloak v2 Forgot Password form button

Real push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42527859390 on SHA 3346100a56cda683df7de2a250282ca3164e5bf9 completed FAILURE only at reset-request-submit stage=TimeoutError, after all IDP-00/01/02/02A/03/04/05/13/14/15/16 logged PASS. This accurately localizes failure to click of Forgot Password form submit; email message was not yet asserted for this reset test. Official Keycloak v2 login-reset-password.ftl source https://github.com/keycloak/keycloak/blob/main/themes/src/main/resources/theme/keycloak.v2/login/login-reset-password.ftl has form id=kc-reset-password-form and **button id=kc-form-buttons**. Previous selector only accepted input[type=submit] or #kc-submit, neither of which matches v2. Narrow UI test correction targets the actual form-scoped #kc-form-buttons button, with button/input fallbacks. No test assertion removed, no product code/real mail/public endpoint. Tested=NEXT_GITHUB_CI_PENDING; Accepted=PENDING.


## IDP-CI-01-U — Forgot/Reset PASS, distinct flow callback clarification

Real push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42528115806 tested SHA 39f600e37cadc37ff1ac555a07c95fccfda24c35, completed FAILURE in browser suite **after** IDP-06-forgot-reset-once PASS. Previously IDP-00/01/02/02A/03/04/05/13/14/15/16 also PASS. The next test was old-password rejection; failure was type AssertionError with stale global stage browser-login-form-render, not a validated old-password acceptance. Successful password reset may generate a callback for the original reset-initiating OIDC flow; the shared callback queue must not be mistaken for a new successful invalid-password attempt.

Correction: after successful reset/consumed-link test, inspect and drain any *original* callback, requiring its state to match the original reset flow's nonce-bound state, then start an independent old-password negative login with a fresh authorization context. If a callback belongs to another flow, fail closed. Product Auth, codes and session semantics unchanged. Actual old-password/new-password and expiry/MFA still NOT_PASS until next CI. No token or state value published. Implemented=FLOW_DISAMBIGUATION; Tested=PENDING; Accepted=PENDING.


## IDP-CI-01-V — negative old-password login must scope callback to its state

On exact SHA dce2a930269542ff0819d2f6b9c09c7c6ac4ae15, real GitHub Actions push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42528362961 concluded FAILURE in invalid-password login immediately after IDP-06-forgot-reset-once PASS; prior IDP-00/01/02/02A/03/04/05/13/14/15/16 also PASS. Actual failure category AssertionError but the previous stage label remained browser-login-form-render, so root cause was NOT established. An IdP callback from an earlier unrelated reset flow must NOT be confused with a successful auth-code callback from an invalid-password attempt; discarding ALL callback evidence would also be wrong.

Changed only the test's negative login helper: explicitly require a visible login form AND Keycloak error indicator after rejected password, then inspect any pending callback's state and fail if any equals the current invalid flow's cryptographically generated state. Ignore prior unrelated flow callbacks without exchanging their codes; record fixed stage markers for form/error/callback to enable a precise next-run diagnosis. This is stronger ownership evidence, not allowing invalid password to log in. No URL/code/token/password printed. Next CI required; IDP-07 old password and IDP-08 new password, expired link and MFA still NOT_PASS. Implemented=SCOPED_NEGATIVE_LOGIN; Tested=NEW_RUN_PENDING; Accepted=PENDING.


## IDP-CI-01-W — rejected old password must be evidenced by no current-flow code, not CSS class

Actual GitHub Push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42528641316 on f35adf197cf8077a66e4368577a81a3923e577cd finished FAILURE at stage=invalid-password-error-visible, category AssertionError after IDP-06 reset PASS and all prior IDP-00/01/02/02A/03/04/05/13/14/15/16 PASS. The real login form was visible after the old-password attempt; the test's legacy CSS-only error-message selector failed. No IDP-07 negative PASS is claimed, and Keycloak v2 theme presentation cannot be inferred from a missing legacy selector.

Corrected test to require actual navigation settled, login form still visible and browser not at callback, then examine the callback queue and reject ANY new code with the old-password attempt's exact cryptographically random state; stale callbacks from other flows are irrelevant. Error-text visibility is reported as a BOOLEAN nonsecret fact only, not used as a substitute for code denial. This preserves stricter outcome security while avoiding coupling to a theme CSS name. No token/code/password/URL contents logged. New CI remains required. Implemented=REASONABLE_NEGATIVE_OIDC_OUTCOME_TEST; Tested=CI_PENDING; Accepted=PENDING.


## IDP-CI-01-X — valid recovery/password and MFA enrollment verified, bad→good OTP flow problem

Real push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42528928714 on a5d662d78bd24a59e9f358abb1856cd5f57367b6 concluded FAILURE late in real Chromium. Actual log PASS: IDP-00/01/02/02A for both users; IDP-03/04/05/13/14/15/16 OIDC/PKCE/refresh/replay/issuer/JWT/Admin deny/logout; IDP-06/07/08/09 real local-only password Reset + old password denied/new password accepted + expired link denied; IDP-10 manager required TOTP setup/no immediate password-only callback. Failure at stage=manager-mfa-valid-otp-callback TimeoutError after an intentionally wrong OTP attempt in SAME browser login flow. IDP-11, IDP-12, IDP-17 not PASS; candidate evaluation still incomplete.

Narrow test correction: after proving wrong OTP keeps form and no auth callback, CLOSE that failed authentication context and use a completely new authorization state, nonce and PKCE verifier for positive manager login with valid OTP. A rejected MFA attempt may invalidate its current authentication context. This does NOT weaken password-only or wrong-OTP negative conditions and does not inject tokens/MFA/override owner. Run again; no fixed result asserted ahead. Implemented=MFA_FRESH_VALID_FLOW; Tested=CI_PENDING; Accepted=PENDING.


## IDP-CI-01-Y — manager OTP replay counter hypothesis after two real failed runs

Both independent actual Runs on source SHA 34f7a40b4a237c2bb8bf30779fde6be2d9299f5f: Push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42529223808 and PR https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42529228398 concluded FAILURE only at manager-mfa-valid-otp-callback (TimeoutError) despite *fresh* Authorization Code+PKCE/login for positive OTP. IDP-00/01/02/02A/03/04/05/06/07/08/09/10/13/14/15/16 all reported PASS. Therefore reusing a bad-OTP login flow was NOT the cause; that prior hypothesis was refuted. IDP-11/12/17 still NOT_PASS.

New narrow hypothesis: Keycloak replay avoidance may reject a TOTP code from the *same 30-second time-step* used at initial enrollment even in a later new login. The test now captures only the numerical counter index in RAM at enrollment, waits with a bounded 35-second ceiling for a later counter before generating and submitting the positive OTP, checks the resulting OTP is NOT the previously consumed enrollment OTP, and reports only a boolean counter advance (never seed, OTP, token, timestamp or user data). Keep wrong OTP and password-only denial assertions unchanged. The next CI run must establish/refute this hypothesis; no asserted PASS yet. No product/DB/code/schema/real email or network changes. Implemented=TIMESTEP_REPLAY_AWARE_TEST; Tested=NEXT_RUN_PENDING; Accepted=PENDING.


## IDP-CI-01-Z — correct TOTP replay counter proved; manager REST role still unverified

Actual isolated GitHub push Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42529615390 tested 5e25db454f99be5f9d4aabedf70478551e34a52a and completed FAILURE after Keycloak/SMTP/internal-network checks and all prior IdP cases PASS. Crucial new **IDP-11-manager-mfa-no-password-only-bypass PASS** with manager valid OTP from a *new counter* after enrollment and wrong OTP denied. This confirms same-timestep OTP replay avoidance hypothesis for the tested flow. Last failure: AssertionError at stale manager-mfa-valid-otp-callback marker after IDP-11, likely manager realm-management view-users Admin REST assertion; IDP-12 and IDP-17 NOT_PASS and exact status cannot be inferred yet.

Narrow test-only diagnostic: record only numeric Admin REST HTTP status and booleans for client roles view-users/query-users and realm-management audience in parsed synthetic manager access JWT (no token, claims identifiers or role lists logged); set distinct stage manager-minimal-admin-rest, retain required 200 assertion and no unbounded realm-admin grant. Next CI required; no false role acceptance. No product BFF/RLS/Auth or external email. Implemented=ROLE_DIAGNOSTIC; Tested=PENDING; Accepted=PENDING.


## IDP-CI-01-AA — verified Keycloak 26.8.2 Admin REST audience requirement (2026-11-09)

Handoff checked live main = starting 4831ff90470028abab1dd6dd78834fcf3446a716, existing unmerged Draft PR #13, branch agent/auth-idp-ci at 694a7548c5fe12df0bbaf2259cf9340a04a30d1c; eight changed files all in granted paths. No concurrent run, no parallel branch or PR. Existing task, AGENTS.md and ownership re-read. No change to product Auth/UI/API/PostgreSQL History/shared checklist. Source: references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md Module 05 P3M05-A06/A07/A08/A10; this remains IdP-only, not a canonical Gate PASS.

Real GitHub Actions Run https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42529894840 on EXACT tested SHA 694a7548c5fe12df0bbaf2259cf9340a04a30d1c: completed FAILURE. The disposable containers started, internal-only network/actual egress-denial passed, teardown and sanitized artifact ID 13636698417 succeeded. Real browser+SMTP+OIDC positive/negative cases IDP-00/01/02/02A/03/04/05/06/07/08/09/10/11/13/14/15/16 all PASS as labeled in report.json. Last stage manager-minimal-admin-rest FAIL: HTTP 401 (NOT 200); manager token had view-users/query-users client roles and a realm-management audience but no verified Admin REST audience or kc-admin-api scope. Thus IDP-12/17 NOT_PASS. No blanket permission granted and no acceptance from prior PASS labels.

Root cause corroborated by OFFICIAL Keycloak 26.8.2 upgrading guide https://www.keycloak.org/docs/26.8.2/upgrading/ : newly enforced Admin REST access-token audience PLUS special kc-admin-api scope; generic realm-management audience and roles alone are not enough. The prior 401 is consistent with that requirement. Do NOT switch the audience check off; do NOT grant realm-admin.

Narrow correction to existing CI-only Python helpers: attach built-in kc-admin-api scope as OPTIONAL to existing synthetic OIDC callback client, request it ONLY in the fresh successful manager+TOTP browser authorization, assert both actual scope and exact Admin REST URL in that real access token, retain the limited view-users role and existing 200 authorization requirement. Ordinary user OIDC remains without the optional scope and still must be denied Admin REST, with a new nonsecret boolean assertion. This is not a BFF/admin frontend/product privilege scheme. No token/claim values logged or persisted. Exact reproduction remains workflow command docker build; docker compose up; network_guard.py; docker run ... python /suite/evaluate.py; unconditional docker compose down. Static source checks are possible, but the new revision's end-to-end result is CI_PENDING until actual GitHub run; it must not be reported as PASS in advance.

Observed on prior successful IDP-16 step: admin-initiated IdP logout caused old refresh HTTP 400 and old UserInfo HTTP 401 while the old access JWT's local signature still verified before expiry (configured 180 seconds). No product BFF session, token introspection or after-reset refresh/session revocation was tested; those are explicit remaining checks. No real SMTP/delivery outside Docker or Iranian reachability verified. Implemented=OPTIONAL_ADMIN_API_SCOPE_NARROW_FIX; Tested=NEXT_GITHUB_RUN_PENDING; Accepted=SUPERVISOR_PENDING. Keep Draft; no merge.


## IDP-CI-01-AB — two real green CI runs; isolated candidate ready for independent review (2026-11-09)

Tested SOURCE SHA (not the later documentation-only checkpoint commit): 35b1607b13893cfc2012cf4b3e04b6f3406a120b. Baseline/main still 4831ff90470028abab1dd6dd78834fcf3446a716. Existing open unmerged Draft PR #13 on agent/auth-idp-ci, no parallel branch. This checkpoint records the real outcome of the preceding code+checkpoint commit. No changes to accepted API/History/UI/DB/Root/Schema/canonical checklist, no deployment or real users.

Actual GitHub Actions first-attempt COMPLETED/SUCCESS independently on the same tested SHA:
- push: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42611617511 (sanitized report artifact 13671270312)
- pull_request: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42611629862 (sanitized report artifact 13670207938)
- The inspected PUSH artifact report.json says overall PASS, current_stage completed; all labeled IDP cases PASS. All job steps SUCCESS including network_guard, the actual browser suite and unconditional teardown. Credentials and disposable Docker volume/network were cleaned. No raw email bodies, action links, cookies, tokens, authorization codes, passwords or OTP seeds are in the sanitized artifact.

Actual positive checks: IDP-00 Keycloak realm/discovery and configured length/digit/uppercase/special-character policy + brute-force settings; IDP-01 first/second synthetic browser registration; IDP-02 real local-only verification mail/action; IDP-02A separate locally captured UPDATE_PASSWORD email for verified users (do NOT claim a single-email signup UX); IDP-03 real independent Chromium OIDC Code+S256 PKCE for two different subjects; IDP-04 old refresh before logout returned HTTP 200; IDP-06 real Forgot/Reset and link consumption; IDP-08 new password login; IDP-10/11 manager required TOTP enrollment, then a fresh login with valid newer-counter TOTP; IDP-12 limited manager view-users Admin REST GET returned HTTP 200 with kc-admin-api scope and exact Admin REST audience. Note that the optional admin scope was explicitly requested ONLY by manager's positive flow and was not requested by ordinary user.

Actual negative checks: IDP-01 unverified email could not complete callback; IDP-02 verified action link replay produced no new OIDC code; IDP-05 authorization code replay denied; IDP-07 old password rejected after reset; IDP-09 expired password action denied; IDP-10/11 password-only and intentionally wrong TOTP failed to yield callback; IDP-13 forged JWT signature/wrong nonce rejected by JWT validator, issuer/audience/expiry checks on real signed ID tokens; IDP-14 unregistered redirect rejected; IDP-15 ordinary user's Admin REST GET returned HTTP 401 and no kc-admin-api scope was requested. The IDP-17 case reports a constrained configured realm-management view-users role, not product admin authorization nor an exhaustive negative mutation test. Configured password and brute-force policy were asserted, but behavioral lockout and weak-password form rejection were NOT independently exercised.

Source of previous 401 failure and bounded fix: Keycloak 26.8.2 officially requires BOTH built-in kc-admin-api scope and a special Admin REST URL audience, see https://www.keycloak.org/docs/26.8.2/upgrading/ . Earlier Run 42529894840 failed 401 despite view-users role and generic realm-management audience. Current test attaches kc-admin-api to CI callback client as OPTIONAL and requests it only on MFA manager's successful OIDC authorization; the report confirms admin_get_status=200, has_view_users_client_role=true, has_query_users_client_role=true, scope_has_kc_admin_api=true and audience_has_admin_rest_url=true. No disabled audience verification, no realm-admin grant, no access-token injection, no product change.

Actual logout observations (IDP-16): Keycloak bootstrap admin explicitly logged out the tested ordinary user's IdP session; old refresh returned HTTP 400; old UserInfo with the old access token returned HTTP 401; independently local JWT signature remained valid before expiry, configured access token lifespan 180 seconds. These are three different facts. Do NOT infer the bearer JWT's signature is revoked, or that future product BFF cookies have been invalidated. Token introspection and explicit IdP session-list comparison were not tested.

Actual reset observations: old credential rejected, new credential login succeeded, used link and expired link rejected. **Old refresh token, access-token UserInfo, IdP session-list behavior AFTER password reset NOT_TESTED**; this remains a separate required future verification, not a fabricated PASS. Browser end-session RP logout (as distinct from observed admin-initiated IdP session logout) also NOT_TESTED.

Security/isolation confirmed on both Runs: Keycloak quay.io/keycloak/keycloak:26.8.2, separate PostgreSQL identity DB postgres:17.11, mail-capture-only Mailpit ghcr.io/axllent/mailpit:v1.32.0, Playwright v1.64.1 Chromium; disposable Docker Internal=true and NO host port publishing; DB+test-runner actual outbound TCP probes failed as required, one isolated Docker network, real loopback callback only, Python client limited to internal DNS, no external SMTP, no production services, no install on Mac. Runner image tests code with pinned dependency versions; Python patch version inside image was not logged separately.

Fit assessment: Keycloak is a TECHNICALLY VIABLE ISOLATED SELF-HOSTED CANDIDATE for tested email verification/password recovery/OIDC PKCE/role/TOTP flows. This is NOT vendor selection, Auth product acceptance, security certification, HA/TLS/availability/hosting/Iran delivery verification or Production readiness. Pending employer/supervisor decisions: hosting region/provider, Iran legal/reachability, operations owner and patch/backup/monitoring budget, real SMTP choice and deliverability, approved product Auth architecture and user/admin policies.

Next separately authorized BFF/API + UI/DB integration package must implement trusted OIDC iss+sub -> immutable internal owner mapping and RLS under real user contexts, BFF server-only sessions and secure cookies/CSRF/session rotation, state/nonce/code exchange and token storage, logout and reset revocation across BFF+IdP+refresh+access, admin-only step-up and actual forbidden operations, negative stale/stolen cookie and cross-user tests, status/deletion after session revoke and telemetry redaction; separately strengthen behavioral password/brute-force tests and fully measure post-reset IdP token/session effects. NB23 draft input remains only contract_version + question; Module 00 and live engine remain blocked.

Precise status at review handoff: IMPLEMENTED=ISOLATED_IDP_TEST_HARNESS; TESTED=TWO_GREEN_GITHUB_CI_RUNS_ON_EXACT_SOURCE_SHA; ACCEPTED=NONE / SUPERVISOR_PENDING. Proposed delivery label READY_FOR_REVIEW — ISOLATED_IDP_EVALUATION. Keep PR DRAFT; DO NOT MERGE independently. This is P3M05 IDP candidate evidence only, not AUTH_PRODUCT_ACCEPTED or PRODUCTION_READY.

## IDP-CI-01-AC — limited follow-up A/B/C prepared, awaiting real CI (2026-11-09)

Supervisor-authorized continuation of SAME mission and same Draft PR #13.
Live GitHub branch and expected Starting HEAD both
59f0d63bea6ebdd144a990848eb4efda2aa0a160; main remains
4831ff90470028abab1dd6dd78834fcf3446a716. Last existing head CI
Run 42612169707 SUCCESS; no active run and no need to rebuild previous
test cases. Existing PR unchanged in ownership and scope. Sources/IDs:
references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md,
Module 05 P3M05-A02/A06/A07/A08/A10. C is isolated IdP password/lockout
behavior, not full product enforcement or M05 Gate.

Implement A:
- Reuse one real callback state validation function before actual Code exchange.
- Independent real browser Code+PKCE flows for modified and missing state
  reject via explicit assertion; original genuine Code must still exchange.
- Negative expected nonce, issuer and audience use REAL signed ID token and
  fail with explicit expected verification exceptions; positive expectations
  remain valid. Independent fresh Code with incorrect verifier is denied by
  real IdP token endpoint; original replay denial remains preserved.
Implement B:
- Independent pre-reset real browser OIDC login and silent SSO evidence
  in persistent original Chromium context. Actual password-reset flow is
  separate. After reset, probe original browser before refresh; individually
  collect old refresh status, old UserInfo status and local JWKS verification.
  Any surviving token or cookie is an OBSERVED limitation, not a test failure
  masked with admin-initiated logout. Strengthen previously observed logout
  UserInfo denial to a required explicit assertion.
Implement C:
- Synthetic third policy probe with its own local-only UPDATE_PASSWORD action,
  real weak-form rejection and compliant-password acceptance followed by
  independent login; actual failure counters, bounded attempts <=7,
  lockout (correct password denied), natural expiry and successful login
  verified via Keycloak read-only Attack Detection REST. No admin release.
  Change disposable CI realm waitIncrementSeconds 5->12 to make behavioral
  observation bounded; keep failureFactor 5 and max 30. This is neither a
  recommended production policy nor an unauthorized realm outside CI.

Changed mission paths ONLY:
tests/phase3/integration/auth_idp/evaluate.py,
tests/phase3/integration/auth_idp/support.py, infra/auth-ci/README.md,
and THIS single cumulative checkpoint. Existing workflow, Docker single
internal-only network, zero published ports, denied egress probes, Mailpit
local capture, 3-day sanitized artifacts, cleanup and no product edit
remain unchanged. Official Keycloak 26.8 Admin REST attack detection:
https://www.keycloak.org/docs-api/26.8.0/rest-api/index.html ;
official temporary brute-force account policy:
https://www.keycloak.org/docs/26.5.7/server_admin/ ;
Keycloak reset preserves internal-user session by default when same
authentication context is used (not an assumed result for this independent
old-context experiment):
https://www.keycloak.org/docs/26.8.0/server_admin/ .

Check command (in unchanged auth-idp.yml):
python -m compileall -q tests/phase3/integration/auth_idp ;
docker run --rm --network authidpci_authisolated ... python /suite/evaluate.py ;
automatic CI startup/network_guard, unconditional volume and credential teardown.
Result for THIS source revision: NOT_RUN pending real CI. Retain prior green
Runs 42611617511, 42611629862, 42612169707 on their actual prior SHAs.
Implemented=SOURCE_A_B_C_PREPARED; Tested=NEW_CI_PENDING; Accepted=NONE.
No Auth product, UI, History, PostgreSQL product, root, shared schema,
checklist, bank, model, Mac installation, real email or deployment.


## IDP-CI-01-AD — real A/B pass, C action-email stage failure, narrowed retest (2026-11-09)

Exact SOURCE SHA 3554a72e92cb27ed006e91025294838853f8fa54:
both new CI events failed (Push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42614945923 and PR https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42614953978).
PR sanitized artifact 13672252037 was downloaded and READ. Internal Keycloak/DB/Mailpit startup, actual denied egress and no published ports, and teardown PASS. All existing IDP cases through B and all new A01..A06 PASS. Specifically actual wrong/missing State rejected before Code exchange with the original valid Code still exchangeable; wrong nonce/issuer/audience rejected by actual JWT validator, separate fresh PKCE Code wrong verifier returned HTTP 400, and old Code replay was denied. A tested and PASS on this failed CI SHA (not full-suite acceptance).

B real pre-reset SSO proved through OIDC prompt=none. After actual reset of same synthetic user in another browser context, old ORIGINAL session's prompt=none OIDC authorization/code exchange succeeded without entering new password, old refresh returned HTTP 200, old UserInfo returned HTTP 200, locally verified JWT signature remained valid before configured 180-second expiry. These real observations show Keycloak configured reset did NOT revoke the preexisting SSO session or old access/refresh; this is a material next-package security requirement, not an AUTH_PRODUCT_ACCEPTED claim. Existing separate admin-initiated logout userinfo denial now ASSERTED HTTP 401/403 and real Run PASS; do not conflate with Reset. These B results were in the actual sanitized report with after_password_reset and revocation nonsecret fields. No credentials/tokens/cookies printed or uploaded.

C NOT_PASS: first live suite failed with sanitized stage policy-local-update-password-email, AssertionError, after IDP-09. That broad stage encompassed email retrieval, action-link extraction and first browser navigation, so exact root cause NOT_VERIFIED; do not falsely label missing message. Narrow fix: use existing already verified second synthetic user and already proven Mailpit UPDATE_PASSWORD action for actual weak vs strong form policy; independent third account with valid bootstrap synthetic password only for login-failure/temporary-lockout/natural-release tests. Add safe constant stage names around Mailpit retrieval, action-link extraction, password form (never log body or link). No sensitive data/real SMTP, product edit, user admin logout, admin lockout clear or disabled tests. Four original allowed task paths affected; same branch same PR, no new CI claim before running.

Exact method remains .github/workflows/auth-idp.yml, unchanged, with python compileall and actual Chromium/Mailpit/IdP Docker isolated integration; checkpoint cumulative. Implemented=C_ACTION_SOURCE_DIAGNOSTIC_NARROWED; Tested=A_B_PASS_ON_FIRST_SHA_C_FAILED; Accepted=NONE. Next: inspect rerun outcome on the NEW source SHA. Keep Draft, do NOT merge.


## IDP-CI-01-AE — C standalone action opened no form; use proven user-initiated Forgot/Reset

Two actual real CI Runs on source aeebdf8c1f6876d32057fb10ce5b73a3552e912d:
Push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42615811964
and PR https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42615822049
completed FAILURE. Actual push sanitized runtime reached IDP-A01..A06, B00,
B01 and all prior base cases through IDP-09 PASS. Failing stage
policy-action-browser-form AssertionError: local mail was captured and the
action token link parsed, but the standalone UPDATE_PASSWORD action landing
did not show a password input in a FRESH browser context. Exact DOM
reason unverified; no weak-password or Brute Force PASS claim. Isolation
and teardown PASS, sanitized logs contain no URLs/credentials.

Narrow workaround based on actual prior positive IDP-06 behavior, not bypass:
the SAME already verified synthetic second user initiates a normal browser
Forgot Password action, and follows its locally SMTP-captured reset link in
the SAME original browser authentication context (not the standalone
admin-created action). Weak and policy-compliant password are submitted on
that same real reset form, with explicit rejection then acceptance and
fresh browser login proofs. Separate synthetic third account still tests
bounded Brute Force. No Admin logout, admin lockout release, real SMTP,
other repository, product BFF/API/UI/History, root/schema/checklist or workflow
changes. Only evaluate.py, infra/auth-ci/README.md and this same cumulative
mission ledger updated. Tested on new revision=PENDING until real CI.

Run reproducible: unchanged automatic .github/workflows/auth-idp.yml with
docker build, docker compose, docker network inspection/egress denial,
python compileall, actual Chromium /suite/evaluate.py, always teardown,
sanitized artifact. Keep Draft PR #13, no merge. Implemented=C_BROWSER_RESET_SESSION_FIX;
Tested=A_B_PASS_PREVIOUS_SHA_C_PENDING; Accepted=NONE.


## IDP-CI-01-AF — FINAL verified A/B/C CI-only evidence, review handoff (2026-11-09)

Continuation Starting HEAD 59f0d63bea6ebdd144a990848eb4efda2aa0a160. Historical main and task base 4831ff90470028abab1dd6dd78834fcf3446a716. Same agent/auth-idp-ci branch, existing open Draft PR #13. Source: references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md, Module 05, P3M05-A02/A06/A07/A08/A10. No product Gate acceptance. Retain all prior historical failures, code and successes.

**Actual TESTED CODE SHA:** 835bd417ede49184caa93f36bbfcc8d7bac12a3a.
Both GitHub Actions first-attempt runs completed SUCCESS on this exact SHA:
- Push https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42616328060
- PR https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42616335573
- Downloaded and READ real sanitized PR artifact 13673196367: overall PASS, current_stage completed, IDP-A01..A06, B00/B01 and C01..C03 all PASS.
All CI job steps passed, including real Chromium/Keycloak+PostgreSQL identity-only/Mailpit, actual outbound TCP denial, no published ports, internal-only network, unconditional teardown and sanitized artifact. Keycloak 26.8.2, PostgreSQL 17.11, Mailpit 1.32.0, Playwright Chromium 1.64.1 pinned. No secret, email body, Code, Cookie, Token, password, reset URL or OTP seed logged or uploaded.

**A — real negative OIDC PASS:**
- A01 wrong State, A02 absent State, each applied to a DIFFERENT genuine browser-issued, still-unexchanged Code. Both rejected by same checked_callback_exchange function as positive flow with explicit STATE_MISMATCH BEFORE exchange, original legitimate Code still exchangeable.
- A03 bad expected nonce -> AssertionError, A04 bad expected issuer -> InvalidIssuerError, A05 bad expected audience -> InvalidAudienceError, all using a REAL signed Keycloak ID token and independently rechecked with correct expectations.
- A06 separate fresh browser Code with invalid PKCE S256 verifier -> real IdP token HTTP 400. Existing IDP-05 code replay HTTP 400 and invalid redirect, signature tamper checks remain PASS.
- No product callback, fake token, auth override or actor selector.

**B — measured genuine pre-reset old browser SSO and tokens PASS:**
- B00 independent actual OIDC login for the second synthetic user in retained Chromium context, prompt=none SSO with validated Code/PKCE/nonce BEFORE reset succeeded.
- After real Reset via separate verified-email browser flow, with NO admin logout, B01 prompt=none on SAME old browser cookie context still succeeded with actual OIDC Code/PKCE and validated signed ID token. Old refresh token returned HTTP 200, old UserInfo with old access returned HTTP 200, old access JWT locally passed JWKS signature+exp check before expiry. All actual observed values; negative revocation was NOT invented to obtain green CI. Browser SSO was probed before refresh to avoid changing session evidence.
- Separate IDP-16 ADMIN-INITIATED logout: old refresh HTTP 400 explicitly asserted, old UserInfo HTTP 401 explicitly asserted as 401/403 allowed denial, old signed access JWT signature still verifies before expiry (realm lifespan 180 seconds). Not equivalent to RP/BFF logout. Access token introspection NOT_RUN.
- **Security consequence:** In this tested Keycloak configuration password Reset DOES NOT invalidate the old browser SSO nor pre-reset access/refresh. Future BFF/API must explicitly handle and test all-session revocation on reset/logout and an independent old-JWT/token lifetime policy. No product BFF session exists in this evaluation.

**C — real password policy + brute-force behavior PASS:**
- C01 second verified synthetic user initiated REAL Forgot/Reset browser flow, local Mailpit action followed in the SAME authentication context; submitting weak password left reset form visible (rejected). Strong new randomly generated compliant password accepted; fresh OIDC login with new password succeeded, weak and previous valid password denied.
- Separate third synthetic policy-probe account with generated compliant initial password was used only for lockout. C02 five (5) bounded deliberate wrong-password Chromium logins (maximum allowed 7, spacing > quick-login threshold), Keycloak read-only Attack Detection REST observed numFailures=5 and disabled=true. Attempt with CORRECT password while disabled was denied.
- C03 status polling observed disabled=false naturally, WITHOUT admin clear or forced logout; fresh real OIDC login with correct password then succeeded. This is observed lockout + release, not sleep-only PASS. CI-only realm failureFactor=5, waitIncrementSeconds=12 seconds, maxFailureWaitSeconds=30 seconds; not a proposed production policy.
- Previous real source runs 42614945923/42614953978 (initial C broad action-email stage failure) and 42615811964/42615822049 (standalone admin action landing did not present password form) remain logged in earlier checkpoint sections. Final C uses proven browser-initiated Forgot/Reset, no lowered assertions.

**Implementation paths in continuation:** tests/phase3/integration/auth_idp/evaluate.py, tests/phase3/integration/auth_idp/support.py, infra/auth-ci/README.md and this SINGLE cumulative checkpoint. Existing Docker/Compose, .github/workflows/auth-idp.yml, product API/UI/History/DB, root/shared contracts, checklist and RAG_finance repo unchanged. Exact checks: unmodified GitHub Workflow auth-idp.yml invokes docker build, compose up, network_guard.py + denied egress probes, python -m compileall, real Docker Python /suite/evaluate.py, always compose down --volumes and sanitized artifact upload. No Mac installation, public port, real email, paid service, purchase or deployment.

Remaining separate next package: enforce CSRF and BFF server-side session/cookie rotation/revocation, issuer+subject-to-immutable-owner binding, token/session invalidation on reset/logout, real authenticated RLS, admin step-up and cross-user negative cases. Production TLS/HA, real SMTP deliverability, Iran reachability, provider/hosting/cost selection, security certification, NB23 live runtime and Module 00 remain blocked/out of scope. Keycloak is technically viable as an ISOLATED candidate only, not selected production Auth.

Implemented=LIMITED_A_B_C_CI_TESTS; Tested=TWO_REAL_GREEN_RUNS_ON_EXACT_SHA; Accepted=NONE / SUPERVISOR_PENDING. READY_FOR_REVIEW — ISOLATED_IDP_EVALUATION. Keep PR #13 DRAFT/UNMERGED. This is final TESTED CODE SHA; a later documentary-only final commit SHA must be reported separately.


## IDP-CI-01-AG — BND-IDP-02A independent standard Fresh Reauthentication / Reset probe (2026-11-10)

**Live preflight:** repository ONLY `Shahbazi-Amir/RAG_finance_app`; `main` live at EXACT Starting SHA `a29fae8392d6664926327e1ab2eeaa4a8b32f85d`. PR #20 `BFF-SERVICE-01` is CLOSED/MERGED with merge SHA exactly `a29fae8392d6664926327e1ab2eeaa4a8b32f85d`, accepted code HEAD `6f6c5a72ccd2e979e5eb4654bf7f57f59f57aa66` and CI tested source `636b9e28fd5926f08607623746ca082cc8acc46a` (Run `42707733663`), limited RSA service assertion sender and isolated mTLS transport only; NOT OIDC/real Session issuance, Cookie/CSRF, fresh reauth, external Reset or Product Auth. Existing PR #17/#18/#19 also merged with limited synthetic API trust/durable Replay and DB admission; no Product Auth Gate. Branch list and all PR #1–20 inspected; **NO existing similar BND-IDP-02A PR/branch**, no conflicting newer workflow. New branch `agent/idp-reauth-proof` created from EXACT live main SHA, no main or parent repo write.

**Files and ownership inspected before any change:**
- `infra/auth-ci/compose.yml`, `Dockerfile.test-runner`, `README.md`;
- `tests/phase3/integration/auth_idp/evaluate.py`, `support.py`, `network_guard.py`;
- `.github/workflows/auth-idp.yml`;
- **this EXISTING** `coordination/tasks/AGENT-API-AUTH-IDP-01.md`, read completely (~66 KB);
- `docs/adr/0005-auth-session-boundary.md`, AGENTS.md, coordination/ownership.md and accepted earlier IDP-01 evidence.
Only these named FOUR existing paths modified: `tests/phase3/integration/auth_idp/evaluate.py`, `infra/auth-ci/README.md`, `.github/workflows/auth-idp.yml`, and THIS cumulative checkpoint. No second mission file, new test directory, SPI/Extension, Outbox, migrations, API/Web/History/DB repository, ADR, root/contract or canonical checklist edits. Old IDP-01 tests remain in the same real Chromium/Keycloak/Mailpit run without weakening.

**Map traceability:** primary Module 05 `P3M05-A01/A02/A06/A07/A08/A09/A10` (only bounded password, session, reset and security event *candidate* evidence); supporting `P3M03-A01/A03/A08`, `P3M06-A03/A05/A07`, `P3M13-A03/A07/A08/A09/A10` are *context*, NOT Gate progress or tested History wiring. Existing `P3OP03-R01/R02/R05` are operational overlays, not counted. Module 00 and all M03/M05/M06/M13 Gate statuses unchanged.

**Exact pinned versions (unchanged from existing CI):** Keycloak `quay.io/keycloak/keycloak:26.8.2`, IdP-only `postgres:17.11`, `ghcr.io/axllent/mailpit:v1.32.0`, Playwright Python/Chromium `1.64.1`, Python Playwright Docker `v1.64.1-noble`, requests `2.32.5`, PyJWT[crypto] `2.10.1`, pyotp `2.9.0`, GitHub ubuntu-24.04; test-real Python patch from CI to be observed, NOT assumed. Existing internal:true zero published ports, egress denial from DB and browser, local synthetic SMTP only, in-memory passwords, sanitation and volume teardown unchanged.

**Existing key finding, not to be erased:** In actual IDP-01 Test B after Forgot/Reset, old pre-reset independent browser `prompt=none` still succeeded, old refresh returned 200, old UserInfo returned 200, locally verified old access JWT signature still validated before exp; no administrator logout was used in that Reset comparison. Admin-initiated *separate* logout denied old refresh/UserInfo, but independently signed access JWT retained signature before expiry. These do not prove cross-DB reset event propagation, nor globally logout all old BFF Sessions.

**Standard capabilities researched BEFORE code:**
1. Keycloak built-in Browser **Cookie** authenticator can automatically accept existing SSO for ordinary OIDC Code flow; a valid signed token on its own is NOT fresh credential evidence.
2. OIDC `prompt=login` and `max_age=0` are existing standard requests for actual reauthentication; real login form must require new credential and old one denied in retained old-cookie browser, code+S256 PKCE, state, nonce, iss, aud and auth_time verified. `auth_time`, ACR or AMR claim alone does NOT prove interaction, freshness, global logout or external cross-system delivery.
3. Keycloak built-in `Send Reset Email` of Reset Credentials flow has standard `force-login=true/false/only-federated` config (default only-federated). New CI sets `force-login=true` in the EPHEMERAL realm via standard Admin REST `POST /authentication/executions/{id}/config` and requires GET readback, no SPI/extension. A successful forced login after the active Reset flow does NOT guarantee that other pre-existing browser SSO/Refresh/Access was revoked.
4. Forgot/Reset via real browser and local captured Mailpit email, Required Action UPDATE_PASSWORD and Admin REST Reset Password each get separate synthetic old/new password verification. Account Console password change is a standard alternative but **not tested** by the current isolated harness, not silently counted under Forgot/Required Action. External Admin Reset (no product event outbox/ack) and non-tested Account Console/federated/passkey variants do not get finite/reset-all revocation guarantees.
Official baseline docs https://www.keycloak.org/docs/26.8.0/server_admin/ , https://www.keycloak.org/docs-api/26.8.2/rest-api/index.html , https://www.keycloak.org/securing-apps/oidc-layers and prior ADR 0005; Keycloak standard Force login after reset is documented in the Server Admin Guide. Documentation is a capability claim, NOT empirical 26.8.2 pass until CI.

**New case matrix in EXISTING `evaluate.py`, no self-signed fake IdP tokens:**
- RA-00 actual built-in reset flow + configuration readback;
- RA-01/02 real browser initial password OIDC Code+PKCE/nonce and retained old SSO before reset;
- RA-03 real Forgot/Reset changing password with old rejected/new accepted;
- RA-04/05/06 retained old browser cookie with `prompt=login&max_age=0` MUST show password form/no silent callback, reject old pwd, accept new pwd with new verified signed ID token `auth_time` in real challenge window; interactive action is required in addition to claims.
- RA-07 malformed/missing/wrong callback state before exchange, signed nonce/issuer/audience negatives and old code replay; existing A06 wrong PKCE verifier test retained.
- RA-08 after Reset independent old SSO/Refresh/UserInfo numeric/boolean observations (not mistaken for successful global revocation);
- RA-09 retained cookie `prompt=none&max_age=0` MUST NOT issue a silent OIDC Code. A silent Code fails the test and is a blocker, never relabeled fresh.
- RA-10 Admin REST reset old denied/new accepted; RA-11 standard UPDATE_PASSWORD Required Action displayed/fulfilled and separate old/new credentials tested; RA-12 bounded evidence verdict `PARTIALLY_PROVEN` only if all required tests pass. Account Console NOT_TESTED, external Reset events/Revocation NOT_PROVEN. No product `finish_simulated_reauth`, issuing Product Session or service message fallback.

**Actual commands from unchanged CI framework:** `docker build -f infra/auth-ci/Dockerfile.test-runner -t auth-idp-runner:ci infra/auth-ci`; `docker compose --env-file $RUNNER_TEMP/idp-ci.env -f infra/auth-ci/compose.yml up -d`; `python tests/phase3/integration/auth_idp/network_guard.py`; `python -m compileall -q tests/phase3/integration/auth_idp`; `docker run --rm --network authidpci_authisolated ... auth-idp-runner:ci python /suite/evaluate.py`; unconditional teardown/credential deletion and sanitized 3-day `report.json` artifact. **Only Workflow change**: enable trigger and same guarded job for new `agent/idp-reauth-proof` branch while leaving original `agent/auth-idp-ci` path/guard intact. No dependency version, network or image change.

**Failure policy:** if standard force-login config, real old-cookie challenge, prompt=none max_age=0, ID token auth_time, Required Action or Admin Reset fail, report exact **fixed safe stage and exception type**; preserve failed CI evidence, do not remove a negative check or invent success. `PARTIALLY_PROVEN` is attainable ONLY for tested local forced fresh login; external Reset/worst-case event delivery is BLOCKED regardless of that result. Supervisor must separately approve any later secure API↔BFF integration. Changed source and CI status on this first push are **NOT_RUN** pending GitHub Actions; implemented=ISOLATED_STANDARD_REAUTH_PROBE_PREPARED, tested=NO_NEW_CI_YET, accepted=NONE. No merge.


## IDP-CI-01-AH — first BND-IDP-02A actual CI: original IDP-01 baseline PASS, reset-flow inspector unresolved

**Tested source SHA:** `0e3750e105a88ac04b52437c59f3f3594ef4957d`. [Actual GitHub Actions Push Run 42717943231](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42717943231) **COMPLETED FAILURE** at new fixed safe stage `RA-config-inspect-standard-flows`, category `AssertionError`. Real pinned Keycloak 26.8.2, isolated PostgreSQL 17.11 and Mailpit 1.32.0 started; internal-only networking, zero published ports, DB and browser outbound TCP denial PASS; cleanup and credential deletion PASS. All prior IDP-01 native browser/SMTP/PKCE, original Reset, A/B/C, bounded brute-force and administrator TOTP tests reached observed PASS through `IDP-12-manager-minimal-role`. No new RA-00/RA-01..RA-12 PASS, no fresh-auth result, no false Keycloak capability conclusion. Before this failure the new test had made only a synthetic Keycloak Admin REST flow-inspection call after the old suite, not a product/extension/migration change.

The current stage covered one or more Admin REST calls and built-in flow/execution alias assertions, so the exact cause CANNOT be inferred from the category alone. **Test-only diagnostic, no security relaxation:** log and store only the Keycloak standard flow alias subset containing "reset" and execution authenticator identifiers, with distinct fixed stages between GET list, alias match, Browser and Reset execution inspections. These are public/static configuration identifiers only; NEVER log user, email body, password, OTP, Token, Cookie, Reset link or Keycloak Authorization URL. No test checks removed. Re-run on a new Push with this checkpoint atomically. `PROVEN`, `PARTIALLY_PROVEN` and product Auth remain NOT_ESTABLISHED at this SHA.


## IDP-CI-01-AI — second real CI stopped earlier: bootstrap Admin token freshness (2026-11-10)

**Source SHA:** `ea28fb0186a5487c3af3d80a20bde79d3aa094b7`; [Push Run 42718543627](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42718543627) **COMPLETED FAILURE** at new safe stage `RA-provision-isolated-verified-test-user`, category `AssertionError`. Entire original IDP-01 baseline again passed through manager, including isolated Keycloak/Postgres/Mailpit network and teardown. The failure is now BEFORE `RA-config-inspect-standard-flows`; the new scoped flow debug never ran, so no evidence about alias or execution identifiers. In the prior Run 42717943231 the new synthetic user creation succeeded but the next Admin flow inspection failed. Combined elapsed time of original browser/OTP suite is near Keycloak's short-lived bootstrap Admin REST token expiry; therefore expired CI Admin token is a **plausible hypothesis only**, not independently proven HTTP status (failure sanitization prints no response body or bearer details).

**Narrow, safe correction:** re-obtain a fresh bootstrap Admin REST access token in RAM using the EXISTING `Admin()` helper at the start of `bnd_idp_02a`, AFTER the original old suite and BEFORE new user creation or Admin Flow inspection. This does **NOT** extend lifetime, request a new privilege, change any realm policy, add a browser auth bypass, touch production credentials or change original test assertions. Update only evaluate.py and this same cumulative checkpoint in atomic push. The following CI result, not this hypothesis, will determine whether the standard config exists. First and second runs both FAIL overall; no RA test PASS claimed, no user or token leaked.


## IDP-CI-01-AJ — real third run identifies versioned REST response field mismatch (2026-11-10)

**Source SHA:** `ec7114bce7eedf307b9ff20090c83faa8dd01389`; [GitHub Push Run 42719133392](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42719133392) **COMPLETED FAILURE** at `RA-config-reset-email-execution-match`, category `AssertionError`. All original synthetic IDP-01 A/B/C and browser MFA baseline tests passed, internal egress/network and unconditional teardown PASS. NEW verified evidence: `RA_FLOW_CANDIDATES=['reset credentials']`, exact alias found; `RA_RESET_EXEC_AUTHENTICATORS=['', '', '', '', '', '']`. The stage had successfully fetched the built-in Reset Flow's six execution info records but looked for `authenticator` in a versioned REST response that did not expose that field. This is a **test selector mismatch**, not evidence that standard Send Reset Email or a real password form is missing.

**Narrow correction:** switch only the CI fixture's REST response parsing to the `providerId` field of Keycloak's `AuthenticationExecutionInfoRepresentation` from `GET /authentication/flows/{alias}/executions`, keeping exact desired value `reset-credential-email`, and output only safe provider ID strings to verify live shape. No credentials/URLs/tokens or user data in diagnostics; no change to Keycloak's policies, test security criteria, cryptography, network, versions or product. Existing 13 RA claims remain NOT_RUN/NOT_PASS until new Run. Earlier conclusion about plausible Admin short-lived token refresh is no longer relied on as explanation of THIS failure; separate fresh Admin token still follows standard ephemeral token issuance.


## IDP-CI-01-AK — real fourth run: standard reset force-login, OIDC max_age=0, SSO challenge PASS; negative form automation blocked (2026-11-10)

**Tested source SHA:** `9b3c8e0df53cc7a784582e1f834ba2e2a234ce7d`. [Actual GitHub Push Run 42719627050](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42719627050) **COMPLETED FAILURE** at safe stage `RA-old-credential-denied` with `TimeoutError`; previous old IDP-01/A/B/C baseline, network denial and cleanup all PASS.

**NEW genuinely measured limited PASS before failure:**
- Keycloak actual standard flow aliases `['reset credentials']`, `providerId` records `['', 'conditional-user-configured', 'reset-credential-email', 'reset-credentials-choose-user', 'reset-otp', 'reset-password']`, no SPI; RA-00 standard `force-login=true` config POST and independent GET readback **PASS**.
- RA-01 real initial password browser Code+S256/nonce PASS; RA-02 original cookie's existing SSO `prompt=none` PASS before Reset.
- RA-03 real browser/locally captured Forgot/Reset replaced password: old credential denied, new login accepted, original pre-reset SSO context still preserved; PASS.
- RA-08 old cookie/refresh/UserInfo statuses independently OBSERVED after Reset (values in runner sanitized report; no immediate revocation claimed), PASS as observation.
- RA-09 `prompt=none&max_age=0` from preexisting-cookie context returned NO fresh Code (must require interaction), PASS.
- RA-04 `prompt=login&max_age=0` in SAME original SSO context displayed a REAL `#kc-form-login` form and emitted NO callback BEFORE password entry, PASS. **Neither an actual rejected old credential within THIS challenge nor a successful freshly-entered new one is yet proven**, as the original generic `fill_login` helper timed out in a form interaction. Thus NOT_ALL_RA_TESTS_PASS and overall CI FAILURE. No fake fresh proof from the observed auth_time, which has not yet been reached.

**Narrow safe fixture fix:** Keycloak existing SSO reauthentication may present a username field prefilled/readonly/hidden instead of an ordinary editable form. Add a browser helper that READS only safe form-shape booleans, ensures password and submit visible, fills username only when editable or asserts prefilled expected username when readonly, submits a real password using Playwright. Reuse exactly the same original old SSO cookie context; old password MUST be rejected before any callback. After the negative, close the failed authentication sub-session and create a fresh new Code+PKCE/state challenge within that SAME old cookie context for new password, because invalid credential may restart the first sub-session. All old/new assertions, `max_age=0`, `prompt=login`, state/nonce/issuer/audience/code replay, signed fresh auth_time checks remain unchanged; no client fake fresh success, no modified Keycloak privileges, network, versions or product. **Status:** tested partial before failure, next source pending CI.


## IDP-CI-01-AL — takeover of EXISTING BND-IDP-02A branch; exact real successful CI (2026-11-10)

**NO DUPLICATE BRANCH/PR/WORK.** At takeover, live `main` was exactly the supplied Starting SHA `a29fae8392d6664926327e1ab2eeaa4a8b32f85d` and PR #20 was already **CLOSED/MERGED** with exact merge SHA; only limited BFF-SERVICE-01 service assertion/mTLS scope was accepted. Existing mission branch `agent/idp-reauth-proof` already existed at **TESTED SOURCE SHA** `e41847a3173786b179e5caf998c35d09fca72242`, five ordinary commits ahead of main, no open PR. Existing relevant files were identified/reviewed BEFORE this continuation: `infra/auth-ci/compose.yml`, `Dockerfile.test-runner`, `README.md`, `tests/phase3/integration/auth_idp/evaluate.py`, `support.py`, `network_guard.py`, dedicated `.github/workflows/auth-idp.yml` and this ORIGINAL cumulative checkpoint. Prior AG/AI/AJ/AK + older original IDP-01 ledgers and actual failures were preserved, not re-created. Files already changed on branch: **only** `infra/auth-ci/README.md`, `tests/phase3/integration/auth_idp/evaluate.py`, `.github/workflows/auth-idp.yml`, this cumulative task file. No new code change made during takeover: previously prepared tests had a full successful independent GitHub CI and were therefore retained unchanged.

**Actual latest source CI:** [GitHub Push Run 42720391540](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42720391540) on exact tested source SHA **COMPLETED / SUCCESS**. All workflow steps successful: pinned Playwright image build, isolated Keycloak/PostgreSQL/Mailpit readiness, Docker Internal=true and zero published ports, negative outbound TCP probes from DB/browser, actual Chromium OIDC+SMTP+TOTP/password tests, CI-only Python compile, **unconditional volume/container/network/credentials teardown**, sanitized evidence artifact `auth-idp-sanitized-42720391540` (artifact ID `13719514156`, retained 3 days). Real log emitted `ISOLATED_IDP_EVALUATION_PASS`. No product Auth access or production IdP connection. No live Mac install or email.

**Distinct observed real case outcomes (safe stage labels in actual CI logs, not inferred from feature names):** all **13 RA cases RA-00..RA-12 PASS**:
- **RA-00:** built-in `reset credentials` flow standard `reset-credential-email`/Send Reset Email `force-login=true` configured via Admin REST and read back, no SPI.
- **RA-01/RA-02:** real initial browser password OIDC Code+PKCE login; original cookie `prompt=none` SSO before Reset.
- **RA-03:** real Forgot/Reset via Mailpit local capture; old credential denied, new accepted.
- **RA-08 (observation only):** independent pre-reset SSO/refresh/UserInfo queried after Reset with no forced admin logout; **their exact HTTP results are kept in sanitized report, not asserted globally invalid**.
- **RA-09:** original SSO browser `prompt=none&max_age=0` emitted no silent fresh Code.
- **RA-04/RA-05:** same old-cookie browser with `prompt=login&max_age=0` displayed a real credential form/no premature callback; old password denied in that challenge.
- **RA-06/RA-07:** fresh separate Code/PKCE/state+nonce challenge in SAME old browser accepted newly entered password, signed ID token `auth_time` lay in real challenge window; wrong/missing state, nonce, issuer, audience and Code reuse rejected. Prior IDP-01 independent A01..A06 PKCE/callback negatives still ran (baseline retained). ACR/AMR are recorded only for presence/type; **not standalone proof**.
- **RA-10:** standard Admin REST password reset replaced password (old refused/new accepted), with NO assertion that external old sessions were all revoked.
- **RA-11:** built-in `UPDATE_PASSWORD` Required Action form completed and separately verified old rejected/new accepted.
- **RA-12:** explicit bounded `PARTIALLY_PROVEN` verdict for **interactive local** fresh password proof; external Reset, product revocation and durability NOT_PROVEN.

**Clear coverage matrix (not all reset routes empirically covered):**
1. Forgot/Reset — TESTED in actual Chromium + local Mailpit; Force Login `true` config READBACK; old/new credential plus original-cookie fresh-challenge tested.
2. Account Console password change — **NOT_TESTED**. Standard feature identified but NO separate Account Console browser challenge was executed.
3. Required Action UPDATE_PASSWORD — TESTED on distinct synthetic browser/account, old/new credential; does not imply all other contexts revoked.
4. Admin Reset — TESTED via standard isolated Admin REST + separate browser logins old/new; NO delivered credential-event-to-product DB proof.
5. Federated/passkeys/alternative reset paths — NOT_TESTED in this local realm.

**Assurance interpretation:** `auth_time` from a correctly signed, issuer/audience/nonce-checked ID token is only supporting temporal evidence; real credential entry, rejected old credential, SSO cookie retention, fresh callback state/PKCE and interaction are the independent strong evidence. Do not assume `acr`/`amr` means password authentication if the configured Flow cannot independently prove it. Standard `prompt=login&max_age=0` can enforce one **new local interactive challenge** on this tested Keycloak configuration, but `force-login=true` alone does not revoke independent prior SSO, refresh/access token or product Session. The original PR #13 reset-negative measurement (old prompt=none/code, refresh 200, UserInfo 200 and locally valid signed JWT) remains true for its prior configuration. Present successful RA-09 `prompt=none&max_age=0` separately from ordinary `prompt=none`; do not substitute one for the other.

**Decisive unsolved external-Reset blocker:** no cryptographically bound, durable, monotonic credential-change epoch/outbox from **all** Keycloak password mutation surfaces, no at-least-once bounded authenticated event delivery to product DB or ack/reconciliation, no all-product-session revocation or admission fencing after external reset, no accepted Fresh Reauth authorization binding in product BFF/API. No finite cross-DB propagation/revocation bound can be proven here. The original ADR 0005 gap is not closed; no `finish_simulated_reauth` evidence, no Gate acceptance. Next separately authorized work may examine built-in logout/backchannel capabilities and IdP event delivery design or a stronger barrier, but this mission MUST NOT add extension/SPI, custom outbox, Migration or product wiring.

**Exact unchanged workflow method:** `docker build --pull -f infra/auth-ci/Dockerfile.test-runner -t auth-idp-runner:ci infra/auth-ci`; `docker compose --env-file "$RUNNER_TEMP/idp-ci.env" -f infra/auth-ci/compose.yml up -d`; `python tests/phase3/integration/auth_idp/network_guard.py`; `python -m compileall -q tests/phase3/integration/auth_idp`; isolated `docker run ... auth-idp-runner:ci python /suite/evaluate.py`; unconditional `docker compose ... down --volumes --remove-orphans` and credential-file deletion. Pinned Keycloak 26.8.2, PostgreSQL 17.11, Mailpit 1.32.0, Playwright/Chromium 1.64.1; no version upgrade. The first four non-green Runs 42717943231 / 42718543627 / 42719133392 / 42719627050 and their narrowed fixes are honestly preserved under AH–AK. No claim those passed.

**Traceability unchanged:** `P3M05-A01/A02/A06/A07/A08/A09/A10` primary, `P3M03-A01/A03/A08`, `P3M06-A03/A05/A07`, `P3M13-A03/A07/A08/A09/A10` supporting and P3OP03-R01/R02/R05 as non-counting overlay. **Implemented**=ISOLATED_KEYCLOAK_STANDARD_FLOW_AND_REAL_BROWSER_FIXTURE; **Tested**=ALL_RA_13_PASS_ON_REAL_CI_SOURCE_SHA; **Verdict**=PARTIALLY_PROVEN local fresh credential, BLOCKED comprehensive external reset; **Accepted**=NONE/SUPERVISOR_PENDING. READY_FOR_REVIEW — ISOLATED_REAUTH_PROOF. No product Session issuance, Auth product/m05 Gate, source DB migration, deploy, real email, model, purchase or parent repository write. This checkpoint will be the ONLY post-test documentation edit; Final SHA differs from previously tested source SHA and any CI run on it must be independently checked before claiming success.


## IDP-CI-01-AM — BND-IDP-02B source checkpoint; awaiting CI

**Exact confirmed live baseline**: `main` =
`21de761c880c5c7c0241fb8ce683e616e44ca11b`; PR #21 merged
with identical merge SHA. No matching open PR or existing 02B branch.
Created `agent/idp-reset-boundary` from that baseline. Reused all
original 01/02A suites, pinned Keycloak 26.8.2/Postgres 17.11/
Mailpit 1.32.0/Playwright 1.64.1 and original cumulative mission file.
Read AGENTS, ownership, ADR 0005, existing checkpoint and exact IdP
harness/Workflow before edit.

**Bounded ownership**: P3M05-A01/A02/A06/A07/A08/A09/A10 (Module05);
support P3M03-A01/A03/A08, P3M06-A03/A05/A07,
P3M13-A03/A07/A08/A09/A10; P3OP03-R01/R02/R05 overlays only.
No new Gates.

**Exact 5 changed authorized paths**:
`tests/phase3/integration/auth_idp/reset_logout.py` new temporary
in-runner recipient + four credential-change route/browser/session
tests and real logout/outage/negative-token tests;
`tests/phase3/integration/auth_idp/evaluate.py` append 02B hook
only AFTER previous 01/02A successful suite;
`.github/workflows/auth-idp.yml` add scoped branch and internal
Docker DNS alias to existing runner, never publish port;
`infra/auth-ci/README.md` document exact test-only boundary;
`coordination/tasks/AGENT-API-AUTH-IDP-01.md` THIS cumulative ledger.

No product API/UI/DB, Migration, root, shared Contract/ADR/checklist,
Keycloak version, real email, SPI, outbox, Mac install or Deploy.
Standard OIDC backchannel.logout.url triggers Logout events if emitted;
it is NOT automatically an external credential-change notification.
Receiver uses standard RS256/JWKS, iss/aud/time/events/sid/sub/jti and
in-memory replay validation for synthetic tests; it never claims durable
JTI or sends product Session messages. Real receiver outage/restart
and finite retry observations are planned, no guarantees assumed.

**Commands**: unchanged existing GitHub `auth-idp.yml` Docker build,
Compose up, network_guard+egress deny, `python -m compileall -q
tests/phase3/integration/auth_idp`, same Playwright runner
`python /suite/evaluate.py` plus new module, always Compose
down --volumes and sanitized 3-day artifact. All prior 01/02A cases
remain strict. First test outcome NOT_RUN until real Actions; failures
will be recorded in THIS file, not hidden. **Implemented** source
prepared; **Tested** NOT_RUN; **Accepted** none, supervisor pending.


## IDP-CI-01-AN — first real BND-IDP-02B CI fails at Account Console view (2026-11-10)

**Exact tested source:** `4e508e4dfa065fdcf4c9ae4b370d2c598d8e46a3`,
[GitHub Push Run 42849562118](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42849562118)
**COMPLETED FAILURE** in stage `RB-account-console-navigate`, category
`AssertionError`. The long-standing original IdP-01 baseline and ALL
RA-00..RA-12 had independently passed on this same run. New
`RB-backchannel-standard-client-config-readback` PASS after standard
client configuration and independent readback; new real
`RB-route-forgot-actual-password-and-session-matrix` PASS, proving
real independent synthetic Forgot/Reset with prior-session measurements.
**No Account Console password change, no Required Action/Admin route
matrix, no Logout Token delivery, no outage test was yet proven.**
Keycloak/Postgres/Mailpit startup, internal no-egress network, cleanup
of volumes/network and secret file remained PASS. Actual safe failure
stage does not distinguish redirected Account Console login from
missing Update button, so no claim which cause.

**Narrow test-only correction:** inspect ONLY safe booleans/counts
(login form, update link/button, Signing in route, password form,
account path), without page URL/query, headers, token, user text or
credentials. If the Account Console's separate `account-console` OIDC
client presents a REAL login form, fill the existing synthetic user's
valid credential and retry the normal browser Account Console UI path;
never bypass with Admin REST or claim the Account Console route changed
a password without actual UI. Test remains strict: update password,
independent old login DENY and new login ACCEPT before PASS. Need new
CI to determine UI shape; baseline assertions retained. No Keycloak
version/flow, DB migration, product or workflow grant changed.


## IDP-CI-01-AO — actual rerun isolated Account Console navigation evidence

First attempt 2 source `e3fa3b4c9767e721eb474840316790b335219097`
[Run 42850378441](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42850378441)
attempt 1 **FAILURE** BEFORE 02B at original IDP-01 manager-MFA form
`manager-mfa-enrollment-submit` TimeoutError; no new Account Console
diagnosis. **Reran same failed GitHub job, unchanged code and tests**,
attempt 2: original IDP-01, all RA-00–12 PASS; standard backchannel client
configuration PASS; Forgot/Reset independent old SSO/Refresh/UserInfo
PASS; then Account Console failed at `RB-account-console-safe-ui-shape`
with AssertionError. Safe live UI shape:
`account_path=True, login_form_visible=False,
update_button_count=0, update_link_count=0,
signing_in_link_count=0, password_new_count=0,
account_security_link_count=2`.
Therefore it displayed an account-app path and Account Security
navigation but **NO** Update action or login form: NO real Account
Console password change proven, and no claims of password revocation,
later route or Logout Token/outage progress. Both attempts require
failing overall; the first is unrelated historical browser fixture
flakiness, and the second is a reproducible UI navigation miss.

**Narrow next change:** Browser visits the Account Console's own
`account-security` / `signing-in` link rather than assuming a direct
deep hash renders its child; add only safe **booleans** for existence
of signing-in href/hash and error/password page indicators. No
document body, raw href, URL, username, email, Cookie, JWT, Reset link
or password in stdout/artifact. Keep exact successful old-password
reject/new-password accept criterion; no Admin REST mutation fallback.
If the standard UI remains inaccessible, mark NOT_PROVEN; no version
upgrade, application/product code, DB/schema or service grant change.


## IDP-CI-01-AP — third real CI: Account Console deep-hash renders noninteractive nav; bounded root fallback

**Source** `3abb368e8b827f595cb19c5c086c54581eebe274`,
[Push Run 42851688072](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42851688072)
**COMPLETED FAILURE** only on new stage
`RB-account-console-navigate-own-security-menu` with
Playwright `TimeoutError`. Previous IDP-01/RA-00..12 PASS,
standard OIDC Back-channel config readback PASS, Forgot/Reset
old independent browser and token matrix PASS.
Safe observed UI shape on Chromium: account path True,
no login form, no Update button/link, a DOM `signing-in` href
present, signing-in fragment correct, password text absent,
no generic error wording. The attempted Account Security DOM link
could NOT be clicked as an interactive visible element. This is
**NOT** proof that Account Console credential edit happened and
is NOT an IdP rejection of the new password. Required/Admin route,
standard logout/backchannel JWT and outage not yet reached.

**Next strict fixture behavior**: Navigate the standard Account
Console ROOT first, inspect only safe element counts/visibility,
click its OWN visible `Signing in` or Account Security link,
and insist on real Update button and password form before any
PASS claim. If UI is still unavailable, capture `BLOCKED` for
Account Console and **continue** independent Required/Admin
and Logout/receiver-outage tests; after all other tests, report
a final non-green CI/fail-closed `ACCOUNT_CONSOLE_NOT_PROVEN`.
This is explicitly NOT an alternative Admin REST password update
or fabricated success. No other security criterion weakened,
no versions/migrations/Keycloak product or network permissions
changed. Exact prior failed stages and first MFA timeout remain
in original checkpoint.


## IDP-CI-01-AQ — bounded FINAL BND-IDP-02B evidence, independent routes + Logout; Account Console BLOCKED (2026-11-10)

**Tested source SHA:** `a2ff6c75b81290bc003f45a2d56feea1c2e30e6f`.
**Real [GitHub Push Run 42852620874](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42852620874): COMPLETED / FAILURE**. The failed overall status is **intentionally retained**: standard Account Console password change was NOT PROVEN despite real Chromium UI attempts. Browser-runner code records its blocker and runs other independent tests before final generic rejection `RB-account-console-not-proven-final`; no false all-green CI, no Account Console PASS, no fallback to Admin REST claiming Account Console. The same run verified all original `IDP-01`/A/B/C and `RA-00..RA-12` previously accepted Chromium/Keycloak, plus new bounded cases listed below. Runner's pinned Keycloak 26.8.2, identity Postgres 17.11, Mailpit 1.32.0 and Playwright 1.64.1 unchanged. Internal-only Docker network, no host ports, negative egress test, synthetic `.test` accounts, teardown/credential deletion PASS.

**Audited source of factual matrix:** [sanitized CI artifact `auth-idp-sanitized-42852620874`](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42852620874/artifacts/13780518282), ID `13780518282`, 3-day retention; GitHub job logs list all RB stage outcomes and `ISOLATED_IDP_EVALUATION_FAIL stage=RB-account-console-not-proven-final category=AssertionError`. Artifact read as JSON, no bearer/refresh/id/logout JWT, raw cookie, email, reset link, login code, OTP seed or action-token URL exposed in outputs. Actual static `safe_report` overall is **FAIL**.

**Four independent pre-change-browser/refresh/access observations on synthetic users (do NOT extrapolate to Product Session):**

| Keycloak standard password mutation | New credential / prior credential outcome | Preserved original browser `prompt=none` | Original Refresh HTTP | Original Access/UserInfo HTTP | Valid backchannel tokens observed during mutation | User event type enums seen in the bounded test window |
|---|---|---|---|---|---|---|
| Forgot/Reset (real local Mailpit) | NEW ACCEPT / OLD DENY — PASS `RB-route-forgot` | TRUE | 200 | 200 | 0 | `LOGIN_ERROR`, `RESET_PASSWORD_ERROR`, `SEND_RESET_PASSWORD`, `UPDATE_CREDENTIAL`, `UPDATE_PASSWORD` |
| Built-in Required Action `UPDATE_PASSWORD` | NEW ACCEPT / OLD DENY — PASS `RB-route-required` | TRUE | 200 | 200 | 0 | `UPDATE_CREDENTIAL`, `UPDATE_PASSWORD` |
| Standard Admin REST `reset-password` | NEW ACCEPT / OLD DENY — PASS `RB-route-admin` | TRUE | 200 | 200 | 0 | none in *user-event endpoint*; Admin REST event endpoint NOT queried |
| Account Console UI Account Security/Signing in | **BLOCKED/NOT_PROVEN**; never submitted password change | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | NOT_PROVEN | NOT_MEASURED |

**Important event attribution limit:** the Keycloak built-in user-event type set is computed within the route + credential-check/old SSO test window. The Forgot/Reset helper itself checks old-password denial, new-password login and action-token replay; event types like `LOGIN_ERROR`/`RESET_PASSWORD_ERROR` must NOT be attributed specifically to successful credential change. The set difference identifies **observed** built-in user event enums in this isolated Keycloak realm, not an atomic per-change event, webhook, durable queue, cross-DB delivery or eventual product revocation. Standard Admin Reset may use a separate Admin Event channel, which was **NOT** inspected: zero user events does **not** mean zero Admin Events. The counts above are for the registered OIDC client ONLY in the measured window; other clients, retry or different deployments not tested.

**Logout separate from password change (same synthetic DB, same client):**
- `RB-standard-oidc-logout-measured` **PASS**: real RP-initiated standard `end_session_endpoint` from authenticated Chromium context with genuine ID Token hint, original Refresh HTTP 400, original UserInfo HTTP 401, standard Back-channel valid token delivered to test recipient.
- `RB-standard-admin-logout-backchannel-delivered` **PASS**: independent standard Keycloak Admin REST user logout invalidated prior Refresh (HTTP 400), and real Back-channel Logout Token reached the isolated receiver.
- `RB-logout-token-real-signature-claims-and-replay-negatives` **PASS**: receiver verified real Keycloak JWKS RS256, exact issuer, test-client audience, `iat/exp`, exact OIDC backchannel `events`, nonempty `sid` or `sub`, no `nonce`, unique `jti`. Replayed exact signed token got HTTP 409, altered-signature/invalid compact or wrong content-type HTTP 400; wrong expected issuer/audience were rejected by real JWT verifier; invalid event/time/identity/nonce checked through policy negative tests on COPIES of already verified signed claims. No fabricated issuer-signed token for mutated events. Received tokens and client credential references remained RAM-only and were never logged.
- `RB-receiver-outage-and-restart-observed` **PASS as measurement**: actual TCP listener CLOSED before a fresh standard Admin Logout, original Refresh returned HTTP 400, **0 delivered while offline**. Receiver reopened on same internal alias/port and **0 messages arrived in bounded 4-second observation**. This does NOT prove Keycloak will never retry later; no durable retry, delivery, persistence, recovery or acknowledged product Session invalidation is proven. Receiver's own replay set is RAM-only and restart persistence NOT_IMPLEMENTED, emphatically not production-grade.

**Account Console exact safe browser evidence and blocker:** Direct Keycloak `/realms/{realm}/account/#/account-security/signing-in` shows account path and one DOM link with signing-in href, correct fragment, no login form, **zero visible/counted Update buttons**, zero password form, zero 'password' wording, no recognized error wording. Attempt to click account security menu timed out because its DOM link was not visible. A second attempt navigated to Account Console ROOT, but `root_signing_link_count=1` (invisible), `root_security_link_count=2` (invisible), `root_has_update_button=False`; no actual password change attempted. **This proves a CI fixture/Account Console UI coverage blocker only**, not that Keycloak lacks the standard capability or that Admin/Required action paths can stand in for an authenticated Account Console UI. Do not represent this route as passed, or infer revocation of its pre-change tokens. Next isolated task needs to diagnose account SPA/bootstrap/access prerequisites with safe browser/network diagnostics or build a supported Account UI fixture, then repeat actual old/new credential verification and independent session probes.

**Actual failure history retained cumulatively in AM–AP:**
1. [Run 42849562118](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42849562118) failed at first Account UI Update button on direct deep link after previous IDP and Forgot successes.
2. [Run 42850378441](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42850378441) attempt 1 failed transient old suite manager MFA form timeout; unchanged same-code rerun attempt 2 old suite PASS, safe Account UI shape found no Update; failed there. No historical test weakened.
3. [Run 42851688072](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42851688072) failed Account hidden link click after old/new Forgot successes.
4. [Run 42852620874](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42852620874) final tested source ran all independent Required/Admin/Logout/receiver/offline suites **PASS**, but marked Account `BLOCKED` and ended **FAIL** overall intentionally.

**Simplest next separately approved work:**
1. **Restrict and prove reset entry surfaces before any Product Auth Gate**: define which password changes can be centrally initiated and which are independently available in Account Console, Required Action, Keycloak Admin, identity federation and recovery. If feasible, explicitly restrict unsupported external paths and prove enforcement in real browser/Admin API tests; neither this CI nor a setting by itself proves that such restriction is complete.
2. **Keep product revocation authoritative and fail closed** with existing DB Session/epoch/fence primitives; controlled product reset must revoke/tombstone product Sessions before permitting any reset flow. On external IdP mutation without authenticated durable notification, do NOT create a fresh Product Session from old SSO or assert bounded automatic logout. OIDC `prompt=login&max_age=0` is evidence only for local fresh login, not remote product revocation.
3. **Reuse standard Logout/Backchannel only for events actually observed**, with signature/aud/issuer/iat/exp/events/sid-or-sub/JTI validation at the eventually approved BFF consumer and separate persistent dedupe/queue, but don't treat Logout as guaranteed Password Reset event. Outage test proves NO observed catch-up in 4 seconds. If any uncontrolled external mutation paths must remain usable, seek a **separate authorized evaluation of authenticated durable event extraction/ack/reconciliation and fail-safe session barrier**; an SPI/outbox may need consideration in a different mission only AFTER standard coverage is exhausted. No extension or migration implemented here.

**Scope and acceptance:** still exactly five authorized IdP paths since Starting main (new `reset_logout.py`, existing `evaluate.py`, existing `auth-idp.yml`, existing `infra/auth-ci/README.md` and THIS unchanged path used as cumulative ledger). No product API/BFF/UI/History/DB or Migration 001–005, shared contract, ADR, checklist or parent repo edits; no real mail/credential, model, public server or deploy. Source traceability unchanged: P3M05-A01/A02/A06/A07/A08/A09/A10 primary, supporting P3M03-A01/A03/A08, P3M06-A03/A05/A07, P3M13-A03/A07/A08/A09/A10; P3OP03-R01/R02/R05 non-counting overlays. **Implemented:** CI-only four reset pathways attempted, standards-based Logout Token receiver/outage measured; Account Console UI attempt BLOCKED. **Tested:** real GitHub Runner partial successes above and overall FAILURE on exact code SHA (no green 02B run). **Accepted:** NONE/SUPERVISOR_PENDING. **Verdict:** PARTIALLY_PROVEN explicit Logout/three reset paths; BLOCKED complete four-path coverage and external reset delivery; **READY_FOR_REVIEW — STANDARD_RESET_LOGOUT_EVALUATION** with visible blockers, NOT AUTH_PRODUCT_ACCEPTED or Gate PASS. The following final HEAD is documentation-only relative to tested code SHA; CI status of that HEAD must not be invented.


## IDP-CI-01-AR — precise constrained Account Console root-cause probe on existing PR #22 (2026-11-10)

**Authorized limited continuation from checked HEAD**
`ee539d1932166c387a7cc1660c50356b2df33d8f`: exact branch
`agent/idp-reset-boundary`, existing open Draft PR #22, base `main`
`21de761c880c5c7c0241fb8ce683e616e44ca11b`; no new branch,
PR, migration or checkpoint file. Previous CI [42852620874](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42852620874)
**FAIL** with only Account Console not proven; 3 password routes and
two real Logout operations, negative signed JWT, listener outage probes
had distinct real successes. Preserve their exact per-route numeric
matrix and all previous 01/02A IDP regressions. No false green status.

**Observed pre-fix limitation:** `a[href*="signing-in"]` and Account
Security link nodes exist in DOM but prior `.first` was hidden and
`Update` never visible. Fixed `wait_for_timeout(1200/1300)` cannot
establish React SPA readiness. It is **NOT YET** evidence of missing
standard Account Console capability, user authorization failure, JS
breakage or a password mutation. Standard documentation uses Account
Security → Signing in → Password Update. The known old browser SSO
cookie and regular OIDC callback are not a substitute for this action.

**Narrow two-file change, SOURCE NOT_RUN until CI:** Only
`tests/phase3/integration/auth_idp/reset_logout.py` and this same
cumulative checkpoint appended; no workflow or version change.
Explicit **1440×900** Playwright Page viewport is set before navigation.
Before browser mutation, read **existing standard**
`account-console` and `account` client configuration via read-only
Admin GET, reporting non-secret boolean enabled, publicClient and
standardFlowEnabled flags; no grant/policy/client modification.
Instrument browser `response`, `requestfailed`, `pageerror` with
ONLY fixed resource route categories, HTTP status counts and whitelisted
JS exception-type categories (never URLs/query, header, HTML, token,
Cookie, email, OTP, password or reset link). Inspect **every** matching
Update button/link, signing-in/security nav link, menu and expansion
control for actual visible and enabled state. Wait by **conditional
bounded predicates** for visible enabled real UI controls, not a
longer fixed sleep; open ONLY real visible menu button if collapsed,
then click a visible signing-in/security link with `.nth(visibleIndex)`
rather than `.first` or forced clicks. Genuine user/password form
and independent old-password deny/new-password accept remain required.
A handler may record a bounded Account Console blocker, continue
independent Required Action/Admin/Logout/outage tests and finally
FAIL the overall run if Account Console is unproven.

**Security and decision:** If HTTP 401/403 or script/network errors
appear, classify root cause on actual CI; no guessed Keycloak config
changes or elevated admin access. True Account Console password edit
must precede old cookie SSO/Refresh/UserInfo/backchannel observation
on its *original* Session and later independent credential checks.
No SPI, outbox, BFF/History API or product DB, migrations, real email,
Mac install, deploy or merge. Earlier user-event vs Admin Event
attribution limitations unchanged. **Implemented:** diagnostic source
prepared; **Tested:** new source NOT_RUN, historical 02B CI FAILURE;
**Accepted:** NONE/SUPERVISOR_PENDING. No Gate opened.


## IDP-CI-01-AS — Account Console safe runtime diagnostics on real CI 42888996706

**Actual source SHA:** `306dc11d2c1c2827ba4735be6ca17695c0026faa`,
[Push Run 42888996706](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42888996706):
**COMPLETED FAILURE**, solely `RB-account-console-not-proven-final`
after previous IDP-01/RA-00..12 PASS, Forgot/Reset route PASS,
Required Action PASS, Admin Reset PASS, genuine RP/Admin Logout tokens
and negative-validation/outage PASS. The receiver/outage/old Session
matrix is unchanged from previous AQ. All containers/network and
credentials torn down successfully.

Read actual [sanitized artifact 13798056513](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42888996706/artifacts/13798056513):
standard `account-console` OIDC client **present/enabled**,
`standardFlowEnabled=true`, `publicClient=true`, built-in
`account` client exists; no extra grants were made. Explicit
**1440×900** page viewport, document at Account Console path,
not at login/redirect; real DOM ready. Network safe counters:
4 Account document/API HTTP 200, 25 theme/SPA static asset HTTP 200,
3 OIDC HTTP 200 and 1 OIDC HTTP 302, **no observed 401/403**,
no `requestfailed` and no `pageerror` events in capture window.
Matching UI elements ALL enumerated: 1 signing-in link invisible,
2 Account Security links invisible, **0** Update buttons/links,
**1** visible/usable menu-like button and 3 visible/usable
aria-expanded=false buttons. No password form or active login form.
The previous `.first` navigation failure was not proof of missing
capability. **This evidence excludes disabled account-console and
observed unauthorized HTTP as immediate causes**, but does not yet
identify whether menu opens navigation, app displays a fallback
screen, or script console emitted errors not surfaced as pageerrors.
No password was changed through Account Console; no green CI claim.

**Next narrow diagnostics, same five-path limit:** capture ONLY
fixed allowlisted English UI section words as booleans, rendered
body-length bucket, visible menu-button category and whether
aria-expanded actually changed after a genuine UI click; also
categorize console errors (CSP/CORS/load/fetch/syntax/other) without
ever persisting message, URL, HTML, Cookie, token or user text.
Continue to demand a rendered Signing in password Update button
and actual independent old/new credential proof. No extra timeouts,
role change, browser JS injection, element force click or new
workflow/migration. New source awaits real GitHub CI.


## IDP-CI-01-AT — real CI 42890184780 shows separate Account Security accordion; scoped selector correction

**Source SHA** `c67f4d7a8fc022674ee6e9c54d6f8c7a3978dbc0`,
[Push Run 42890184780](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42890184780):
**COMPLETED FAILURE** with exact Account Console stage
`RB-account-console-ui-not-ready`. Prior IDP-01, RA-00–12,
Forgot/Reset, Required Action, Admin Reset, RP/Admin OIDC Logout,
genuine Logout Token negative/replay matrix and receiver-outage
experiments all PASS in this same real run; global CI FAILURE remains
correct until real Account Console password change is verified.

**Safe Account UI rendering evidence**: body text is a SHORT visible
content bucket and contains `Personal Info`, `Account Security` and
`Applications` sections but **not** `Signing in`, `Password` or
`Update`. Main section is visible. Exactly one visible
`Navigation` menu-like button has `aria-expanded=false` and 3
additional visible `aria-expanded=false` buttons. The existing
generic "Menu" selector clicked a **Navigation** button, not the
specific Account Security accordion. One Signing-in anchor and two
Account Security anchors remain in the DOM but hidden; default
account-console client active and its assets/API return HTTP 200.
**No failed request/HTTP 401/403** observed. Two generic console
error events were counted and sanitized, not identified as
session/auth denials; no JavaScript pageerror or requestfailed.
No credential edit from Account Console yet; total Run FAIL.

**Tested hypothesis, not automatic Root Cause PASS:** a separate
rendered `Account Security` **button** likely controls the hidden
nested Signing-in link. Next source change adds a real accessible
`role=button/name=Account Security` locator, enumerates ALL
matching visible/enabled controls and prioritizes clicking that
button before any generic Navigation menu. It records only
aria-expanded before/after booleans and then clicks the first
**actually visible** Signing-in link using its observed index.
No `.first` hidden-element fallback, synthetic update, JS
injection, force-click, extra grant, role elevation, guessed Keycloak
theme change or fixed sleep. Actual password update followed by
independent old-password DENY/new-password ACCEPT and original
SSO/Refresh/UserInfo/Backchannel counts is still the sole
successful outcome. Exact source retest PENDING.

**Scope** remains same PR #22, same branch, only isolated
`reset_logout.py` and cumulative checkpoint appended; existing
pinned versions, network isolation, previous security regressions
and mandatory teardown unchanged.


## IDP-CI-01-AU — confirmed standard Accordion + SPA path readiness bug on real CI (2026-11-10)

**Exact tested SHA** `fa38fe1de9a1b413c792303aecfa348818ab31bc`,
[GitHub Run 42891043095](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42891043095)
**COMPLETED FAILURE overall** only for `RB-account-console-not-proven-final`
after all previous IDP-01, BND-IDP-02A, three password
mutation routes, standard RP/Admin Logout, real JWT negative and
receiver-outage tests had passed independently in the SAME run.

**Decisive actual UI evidence:** after clicking the real accessible
**Account Security** accordion button (instead of the previously
chosen Navigation menu), the Keycloak Account Console rendered
`Signing in`, `My Password`, and `Update` words in main content
with **one genuinely visible & enabled Update button**, **one visible
Signing in link**, **two visible Account Security links**, and one
visible Account Security button, while its Navigation menu reported
`expanded=True`. Previously all these child links were hidden.
Viewport 1440×900, 5 account document/API HTTP 200, 37 theme/SPA
asset HTTP 200, OIDC 3×200 and 1×302, no observed 401/403 or failed
requests, plus two non-sensitive generic console errors which are not
causal evidence. Standard account-console and account clients remain
enabled/present with no added grants. **No password was changed yet**,
because the conditional readiness predicate erroneously insisted
`"signing-in" in urlsplit(page.url).fragment` (legacy deep `#/`
fragment), while the actual rendered Account Console's browser
navigation is path-based after the real click. Safe diagnostic printed
`on_signin_hash=False`, but visible Update button=True. The test
wrongly rejected a visible working form before clicking Update.

**Minimal source fix:** accept a page if and ONLY if the genuine
Update button/link is visible/enabled AND the actual browser URL has
the standard **`/account-security/signing-in` PATH**, OR the old
standard signing-in fragment; no assumption that a hidden anchor is
ready, and no removal of route assurance. Add ONLY a safe boolean
`on_signin_path` to report; do not print URL, query or browser
content. Clicking the Update button and real password form still
requires further actual CI. No change to Keycloak roles, UI product,
API/DB/migrations, IdP version/network, callback policy, Logout tests
or approved contracts. Previous red runs remain red. New source
NOT_RUN until next CI.

**Root cause (scope of fixture):** wrong element selector prioritized
a generic Navigation dropdown, leaving the Account Security
accordion collapsed; then erroneous hash-only URL readiness check
rejected the successfully expanded **path-router** Signing In view.
This is a **test harness routing/selector** error, not evidence
that standard Keycloak Account Console was disabled, missing
permissions, or that external Reset revocation is solved.


## IDP-CI-01-AV — BND-IDP-02B account-console real successful CI, all four routes and Logout (2026-11-10)

**Exact TESTED CODE SHA:** `1b7e264db74d4ee30a2549ed3384642492d9863a`.
[Real GitHub Actions Push Run 42891870367](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42891870367)
**COMPLETED SUCCESS** on exactly this source SHA (not just source
preparation). Full original IDP-01 browser/SMTP/TOTP/PKCE/Reset
regressions and RA-00..RA-12 completed PASS, followed by ALL
BND-IDP-02B RB steps PASS including the previously blocked REAL
Account Console. GitHub log explicitly records:
`RB-route-account-actual-password-and-session-matrix: PASS` and
`ISOLATED_IDP_EVALUATION_PASS`. Same run confirms
`NETWORK_GUARD_PASS` (Docker Internal=true, zero published ports,
outbound TCP denied), unconditional container/volume/network/secret
teardown and `EPHEMERAL_IDP_TEARDOWN_CHECK_COMPLETE`.
[SANITIZED JSON artifact 13797964580](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42891870367/artifacts/13797964580)
is **overall PASS**, with 3-day retention: actual separately
captured non-secret JWT/Session/route counters only.

**Real Account Console root cause, NOT guessed configuration:**
1. Previous fixture selected `.first` matching Account Security/
   Signing-in links without checking actual element visibility. Those
   DOM nodes were hidden because the separately accessible real
   **Account Security button** was an accordion in collapsed state.
   An unrelated generic Navigation menu button was toggled instead.
2. The exact real Chromium 1440×900 run changed accordion
   `aria-expanded` from **false → true** by clicking its actual
   visible accessible `role=button/name=Account Security` control,
   without JS injection, forced click or direct password API.
   This exposed one visible Signing-in link and one visible/enabled
   **Update** button, alongside `My Password` content.
3. Old fixture rejected this visible valid state because it demanded
   `signing-in` in the URL **fragment/Hash only**, despite the
   standard Keycloak account SPA having navigated to the actual
   `/account-security/signing-in` **path** after real UI click.
   Source fix checks visible enabled Update AND standard route
   (actual path OR legacy fragment), no generic fallback.
4. On the corrected code the REAL Account Console Update UI was
   clicked; the real password form was filled/submitted in Chromium.
   Independent fresh OIDC Code+PKCE browser login with the **old
   credential was denied**, then independent login with the
   **new credential was accepted**. No Admin Reset stand-in.
   Account Console client was read-only inspected: present/enabled,
   standard flow and public client true, built-in account client
   present; **NO permission changes/elevation**. The actual prior
   credential rejection plus newly accepted credential proves a
   genuine password mutation on this isolated local account.

**Exact separate four-path old-session/Backchannel evidence on CI:**

| Password change route | REAL password verification | Retained original browser `prompt=none` | Prior Refresh HTTP | Prior Access/UserInfo HTTP | Backchannel Logout tokens DURING change | Observable built-in Keycloak user event types in test window |
|---|---|---|---|---|---|---|
| Browser Forgot/Reset via local Mailpit | OLD DENY / NEW ACCEPT | TRUE | 200 | 200 | 0 | LOGIN_ERROR, RESET_PASSWORD_ERROR, SEND_RESET_PASSWORD, UPDATE_CREDENTIAL, UPDATE_PASSWORD |
| REAL Account Console UI (Account Security → Signing in → Update) | OLD DENY / NEW ACCEPT | TRUE | 200 | 200 | 0 | UPDATE_CREDENTIAL, UPDATE_PASSWORD |
| Built-in UPDATE_PASSWORD Required Action | OLD DENY / NEW ACCEPT | TRUE | 200 | 200 | 0 | UPDATE_CREDENTIAL, UPDATE_PASSWORD |
| Standard Admin REST Reset | OLD DENY / NEW ACCEPT | TRUE | 200 | 200 | 0 | none in queried USER events; Admin Event endpoint NOT queried |

**Interpretation boundaries:** These HTTP 200 and preserved silent SSO
results explicitly show that **NONE of the four tested changes**
invalidated the original IdP browser session or the previous Refresh
and Access/UserInfo values in this disposable Keycloak realm. Zero
Backchannel tokens were observed **during each mutation** for the
single registered synthetic OIDC client; this is not universal
nonexistence across Keycloak settings, clients or other events.
The user-event enum set-difference includes the subsequent negative
old-password and fresh new-password tests; event types must NOT be
causally assigned to one mutation from this aggregated window.
Admin events NOT read; no claim Admin Reset produced zero admin
events. Event DB is not a product delivery outbox.

**Same real CI independently retains standard Logout evidence:**
- Genuine RP-initiated OIDC end-session: original Refresh HTTP 400,
  prior UserInfo HTTP 401, a correctly signed Keycloak Logout Token
  arrived at isolated CI-only Backchannel receiver.
- Independent Admin user Logout: original Refresh HTTP 400, genuine
  Logout Token arrived.
- Genuine Logout Token RS256/JWKS + issuer, audience, `iat/exp`,
  exact events, `sid` or `sub`, no `nonce`, JTI validation passed;
  direct replay got HTTP 409; forged/tampered or wrong-form HTTP
  400; mismatched expected issuer/audience denied; synthetic claim
  mutations on COPIES of the verified claims denied (not forged
  IdP-signed alternate tokens).
- Real receiver shut down BEFORE Admin Logout: 0 received while
  offline, 0 caught up within 4 seconds after restart. No claim
  Keycloak NEVER retries later; no durable acknowledgment,
  retention or cross-DB repair proven.
- No product session issuance or external product reset/History
  wiring. **Product-wide external credential-change/session
  revocation remains BLOCKED**, even though local four-route
  coverage is PROVEN and overall limited CI is green.

**Exhaustive continuation failure audit, in order, with actual GitHub runs:**
- Prior PR #22 Run 42852620874 and original AM–AQ history:
  Account Console real UI missing in fixture due hidden DOM
  and deep route assumptions; other RB paths passed; overall FAIL.
- [Run 42888996706](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42888996706)
  tested 306dc11d2c1c2827ba4735be6ca17695c0026faa:
  old IDP suites and other RB tests PASS; 1440×900 explicit
  viewport/read-only client config/assets 200; no observable
  401/403/pageerror/requestfailed, 0 visible Signing-in and Update;
  Account Console UI NOT_READY; overall FAIL.
- [Run 42890184780](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42890184780)
  tested c67f4d7a8fc022674ee6e9c54d6f8c7a3978dbc0:
  visible section words Personal Info/Account Security/
  Applications; Navigation menu still collapsed, hidden
  Signing-in link; 2 sanitized generic console errors without
  raw contents; Account not ready; overall FAIL.
- [Run 42891043095](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42891043095)
  tested fa38fe1de9a1b413c792303aecfa348818ab31bc:
  Account Security accordion clicked, visible/enabled real
  Update button, My Password and Signing in content; **erroneous
  hash-only predicate** prevented form execution; overall FAIL.
- [Run 42891870367](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42891870367)
  tested 1b7e264db74d4ee30a2549ed3384642492d9863a:
  path OR hash + visible Update; actual Account Console form
  submitted; old password denied/new accepted; original
  SSO/Refresh/UserInfo/Backchannel observed; ALL prior and
  RB cases PASS; overall **SUCCESS**. No earlier failures were
  overwritten or represented green.

**Change scope/versions:** Since given starting HEAD
`ee539d1932166c387a7cc1660c50356b2df33d8f` the ONLY
source security/test behavior changed is
`tests/phase3/integration/auth_idp/reset_logout.py`. Diagnostic
changes and checkpoint were made in the same allowed existing
file `coordination/tasks/AGENT-API-AUTH-IDP-01.md`;
the final documentation follow-up appends this checkpoint and
`infra/auth-ci/README.md` inside the ORIGINAL five allowed
PR #22 paths to keep instructions current. Keycloak 26.8.2,
Postgres 17.11, Mailpit 1.32.0, Chromium Playwright 1.64.1
and Docker Internal-only egress denied unchanged. No actual
email, production IdP, model, public service, local Mac install,
version bump, role privilege, SPI/extension, new outbox,
Migration 001–005 or product API/BFF/UI/DB/History modification.

**Recommendation for separate next mission:** Bounded/
enforceable allowed Reset entry surfaces + product-authoritative
Session revocation/reset_gate first. If Account Console, Admin
Reset, Required Action or external identity federation remain
available, standard Logout alone is insufficient as a password
mutation event: separately authorize a tested reliable
authenticated credential-change event/ack/reconcile and fail-safe
product session barrier; don't assume built-in user-event storage
or a received Logout Token provides durable cross-DB delivery.
No solution/production acceptance in this isolated package.

**READY_FOR_REVIEW — STANDARD_RESET_LOGOUT_EVALUATION**,
**Implemented**: standard browser Account Console password
change and four-path measured old Session/Backchannel behavior
plus prior Logout/outage negative tests;
**Tested**: exact green real GitHub Actions source SHA above;
**Accepted**: NONE/SUPERVISOR_PENDING; no Gate, never
`AUTH_PRODUCT_ACCEPTED`. Final documentation-only HEAD
will differ from tested source; verify its own CI before saying
its exact SHA is green.


## IDP-CI-01-AW — BND-IDP-02C controlled Reset-entry SOURCE preparation, independently isolated Realm (2026-11-11)

**Live preflight:** `main` exactly `600bbd68ce8883d960b789320bc8b2454a3ff66c`, corresponding to PR #22 CLOSED/MERGED with EXACT merge SHA. No existing similar 02C branch or PR; created new mission branch `agent/idp-controlled-reset` from exactly that main. Prior PR #22 all four Route/Logout CI success remains accepted only as disposable identity browser proof; no product Auth or Reset revocation.

**Owner and trace:** primary P3M05-A01/A02/A06/A07/A08/A09/A10; supporting P3M03-A01/A03/A08, P3M06-A03/A05/A07, P3M13-A03/A07/A08/A09/A10, P3OP03-R01/R02/R05 non-counting overlay. ADR 0005, original cumulative IdP record, AGENTS, path ownership, pinned IdP workflow/compose/support and existing 01/02A/02B source inspected before writing. No Gate accepted.

**Scope**: new `tests/phase3/integration/auth_idp/controlled_reset.py` only for second synthetic `auth-idp-controlled-ci` Realm; tiny end-of-suite call in existing `tests/phase3/integration/auth_idp/evaluate.py` AFTER old complete 01/02A/02B regression; scoped branch/workflow guard update in existing `.github/workflows/auth-idp.yml`; append `infra/auth-ci/README.md` and THIS same cumulative file. No compose/image version, network, DB product, API/UI/History/contract, migration, custom SPI/outbox, privileged role escalation, real email, deploy or Mac install.

**Standard-only candidate**: resetPasswordAllowed=false, registrationAllowed=false, account-console client disabled, required-action provider UPDATE_PASSWORD disabled, all read back. This is NOT assumed a comprehensive boundary. Test exact direct Forgot and account path, user-authenticated kc_action, preissued execute-actions-email action-token and pre-initialized OIDC Required Action, ordinary and view-users-only operator denied Admin reset, manage-users service account positive and separate-other-user broad-scope probe; must verify old/new credentials independently where relevant. Master bootstrap explicitly outside boundary. Browser uses real Chromium Code+PKCE, state/nonce and signed JWT validation; not a service-session replacement. Tokens/action links, Cookies, user credentials, raw URL/HTML are transient RAM only and never saved/logged.

**Decision**: do not silently claim `FEASIBLE` if standard builtin `manage-users` is broader than target user or any old flow survives; fail-closed `NOT_PROVEN` with full per-route evidence. No claim accepted Password Reset event delivery or product Session revocation. Keycloak 26.8.2 and temporary PostgreSQL 17.11/Mailpit 1.32.0/Playwright 1.64.1 remain pinned and the isolated network/teardown preserved. Public documentation around 26.8 has variable patch tags, so actual 26.8.2 CI/readback is decisive.

**First real GitHub CI status**: NOT_RUN on prepared source; no asserted PASS. Future failures, fixes, numerical HTTP/callback evidence and exact actual run links will be appended ONLY here; preserve all previous checkpoints. `Implemented=SOURCE_PREPARED`, `Tested=NOT_RUN`, `Accepted=NONE/SUPERVISOR_PENDING`. READY_FOR_REVIEW only after reproducible real evidence and explicit limits.


## IDP-CI-01-AX — first actual BND-IDP-02C GitHub CI failure, narrow negative-assertion adapter

**First exact source** `9651c12096fc8fa292b119d90edccfd70ea21f45`:
[GitHub Push Run 42901264824](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42901264824) **COMPLETED FAILURE** after all unchanged prior IDP-01, RA-00..12, RB four-route and Logout regressions passed. **RC-00** second disposable Realm+client, **RC-01** genuine normal user's pre-restriction Code+PKCE sign-in, **RC-02** old action token and pre-started UPDATE_PASSWORD form (while enabled) and **RC-03** exact readback of standard resetDisabled, registrationDisabled, account-console-disabled and UPDATE_PASSWORD-provider-disabled all **PASS**. Failure: `RC-after-lock-browser-and-kc-action` category `AssertionError` before any direct-route result was recorded. No inference of successful or blocked kc_action from this failed phase. The old suite, Docker internal-only network and mandatory teardown passed.

**Minimal patch rationale:** Playwright `expect(locator).to_be_visible` raises `AssertionError` when the standard action is absent; negative form visibility is an expected observation and must not stop subsequent independent credential tests. Catch it ONLY around the candidate password-form visibility assertion; do not catch login callback, Admin permission, or signed token errors. Ensure adversarial action-token/AIA pages that redirect to the isolated test callback are drained explicitly with only a non-secret callback COUNT, never validated as fresh credentials or reported as a login success; otherwise stale Code can contaminate independent OIDC Code+PKCE checks. Independently verify the new `kc_action` target's old password remains valid before any positive service Reset. No production behavior, flow, privilege, version, network or baseline regression changed. Re-run required; status TESTED=EARLY_FAILURE, ACCEPTED=NONE.


## IDP-CI-01-AY — second GitHub 02C CI reached new direct probes; Account test Harness TypeError

[Real Push Run 42902277678](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42902277678) exact source `0386eae268a2088540b741ccb720a6a54d260ff0` **COMPLETED FAILURE** at `RC-after-lock-account-console-direct` with `TypeError`. The old complete IdP-01/02A/02B regressions PASS. New second synthetic Realm creation/Code-PKCE pre-login and pre-issued local UPDATE_PASSWORD action token/in-flight browser form **PASS** (RC-00–02), and exact separate standard restriction toggles/readback **PASS** (RC-03). **RC-04 new user-authenticated direct `kc_action=UPDATE_PASSWORD` probe PASS as a measurement**: real new Update Password form NOT visible, not submitted, **one test callback captured without mutation proof**. **RC-05 Forgot UI/direct request probe PASS as a measurement**: visible Forgot link false, no password form on tested direct GET, no newly issued Mailpit message. These are NOT yet comprehensive entry closure.

[Actual sanitized artifact 13804190569](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42902277678/artifacts/13804190569) confirmed those Boolean/Count values, independently of log labels. No action-token replay, in-flight post-policy form submission, Account Console direct proof or service-role/Admin REST test had been reached yet. The immediate failure arose exclusively from incorrect `await request("GET", LOGIN + "/account/")` where `support.request` is **synchronous requests.Response**, not awaitable. Narrow source fix removes `await`; browser resource loaded and no raw URL, Cookie, token, email, password or HTML logged. No server privileges/config or test acceptance weakened. Overall Run remains **red**. Upcoming CI must reach the later high-risk scenarios.


## IDP-CI-01-AZ — third actual 02C CI, service positive reset negative-assertion fixture mismatch

[GitHub Push Run 42903195429](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42903195429) exact SHA `1c8d8ef754804ee3b2f100e72a5fa436220acd46` **COMPLETED FAILURE** at `RC-service-role-real-password-change` `AssertionError`. All earlier IDP-01/02A/02B regression suites PASS. Second distinct disposable Realm created successfully, stored/readback standard resetPasswordAllowed=false, registrationAllowed=false, account-console enabled=false, UPDATE_PASSWORD required-action provider enabled=false. RC-04 direct real user-authenticated `kc_action=UPDATE_PASSWORD`: no password form, no submit, **one OIDC callback not treated as password mutation**. RC-05 Forgot link hidden, direct route no password form/no new email; RC-06 Account Console direct route HTTP 200 (static document), no password Update button/form. RC-07 old preissued email action-token URL: no password form or submit. RC-08 preexisting real UPDATE_PASSWORD form was SUBMITTED after the restriction and one callback observed (**NOT proof of password actually changed**, independent credential verification still required). RC-08a new direct user's old credential still accepted. RC-09 view-users-only operator Admin Reset returned **HTTP 403**. All RC-00..09 labels PASS as bounded observations; no `RC-10` positive service reset / independent old/new login yet and no valid final single-entry verdict.

[Sanitized artifact 13804216453](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42903195429/artifacts/13804216453) is the source of the above numeric values. Next code change ONLY aligns negative old-password browser login with proven existing `evaluate.py:login(expect_failure=True)`: check network-idle actual login form and explicitly reject any callback carrying THIS flow's state; DO NOT require a theme-specific `#input-error` CSS selector, which is not a security property. In addition record only the actual HTTP STATUS returned by the trusted service's standard reset call before independent browser denial/acceptance. This is not a weakened negative test: callback state-binding and real browser login rejection remain mandatory. Root/scope not changed. All earlier failure history remains preserved. Test must be re-run; no service or stale-flow success implied from this red Run. `Accepted=NONE`, overall still NOT_PROVEN.


## IDP-CI-01-BA — BND-IDP-02C takeover and fail-closed unauthorized ordinary user Admin API probe

**Live preflight:** requested `main` SHA `600bbd68ce8883d960b789320bc8b2454a3ff66c` is exact and PR #22 is **MERGED** with this exact SHA. Existing branch `agent/idp-controlled-reset` already at
`3fbbd7e8d9507dbf870330d9b6188fed6d3cc77c` and existing independent
Draft [PR #23](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/23)
already OPEN, five authorized paths only. **Reused** the existing
02C work, no new branch/PR/Realm apart from its existing synthetic
CI fixture; all previous IdP-01/02A/02B regressions unchanged.

**Real tested prior SHA** `3fbbd7e8d9507dbf870330d9b6188fed6d3cc77c`:
both [Push 42904227495](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42904227495) and [PR 42904237087](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42904237087)
COMPLETED **FAILURE by explicit policy denial** `RC-adversarial-bypass-final-denial`. All previous IDP suites PASS, second Realm RC-00..11 PASS as **measurements**, including:
- Standard `resetPasswordAllowed=false`, registration disabled,
  `account-console.enabled=false`, and
  `UPDATE_PASSWORD.enabled=false` independently read back.
- New `kc_action=UPDATE_PASSWORD` produced no password form
  (1 ordinary OIDC callback is **not** credential change), direct
  Forgot link absent/no update form/no local Reset mail;
  direct Account Console returned static HTTP 200 but no active
  Update button/form. Pre-policy minted UPDATE_PASSWORD action
  link produced no update form on tested browser attempt.
- **Authenticated old pre-policy UPDATE_PASSWORD form remained usable
  after policy hardening**. Real form submitted and independent new
  credential OIDC login ACCEPTED: observed `inflight-form` bypass
  of any *single-entry* guarantee.
- Restricted operator `realm-management/view-users` received
  Admin REST reset HTTP 403.
- Separate intended reset service `realm-management/manage-users`
  received HTTP 204 when resetting its target; after that the
  original credential was DENIED and new credential ACCEPTED by
  independent genuine OIDC/PKCE browser checks.
- **Same service** used its **unchanged** built-in `manage-users`
  role against a second synthetic unrelated account, HTTP **204**:
  permission is broader than an individual target. Not a safe
  per-user credential Reset entitlement.
- Entire original IDP regression/network cleanup passed, no real
  email, model, migrations, product API/Auth/DB, production events
  or Session proof. Real sanitized JSON artifact
  [13803748704](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42904227495/artifacts/13803748704)
  confirms `RC_bypass.bypass_classifications=["inflight-form"]`,
  `RC_service_scope.other_user_reset_http=204`,
  `RC_service_controlled_reset_http=204`, verdict NOT_PROVEN.

**Exact remaining narrow proof added for user request**: the existing
real ordinary synthetic OIDC user now also invokes the **direct**
Admin REST reset-password endpoint with its own genuine unprivileged
access token; MUST receive 401/403, followed by genuine successful
OIDC sign-in with the original credential showing that neither
ordinary-user nor `view-users` operator unauthorized calls changed
password. Test-only code unchanged other than this negative operation
and its sanitized HTTP count in `RC_role_limits`. Do NOT modify
`manage-users` entitlement or disable in-flight bypass to chase
green. New source CI to rerun on this branch. **02C intended
conclusion remains NOT_PROVEN** and **overall CI MUST remain red**
when in-flight bypass or cross-user service reset is observed.
No policy/Gate or AUTH_PRODUCT_ACCEPTED.

**Official candidate next investigation, NOT assumed present/enabled
in pinned 26.8.2**: Keycloak fine-grained administration includes
`reset-password` scope and can delegate per-user management with
policy evaluation, whereas built-in `manage-users` bypasses that
fine-grained check; must separately reproduce scoped and target-denied
Admin REST tests **without** global `manage-users` in a newly
authorized package, and still address pre-policy in-flight action
form or enforce a Reset drain/barrier before claiming single entry.
Trusted root/realm-admin and outage/recovery remain outside
policy, no infrastructure admin restriction asserted.


## IDP-CI-01-BB — BND-IDP-02C final bounded controlled Reset evaluation / two real bypasses (2026-11-10)

**Base and handoff:** verified live main `600bbd68ce8883d960b789320bc8b2454a3ff66c`
(the precise MERGED PR #22 SHA); adopted pre-existing branch
`agent/idp-controlled-reset` and the SAME pre-existing open
Draft PR #23. No duplicate mission, branch, PR, fixture Realm
or checkpoint. Starting head of adopted branch was
`3fbbd7e8d9507dbf870330d9b6188fed6d3cc77c`. The previously
tested failed CI events and narrow fixes remain in AX–BA.
Only source continuation: one additional synthetic
**ordinary OIDC access-token bearer** direct Admin REST reset
negative and independent old-password survival confirmation,
with no policy, security acceptance, Keycloak Realm setting,
version, product or workflow change.

**Exact tested source SHA**
`eedb648e32b79c990a476783b5e3df26bd4a3033`.
[Real GitHub Push Run 42907619285](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42907619285)
**COMPLETED / FAILURE** precisely because `RC-adversarial-bypass-final-denial`
asserted the **fail-closed** verdict. Original IdP-01 + all 02A
RA-00..12 + all 02B four password-route and OIDC Logout/
Backchannel JWT replay/receiver outage regressions PASS in same
run, BEFORE new RC tests. RC-00..RC-11 PASS **as bounded
individual observations**, not as evidence that the strong
single-entry hypothesis was satisfied. `NETWORK_GUARD_PASS`,
Keycloak/Postgres/Mailpit readiness and mandatory
`EPHEMERAL_IDP_TEARDOWN_CHECK_COMPLETE` verified; no real email,
external model, public network, deploy or product Session.

**Actual sanitized artifact:** [auth-idp-sanitized-42907619285,
artifact 13805158908](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42907619285/artifacts/13805158908),
3-day CI retention; read directly as JSON. `overall=FAIL`,
`current_stage=RC-adversarial-bypass-final-denial`,
`RC_verdict.controlled_entry=NOT_PROVEN` and
`RC_bypass.bypass_classifications=["inflight-form"]`.
No token, password, cookie, mail body/action-token link or
browser URL/query entered the artifact.

**One distinct REAL second Keycloak Realm only**
`auth-idp-controlled-ci` under existing pinned Keycloak 26.8.2,
Postgres 17.11, Mailpit 1.32.0, Playwright Chromium 1.64.1
and Docker internal-only network; earlier realm
`auth-idp-ci` and its source/regressions untouched.

**Standard Realm restrictions applied and READ BACK:** 
`resetPasswordAllowed=false`;
`registrationAllowed=false`;
standard OIDC `account-console.enabled=false`;
built-in Required Action `UPDATE_PASSWORD.enabled=false`.
These DO NOT automatically revoke tokens or already rendered
password-update challenges. Root/bootstrap and realm-admin
remain privileged recovery authorities OUTSIDE these restrictions.

### BND-IDP-02C actual adversarial matrix — careful interpretation

| Origin / attack or approved route | Real post-policy result | What that proves / does NOT prove |
|---|---|---|
| New normal-user Forgot/Reset UI + tested direct URL | Forgot link not visible; no password form; zero new local reset mail | Negative for tested request; hiding link alone not taken as comprehensive proof |
| Direct real `kc_action=UPDATE_PASSWORD` authorization | No password form, no submit; **one OIDC callback** | Callback is NOT password mutation; original password independently still accepted |
| Direct browser Account Console URL | HTTP **200 document**, but no Update button or password form; standard account-console Client disabled | 200 static document is NOT proof a usable password-change feature survives; no actual mutation observed |
| UPDATE_PASSWORD action-token link issued before policy | No actual password form, no submit; zero callbacks | Tested stale link did NOT change credential; doesn't prove all other action tokens or external flows blocked |
| **UPDATE_PASSWORD in-flight real form opened BEFORE restriction** | Form submitted AFTER readback, one callback, and **independent new-password OIDC login succeeded** | **CONFIRMED SELF-SERVICE BYPASS** of strict single-entry policy (old in-flight state survived policy change) |
| Ordinary nonadmin's real OIDC Access Token → direct Admin reset-password | HTTP **401**, original password still accepted in real browser | Ordinary identity cannot perform tested Admin Reset |
| Restricted operational service with only `view-users` → Admin Reset | HTTP **403** | Denied as expected |
| Intended reset service with only built-in `realm-management/manage-users` → target synthetic account | HTTP **204**, independent OLD DENY / NEW ACCEPT | Genuine standard service reset possible, but alone NOT bounded least privilege |
| **Same service** → a second unrelated synthetic account | HTTP **204** | **CONFIRMED OVERBROAD SERVICE AUTHORIZATION**, not target-scoped |
| Trusted root/realm-admin/recovery administrators | Explicitly OUTSIDE negative model | No claim infrastructure/root privileges are restricted |

**Critical interpretation:** `manage-users` is a broad
built-in role in this pinned tested configuration. Its privilege
scope cannot be represented as a single-account Reset service
entitlement. A controlled service endpoint and an actual service
credential update can work while exclusive Reset entry is still
**NOT_PROVEN**. The pre-policy in-flight real password form
alone disproves admission through ONLY the intended new service,
even if fresh Forgot/Account/kc_action paths appear disabled.
The green individual probes (RC-00..11) coexist with the real
overall FAIL. No simulated login/reauth or fake reset success.

**Independent standard administration design option, NOT
implemented or tested here:** Keycloak fine-grained admin
permissions can conditionally distinguish `reset-password`
from broader `manage`, with per-user/policy restrictions;
in its administrative role model, built-in global `manage-users`
bypasses these finer checks. The 26.8 documentation describes
this capability; it still needs exact 26.8.2 Admin REST
configuration/readback plus REAL positive in-scope and negative
out-of-scope credential resets in a separately authorized
isolated test. Official documentation:
`https://www.keycloak.org/docs/26.8.0/server_admin/` and
`https://www.keycloak.org/docs/latest/server_admin/` —
do NOT mistake variant patch or current online docs for
pinned-version proof. First investigate policy reset scope
and avoid broad manage-users entirely. Independently
establish a **transition/drain barrier** for started action
tokens/forms or bounded cancellation/expiration before
exclusive service Reset begins. Without both solutions,
single-entry claim remains unproven. Root/realm-admin and
break-glass need separate trust policy, not magic IdP
restriction.

**Decision: NOT_PROVEN for exclusive controlled Reset.** 
Current CI intentionally fails closed; do not soften
`RC-adversarial-bypass-final-denial`, disable the in-flight
probe, or consider a CI PASS necessary to say the evaluation
completed accurately. The next narrowly scoped package should
evaluate same-version fine-grained per-user reset-password
authorization and a verified pre-existing-flow drain/cancel
boundary, then re-run ALL direct/browser/token/Admin positive
and negative cases. Product-owned DB Session/epoch/revocation
barrier is a separate subsequent integration, NOT tested here.
No external Reset delivery/Outbox/ack, no product Auth
Session and no Gate.

**Implemented:** two-Realm standard-only CI candidate,
in-flight token/action challenges, actual browser and Admin
REST permission & broad-role counterexamples;
**Tested:** actual real GitHub CI, earlier complete IDP
regressions pass, case RC-00..11 measured, final
NOT_PROVEN deliberately RED at RC-adversarial-bypass-final-denial;
**Accepted:** NONE / supervisor pending. 
**READY_FOR_REVIEW — CONTROLLED_RESET_ENTRY_PROOF** with honest
negative result, no `AUTH_PRODUCT_ACCEPTED` or Merge.
Only five previously authorized files changed since
starting main; final documentation-only commit (if any)
does NOT convert any red tests green.


## IDP-CI-01-BC — scoped FGAP v2 and authentic pre-policy session transition probe (2026-11-11)

**Preflight observed** on 2026-11-11: main `600bbd68ce8883d960b789320bc8b2454a3ff66c`,
existing branch `agent/idp-controlled-reset` at
`32b690dfadf15a2bb044199d668b1abfc4136756`, same original
open Draft PR #23. Final PR CI 42908568238 is COMPLETE FAILURE
on exactly this HEAD, not PASS; logs show prior IDP/RA/RB cases,
RC-00..11 as measured, then the deliberate security denial.
No parallel branch or PR or new realm.

**Documentation checked before changing the disposable fixture:**
Keycloak 26.8.x supported FGAP v2 (NOT deprecated preview v1)
is standard realm opt-in `adminPermissionsEnabled`. Its Users
`reset-password` operation supports explicit per-UUID scope via
`admin-permissions` client policy and permission endpoints; broad
built-in admin role skips the fine-grained decision. Official guide:
https://www.keycloak.org/docs/26.8.0/server_admin/
and REST: https://www.keycloak.org/docs-api/26.8.0/rest-api/index.html.
This documentation is NOT same-patch readback or runtime proof.

**Session transition investigation:** Standard Admin REST
`POST /logout-all` removes user sessions, not explicitly all
authentication sessions. Official Keycloak issue #49007 concerns
persisting in-progress authentication sessions after logout. To avoid
confusing expiry/logout and Required Action cancellation, source adds
a SECOND already-rendered UPDATE_PASSWORD form opened BEFORE policy
lock, and a SECOND pre-issued action-token link; after preserving the
original RC-08 undrained bypass measurement, attempts both after the
real standard global user-session logout (same form without reload).
Independent fresh OIDC credential checks at final denial are mandatory.
This is a disposable-only global logout test, NOT a proposed viable
per-user production barrier or evidence of durable token revocation.

**Implemented in this commit:** limited `controlled_reset.py`
tests only, documentation append in `infra/auth-ci/README.md` and
this SAME cumulative checkpoint. No other file, network, product
module, migrations, runtime, IdP version, SPI, outbox or workflow
modification. First original 01/02A/02B suites retained, original
strict fail-closed assertion retained; extra RC-12..14 measurement
labels are NOT additional canonical checklist completions.

**Tested:** NEW SOURCE PENDING REAL CI (do not report PASS before
exact SHA and real Run); historical tested SHA
`eedb648e32b79c990a476783b5e3df26bd4a3033`,
historical FINAL `32b690dfadf15a2bb044199d668b1abfc4136756`
and failures including 42908568238 remain archived above.
**Accepted:** NONE / SUPERVISOR_PENDING.


## IDP-CI-01-BD — real first FGAP/Logout Run and one narrow safe stage probe (2026-11-11)

**Exact tested source:** `5a488acaccb56d1fca598f1c92a3c0e6e813db33`.
[Real PR CI 42910810577](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42910810577)
completed FAILURE at `RC-fgap-v2-exact-permission-config-readback`,
category AssertionError; real job `130160659449`, sanitized artifact
`13808080860` (`overall=FAIL`). Original IDP-01 / 02A / 02B,
RC-00..11 and RC-12 logout-all measurement labels all reached.
Ephemeral network deny and teardown PASS. No scoped service permission
success or unauthorized target proof occurred; FGAP remains UNVERIFIED.

**Actual sanitized logout observation:** standard
`POST /admin/realms/{realm}/logout-all` returned HTTP 200.
The independently preserved REAL UPDATE_PASSWORD form created
BEFORE locking restrictions and NOT reloaded was successfully
submitted AFTER logout-all, with one callback. The second
preissued action link presented no password form and no callback.
The post-logout independent credential check had not yet
been reached at the subsequent FGAP failure, so password mutation
after logout is NOT yet independently verified. The original
undrained in-flight form mutation remains previously confirmed.

**Narrow correction only:** add static sanitized stage labels for
individual existing FGAP configuration/readback steps, without
changing permission scopes, assertions, service roles, IdP settings,
original suites, operation conditions, versions or acceptance logic.
This differentiates unsupported capability / REST setup / readback
failures with ONE more real CI. Secrets, response bodies, user UUIDs,
credentials, HTTP URLs and tokens remain undisclosed. If standard
configuration remains unsuitable, stop and report to supervisor;
do not pursue speculative retry cycles.

**Implemented:** diagnostic stage names only in one test file,
append cumulative checkpoint here.
**Tested new SHA:** pending real CI; **Accepted:** none.


## IDP-CI-01-BE — CI proven narrow FGAP REST readback mismatch and full-object retry (2026-11-11)

**Exact tested SHA** `8559fd771c5f96a599506a9c495500e60406eab3`:
[real PR Run 42911896683](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42911896683)
COMPLETED FAILURE at sanitized diagnostic
`RC-fgap-v2-exact-permission-readback` with AssertionError,
AFTER the standard realm activation/readback, auto-created
`admin-permissions` discovery, service-account no-broad-role
readback, `policy/user` creation, `permission/scope` creation,
and permission list fetch. This pins the failure to the naive
assumptions about list-entry readback fields, not failure to
activate the supported FGAP V2 or create the permission.
Original legacy regressions and real 02C baseline routes
remain observed; there was no scoped target/non-target reset
test, hence service scope UNVERIFIED. Cleanup passed.

**Bounded source correction:** The official 26.8 server-admin
guide documents list/read permission endpoints independently.
After identifying the exact server-created permission ID from
the listing, GET that single full scope-permission by ID and
verify persisted name, exact Users resourceType, exact
`reset-password` scope, ONLY the target user UUID and the
linked policy. Export only four boolean checks, no UUIDs.
Do NOT remove or relax these four security properties; future
direct Admin REST and genuine old/new OIDC tests remain
necessary. If Keycloak representation differs, record actual
failed check and stop further speculative changes.
No other tests, versions, role scopes or core API/UI/DB
modules changed. **Tested new source:** pending real CI;
**Accepted:** NONE, security verdict NOT_PROVEN.
