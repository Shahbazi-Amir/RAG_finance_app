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
