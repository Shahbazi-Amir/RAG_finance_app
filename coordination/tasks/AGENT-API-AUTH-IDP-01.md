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
