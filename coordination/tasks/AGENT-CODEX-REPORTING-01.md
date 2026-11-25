# CODEX-REPORTING-01

## 2026-11-23 / CODEX-REPORTING-01-01

Status is review. Supervisor approval is pending.

- Roadmap evidence reference is P3M22-A06 and operational P3OP11-R07, launch checklist backup and restore. This reporting mission adds no roadmap completion credit.
- Baseline is Shahbazi-Amir/RAG_finance_app, report branch codex created at 67ffa71f4dc43b29e8df7b74bd40f7bd16875cde. Existing backup report revisions and evidence provenance are in the [baseline](../../docs/codex_execution/BASELINE.md).
- Implemented files are this checkpoint and README.md, BASELINE.md, WORK_LOG.md, BACKUP_STATUS_FA.md, RECOVERY_PLAN.md and CURRENT_STATUS.md under docs/codex_execution. A separate worktree protects the working checkout. Sanitized summaries preserve the historical evidence while keeping operational artifacts local.
- Git identity, access retry and verification methods are recorded in the [work log](../../docs/codex_execution/WORK_LOG.md). Runtime and restore testing were outside this mission. Git history and remote ref inspection identify the publication.
- Remaining dependency is authorization for isolated full-stack recovery verification. Supervisor acceptance is separate.

### MAC-FIRST-START-01

- P3M22-A06 / P3OP11-R07, launch checklist backup and restore. No completion credit.
- Baseline: RAG_finance_app detached at 67ffa71f4dc43b29e8df7b74bd40f7bd16875cde. Reporting branch codex started at 552ab762736dfb9df3d6c428e056cec0b282d9d6. Backup sets 20261122T225147Z and 20261122T230515Z-docker. Live API image 2de6c25d8bd1.
- Implemented operationally: started the existing demo-db and retried the existing API. Added the Persian Markdown and RTL HTML reports under docs/codex_execution. Tested: both SHA256SUMS lists passed, demo-db became healthy and pg_isready accepted connections, original API repeated exit 78. Supervisor acceptance pending.
- Diagnostic helper failed to import with PermissionError. docker diff and metadata comparison confirmed the original has application changes in its writable layer. Retain the existing container pending a recoverable baseline. The API denial within the original remains unresolved.
- Commands, rollback, evidence and dependencies are in [the Persian report](../../docs/codex_execution/MAC_FIRST_START_FA.md). Isolated full restore and end-to-end retrieval remain open.

### MAC-FIRST-START-01 — writable-layer and API correction

- P3M22-A06 / P3OP11-R07, launch checklist backup and restore. Reports start at 84d58b1. Product execution branch ops/mac-first-start starts at 5fe21e9 and carries local 4752c2b.
- Implemented: encrypted inspect/diff, local snapshot 6c6a05dcd26a and offline permission/readiness correction in infra/mac-first-start/{Dockerfile.api,compose.api.yaml}; updated both Persian reports. API container and original volumes retained.
- Tested: Compose resolves seven services with profiles enabled. Snapshot diagnostic reproduced protected-schema PermissionError after config and read-only preflight; fixed build imports schema under UID 11001. Restore archive pipeline, fixed runtime check and supervisor acceptance remain open.
- [Reproducible evidence and rollback context](../../docs/codex_execution/MAC_FIRST_START_FA.md). No gated completion credit.

### MAC-FIRST-START-01 — isolated recovery and live API

