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


## BND-IDP-02A — Standard fresh-credential reauthentication boundary (2026-11-10)

**Status:** source prepared for an *independent Draft PR* on
`agent/idp-reauth-proof`; **NOT_RUN until actual GitHub Actions evidence**.
This continues the SAME cumulative
`coordination/tasks/AGENT-API-AUTH-IDP-01.md`. Previous isolated
IDP-00..17 / IDP-A/B/C baseline cases remain part of every run.
No Keycloak version upgrade, SPI/extension, custom outbox, DB schema,
new product API endpoint, browser product login, BFF session, email relay
or real production credentials are used.

**Pinned topology:** exactly the existing Keycloak `26.8.2`,
identity-only PostgreSQL `17.11`, Mailpit `v1.32.0`, Playwright
Chromium `1.64.1` and its existing in-network callback. Docker
`Internal=true`, zero published ports, actual egress-denial probe,
only `.test` synthetic mail addresses, transient secrets in memory,
sanitized report.json only, complete volume teardown. Two extra synthetic
verified users `fresh-reauth@example.test` and
`required-reauth@example.test` are provisioned by the existing CI-only
Admin fixture, never in product DB.

### Standard Keycloak candidate options, not an acceptance decision

- Built-in Browser flow **Cookie** can complete ordinary OIDC authorization
  with old SSO without another password. This is NOT proof of credential
  freshness, no matter whether the returned ID Token has a valid signature.
- OIDC `prompt=login` with `max_age=0` is a standard client-initiated
  interactive reauthentication request. CI requires a *real password form*
  on the existing pre-Reset cookie context, **old password denied**, actual
  newly changed password **entered and accepted**, distinct Code+S256 PKCE
  and strict callback state/nonce/issuer/audience/one-time exchange.
  A fresh, signed ID Token `auth_time` in the real challenge window is
  additional evidence **but never suffices alone**. `acr`/ `amr`
  are recorded only as presence/type/limited LoA hints: they cannot prove
  exactly which password was entered, what user interaction happened,
  or that an external product Session was revoked.
- Keycloak built-in **Send Reset Email** execution has configurable
  `force-login` `true` / `false` / `only-federated` (default). The
  experiment sets `true` via the standard Keycloak Admin REST
  `/authentication/executions/{id}/config` endpoint, then RE-READS the
  stored config. It changes only the isolated test realm. Even `true`
  is **not** an authenticated event to the separate product Session DB,
  does NOT revoke all pre-existing independent browser SSO/refresh/access
  credentials, and cannot be used to promise bounded reset propagation.
- For `prompt=none`, Keycloak may issue ordinary Code while an old SSO
  remains valid. The test observes that separately, and requires
  `prompt=none&max_age=0` to return an interactive-login-required
  error, never treating a silent Code as fresh. If real Keycloak issues
  a Code despite the `max_age=0` negative, the test **fails** and the
  configuration is considered BLOCKED for this assertion.
- **Forgot/Reset:** real browser-initiated reset + captured local-only mail
  with old/new password tests. Force-login option is tested only in this
  disposable realm.
- **Required Action UPDATE_PASSWORD:** separate synthetic user has the
  built-in required action, actual password form and independent old/new
  login; this alone is not accountwide logout or proof of later fresh reauth.
- **Admin Reset:** dedicated synthetic Admin REST credential-reset request,
  independent old/new browser password checks; **no forced user logout**
  or read-only event acknowledgement converted to a product Session reset.
- **Account Console password change:** standard Keycloak feature, but this
  fixture does not currently exercise its separate Account Console
  authenticated credential-editing UI/API or all federated/required-action
  branches; **NOT_TESTED / NOT_COVERED** until a separately authorized
  browser harness exists. External Admin Reset/Account Console/Required
  Action events are NOT proven durably or promptly delivered into a product
  DB. No fake `finish_simulated_reauth` substitute is used.

### Planned real-browser adversarial matrix

`RA-00` standard flow inspection and `force-login=true` readback;
`RA-01/02` initial real password OIDC login and ordinary old-browser
SSO; `RA-03` real Forgot/Reset old/new credential;
`RA-04/05/06` same original SSO cookie cannot obtain *fresh*
authentication without real new password form, old password fails and
new succeeds with signed `auth_time`;
`RA-07` wrong/missing state, wrong issuer/audience/nonce and code replay
denials (also preserve prior A01–A06 independent PKCE tests);
`RA-08` old normal SSO/refresh/access after Reset independently observed;
`RA-09` no `prompt=none&max_age=0` silent Code;
`RA-10` Admin Reset; `RA-11` Required Action;
`RA-12` bounded evidence verdict. No criterion may be silently waived.
The actual `PARTIALLY_PROVEN` verdict is permitted only after all
mandatory cases execute successfully; if a new negative fails, report
the actual blocker and **BLOCKED**, never a fabricated PASS.

