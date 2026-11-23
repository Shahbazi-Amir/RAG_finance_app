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