- P3M22-A06 / P3OP11-R07. Reporting baseline 4053092. Local execution branch now f1a83c4 with versioned API and Bootstrap image fixes.
- Implemented: added recovery and live API evidence to the existing Persian Markdown/HTML pair, added a local recovery report beside the encrypted archive, deployed only product-api with the versioned override using original mounts.
- Tested: seven new checksums, authenticated Docker load and isolated entrypoint, private readiness/protocol on the new image using an isolated ledger, then live API healthy at d98dfeaca7c41. Bootstrap fixed-image import passed; its runtime and the remaining stack are under test. Full-stack recovery and supervisor acceptance remain separate.
- [Evidence, rollback instructions and open items](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — seven service starts and HTTPS ingress

- P3M22-A06 / P3OP11-R07. Reporting baseline d218ed1. Local execution through 136bd8f, with routing fix 84e474d and non-root ingress fix 7ce11c9.
- Implemented: started both existing databases, Keycloak, Bootstrap and BFF, fixed Compose namespace and nginx chown errors, and populated a new private ingress volume from protected local inputs. Existing volumes retained. Recorded progress in the same Markdown/HTML reports.
- Tested: three Docker health checks passed simultaneously. BFF verified mTLS against Bootstrap and API. nginx syntax and trusted HTTP 200 passed. Keycloak discovery returned 502, browser timed out, API and Bootstrap probes timed out under load. Longer read-only tests confirmed the actual metadata and Bootstrap checks. The readiness-v2 offline image built successfully. Runtime verification remains open.
- [Evidence and recovery context](../../docs/codex_execution/MAC_FIRST_START_FA.md). Supervisor acceptance separate and pending.

### MAC-FIRST-START-01 — stable API and Keycloak diagnosis

- P3M22-A06 / P3OP11-R07. Reporting baseline 377ac12. Local execution 136bd8f and 6a3d426. Same report artifacts updated.
- Implemented and tested: readiness-v2 deployed. API and Bootstrap healthy with full checks, BFF mTLS healthy, TLS-verified HTTP 200, all seven running. Keycloak discovery remained 503 during bootstrap and browser controls timed out. No signed application request or engine dispatch was attempted.
- Tested recovery evidence: freshly encrypted Pg archive verified and restored into network-disabled PostgreSQL with a new volume. 101 tables restored. No original volume was replaced. JVM witness identified a Liquibase remote analytics path, fixed in the local Compose overlay. Supervisor acceptance and full-stack/browser acceptance are separate.
- [Evidence and rollback context](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — optimized IdP restart and capacity checkpoint

- P3M22-A06 / P3OP11-R07. Reporting baseline 02eb586. Local execution branch 2a5948f. Added evidence to the same Persian Markdown and HTML reports.
- Implemented: retained Keycloak augmentation in a verified local snapshot, then applied only the offline Keycloak Compose revision. Original database and private volumes remained attached. Tested: managed restart produced a new Running container, HTTPS returned trusted 200, and discovery was 502 during restart. Three Docker healthchecks plus HTTPS passed. API and Bootstrap periodic checks became unhealthy after earlier successful full preflights.
- Open: stabilize Docker resource headroom, verify offline Keycloak readiness, obtain a valid local test session, then measure the signed request, C018 and Refresh. Backup and full restore remain partial. Supervisor acceptance separate.
- [Evidence and recovery context](../../docs/codex_execution/MAC_FIRST_START_FA.md).

- Recheck from 71148b4 (same MAC-FIRST-START-01 / P3M22-A06 / P3OP11-R07). A sanitized direct Docker preflight isolated the renewed denial to the psycopg error branch of the live DB authority check. Added this evidence to both reports. The exact database transport failure and stable recovery remain open.

- Final observed status from a46ae51 (MAC-FIRST-START-01 / P3M22-A06 / P3OP11-R07). Trusted ingress returned 200 and OIDC discovery returned 502. All seven containers were running, with all five Docker healthchecks now unhealthy. Updated both reports. Wait for the private archive stream before changing Docker Desktop capacity.

### MAC-FIRST-START-01 — post-resource runtime recheck

- Status: review. P3M22-A06 (Module 22, activity 6) and P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 50d26aa. Execution baseline ops/mac-first-start 2a5948f and detached workspace 67ffa71. Prior verified Keycloak snapshot retained.
- Implemented: started the seven existing containers in place. Updated this checkpoint and docs/codex_execution/MAC_FIRST_START_FA.md and docs/codex_execution/MAC_FIRST_START_FA.html. Resources observed at 4 CPU and 6212030464 bytes. Existing images and mounts retained.
- Tested: docker ps and docker inspect State.Health.Log confirmed five healthy services with repeated zero exit codes. Trusted loopback ingress returned 200. Keycloak readiness on port 9000, issuer discovery and JWKS returned 200. The actual login form POST returned 303 with browser fetch metadata and the live authorization endpoint returned a password form with 200 on retry. See the report for retry limits and the original browser error.
- Pending: Chrome DOM proof timed out. Aggregate IdP SQL found zero enabled non-master accounts. Invited-user callback, signed Product API request, C018, the UI result and Refresh are blocked pending an active invited staging identity with the corresponding application admission. Arvan HOLD. Supervisor acceptance pending.
- [Persian evidence and reproducible checks](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — invited identity and browser checkpoint

- Status: blocked. P3M22-A06 (Module 22, activity 6) and P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 5d9e8cf, remote codex 50d26aa, execution baseline ops/mac-first-start 2a5948f. Previous service readiness carried forward.
- Implemented: updated this checkpoint and docs/codex_execution/MAC_FIRST_START_FA.md and docs/codex_execution/MAC_FIRST_START_FA.html. No application or identity policy change.
- Tested: aggregate Keycloak SQL found zero active, disabled and verified users outside master. One non-master realm is enabled, self-registration and realm Verify Email are disabled, and no SMTP rows are configured there. Product auth SQL found zero identities and sessions and three INITIATED attempts in the sampled ledger. Initial schema and SMTP-column errors were corrected with schema discovery and the actual SMTP table.
- Tested: disposable Chrome with verified loopback pins scheduled location.assign asynchronously and independently observed the Persian login DOM, clicked the native form and observed the password field in the IdP DOM. Prior Page.navigate timeout bypassed in the harness. Internal timeout cause unconfirmed.
- Blocker and next action: an approved staging invitation and proof of email control are required. No supported current staging provisioning workflow located. Signed product request, C018, rendered result, Refresh and invocation counter verification are blocked. Arvan HOLD. Supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Staging invitation v1 design

- Status: blocked. P3M22-A06 (Module 22, activity 6) and P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 0257e19 and execution baseline ops/mac-first-start 2a5948f.
- Implemented: documented a proposed realm-scoped operator procedure in docs/codex_execution/MAC_FIRST_START_FA.md and docs/codex_execution/MAC_FIRST_START_FA.html and recorded this checkpoint. No runtime change.
- Verified by source inspection: docs/operations/phase3_private_staging_integration_v0.md, src/phase3/auth/bootstrap_oidc.py, apps/web/app/api/auth/callback/route.ts, infra/auth-ci/README.md and pinned Keycloak Admin REST references. Previous runtime passes were not repeated. Markdown/HTML parity and git diff --check verified.
- Blocker: one authorized Staging invitation deliverable through an operator-approved email route to a test inbox controlled by the invitee. No live invitation, session, Signed BFF, C018 or Refresh test was run. Arvan HOLD. Supervisor acceptance pending.
- [Persian design and evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — executable invitation and live SMTP blocker

- Status: blocked. P3M22-A06 (Module 22, activity 6) and P3OP11-R07 (§Launch checklist), operational evidence only. Report baseline codex 1aa4caf. Execution baseline ops/mac-first-start 2a5948f with local executable invitation helper committed at b57bf7a. No application code pushed.
- Implemented: local execution helper infra/mac-first-start/staging_invitation_v1.py. Report-only push updates this ledger plus docs/codex_execution/MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html, and CURRENT_STATUS.md.
- Tested: Docker status, five healthchecks, management /health/ready, nginx configuration and CA-verified HTTPS. Parsed the live Bootstrap issuer and used parameterized read-only psql to match exactly one enabled non-master realm with closed registration, zero SMTP rows, and zero users. Helper CLI, issuer and role restrictions, and staged invitation operations checked with local mocks. Initial Docker permission review timed out and the bounded retry succeeded.
- Blocker: an approved Staging SMTP route for a controlled test inbox is absent. No production identity mutation, C018 invocation, or live session/signature/Refresh proof. Existing images, volumes and backup retained. Arvan HOLD. Supervisor acceptance pending.
- [Persian Markdown](../../docs/codex_execution/MAC_FIRST_START_FA.md) and [HTML](../../docs/codex_execution/MAC_FIRST_START_FA.html).

### MAC-FIRST-START-01 — approved SMTP availability check

- Status: blocked. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex ad24281 and execution baseline ops/mac-first-start b57bf7a.
- Implemented: report updates only in docs/codex_execution/MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html, CURRENT_STATUS.md, and this checkpoint.
- Tested: docker version confirmed server access. docker ps -a inventory found zero known mail containers. lsof found zero visible SMTP listeners on 25/465/587/1025. Parameterized realm lookup confirmed one enabled realm, closed registration, and zero matching SMTP and user rows. Reviewed execution helper and local operational configuration. No email or identity writes.
- Blocker: provide one approved Staging SMTP setup for an invitee-controlled test inbox through secure handoff. Invitation, OIDC, signed request, C018 and Refresh remain pending. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Gmail STARTTLS and private management access

- Status: blocked. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 0951842 and execution baseline ops/mac-first-start b57bf7a.
- Implemented: restored Docker Desktop and the seven existing staging containers in place. Report changes only in this ledger, docs/codex_execution/MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html, and CURRENT_STATUS.md.
- Tested: Gmail TCP connection through docker exec and an unauthenticated SMTP STARTTLS probe using Python ssl.create_default_context with Gmail hostname verification. Negotiated TLS 1.3. Trusted curl request to ingress /admin/ returned 403. Keycloak had no published admin port. No SMTP auth, email send, invite, or runtime product attempt.
- Blocker: an authorized private Keycloak administration URL is needed for the account holder to enter the App Password in Staging > Realm settings > Email > Authentication > Password. Ingress access restrictions preserved. Arvan HOLD. Supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — private Keycloak admin route review

- Status: blocked. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 9f7a8fe and execution baseline ops/mac-first-start b57bf7a.
- Implemented: updated this ledger and docs/codex_execution/MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html, and CURRENT_STATUS.md. No listener, access grant, or runtime setting changed.
- Tested: docker inspect showed no published Keycloak ports. Boolean-only checks found no hostname-admin in the running config file or environment and confirmed the ingress admin deny rule. Seven containers were running. Official Keycloak guidance confirms that a separate admin hostname needs proxy-level restrictions.
- Blocker: approval for a loopback-only TLS admin route and an existing authorized Staging operator. SMTP authentication and Test Email remain unexecuted. Arvan HOLD. Supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — temporary authenticated admin entry point

- Status: blocked on operator. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 1940609, execution baseline ops/mac-first-start b57bf7a. Execution changes committed locally at 5764fff.
- Implemented: temporary non-root TLS Nginx listener published only to Mac loopback and browser launch in a separate Chrome profile. Execution paths infra/mac-first-start/keycloak-admin-local.conf, open_local_keycloak_admin.py and staging_invitation_v1.py. Existing ingress and seven containers retained. Report-only push updates this checkpoint and docs/codex_execution/MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: nginx -t, Docker port readback, trusted curl 200 console, 401 unauthorized REST and 403 standard ingress. Both independent headless admin DOM methods timed out. Interactive window launched, operator login unverified. Runtime engine_mount_readiness.py, offline mode checks, five backup SHA-256 entries and seven service readiness checks passed. No engine invocation.
- Pending: existing authorized operator sign-in and manual SMTP password entry, Test Email receipt, invitation, authenticated path, source-capable release validation and Refresh. Stop the temporary listener after use. Full isolated restore and supervisor acceptance remain open. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — existing operator browser authentication

- Status: blocked on SMTP password handoff. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 19b6dc8 and execution baseline ops/mac-first-start 5764fff.
- Implemented: authenticated the existing administrator in an interactive disposable Chrome profile over the approved Mac-only TLS path. Report-only updates to this ledger and docs/codex_execution/MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: read-only aggregate Admin role and credential query, protected config field presence, installed bootstrap-admin help and official recovery documentation. Origin and form destination verified before entering the existing credential from protected config through a process-local Chrome debugging pipe. Post-login console path and Realm settings DOM confirmed. No credential, token, or cookie output.
- Pending: account holder enters App Password in the already authenticated browser, tests SMTP and confirms receipt. Invitation and product end-to-end remain open. Review and rotate the ingress proof before product auth. Stop the local listener after admin work. Supervisor acceptance pending and Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — real SMTP test and Staging invitation

- Status: blocked on invitee action. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 6eecc03 and execution baseline ops/mac-first-start 5764fff.
- Implemented: real SMTP test, one restricted Staging account and one accepted verification-and-password invitation. Only report and checkpoint files pushed.
- Tested: aggregate SMTP policy SQL, Keycloak 26.8.2 button predicate, official admin-cli and Admin REST over loopback TLS. testSMTPConnection returned 204. Account creation returned 201. Invite recovered from SMTP reachability failures after sanitized log checks, TCP rechecks and exact account readback, then execute-actions-email returned 204. Inbox delivery and email verification remain pending. No identity flags written by the operator.
- Pending: invitee opens the link and completes the required actions. Then verify the account, rotate ingress proof before product sign-in, test the product session and C018 route, and stop the temporary listener after management work. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — invitation DNS and browser routing

- Status: blocked on invitee action. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 2cf0bdf, execution baseline ops/mac-first-start 5764fff.
- Implemented: opened an isolated private Chrome window with hostname-to-loopback mapping for staging IdP and product only. Updated this ledger, MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: system resolver returned a non-loopback address for the IdP. Python TLS with the existing CA and both hostnames verified local certificates. Discovery matched the configured issuer. Token-free request to the actual action-token endpoint returned the Keycloak 400 page. Active-tab lookup found no usable existing invitation URL. Token validity and invitee completion are untested.
- Pending: invitee opens the existing link and completes Keycloak confirmation. No duplicate invitation or account. Product E2E and supervisor acceptance remain pending. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — one-hour renewal for the existing invitee

- Status: blocked on invitee action. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 69abad8, execution baseline ops/mac-first-start 5764fff.
- Implemented: issued one official one-hour VERIFY_EMAIL and UPDATE_PASSWORD message for the exact existing Staging account and opened a clean private Chrome window. Report-only paths are this ledger, MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: checked the existing account, realm, client role defaults, group and credential absence over trusted localhost Admin REST. execute-actions-email returned 204 on the single renewal. Fresh browser launched after verifying local TLS for both configured hosts. Expiry of the previous link is invitee-reported. Delivery and action-token completion for the new link remain unverified.
- Pending: invitee opens the new link in the mapped Chrome profile and completes both actions. Then verify account state and continue product E2E. No duplicate user, no Phase 2 changes, Arvan HOLD. Supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — local invitation handoff for real password form

- Status: blocked on invitee link handoff. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 8905dbc, execution baseline ops/mac-first-start 5764fff.
- Implemented: bounded local invitation-only clipboard receiver with exact issuer, host and realm path restrictions. Report-only updates to this ledger, MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: existing account remains unverified and has no password. Browser DOM automation is unavailable on the existing mail browser. No exact invitation was found in the initial clipboard check or within the 150-second receiver window. Independent mounted C018 SQLite storage passed PRAGMA quick_check in immutable read-only mode. No retrieval or model call.
- Pending: invitee copies the current link on the Mac and the receiver opens the actual Keycloak action in isolated Chrome. Password form, identity completion and product E2E remain pending. No second renewal or duplicate identity. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

- Clipboard receiver reactivation from codex 8f7f68a / execution 5764fff, same MAC-FIRST-START-01 / P3M22-A06 / P3OP11-R07. Executed a second bounded 150-second receive and read-only expiry/wrapper detection. No matching invitation arrived. Reports and CURRENT_STATUS updated, no account or invitation mutation. Form and product tests remain blocked. [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — invitation completion and product browser login

- Status: blocked on product-user sign-in. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex d1ec72a, execution baseline ops/mac-first-start 5764fff.
- Implemented: opened the exact existing invite through verified localhost Chrome, rotated the active ingress proof in its two private runtime mounts, closed the admin listener, and started a private Chrome product authentication and one-submit UI harness. Report-only updates to this ledger, MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: original action reached Keycloak DOM and a required-action route. Admin REST confirmed verified email and password credential for the existing account. Nginx candidate syntax and reload succeeded. Trusted product /login returned 200 and normal ingress /admin/ returned 403 after the temporary listener stopped. Actual product OIDC password form witnessed in browser DOM. Browser control disconnected once and the replacement browser showed the same real form. Read-only product SQL showed zero identity links and zero active sessions.
- Pending: user enters the new product-account password directly in Chrome. Product session, signed request, real C018 invocation, source display, no-generation evidence and Refresh are not yet witnessed. No duplicate account or invitation. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — strict TLS repair for the OIDC callback

- Status: blocked on the single post-repair interactive login. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 9024dcf. Execution baseline ops/mac-first-start 5764fff, local certificate profiles committed at 1d5c1ee.
- Implemented: infra/mac-first-start/ingress-ca-v3.cnf and ingress-leaf-v3.cnf. Corrected public certificate extensions with existing keys. Kept legacy public certificate rollback pair and adjusted only ingress leaf and Bootstrap trust mounts. No private values published. Report push updates this ledger, Persian Markdown/HTML and CURRENT_STATUS.md.
- Tested: historical 3 callback 503 and 3 UNKNOWN attempts. Reproduced OpenSSL verify code 85. Validated replacement and legacy pairs, ingress syntax, mounted byte equality, strict discovery/JWKS and token endpoint invalid-request 400 with configured client, BFF private TLS, and ingress proof agreement. Opened only one OIDC browser after these checks, with password form witnessed.
- Pending: callback, product session, signed UI request, real retrieval, sources and Refresh. Stop after a failed interactive attempt. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — confirmed product sign-in and preserved C018 attempt

- Status: review, C018 E2E blocked. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex f689528, execution branch ops/mac-first-start 1d5c1ee.
- Implemented: confirmed the one genuine UI sign-in and single product submit. Preserved the sole failed Attempt. Prepared independent SHA-pinned input copies for a network-disabled diagnostic. Report-only changes in this ledger, MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md.
- Tested: browser session evidence, callback 303, POST 202 once, GET status 200, product ledger FAILED. Chrome reload left ledger unchanged but no engine-status GET 200 was observed and aggregate session evidence confirmed expiry. Verified six input digests and four pinned runtime package versions. Isolated diagnostics exited 1 and timed out at 165 and 220 seconds. The last run reached stage 4 (dense Qdrant copy and validation); timeout diagnosis remains open. No Phase 2 mount was used by the executed diagnostics. Temporary diagnostic container cleaned up.
- Pending: diagnostic root cause and a source-producing release still need evidence. No duplicate question or replay, no Phase 2 writes, Arvan HOLD. Supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — C018 dense correction, real isolated retrieval and budget

- Status: partial, product C018 blocked. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Reporting baseline codex 2dbfb85. Execution commits b03d54a, 121addd, 8367cf6 and 5ee8a25. Source candidate c488837 inspected separately.
- Implemented: local prepare_c018_dense_copy.py, compose.c018-inputs.yaml, profile_c018_onnx.py and engine_mount_readiness.py guard. Existing data bytes and runner pin unchanged. Report-only updates here, MAC_FIRST_START_FA.md/.html and CURRENT_STATUS.md.
- Tested: original Attempt spawn witness EXITED_FAILED with one child, exit 1 and failure near 75 seconds. Reproduced Qdrant lock PermissionError on the original dense clone mode. Fixed copy passed 3,488-vector logical hash and separate copy/open/validate timing. Isolated pinned runner reached CONTEXT_READY with ten results and zero generation in 193.02 seconds, no network. Both uninstrumented and thread-capped tests timed out at the ONNX stage. The second enforced 180 seconds inside the container, exit 124. Local readiness regression passed and 21 candidate source-contract fixture tests passed.
- Pending: repeatable runtime within the current 180-second cap, verified locator contract, and product acceptance. Existing failed Attempt was not replayed. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — recovered frozen runtime and pre-probe checkpoint

- Status: review. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Report baseline e1583be, local execution baseline 5ee8a25 and frozen source sample baseline 5fe21e9.
- Implemented: private mode-0600 freeze manifest and sanitized checkpoint in this ledger and MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md. No image or container changes.
- Tested: inspected all seven exact image/container identities, compared nine source files, verified 11 current asset pins, dense file equality and package versions. Three backup sets returned 60 matching hashes total. Full provenance UNKNOWN; no parallel source was fetched or deployed in this audit.
- Pending: static-only warm trial under unchanged 180-second cap, locator contract and real product verification. Combined approval review returned HTTP 404 and did not execute. Existing failed Attempt preserved. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — frozen comparison, closed security probes and budget trials

- Status: partial. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Report baseline 61591d8. Execution SHA 5ee8a25 and frozen sample base 5fe21e9.
- Implemented: final private mode-0600 freeze manifest and sanitized reports in this checkpoint, MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html and CURRENT_STATUS.md. No Runtime code, image, mount, timeout, data or identity change.
- Tested: matched all seven frozen identities and stable metadata after canonicalizing Docker mount order. Verified exact pin equality and one unchanged FAILED Attempt with one spawn witness. Noninteractive ingress and private mTLS signature negatives passed after fixing the shell variable and Bootstrap method. Warm static files and exact 180-second runner resulted in Stage 6 exit 124. ONNX schedule trial timed out in Stage 4 and did not exercise the candidate option. Sampled cgroups had no reported quota throttling, swap or OOM.
- Pending: product runtime budget and approved locator contract, valid product Refresh and integrated backup restore. Full prior image provenance UNKNOWN. No parallel code imported during this audit. Arvan HOLD and supervisor acceptance pending.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Post-reboot identity and readiness

- Status: review. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), operational evidence only. Report starting ref codex 5cd44a5cdaec6ac7fc357b0862b950b82aab5f2e, execution ref 5ee8a25, frozen source sample 5fe21e9 and private after-freeze manifest dated 2026-11-24 UTC.
- Implemented: report-only updates to MAC_FIRST_START_FA.md, MAC_FIRST_START_FA.html, CURRENT_STATUS.md and this checkpoint. Runtime retained because IDs matched and services were already running.
- Tested: docker ps -a --no-trunc, docker inspect with selected metadata, docker info, docker stats --no-stream, df -h, GET /health/ready on Keycloak management port (200), curl with the mounted public CA and existing loopback hostname (302, TLS verify=0). Missing Health keys required a narrower inspect template. Default curl trust failed with code 60 and passed with the existing CA.
- Open: missing temporary execution checkout and Compose overlay, complete provenance, bounded Runner, approved Locator, product and Refresh, isolated integrated restore. Supervisor acceptance pending. No canonical checklist changes.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Bounded C018 replay and pinned source membership

- Status: review. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), P3M11-A02 (Module 11, activity 2, source authorization remains blocked).
- Baseline: report ref codex 3382eaee6cd38c2363d81ab3a1fa33605f394196, execution starting 5ee8a25 descended from 5fe21e9, C011 and C018 exact pins, frozen API image 438ba61c69ea. Recovered local checkout with git worktree add --detach and retained branch ops/mac-first-start-resume at c90cfa73de7c8f7a264f59f5dedbfaec4dd3693c.
- Implemented locally: infra/mac-first-start/profile_c018_onnx.py and audit_c018_sources.py. Report-only changes: MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md, and this ledger.
- Tested: 11 asset pins and two dense file hashes, real corpus validation and five negative cases, 38 contract unit tests. Sequential Docker trials in a read-only, no-network container, UID/GID 11001:11001, `timeout 180 ... profile_c018_onnx.py --disable-intra-op-spinning --audit-sources`. First retrieval 102.35s and exit 0, repeat exit 0 and outer wall 179s. Local command and trace are run-repeat.zsh / repeat.log under /private/tmp/rag-c018-resume. The initial launch exited 127 because tmpfs masked Python, corrected by moving scratch to /tmp. Dense copy parent was initially absent and creation resolved that error.
- Open: product deployment and acceptance, approved Locator and release permission, Refresh, and integrated restore. Supervisor decision pending. No parallel code import, production Attempt, timeout change, Generation or Gateway. No canonical checklist changes.
- [Persian evidence and decision options](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Real product pre-attempt readiness checkpoint

- Status: blocked. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), P3M11-A02 (Module 11, activity 2). Report baseline codex 44ff2d1, local execution c90cfa7, frozen sample 5fe21e9 and exact C018 runner pin.
- Implemented: report-only checkpoint in MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger. No runtime or contract changes.
- Tested: Docker ps and inspect matched seven exact identity pairs, five healthchecks, Keycloak management readiness 200 and Persian ingress TLS verify=0 with HTTP 200. Live runner SHA-256 matched; live dense mode 0555. One run via /bin/zsh /private/tmp/rag-c018-resume/run-repeat.zsh ended exit 124, outer 185 s and stage 6 batch 4 under timeout 180. No new context or Top-10 receipt. Read-only SQLite showed one FAILED outcome and one EXITED_FAILED witness, exit 1. The initial witness query hit the outcomes DB and was corrected to the separate audit DB.
- Open: runtime budget repeatability, live dense mount repair and rollback for API network namespace dependents, product attempt and refresh, Locator rights and acceptance. Owner-reported ~20 s notebook candidate unverified and untouched. No gate acceptance or canonical checklist edit. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Live dense mount repair and bounded readiness

- Status: review for the deployed fix, blocked for product C018. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), P3M11-A02 (Module 11, activity 2). Report base ba3f2ee, local execution c90cfa7, frozen source sample 5fe21e9, frozen image 438ba61c69ea and derived image 0dc53deefb28. Runner and ONNX reference settings retained.
- Implemented: offline derived image with the local readiness probe; byte-identical staged dense input mounted read-only. Recreated API and three namespace dependents using Compose. Operational overlay and rollback commands under ignored artifacts/mac-first-start. Published paths are MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this mission ledger.
- Tested: real Qdrant failed on scratch .lock with copied mode 0555, then passed with corrected mode and 3488 vectors. Two dense hashes matched both trees. Compared image, mount and environment against effective Compose. IdP DB mount comparison differed from declarative Compose; actual mount remained identical to freeze and was excluded from change. Deployment and rollback dry-runs scoped to four services. Live deployment exited 0, readiness probe exited 0, seven running and HTTPS 200 TLS verify=0. All live mount tuples aligned with Freeze Manifest except the changed dense source. Ledger and witness counts unchanged.
- Runtime evidence: /bin/zsh /private/tmp/rag-live-cutover/run-readiness.zsh with frozen candidate image and timeout 180 returned exit 124 at Stage 4, outer wall 186 s. No new result or Attempt. Current live budget unchanged. Propose one 300 s isolated diagnostic only with supervisor approval. Locator rights, real product attempt, refresh and integrated restore remain open. No checklist or Gate acceptance. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Authorized single offline diagnostic

- Status: blocked for live product. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), P3M11-A02 (Module 11, activity 2). Report base 01b902e, frozen sample 5fe21e9, execution c90cfa7, API image 0dc53deefb28, C018 runner 93233bfd.
- Implemented: isolated stage/resource trace via /bin/zsh /private/tmp/rag-diagnostic-300/run.zsh. Sanitized reports MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger. Raw stage/batch trace locally under ignored artifacts/mac-first-start/diagnostic-300.log. No live change.
- Tested: one no-network, no-dispatch run with timeout 300, actual exit 124, outer wall 305 s, ONNX start 199.036 s, 3 completed batches. Checked live budget still 180 and staged dense mode 0755. Cause of variance UNKNOWN; no new validated optimization supports a second readiness run. Initial sh brace-glob cache check was invalid; explicit paths confirmed pycache present. Host top was sandbox-denied; container metrics were collected instead.
- Pending: product readiness and Attempt, refresh, Locator authorization and review of potential notebook optimization. Supervisor acceptance pending. No canonical checklist or Gate changes. Arvan HOLD.
- [Persian timings and outcome](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — NB23 V4 isolated worker candidate

- Status: review for isolated worker, blocked for product. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), P3M11-A02 (Module 11, activity 2). Report base f69d9dc, local branch ops/nb23-v4-staging from c90cfa7 at d6b659d, V4 source 91a1a346 and receipt 4fb6a89c, image f49f536f4d82.
- Implemented: local infra/nb23-v4/worker.py, verify_trial.py, Dockerfile and .dockerignore; private staged bundle and manifest. Reports only in MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger. Historical typo was in notebook reporting; new harness records a separate lifecycle without rewriting originals.
- Tested: source digests matched, offline Docker build succeeded after starting existing daemon. run-trial.zsh initially failed reading the top-level question before launch; nested evaluation_content question fixed it. One Worker created E5, tokenizer and ONNX once, produced three real contexts with zero generation, and exited cleanly. Verifier exit 1 because ordered Top-10 and Context hashes differed for all three labels. Runtime 41.810 / 37.400 / 44.632 s. Native lifecycle and restart acceptance pending.
- Open: parity and performance, ownership-bound API integration, actual OIDC/UI and refresh, source release permission, freeze and supervisor acceptance. Prior frozen stack was found stopped and preserved, Arvan HOLD; no canonical checklist or Gate changes.
- [Persian timing and evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — V4 parity boundaries and restored local UI

- Status: review for UI availability, blocked for V4 product. P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist), P3M11-A02 (Module 11, activity 2). Report base ebff29f, local execution start d6b659d, trace 7fef2d8, preserved engine 91a1a346 and candidate image f49f536f4d82.
- Implemented: local infra/nb23-v4/trace_parity.py, restored original runtime with docker start, and published MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger. No new build or scorer change.
- Tested: exact DEMO07 reference lineage, probe-login.py product to Keycloak 303 and password form 200 with TLS, seven services running and UI/CSS 200. Probe corrections: closing wrapper for HTTPConnection and matching same-origin fetch header. Offline run-trace.zsh Q2 Hybrid matched, Context differed, Q3 full trace exit 124. Hybrid-only and raw timing evidence under ignored artifacts/nb23-v4-bundle.
- Open: exact divergence within post-Hybrid path, score reference evidence, restart supervision and native lifecycle, V4 Product API/OIDC/Refresh, source authorization, Candidate Freeze and supervisor acceptance. No Gate or canonical checklist progress. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Session candidate smoke and shared-score V4 comparison

- Status: review for BFF, blocked for real product. P3M22-A06 (Module 22, activity 6), P3M14-A01 (Module 14, activity 1), P3OP11-R07 (§Launch checklist). Starting report a8c4554 and execution 78c350b. Trace comparison 2682060, BFF 0ee86f3333ec, V4 91a1a346 and image f49f536f4d82.
- Implemented: existing local BFF patch retained; patched the ignored smoke fixture environment only and added infra/nb23-v4/compare_tail.py. Updated MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger. No live changes.
- Tested: actual Docker BFF 200 homepage, 401 missing alias, 503 corrupt alias using an isolated fixture; 30 unit tests from the preceding checkpoint. Offline V4 shared actual Q2 scores with SHA-verified DEMO08 tail: `{"hybrid_parity": true, "shared_score_count": 100, "local_onnx_order_equal": true, "local_top10_equal": true, "local_context_equal": true, "demo08_tail_matches_historical": false, "v4_matches_historical": false, "generation_calls": 0}`. Read-only PR observations in report. No canonical checklist edits.
- Open: signed trusted activity policy, real authentication and refresh, exact historical ONNX score divergence, authorized V4 integration, native lifecycle, Locator rights and acceptance.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Staging-only trusted idle activity boundary

- Status: review for isolated SQL and blocked for browser/product. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist). Report base 86ed801, execution baseline 2682060 and UI 78c350b. Local execution cec1efc, V4 91a1a346 and frozen candidate f49f536f4d82.
- Implemented: opt-in signed Send in apps/api/product_session_api.py and src/phase3/auth/transactional_admission.py, isolated infra/nb23-v4/staging_idle_renewal.sql and test_staging_idle_renewal.sql/.sh, score_fingerprint.py recovery journal and probe_onnx_options.py, and src/phase3/rag_runtime/persistent_v4_pipe.py with its targeted fixture tests. No changes to existing DB or deployment. Report paths MAC_FIRST_START_FA.md/.html and CURRENT_STATUS.md plus this ledger.
- Tested: PostgreSQL no-network disposable tmpfs run exercised valid, stale, revoked, wrong owner and generation, cap, rollback and concurrent revocation. API unittest test_staging_private_asgi.py 14 passed in frozen image; Node tests auth_bootstrap_010, product-bff-boundary, product-chat-client 14 passed with TMPDIR=/tmp. Browser/OIDC integration not run. Q2 evidence and sandbox limitations in report.
- Recovery evidence: original native exit 1 during receipt serialization, corrected and captured all 25 batches, then one Docker twin with exit 0. Identical tensor inputs, changed logits starting at batch 1. Three worker-transport fixture tests passed. First-batch option probe results in report.
- Pending: real staging login, trusted activity and refresh, verified parity and API integration, publication permission and supervisor acceptance. No canonical checklist or Gate acceptance. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Signed renewal boundary and quantized CPU