**External Reset limitation:** No standard OIDC `auth_time`, `acr`,
`amr`, `max_age` or `force-login` setting by itself guarantees
durable cross-database delivery of every credential event, bounded
all-product-session invalidation, or invalidation of already-issued
locally verified JWTs. Evidence must not say `PROVEN` globally.
Refer to ADR 0005 and the existing IDP-01 observations; production
Auth, Keycloak configuration changes, OTP/passkeys/federated MFA and
full product Gates remain out of scope.

Official references:
- https://www.keycloak.org/docs/26.8.0/server_admin/ (built-in
  authentication flow, Forgot Password, AIA, max_age and OIDC prompt);
- https://www.keycloak.org/docs-api/26.8.2/rest-api/index.html
  (standard Admin REST configuration and password credential actions);
- https://www.keycloak.org/securing-apps/oidc-layers
  (OIDC flows/verification);
- https://www.keycloak.org/docs/26.8.2/server_development/
  (SPI explicitly *not* used).

CI runs the same pre-existing `.github/workflows/auth-idp.yml` commands
with the push/PR branch guard extended to
`agent/idp-reauth-proof`. No service is published. All case results and
version/status values must be verified from the actual sanitized CI
artifact or GitHub job log before supervisor review.


## BND-IDP-02B — standard Logout & Reset coverage, CI-only

**Source prepared, not accepted until actual green CI.** Existing
IDP-01 and RA-00–RA-12 real Chromium/Keycloak tests execute FIRST
and unchanged. The new `reset_logout.py` uses only the same pinned
Keycloak 26.8.2, identity PostgreSQL 17.11, Mailpit 1.32.0 and Playwright
1.64.1 browser in the egress-denied Docker-internal CI network.

**Account Console** is exercised via its real browser Account Security /
Signing in / Password Update screen; Forgot/Reset (local captured email),
UPDATE_PASSWORD Required Action and Admin Reset remain separate routes.
Four independent synthetic pre-change browser contexts/Refresh/Access
credentials are measured after each change without confusing successful
new-password login with invalidating previous credentials. Standard built-in
IdP user event type enums are observed read-only, NOT guaranteed delivery.

A minimal `IsolatedLogoutReceiver` is co-located in the existing
ephemeral browser runner at `idp-logout-receiver:8788`, **internal Docker
DNS only, no published ports**. Keycloak test OIDC client's standard
backchannel.logout.url and session.required settings are configured and
read back. Real POST Logout Tokens are verified with Keycloak JWKS RS256,
issuer, audience, iat/exp, events, sid/sub, nonce prohibition and unique
jti. Negative tests verify replay, forged/broken signature, policy and
expected issuer/audience. Receiver memory is test-only, not production
durability, and no Token/JWT/Cookie/action URL is ever logged or written
to artifacts.

Standard OIDC end-session and Admin user Logout are evaluated separately.
A real receiver stop (closed TCP port) precedes one Admin Logout, then
restart and 4-second bounded observation. Retry, retention and recovery
are recorded only if observed; neither a delivery receipt nor the Keycloak
built-in event database is a verified durable cross-DB outbox. No product
Session/BFF/History wiring, SPI, migrations or live side effects.
Security verdict remains BLOCKED until an independently accepted product
revocation barrier and complete credential-change event coverage.


## BND-IDP-02B Account Console blocker resolved in isolated browser (2026-11-10)

**Current evidence supersedes only the earlier NOT_RUN/UI BLOCKED fixture note
above**; earlier red GitHub Actions runs remain available as audit history.

[Full real GitHub CI Run 42891870367](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42891870367)
completed **SUCCESS** on exact tested source SHA
`1b7e264db74d4ee30a2549ed3384642492d9863a`.
All original IDP-01/RA-00–12 and new RB cases PASS, including
a real Keycloak Account Console password change from a synthetic
Chromium account, followed by independent old-password DENY and
new-password ACCEPT OIDC browser sign-in.

