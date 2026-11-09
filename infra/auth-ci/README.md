# AUTH-IDP-01 — isolated Keycloak candidate, NOT product Auth

Starting commit: 4831ff90470028abab1dd6dd78834fcf3446a716
Branch: agent/auth-idp-ci. GitHub Actions ONLY. No Mac install, product API/UI/DB connection, real SMTP, real account, public endpoint, purchase or deploy.

## Specific pinned versions and official sources (checked 2026-11-08)

- Keycloak 26.8.2, released 2026-11-05: https://www.keycloak.org/2026/11/keycloak-2682-released
- Official Keycloak container using quay.io/keycloak/keycloak:26.8.2: https://www.keycloak.org/getting-started/getting-started-docker
- PostgreSQL 17.11, identity database only; official Keycloak support for 17.x: https://www.keycloak.org/server/db
- Mailpit 1.32.0 (October 2026): https://github.com/axllent/mailpit/releases
- Mailpit REST: https://mailpit.axllent.org/docs/api-v1/
- Keycloak SMTP/verify/reset/OTP/lockout: https://www.keycloak.org/docs/latest/server_admin/
- Keycloak OIDC: https://www.keycloak.org/securing-apps/oidc-layers
- Keycloak Admin REST provisioning: https://www.keycloak.org/docs-api/latest/rest-api/
- GitHub host Python 3.13 for static checks; isolated browser uses official Playwright Python image v1.64.1-noble plus requests 2.32.5, PyJWT[crypto] 2.10.1, pyotp 2.9.0, Playwright 1.64.1 Chromium.

Keycloak uses start-dev with HTTP on internal Docker hostname keycloak:8080 only (no published host port) because this is an isolated evaluation, never production TLS.

## Network and secret containment

All three containers use a single Docker internal network (authidpci_authisolated, Internal=true), no outside-facing network. Identity DB and SMTP have no published ports. NO host ports are published; Keycloak/SMTP/DB/API and Chromium callback run solely inside the internal Docker network. network_guard.py inspects actual containers, exact image tags, one network per container and allowed HostIp/HostPort; the workflow attempts outbound TCP 1.1.1.1:443 from inside the isolated DB container and MUST fail. Chromium allows only Keycloak internal DNS and localhost callback; Python API harness allows only keycloak/mailpit internal Docker DNS. The browser runner is also containerized on the same internal-only network. Mailpit has no outbound relay. It is Docker internal network + actual deny probe, not the Mailpit label, that enforces server-side egress restriction.

Synthetic one-time passwords/DB/admin credentials come from runner memory or chmod-0600 temporary file. User emails first@example.test, second@example.test and realm-operator@example.test only. No SMTP messages, action links, code, cookies, tokens, reset URLs or TOTP seeds are ever published to logs or artifacts. Test failure prints only case ID/type, not unsafe exception details. Cleanup unconditionally removes DB volume, containers, network and credential file. Artifact only sanitized report.json (test IDs/versions/revocation status), 3-day retention.

## Actual test matrix (NOT_RUN until verified on exact GitHub SHA)

IDP-00 realm policy, password strength, brute-force protection, OIDC discovery, actual separate DB.
IDP-01 real browser self-registration A+B, no full login while unverified.
IDP-02 SMTP-captured verification link, signed action, consumed replay not a fresh privilege.
IDP-03 distinct subjects via two actual Authorization Code+S256 PKCE browser logins.
IDP-04 real refresh succeeds before logout.
IDP-05 old authorization code replay denied.
IDP-06 real Forgot Password and local Reset once.
IDP-07/08 old password fails and new password succeeds.
IDP-09 expired action link denied.
IDP-10/11 manager TOTP enrollment mandatory, password-only and wrong-OTP denied, correct OTP accepted.
IDP-12/15 manager granted ONLY realm-management view-users; normal user cannot use admin REST.
IDP-13 JWT JWKS signature, exact audience, issuer, nonce, expiry and tampering validation.
IDP-14 unregistered redirect URI refused by real Keycloak.
IDP-16 real IdP admin-initiated user-session logout: old refresh result, old userinfo result and old locally signed access JWT validation reported separately, not conflated.
IDP-17 bounded manager role and BFF/product follow-up.

The OTP manager case proves this configured actor cannot bypass 2FA on tested logins, NOT that all admin recovery paths or removal of OTP have been secured. Resetting password is NOT blanket revocation of independently issued JWTs, and local JWT signature can remain verifiable until its exp. Product BFF session revocation is outside this mission.