- Status: review for isolated signed renewal, blocked for browser and V4 deployment. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist). Report base bc90f7f, local cec1efc to a3430c7, V4 91a1a346 and local images f49f536f4d82/d8d93260a4d4.
- Implemented: infra/nb23-v4/check_signed_idle.py, test_signed_idle_db.sh and updated probe_onnx_options.py. Report paths MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger.
- Tested: actual isolated PostgreSQL RSA signed transaction, read-only GET timing, replay, invalid proof, wrong owner, unauthorized GET renewal and rollback. Browser/OIDC not exercised. Model hash equality and no external tensor files, different native/Linux binaries and AVX2 visibility. First-batch quant precision reproduced old Docker logits; optimizer-off combination exited 124. Host CPU sysctl initially sandbox-denied and read successfully with approval.
- Open: first divergent operator, compatible Docker runtime, independent browser/OIDC staging, real refresh and V4 integration. No acceptance or canonical checklist edits. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Independent PostgreSQL and Keycloak staging

- Status: review for independent IdP and schema, blocked for browser E2E. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist). Local starting a3430c7, result af57f26, report start 7ec4685, Keycloak 7e66a96e4739, PostgreSQL ff87138949ad and request image d8d93260a4d4.
- Implemented: infra/nb23-v4/check_session_oidc.py, init_session_e2e_db.sh and prepare_session_oidc.py. Report paths MAC_FIRST_START_FA.md/.html, CURRENT_STATUS.md and this ledger. Disposable fixtures and credentials excluded.
- Tested: local image dependency imports, PostgreSQL startup and function signature query, HTTPS discovery and real Keycloak form/code+PKCE by container namespace. OpenSSL flag, init hook access and first authorization timeout corrected. Local container port is not published on the internal network. Browser E2E not run.
- Pending: isolated application TLS, signed Bootstrap/BFF/API, browser Session/Refresh/History and supervisor acceptance. No canonical checklist or Gate edits. Arvan HOLD.
- [Persian evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### MAC-FIRST-START-01 — Account migration handoff

- Status: review for handoff, blocked for Browser E2E and product V4. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist). Live Git observations in Shahbazi-Amir/RAG_finance_app: clean execution branch ops/nb23-v4-staging at af57f26eaac0b20b32a53f0b934f0a5f3d1c814c and origin/codex starting at 88702f547b86d8e44d8d58efa0fc05a50d3da974. Engine and historical test claims reference the prior checkpoints, not new runs.
- Implemented: docs/codex_execution/ACCOUNT_MIGRATION_HANDOFF_20261124_FA.md and this existing ledger. Report-only publication retains exact local resume, provenance and policy boundaries. Private artifacts, candidate code, credentials and raw traces stay on the Mac.
- Verified by read-only git status, git worktree list, git log, git ls-remote, docker ps -a, selected docker inspect fields, docker network inspect and filtered ps executable names. Seven historical containers stopped, isolated PostgreSQL and Keycloak running, no matching heavy host worker found. Initial socket and process accesses were sandbox-restricted; narrow approved read-only calls supplied the evidence. Document checked for whitespace, section coverage and staged scope. No application tests, benchmarks, builds, migrations, starts or rollout.
- Pending: wire isolated Bootstrap, signed BFF, Product API and HTTPS/mTLS, then finish browser Session/History/Refresh/Logout. Independently isolate the first divergent ONNX operator. Source Permission blocked, Arvan HOLD. No new Gate, checklist or supervisor acceptance.
- [Account migration handoff](../../docs/codex_execution/ACCOUNT_MIGRATION_HANDOFF_20261124_FA.md).