**Harness root cause:** The `Account Security` accordion button was
initially collapsed; selecting `.first` hidden anchors or an unrelated
Navigation dropdown never exposed `Signing in`. The actual Account
Console uses a **path-based** SPA route after clicking its visible
security button/link, while the old harness demanded a Hash/fragment
route exclusively. The corrected harness explicitly sets 1440×900
page viewport, reads standard `account-console` client state
without granting new permissions, awaits conditionally visible/enabled
controls, enumerates EVERY match, expands the actual visible
Account Security accordion, follows the visible Signing-in link,
and clicks the real Password Update UI. Safe HTTP status, JS
error class and request failure counts are captured without logging
raw URLs/queries, page text, Cookie, JWT, email or password. No
forced element click, DOM scripting or bypass.

**Observed genuine 4-route matrix in that green CI (all separate
synthetic pre-change sessions):**

| Password route | OLD / NEW | Original SSO silent | Original Refresh | Original UserInfo | Backchannel during mutation |
|---|---|---|---:|---:|---:|
| Forgot/Reset local mail | DENIED / ACCEPTED | survived | HTTP 200 | HTTP 200 | 0 |
| Account Console real UI | DENIED / ACCEPTED | survived | HTTP 200 | HTTP 200 | 0 |
| Required Action | DENIED / ACCEPTED | survived | HTTP 200 | HTTP 200 | 0 |
| Admin Reset | DENIED / ACCEPTED | survived | HTTP 200 | HTTP 200 | 0 |

Keycloak user-event type observations: Account Console and Required
Action showed UPDATE_CREDENTIAL/UPDATE_PASSWORD in bounded test windows;
Forgot/Reset also showed SEND_RESET_PASSWORD etc; Admin Reset showed
no USER events in the queried window (Admin Event API was not tested).
Events are not per-mutation causal tracing or delivery evidence.
Independent RP and Admin Logout produced verifiable signed Backchannel
Logout Tokens and HTTP 400 old Refresh; deliberate receiver outage
produced no catch-up in the 4-second post-restart window. No durable
retry, no cross-database event propagation or product Session
revocation has been proven.

**Acceptance remains limited**: isolated local Account Console
capability and all four synthetic reset route behaviors were
tested; production Auth/Session, external Reset revocation and
event delivery still BLOCKED. No product Gate and no merge.


## BND-IDP-02C — controlled Reset entry feasibility, strictly second disposable Realm

**Isolated evaluation only.** The existing full IDP-01, 02A and 02B
Chromium/SMTP/OIDC/MFA/four password-route/Logout suites run unchanged
FIRST. Only after they succeed is a SECOND realm
`auth-idp-controlled-ci` created in the same pinned, egress-denied,
temporary Keycloak 26.8.2 instance. Its synthetic users, local
Mailpit mail and in-memory client secrets are never shared with the
prior `auth-idp-ci` Realm or any product service. The historical
realm remains unchanged. No SPI, Migration, custom Outbox, production
BFF, product Session or external delivery.

The candidate **standard-only** restrictions are disposable Realm
`resetPasswordAllowed=false`, `registrationAllowed=false`,
`account-console` client `enabled=false`, and built-in
`UPDATE_PASSWORD` Required Action provider `enabled=false`.
Every configuration change is independently read back via the
versioned Admin REST API; toggled UI links alone are not accepted.
These are **not a proven comprehensive policy**, and may prevent
legitimate account management and required onboarding actions.

**Test matrix, with direct adversarial attempts:** user browser login
and direct Forgot/Reset page, Account Console path, real
`kc_action=UPDATE_PASSWORD` with credentials, pre-issued local
`execute-actions-email` update-password action token, and a
password-update challenge already begun before changing policy
(stale in-flight form) are each tested. Fresh OIDC Code+PKCE
logins verify which generated passwords are actually accepted.
For Admin API, a service account assigned **only**
`realm-management/manage-users` attempts the permitted built-in
`PUT /users/{id}/reset-password`, while an operator service
account assigned only `view-users` must fail. Test-only master
bootstrap admin is used only for controlled realm provisioning,
not claimed as a restricted role. The built-in `manage-users`
role may grant **realm-wide user modification**, not one-user
scope: an entirely independent synthetic user is also tested.
This is a sensitive privilege, not a demonstrated fine-grained
product Reset service entitlement.