## Exact CI commands

docker build -f infra/auth-ci/Dockerfile.test-runner -t auth-idp-runner:ci infra/auth-ci

docker compose --env-file $RUNNER_TEMP/idp-ci.env -f infra/auth-ci/compose.yml up -d
python tests/phase3/integration/auth_idp/network_guard.py
python -m compileall -q tests/phase3/integration/auth_idp
docker run --rm --network authidpci_authisolated auth-idp-runner:ci python /suite/evaluate.py (with read-only suite/credentials mounts and a sanitized-report volume)
docker compose --env-file $RUNNER_TEMP/idp-ci.env -f infra/auth-ci/compose.yml down --volumes --remove-orphans

All command/test results MUST be taken from actual GitHub CI. No claim that a future plan passed. Next separate, authorized package: Next BFF server sessions/CSRF, trusted FastAPI Auth, (issuer,subject) stable internal owner, RLS under two authenticated actors, secure logout/reset, enforced admin MFA and policy. NO product connection here.

## Authorized additional evidence A/B/C (2026-11-09; pending CI on modified source)

A: Negative callback state (mismatched/missing) runs through the same
checked_callback_exchange path as positive Code+PKCE, and a genuine unspent
Code remains exchangeable only with the correct callback. Fresh independent
authorization Code tests PKCE verifier mismatch. Signed genuine ID tokens
must reject nonce/issuer/audience misexpectations with precise exceptions;
the previously accepted Code replay assertion remains. Each case is fail-closed.

B: A separate real second-user OIDC login retains its original browser context,
cookies and access/refresh tokens before reset. A real prompt=none OIDC Code
flow proves SSO beforehand; after reset the exact old browser is retested
BEFORE old-token refresh to avoid modifying session evidence. Report actual
HTTP statuses, independent JWKS JWT verification and silent SSO outcome; do
not assume desired revocation. This is not a product BFF or frontchannel logout.
Admin-initiated logout now ASSERTS UserInfo denial rather than merely noting
its status.

C: One extra synthetic policy-probe account, local-only UPDATE_PASSWORD mail,
real weak-password rejection and strong-password acceptance on the action
form, followed by independent login proofs. A maximum of seven password-failure
browser attempts with deliberate spacing checks the real Admin REST brute-force
failure count and temporary disabled state. During lock, correct credentials
must fail. Unlock is observed by polling the read-only Keycloak status, followed
by a successful login; NO admin clear/force-logout, no raw cookies or tokens
and no external SMTP. CI-only waitIncrementSeconds=12, failureFactor=5,
maxFailureWaitSeconds=30; no production policy recommendation is implied.

These additions are NOT_RUN until exact-SHA real GitHub CI results and the
cumulative mission checkpoint attest otherwise. Code, password, OTP and all
action URLs remain in process only.

## C test correction after first A/B real CI failure

Actual 3554a72e... push and PR failed only when an UPDATE_PASSWORD
action link was attempted against the newly admin-created credentialless
policy-probe account; prior actual A and B cases PASS and the old token
observations are recorded in the cumulative task checkpoint. The stage name
did not isolate capture from action URL extraction, so neither was asserted
as the exact cause. The test now uses an ALREADY real SMTP-proven synthetic
verified second user for the behavioral weak/strong password update action,
with distinct safe stage markers. An independently seeded synthetic third
account is still used ONLY for brute-force lockout/expiry and has a real
credential for successful-login baselines. The negative old password checks
include both the weak candidate and the previous known valid password.
No Admin user-session logout or lockout-clear endpoint is called.
This is a source correction; actual retest remains required.

## Second C failure; browser-session reset correction

Exact  aeebdf8c1f6876d32057fb10ce5b73a3552e912d push
Run 42615811964 reached A/B PASS again, then failed with AssertionError
at policy-action-browser-form after actual local message capture and URL
parsing; the standalone admin-created UPDATE_PASSWORD action opened
in a new browser context did not expose the expected password form.
Do not claim the realm rejected password policy: no C policy assertion
was reached. C now uses the exact real browser-initiated Forgot Password
form and locally captured Reset action in the SAME original browser
authentication context that had already passed IDP-06 in this run.
It tests weak then strong password in that real Reset form and verifies
them via independent logins. The separate synthetic policy-probe still
covers read-only brute-force status and natural timeout. No change to
network, workflow, public API or realm authorization.