### Docker_3 / NB23-SESSION-RESUME-09 — post-transfer evidence reconciliation

- Status: review for reports and isolated HTTP/restore evidence. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist). Git baseline Shahbazi-Amir/RAG_finance_app, report `codex` at `7806683`, execution `ops/nb23-v4-staging` at `af57f26` with local WIP. Pinned V4 image `f49f536f4d82`.
- Implemented in this reporting change: `docs/codex_execution/MAC_FIRST_START_FA.md`, `MAC_FIRST_START_FA.html`, `CURRENT_STATUS.md`, `WORK_LOG.md`, `RECOVERY_PLAN.md` and this ledger. Exact execution paths and their roles are listed in the report. Candidate code and private evidence remain local.
- Tested and recovered evidence: HTTP OIDC/Session and cross-owner checks, isolated logical restore, bounded Chrome timeouts, ONNX operand and logits controls and Native exact integer witness. Live read-only Docker and host status succeeded after prior sandbox/automatic review HTTP 404. No Gate or canonical checklist changes. Supervisor acceptance pending.
- Progress 2/20 → 4/20. Next: isolated Docker attention witness, operator diagnosis and Golden proof, Chrome and actual product dispatch once their prerequisites are met. [Detailed evidence and reproduction](../../docs/codex_execution/MAC_FIRST_START_FA.md#docker_3--بازیابی-پس-از-انتقال-حساب)

### Docker_3 / NB23-SESSION-RESUME-10 — full operand witness

- Report baseline 2fa5372, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14, activity 1) remains pending for Chrome; P3M22-A06 (Module 22, activity 6) and P3OP11-R07 (§Launch checklist) retain the isolated restore evidence.
- Tested: Docker exact-attention exit 0, both logits controls true, right operand and both zero points equal between runtimes. Left operand differs and each runtime exactly reproduces its own expected int32 result. GraphProto inspection traced the input through Softmax and DynamicQuantizeLinear.
- Implemented locally: Softmax input/output observation in infra/nb23-v4/probe_onnx_intermediates.py and cumulative execution checkpoint. Updated both report formats, current status, work log and this ledger. Private evidence remains local. Progress 4/20 → 4/20; root cause, Golden, Chrome, real dispatch and supervisor acceptance pending.