**Fail-closed verdict:** FEASIBLE only if direct paths including
old action tokens and pre-started Required Actions fail and
truly least-privilege, bounded service scopes are proven.
If a bypass remains or role scope is too broad, report
`NOT_PROVEN` with an actual non-green CI rather than counting
mere config readback as success. Root, trusted infrastructure
admin, local Keycloak database and recovery operations are outside
the proposed restriction, even under a limited success.
An observed password change is NOT product Session revocation
or an authenticated durable Reset event.

**Authority for same-version examination:** Keycloak 26.8.2
actual REST configuration/readback and built-in RequiredActionProvider
API (https://www.keycloak.org/docs-api/26.8.2/javadocs/org/keycloak/authentication/RequiredActionProvider.html).
Related 26.8-series Admin REST and Server Admin documentation:
https://www.keycloak.org/docs-api/26.8.0/rest-api/index.html and
https://www.keycloak.org/docs/26.8.0/server_admin/
(The latter docs have different patch numbers; all behavioral
claims must be supported by the actual pinned **26.8.2** CI).


## BND-IDP-02C — measured NOT_PROVEN verdict (fail-closed, not acceptance)

The isolated two-Realm standard-only evaluation was run on
[real CI 42907619285](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42907619285)
with source SHA `eedb648e32b79c990a476783b5e3df26bd4a3033`.
Full legacy IDP-01/02A/02B suites PASS; new second Realm
`auth-idp-controlled-ci` RC-00–11 individual cases measured,
then **CI FAILS intentionally at `RC-adversarial-bypass-final-denial`**,
overall `NOT_PROVEN`.

All toggles were read back (`resetPasswordAllowed=false`,
registration disabled, `account-console` disabled,
`UPDATE_PASSWORD` Required Action provider disabled).
Direct new Forgot/kc_action/Account UI and a prior mailed action
token produced no observed new password-update form. However
a **real `UPDATE_PASSWORD` form started BEFORE disabling the
provider was submitted AFTER the policy change and its new
password was independently accepted by actual OIDC browser
login**. This is a direct **in-flight bypass**.

Ordinary OIDC user Admin Reset HTTP **401**, limited
`view-users` operator HTTP **403**; intended service with
built-in `manage-users` performed a real target password
update HTTP **204** followed by old DENY/new ACCEPT. The
**same** service changed a second unrelated synthetic
account HTTP **204**. Thus standard built-in role alone
is **not** narrow single-target permission and must not be
treated as authorized product Reset service admission.

**Next separate bounded evaluation:** same pinned Keycloak
version's fine-grained admin `reset-password` scoped user
permissions **without** a broad built-in `manage-users`
role, plus a separately proven transition barrier for
pre-policy action tokens/in-flight browser challenges.
Only after both are demonstrated could controlled service
entry be reconsidered. Trusted root/realm-admin recovery
remains outside such restrictions. Product Session revocation,
DB fencing, external event delivery and cross-DB Reset
semantics remain NOT_TESTED/BLOCKED. No production code,
migration, SPI, outbox or deploy in this bundle.


## BND-IDP-02C bounded continuation — supported FGAP v2 and existing-flow logout probe

The original RC-00..11 and all older IDP/RA/RB suites remain unchanged.
On the same disposable second Keycloak 26.8.2 Realm, CI now measures:
- A real second pre-policy browser UPDATE_PASSWORD form, retained verbatim
  through policy hardening; POST /admin/realms/{realm}/logout-all is
  applied *after* the original undrained baseline RC-08, and the same
  already rendered second form is submitted without reload. A second
  pre-issued local action-token link is attempted after logout. Both
  outcomes require independent old/new password OIDC verification.
- Supported FGAP V2 via adminPermissionsEnabled (standard version,
  not preview V1) and admin-permissions REST Policy/Permission. A
  Client Credentials principal with **no built-in broad realm-management
  role** is granted only the Users reset-password scope for exactly one
  synthetic account. CI measures target reset, unrelated-account reset,
  and unrelated profile mutation, plus independent credential tests.

These are experiments, not claimed results. Global logout-all describes
user sessions, and does not itself establish cancellation of authentication
sessions or action tokens. The original fail-closed overall security
assertions remain active: even scoped FGAP cannot compensate for an
in-flight bypass. Official version-family sources:
https://www.keycloak.org/docs/26.8.0/server_admin/
https://www.keycloak.org/docs-api/26.8.0/rest-api/index.html
Local same-version tested source, actual Run/JSON results and remaining
blockers must be added in the original cumulative task checkpoint.
No product Auth acceptance or security Gate is authorized.


### FGAP detailed readback clarification (source-only, pending CI)
The first supported-FGAP diagnostic run `42911896683` reached
realm enable, user-policy and scope-permission creation, and
failed only at the direct assertions against a list entry.
Use documented GET by the listed permission's internal ID
for exact full-object checks. Export only four booleans
for resource type, allowed operation, sole resource and
linked policy. Neither a POST status nor a shallow list
is accepted as proof of least privilege. The real target,
unrelated target and unrelated operation tests must still run.


### One final bounded evidence pass
Exact prior PR CI `42912734889` tested full permission GET and
confirmed resourceType=Users, but name-based string comparisons
of persisted scope, resource, and policy associations were all
false. This may be a representation using internal authorization IDs.
The next CI retains these unresolved checks as a blocked final
security verdict while continuing to direct service permission
attempts and independently checking whether an already-rendered
password form really changed credentials AFTER standard logout-all.
Neither representation mismatch nor a successful Reset API call
is an acceptance Gate; never pass without the full proof.


## BND-IDP-02C — verified limited result, final functional matrix (2026-11-11)

**Exact tested source** `a2ac3af6548e310db9c4def20b4bc985468adcd4`.
[Actual GitHub PR Run 42913693567](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42913693567)
COMPLETED FAILURE on strict `RC-adversarial-bypass-final-denial`;
job `130170545439`; sanitized artifact
[13808642104](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42913693567/artifacts/13808642104)
(`overall=FAIL`, `RC_verdict.controlled_entry=NOT_PROVEN`).
All pre-existing IDP-01/02A/02B regressions, isolated network
egress-denial, second synthetic realm, RC-00..11 observations and
mandatory container/credential teardown executed as expected.

**Fine-grained admin REST, bounded positive and negatives:** Standard
`adminPermissionsEnabled=true` enabled/read back on second Realm,
the built-in `admin-permissions` client, user-policy and
specific `Users/reset-password` permission created, and a separate
Client Credentials service principal has NO realm-management
`manage-users`/`view-users`/realm-admin grant. Its direct
`PUT /users/{target}/reset-password` returned **204**, independently
verified by real Code+PKCE browser OLD DENY / NEW ACCEPT. The SAME
principal's cross-target reset returned **403**, with the unrelated
user's prior credential still accepted. Attempted target profile
mutation returned **403**, and root readback confirmed unchanged
profile. The separate historical `manage-users` role remained
demonstrably broad (other-user reset HTTP 204). These data establish
a bounded **functional service authorization** observation; not
production-level identity or the single-entry guarantee.

**Readback limitation:** Admin permission by-ID GET confirmed
resourceType=Users; direct string-equality comparisons of persisted
`scopes`, `resources` and `policies` to submitted names/UUID
returned false, consistent with possible AuthZ-internal references
but NOT independently resolved. The strict stored-ID-to-entity
permission mapping remains `NOT_VERIFIED`, even though direct real
authorization positive/negative tests succeeded. No failed
readback assertion was converted into policy PASS.

**Already-started form: definite second negative:** The same true
pre-restriction UPDATE_PASSWORD form, retained without reload
in another real browser, could still submit AFTER standard
`POST /logout-all` returned **200**. Its new password independently
succeeded, and old credential independently failed via fresh
OIDC Code+PKCE login: a **CONFIRMED SELF-SERVICE BYPASS EVEN AFTER
STANDARD USER-SESSION LOGOUT-ALL**. Pre-issued local action-token
URL separately had no form and did not change its credential.
Fresh Forgot, kc_action and Account Console paths stayed bounded
negative on the tested paths. This does not exhaust all action
tokens, authentication sessions or privilege roots. No standard
authentication-session drain or durable cancellation barrier
was demonstrated on the exact pre-started challenge.

**Result and limit:** `NOT_PROVEN` for exclusive controlled
password-reset entry; strict CI intentionally RED. FGAP V2
standard scoped permission is a credible *partial* route for
the service-authority problem; it cannot solve the in-flight
user-form problem. Need supervisor decision on whether a
non-product standard verified drain/transition period or
authorized different reset architecture is admissible.
Never equate SSO logout or normal session expiry with canceling
a preissued action form. No SPI, custom Outbox, product-session,
Migration, deployment, real email or Auth Gate PASS here.
This is **READY_FOR_REVIEW — CONTROLLED_RESET_ENTRY_PROOF**
as a bounded negative result only.