### Docker_3 / NB23-SESSION-RESUME-11 — Softmax boundary and staging replay

- Report baseline 34ea078, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist).
- Implemented locally under infra/nb23-v4: optional float64 witness in probe_onnx_intermediates.py, guarded staging grants in session_staging_rls.sql and simplified generator in prepare_session_product.py, blank-page readiness in check_session_browser.py, cumulative local checkpoint. Report updated in all five requested report files and this ledger.
- Tested: both Softmax witnesses exit 0 with preserved logits, equal input and different output. Isolated PG provision exit 0, API authority preflight failed at EXECUTE check with stale material, guarded SQL exit 0 and API container restarted. Blank-page Chrome CDP exit 0. First HTTPS poll failed before browser launch. Float64 witness, readiness recheck, Chrome E2E, parity, actual dispatch and acceptance are pending.
- Progress 4/20 → 5/20. See [detailed evidence and continuation](../../docs/codex_execution/MAC_FIRST_START_FA.md#docker_3--مرز-کنترلشدهٔ-softmax-و-بازیابی-staging).

### Docker_3 / NB23-SESSION-RESUME-12 — recovered HTTPS and bounded Softmax measurement

- Baseline report 78a6088, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14, activity 1), P3M22-A06 (Module 22, activity 6), P3OP11-R07 (§Launch checklist).
- Tested: isolated BFF/Bootstrap namespace recreation plus edge restart allowed verified 200/0 on both app and IdP. Chrome then timed out in Page.navigate. Automatic approval for rerunning the modified browser harness returned HTTP 404. Docker numerical reference exited 0 and kept historical/edited logits and fingerprints unchanged.
- Implemented locally: delayed navigation in infra/nb23-v4/check_session_browser.py, temporary candidate Softmax precision option in probe_onnx_intermediates.py, and local checkpoint. Updated all five report files and this ledger. Progress 5/20 → 5/20. Native numerical reference, candidate check, Chrome, Golden, product dispatch and acceptance remain open. [Details](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-13 — native reference and approval errors

- Baseline report 78a6088 with unpublished checkpoint 12 WIP, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: Native reference exit 0, both logits controls and previous fingerprints reproduced. Both runtime Softmax outputs are close to float64. Docker candidate launch and preliminary report publication attempt were rejected because automatic review returned HTTP 404. No executed candidate result on Docker. Chrome variant remains unrun.
- Implemented: local ledger plus cumulative sanitized Markdown, HTML, status, log and mission ledger. Added exact reproducible Docker invocation. Progress 5/20 → 5/20. Native candidate first-batch control pending, followed by parity only if remediation evidence supports it. Acceptance pending. [Detailed evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-14 — negative candidate result

- Report baseline 78a6088 with local pending reporting changes, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: native candidate option exit 0 on frozen Batch 1 with both logits controls and input fingerprints reproduced. Candidate max absolute delta 0.31366491317749023 against unchanged Native logits. Candidate fails required equality. Docker candidate and delayed Chrome action did not run after HTTP 404 review failures.
- Implemented this checkpoint in the local execution ledger and report documents. No runtime promotion. Second approval review for publication returned HTTP 404, latest verified GitHub report remains 78a6088. Progress 5/20 → 5/20. Next trace the causal impact with exact native Softmax output substitution and plan controls, continue independent browser flow when review is available. Golden, real dispatch and acceptance pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-15 — experimental retrieval-only integration

- Git baseline report 78a6088, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist). Owner changed the private test priority; official Golden and Freeze remain unaccepted.
- Implemented in the dedicated worktree: session-compose.yaml, session_worker_socket.py, session_product_api.py, check_session_browser.py, persistent_v4_pipe.py and its targeted socket regression. Existing frozen C018 resources, private data, candidate code and numeric traces remain outside the report branch.
- Tested: approved status inventory, existing three transport fixtures and Compose service list. Socket regression initially blocked by sandbox bind. Runtime startup and integrated test in progress. Formal 5/20, private 0/20 PASS, Freeze pending. [Cumulative evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-16 — stack ready and Chrome sign-in

- Report baseline 2ddff18, execution af57f26, V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: 4/4 fixture transport tests; PostgreSQL provisioning and Compose up exit 0; Worker-backed API startup, verified HTTPS status and Keycloak; real Chrome callback and signed History. Chrome stopped before POST because Send stayed disabled.
- Implemented locally: wait for UI History readiness and two-question/Refresh assertions in check_session_browser.py; cumulative ledger and private T01–T20 matrix. Formal 5/20, private 5/20 PASS, official acceptance pending. [Evidence and next command](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-17 — real Chrome-origin V4 context

- Report baseline c2be263, execution af57f26, V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: real Chrome Send and Refresh same Conversation/Attempt, one POST, SQL Send-only renewal. Real Worker CONTEXT_READY with 10 results and 95,537 ms. UI context wait expired at 95 seconds; extended recheck running. Generation/Gateway remain disabled.
- Implemented locally: V4 duration measurement persistence, conditionally exposed via existing signed API and consumed by BFF UI; staged banner and offline derivative recipe. Exact paths in report. Build and runtime validation pending. Formal 5/20, private 11/20, acceptance and Freeze pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-18 — real result browser recovery

- Report baseline 768b9be, execution af57f26, V4 f49f536f4d82, derivative UI 37b5c8ec3c50. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: two real CONTEXT_READY attempts and 95,537/73,111 ms with stable Worker PID. Signed Chrome GET and correlation-restored reload rendered actual result without POST. Offline Next and TypeScript build exited 0 and isolated SQLite fixture preserved duration and owner scoping. Automatic initial DOM wait and same-session distinct second question remain open.
- Implemented: browser read-only recovery diagnostics, status-control recheck and extended cross-owner test. Cumulative local checkpoint and report updated. Formal 5/20, private 12/20, supervisor acceptance pending. [Evidence and continuation](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-19 — persistent UNKNOWN and owner-scoped recovery

- Report baseline fea70af, execution af57f26, V4 f49f536f4d82, owner recovery UI 8b72e5b40a65. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: another Chrome-origin Attempt persisted as UNKNOWN, with no completed runtime receipt. Second fixture account denied the other account's conversation, Attempt and retrieval result. Offline derivative build and TypeScript succeeded. Live recovery across natural expiry pending.
- Implemented locally: attempt checkpoint owner binding, product chat expiry handling, staged build recipe, socket-peer cleanup and startup/error metrics, Chrome expiry and HTTP busy harnesses and local operator guide. See exact paths and methods in [report](../../docs/codex_execution/MAC_FIRST_START_FA.md). Formal 5/20, private 12/20, quality acceptance and Freeze pending.

### Docker_3 / NB23-SESSION-RESUME-20 — replay-only Idle regression

- Report baseline 11f5bc0, execution af57f26, V4 f49f536f4d82, recovery UI 8b72e5b40a65. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: cold readiness 111,945 ms and verified HTTPS; two Chrome expiry runs blocked by CDP evaluation timeout. Owner-scope fixture 5/5. HTTP contention persisted a FAILED Attempt. Its replay check failed on the unfixed version. Host ASGI fixture prerequisite LibreSSL -addext unavailable.
- Implemented locally: renew only after fresh T1/T2 inside the existing signed transaction in apps/api/product_session_api.py, and replay-only existing receipt probe in infra/nb23-v4/check_session_browser.py. Integration recheck pending. Formal 5/20, private 12/20, acceptance and Freeze pending. [Details](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-21 — cursor provisioning on isolated History

- Report baseline 11f5bc0 with checkpoint 20 local, execution af57f26, V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: actual Worker TimeoutError and persistent UNKNOWN, API restart and private TCP readiness, 149,423 ms Worker startup. OIDC callback succeeded while History returned structured 503 CURSOR_CONFIGURATION. Cursor key creation/mode/reuse smoke passed locally. Private-ASGI fixture remains blocked on host LibreSSL; no-dispatch tests reported 15 pass, one skip.
- Implemented locally: session_product_api.py isolated protected cursor configuration and check_session_browser.py sanitized History diagnostics. Latest rollout/replay and fresh send pending. First report publish attempt and one read-only escalation returned HTTP 404. Formal 5/20, private 12/20, acceptance pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-22 — verified same receipt with no Idle renewal

- Report baseline d07f216, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Implemented locally: API/Worker startup separation and controlled rewarm in session_product_api.py, readiness admission guard in apps/api/product_session_api.py, startup timing support in persistent_v4_pipe.py and updated runbook.
- Tested: real isolated HTTPS, OIDC and paginated signed History; existing FAILED receipt replay HTTP 200 with unchanged SQL session timestamps, outcome and Attempt count. Initial synchronous startup failure recovered by the isolated architecture change. Fresh Send/Worker and Chrome flow are pending. Formal 5/20, private 13/20, approval and Freeze pending. [Details](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-23 — current Worker startup blocked

- Report baseline d07f216, execution af57f26, pinned V4 f49f536f4d82 and owner recovery UI 8b72e5b40a65. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: current approved trial exit 1 with Worker startup TimeoutError; earlier signed History and safe replay passed on the same new stack. New Send and Chrome completion not run. No reranking or ONNX changes.
- Implemented cumulative reporting and local checkpoint; complete private T01–T20 status and safe owner/rollback procedure are in the Persian report. One publication approval and one separate status read returned HTTP 404. Formal 5/20, private 13/20, official acceptance/Freeze pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-24 — scoped recovery and transport readiness

- Report baseline b67d6a4, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: read-only Docker/host/cache/cgroup checks, PG provision and scoped Compose startup, two verified HTTPS 200s and three private listeners. Current worker child and connected socket remained active while archived timeout logs were excluded. New startup timing unavailable.
- Implemented: running witness and lower observation frequency in check_session_browser.py, corrective checkpoint local and reports. Formal 5/20, private 13/20, Chrome and acceptance pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-25 — current dispatch and Chrome blocker

- Report baseline f492c64, execution af57f26, pinned V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: authenticated signed OIDC/History and current fresh dispatch RUNNING, then operational ledger UNKNOWN without a new POST. Automatic recovery left one engine child connected. Current HTTPS and internal readiness were observed. Chrome pipe, direct page WebSocket and standalone dump-dom stopped before Send; exact symptoms are in the report.
- Implemented: browser transport alternative and safe diagnostics in check_session_browser.py and cumulative reporting. Formal 5/20, private 13/20, Chrome owner window and readiness pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-26 — fresh-attempt deadline and resource evidence

- Report baseline 40a41f2; execution af57f26; V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Tested: host memory/CPU/iostat, Docker per-service usage and cgroups, no active excess test process. Verified HTTPS, fresh authenticated Send, old 179.230-s T2-to-UNKNOWN and current 180-s RUNNING-to-UNKNOWN. No result metrics or owner window; no Chrome automation repeated.
- Implemented: changed the question in the existing staging HTTP harness and updated cumulative local/report evidence with a short manual checklist. No resource changes. Formal 5/20, private 13/20, Freeze and acceptance pending. [Detailed evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-27 — manual diagnostic handoff

- Report baseline 7ddf7d4; execution af57f26; V4 f49f536f4d82. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Implemented: staggered startup documented in infra/nb23-v4/STAGING_RETRIEVAL.md and owner launcher process liveness in check_session_browser.py. Preserved existing work, sources, frozen C018 and parallel branches.
- Tested: isolated PG/IdP-first Compose, app/IdP HTTPS 200/0, real signed test exit 0, CONTEXT_READY with 10 results, 86,982 ms Worker and 89.001 s signed-poll observation. GET/replay and logout retained signed behavior. Same Worker and dedicated Chrome were live after owner launch. Formal 5/20, private 14/20 (T20), manual browser steps and official acceptance/Freeze pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-28 — human diagnostic and Version B product fixes

- Report baseline cb57ead; execution af57f26; pinned V4 f49f536f4d82; local BFF 49970b87b4ab. P3M14-A01 (Module 14 activity 1), P3M22-A06 (Module 22 activity 6), P3OP11-R07 (§Launch checklist).
- Owner-reported Chrome manual evidence: login, actual 10-result retrieval at 139.47 s, expiry and same-Attempt recovery after sign-in, stale processing label and new-thread navigation defect, successful session-management round trip. Old SQL deadlines and matching result independently observed without exposing owner identifiers.
- Implemented: scoped local session policy across Bootstrap, BFF alias and callback cookie; draft promotion, terminal label, retrieval polling and keyboard handling. Exact paths and Dockerfile, checker and runbook changes in report.
- Tested: offline build/TypeScript, staged BFF/Bootstrap-only replacement, preserved API/Worker/PG/IdP and History/outcome counts, signed HTTP policy and revocation exit 0. Chrome recovery/controls proceeded to the Logout boundary, then Chrome tooling errored on both attempts. New keyboard Send/live result display remain manual checks. Formal 5/20, private 14/20, acceptance and Freeze pending. [Evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-29 — approved local scope and selective handoff

- Report baseline dd2cf7f; execution af57f26; V4 f49f536f4d82; BFF 0c2cba75df12. Sources: previous owner manual report, live signed session and aggregate ledger, no private data. Canonical P3M14-A01/A02/A03/A09/A10/A11 and P3M15-A01/A02/A03/A07/A10; isolated recovery P3M22-A06 and overlay P3OP11-R07. Consult the independent mapping for UI-03/05/06/10/11.
- Implemented: apps/web/src/ui/product-chat.tsx, apps/web/app/history/history.css, infra/nb23-v4/session_conversation_titles.sql, provision_session_postgres.py, Dockerfile.session-v4-web, check_session_browser.py and STAGING_RETRIEVAL.md. No shared migration or wire contract changes. Local trigger kept in B; DB specialist review for future title mechanisms.
- Tested: three corresponding actual durations and ten results, SQL rollback dry run and applied title-only backfill with count parity, offline build, BFF-only rollout with in-memory store, preserved containers and signed policy/revocation. Chrome Page.navigate timed out on new image; manual regression pending. Owner reports prior full private checklist successful, separate from automated evidence. Formal 5/20 with supervisor acceptance/Freeze pending.
- [Cumulative evidence](../../docs/codex_execution/MAC_FIRST_START_FA.md) and [selective handoff](../../docs/codex_execution/LOCAL_DOCKER_UI_FIXES.md).

### Docker_3 / NB23-SESSION-RESUME-30 — human confirmation and execution rollback point

- Report baseline 28de5d0, execution af57f26 with existing WIP, BFF 0c2cba75df12 and Engine V4 f49f536f4d82. P3M14-A02/A03/A09/A11 (Module 14 UI/History), P3M15-A02/A03 (Module 15 title/order), and recovery P3M22-A06 / P3OP11-R07 (§Launch checklist).
- Human evidence: owner explicitly reported all six checkpoint 29 manual UI checks successful. Automated browser test was not rerun. Official quality, Golden, Freeze and supervisor acceptance remain open.
- Created private local execution snapshot artifacts/nb23-v4-recovery-cp30. Validated 221 archived files, SHA256SUMS, four live mount hashes, seven image IDs and six-service pinned Compose after extraction. No live recovery drill. All seven service start/image identities unchanged. Package excludes private data, sessions, credentials, model/index and image layers. Only sanitized reports are published.
- [Owner evidence and recovery boundaries](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### Docker_3 / NB23-SESSION-RESUME-31 — offline DeepSeek preparation

- Report baseline 50eb808; execution af57f26, retained BFF 0c2cba75df12 and V4 f49f536f4d82, local NB22E-v4 and C340 pinned template. P3M10 (Module 10 Attempt/idempotency); P3M13 (Module 13 API); P3M14-A03/A09 (Module 14 UI/error); P3M15-A01/A07 (Module 15 persistence and ownership).
- Implemented two offline sources under infra/nb23-v4, approved two-variable private config outside worktree and cumulative reporting. Six Mock tests, pinned template and private ENV preflight passed. No actual historical failure rerun, secret publication, provider charge, product deployment or UI integration.
- Same-Attempt Context payload bridge and separately approved egress remain blocking. Runtime provider validation, semantic/citation policy, persisted response UI and formal acceptance pending. [Evidence and provisional test budget](../../docs/codex_execution/MAC_FIRST_START_FA.md).

### NB23-SESSION-RESUME-32

P3M10 (Module 10 Attempt و منع تکرار)، P3M13 (Module 13 API)، P3M14-A03/A09 (Module 14 نمایش و خطا)، P3M15-A01/A07 (Module 15 ذخیره و مالکیت). مبنا، مسیرهای دقیق، فرمان‌ها و نتیجه آزمون، شکست TS2307، تصمیم‌های اجرایی و وابستگی‌های بعدی در [شواهد تجمعی](../../docs/codex_execution/MAC_FIRST_START_FA.md) ثبت شده‌اند. پیاده‌سازی و آزمون مؤلفه Mock ثبت شد. پذیرش ناظر و آزمون واقعی بازند.


### NB23-SESSION-RESUME-33

آداپتر HTTPS آزمون آفلاین ۳/۳ را گذراند و پشته Chrome ساختگی ساخته شد. PostgreSQL، API و Worker سبک آماده شدند. آزمون Chrome در مهلت بعدی آمادگی Keycloak ادامه دارد. درخواست خارجی صفر. P3M10، P3M13، P3M14-A03/A09 و P3M15-A01/A07. [نسخه مبنا، مسیرهای تغییر، فرمان آزمون و نتیجه به‌همراه اقدام بعدی](../../docs/codex_execution/MAC_FIRST_START_FA.md).


### NB23-SESSION-RESUME-34

آزمون یکپارچه Chrome، Keycloak، BFF، API، PostgreSQL و Generation Mock موفق شد. پاسخ زیر سؤال و حفظ همان Attempt در Refresh و History، با دقیقاً یک dispatch تأیید شد. آداپتر HTTPS غیرفعال است. درخواست خارجی صفر. P3M10، P3M13، P3M14-A03/A09 و P3M15-A01/A07. [نسخه مبنا، مسیرهای تغییر، فرمان آزمون و نتیجه به‌همراه اقدام بعدی](../../docs/codex_execution/MAC_FIRST_START_FA.md).


### NB23-SESSION-RESUME-35

کنترل بسته زنده و دستور smoke آماده شد و آزمون آفلاین ۴/۴ موفق بود. تعرفه همان Gateway و بازیابی کامل حساب و تاریخچه نسخه B احراز نشد. درخواست خارجی صفر و نسخه B دست‌نخورده است. P3M10، P3M13، P3M14-A03/A09 و P3M15-A01/A07. [نسخه مبنا، مسیرهای تغییر، فرمان آزمون و نتیجه به‌همراه اقدام بعدی](../../docs/codex_execution/MAC_FIRST_START_FA.md).


### NB23-SESSION-RESUME-36

Smoke واقعی ساختگی موفق شد و گزارش آن پس از اعتبارسنجی آفلاین یک پاسخ ثبت شد. Volumeها و PostgreSQL پایدار مستقل برقرارند و Chrome هنوز در مرحله آزمون است. P3M10، P3M13، P3M14-A03/A09 و P3M15-A01/A07. [نسخه مبنا، مسیرهای تغییر، فرمان آزمون و نتیجه به‌همراه اقدام بعدی](../../docs/codex_execution/MAC_FIRST_START_FA.md).
