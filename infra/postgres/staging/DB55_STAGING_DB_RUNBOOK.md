# DB55-STAGING-EXEC-01 — Foundation PostgreSQL staging execution package

STATUS: PREPARED ONLY / NOT APPLIED / SUPERVISOR+DB+OPS APPROVAL PENDING (2026-11-15).
No SQL, GRANT, schema change, staging access, restore, host operation or Gateway call was performed by this package. Unknown actual staging DB name, host, runtime user, backup, operator and deployed SHA MUST be filled from the authorized Ops inventory, not guessed. Keep C023 unaffected.

## 0. Immutable inputs and proof boundary

- Candidate Foundation Draft #55: https://github.com/Shahbazi-Amir/RAG_finance_app/pull/55 ; observed HEAD 9d4cf5dc6cb86b5cc174b71b9ed08c42f57d77de; API #53 pinned at 92f83561fcb8391f68b0b4e86ab5dcfc3970e8c5; UI #54 pinned at 0c522847cc627ade62f3da253332555f12b822a5. Git SHA is NOT the deployed SHA.
- main d93dcf7cbf9290acd4cd3aa0164ef05689049da4 contains 001–008. Login 009 from Draft #44 source 656604356dadea953031fcdb74650a5d42df4e9b, Login 010 from Draft #47 source 1678e87b7984094b74ec995383b8d4383e5f5ae7, Dispatch 011 from Draft #56 source b0ba6dbf6100109cb58f8cb49da808839d68c5f0. 009–011 are NOT merged. DBA needs a signed exceptional release manifest and Foundation approval before any staging installation.
- DB011 DB-only PG17.11 13/13 PASS: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43710425019 (Job #132800564220). API #53 signed PG17.11 011 stub Run #43714534192 is a CI-only in-memory counted stub, NOT paid delivery nor no-dispatch C018 evidence. No real staging DB, login or Gateway acceptance.

## 1. Scope split: NO DISPATCH versus paid LIVE

| Stage | Required migrations | Required function-only grants | Gate |
| --- | --- | --- | --- |
| session_core — already active Session / History / Logout | 001,002,003,004,005 | history_app: auth_l1 schema USAGE plus 005 consume_service_assertion(text,bigint) and 004 admit_session_fenced(text,text,bigint,integer). auth_revoker: existing schema USAGE plus the same two functions and 003 revoke_one(text,bigint). | Insufficient for NEW invited login. |
| private_no_dispatch — invited initial Login, signed POST 202, GET Status, C018 no Generation | Complete ordered chain 001–010. 006 is 009 gate prerequisite; 007/008 part of the ordered DB release. 009 and 010 come from the independent tested Draft SHAs, not main. | Above 003/004/005 bridge PLUS 009 bootstrap/issuer/binder/reader/cleaner roles and 010 auth_login_claim_reader with its exact function-only grant. | API must stay NO_DISPATCH_ONLY, no paid Gateway, no 011 requirement. |
| live_011 — DB Claim authority preparation only, after separate approval | 001–010 already approved and audited, THEN 011 UP. | history_app only 011 claim_external_dispatch/status_external_dispatch EXECUTE; dispatch reporter only flag_external_dispatch_unknown; independent reconciler only reconcile_external_dispatch. No direct Registry SELECT/UPDATE, no PUBLIC EXECUTE, FORCE RLS. | Installing 011 does NOT activate Paid Dispatch, T3 or LIVE_VERIFIED. |

Existing roles to provision via authorized DBA/Secret Store BEFORE corresponding migrations (this bundle never creates real accounts or passwords): history_app, history_migrator; auth_mapper, auth_sessions, auth_revoker, auth_reauth; auth_trust_api, auth_replay_cleaner; auth_reset_issuer, auth_reset_executor, auth_reset_lookup, auth_reset_idp_recorder; auth_login_bootstrap, auth_login_issuer, auth_login_binder, auth_login_reader, auth_login_cleaner, auth_login_claim_reader; and ONLY for 011 history_dispatch_reporter/history_dispatch_reconciler. Service roles must be NOSUPERUSER, NOBYPASSRLS, NOINHERIT, NOCREATEDB, NOCREATEROLE. Auth revoker currently also has 003 revoke_all/suspend_owner privileges; if a tighter Logout-only role is desired, coordinate API profile changes first. Neither this document nor CI-only Harness grants install production privileges.

## 2. Safe verification — READ ONLY (operator commands, NOT executed)

Operator gets the actual stage DB name, private DSN, service UID, verified PG server certificate, previous/new compatible app release SHA, approved DBA identity, PITR backup ID/Restore-clone proof and migration ledger from Ops. Never print connection secrets, keys, session digests, users, statements containing questions, or any PII. Each phase query uses catalog-only SQL under BEGIN READ ONLY; it never calls Claim or accesses user data. Run first on an isolated restored clone and only then read-only on target:

~~~bash
# DB55_READONLY_DSN provided by the authorized secret store (not in this repository).
psql -X -v ON_ERROR_STOP=1 -v db55_phase=session_core \
  "$DB55_READONLY_DSN" -f infra/postgres/staging/db55_verify_staging.sql
# Only after 009/010 and approved exact Auth bridge:
psql -X -v ON_ERROR_STOP=1 -v db55_phase=private_no_dispatch \
  "$DB55_READONLY_DSN" -f infra/postgres/staging/db55_verify_staging.sql
# Only after distinct 011 approval and installation:
psql -X -v ON_ERROR_STOP=1 -v db55_phase=live_011 \
  "$DB55_READONLY_DSN" -f infra/postgres/staging/db55_verify_staging.sql
~~~

An error means STOP (missing role/function, unsafe ACL, PG not 17, invalid DB target, wrong schema), not an automatic grant or migration. Catalog PASS only attests current structure/ACL, NOT the installed source digest, TLS/mTLS, real invited A/B, Runner or external provider. Independent staging positive/negative signed HTTP tests are still required.

Capture the PRE-grant privilege matrix with read-only pg_catalog role/schema/function queries and store it in private Ops evidence as booleans; a later blind REVOKE is unsafe without proof grants were absent before this change.

## 3. Release manifest, hash verification and installation order

Do not infer applied migrations from GitHub. Ops supplies actual DBA staging migration ledger and backups; compare names AND source digests. Verified UP Git blob SHA values:

| File stem | Source commit | Git blob SHA |
| --- | --- | --- |
| 001_history_l1 | main d93dcf7cbf9290acd4cd3aa0164ef05689049da4 | b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 |
| 002_one_attempt | main | d1a14f2ba16adb11c44122df1eded15f460d3c83 |
| 003_auth_session | main | 3eec77219a2462136b71b65dcae6e6a2b7998e90 |
| 004_session_aware_fence | main | 530094fe42cf75864bb3c01c1357c01febc419ae |
| 005_service_assertion_replay | main | 2899613dfc5ccac82733e35a5885635c969d99a5 |
| 006_atomic_reset_c1 | main | 98879f4dea04c49db5a4a0e429ef169c6823154d |
| 007_scoped_reset_identity_lookup | main | afe68b8ee866a1feb8a9d70a8a4bf8cba5a56aeb |
| 008_durable_idp_attempt_outcome | main | a94183aeac661476d4462e4a2f766a84e1dd8d32 |
| 009_initial_login_attempt_binding | 656604356dadea953031fcdb74650a5d42df4e9b | 2a694f871bf45aa5540b458bcaea1b2bd343036d |
| 010_initial_login_claim_material | 1678e87b7984094b74ec995383b8d4383e5f5ae7 | 3a8ec114ff29c9d8ef795fb85c32b57aecfa8f27 |
| 011_external_dispatch_claim (LIVE ONLY) | b0ba6dbf6100109cb58f8cb49da808839d68c5f0 | 031d2f438f000154eb4e2b374ce42181b3d812b3 |

Example release-bundle preparation/check, on an authorized LOCAL worktree with pinned Git objects; NOT an SSH/staging command. RELEASE_BUNDLE is an approved, private, empty directory:

~~~bash
git cat-file -e 'b0ba6dbf6100109cb58f8cb49da808839d68c5f0^{commit}'
git show 'b0ba6dbf6100109cb58f8cb49da808839d68c5f0:infra/postgres/migrations/011_external_dispatch_claim.up.sql' > "$RELEASE_BUNDLE/011_external_dispatch_claim.up.sql"
test "$(git hash-object "$RELEASE_BUNDLE/011_external_dispatch_claim.up.sql")" = '031d2f438f000154eb4e2b374ce42181b3d812b3'
git show 'b0ba6dbf6100109cb58f8cb49da808839d68c5f0:infra/postgres/migrations/011_external_dispatch_claim.down.sql' > "$RELEASE_BUNDLE/011_external_dispatch_claim.down.sql"
test "$(git hash-object "$RELEASE_BUNDLE/011_external_dispatch_claim.down.sql")" = 'ce3e7d8a2394f4a090650623770ad261eee2f4c2'
~~~

Repeat exact git show/hash-object checks for EVERY applicable UP/DOWN against signed release manifest. Apply ONLY migration versions proven absent, in order, to a RESTORED CLONE first, with live data shape and role matrix, verifying 002 multi-attempt guard and 009/010 Guard checks. Do not rewrite or skip old migrations, use IF NOT EXISTS to hide drift, or run 011 for no-dispatch. The existing migrations use their own transaction statements in some files; do not assume a blanket psql -1 supplies a globally atomic multi-file deploy. Backup/PITR and an Ops-controlled maintenance window are prerequisites for staging.

Only AFTER separate Foundation+DB+Ops approval, role provisioning and backup verification, DBA examples (NOT RUN HERE):

~~~bash
# If 001–008 are ALREADY installed with exact verified hashes, and 009/010 are not:
psql -X -v ON_ERROR_STOP=1 "$DB55_DBA_DSN" -f "$RELEASE_BUNDLE/009_initial_login_attempt_binding.up.sql"
psql -X -v ON_ERROR_STOP=1 "$DB55_DBA_DSN" -f "$RELEASE_BUNDLE/010_initial_login_claim_material.up.sql"
# Follow with exact scoped bridge, after capturing the PRE-grant ACL snapshot:
psql -X -v ON_ERROR_STOP=1 "$DB55_DBA_DSN" -f infra/postgres/staging/db55_no_dispatch_bridge.sql
# Prove role/function matrix via private_no_dispatch verifier above, NO dispatch.
~~~

If any prior migration is missing, a DBA-signed plan must add it first in numerical order; do NOT run those example commands against an unknown schema. The 009/010 migration creates only functions/grants to PRE-existing role names; creating user/password roles is outside this script.

## 4. Separate LIVE_011 decision (not a green light for Gateway)

Prerequisites: real private NO_DISPATCH smoke passed on staging with signed mTLS BFF/Keycloak A/B POST202 and independent GET, replay/refresh GET-only, no double Runner and CONTEXT_READY/Top10/Generation=0; exact compatible DB and API SHAs accepted; proven restore/PITR; 011 reporter/reconciler roles provisioned with separate restricted credentials; signed independent DB+API+Foundation+Ops authorization; verified service names/UID/GID, C023 non-interference, disabled paid worker. If ANY missing: LIVE_011=BLOCKED.

Only then 011 is rehearsed on restored clone, and in the distinct approved change window installed while Gateway dispatch is STILL DISABLED:

~~~bash
# FUTURE/DBA-ONLY/NOT EXECUTED:
psql -X -v ON_ERROR_STOP=1 "$DB55_DBA_DSN" -f "$RELEASE_BUNDLE/011_external_dispatch_claim.up.sql"
psql -X -v ON_ERROR_STOP=1 -v db55_phase=live_011 \
  "$DB55_READONLY_DSN" -f infra/postgres/staging/db55_verify_staging.sql
~~~

Positive/negative staging function gate: history_app schema history_l1 USAGE and only 011 Claim+Status EXECUTE, NO direct SELECT dispatch ledger; reporter only flag_unknown; reconciler only manual reconcile; PUBLIC zero EXECUTE; all service roles NO BYPASSRLS; table FORCE RLS. The read-only script checks structural ACLs; a separate DBA-approved synthetic attempt race/permission test is required to prove real staging behavior, without sending external Gateway requests or polluting real customer data.

Future API caller contract (not deployed now): inside SAME signed 005/004 session-fenced transaction after committed-intent T1 and T2, call history_l1.claim_external_dispatch(owner,execution_attempts.id,attempt_trace_id); only claim_won=true with DEFINITIVELY CONFIRMED OUTER COMMIT could authorize a single later Gateway send under a separate Live Gate. No Gateway call inside SQL transaction; any unknown commit, worker crash, replay, timeout, UNCERTAIN provider response or already RECONCILED_NOT_DELIVERED never authorizes another send. Owner-scoped status returns NOT_CLAIMED/CLAIMED/UNKNOWN/RECONCILED_* timestamps only. An aged CLAIMED row observes UNKNOWN, with permanent non-reclaimable unique claim. PostgreSQL proves ONE Claim, NOT exactly-once external delivery/billing.

## 5. Return/rollback: preserve evidence, fail closed

At any failing step: keep paid Dispatch DISABLED, freeze further claims/tasks, record ambiguous outcomes as UNKNOWN when supported, revert only Web+API configuration to the APPROVED compatible previous immutable SHAs and retest signed Auth/History/A-B status without launching a second Runner. Never assume a systemd unit or container/service name; obtain verified Ops runbook. Do not auto-replay JTI/Code/Gateway, erase History or drop a claim tombstone.

- 001–010 NO_DISPATCH: prefer app/config rollback, RETAIN existing Auth/History schema/data. Real 009/010 DOWN has evidence guards; do not bypass them. Exact scoped bridge permissions may be reversed only if BEFORE-state ACL proves each named grant was absent and the previous service no longer requires it. The optional file db55_rollback_auth_bridge.sql REVOKEs only the newly added bridge privileges, and is explicitly UNSAFE when permissions existed before the change or would interrupt an active service. DBA+Foundation authorization required.
- 011 before ANY committed claim: after quiescence and restored-clone trial, DBA may evaluate exact checked-in 011 DOWN; it removes the table/functions and must NOT run if claims exist. This is not an automatic rollback.
- 011 after ONE committed claim (including UNKNOWN or manually reconciled): checked-in 011.down MUST raise DISPATCH_011_DOWN_REFUSED_EVIDENCE_EXISTS and preserve the entire evidence. Safe return is code/config rollback with 011 schema retained and manual outcome reconciliation. No DROP/TRUNCATE/lease expiry re-Claim or synthetic blank DB restore. PITR/restore must separately account for already-sent external Gateway operations; otherwise it could erase a reservation and authorize a second paid send.
- Critical technical rollback is versioned code to compatible prior SHA (not a guessed host command), no customer data dump, and Ops audit: operator, timestamp, target, reason, backup ID, preceding committed Attempt counts and sanitized evidence. No direct staging Restore is performed here.

Approval-only bridge return command (NOT executed):

~~~bash
psql -X -v ON_ERROR_STOP=1 "$DB55_DBA_DSN" -f infra/postgres/staging/db55_rollback_auth_bridge.sql
~~~

## 6. Foundation signoff receipt and STOP status

Record named operator/DBA/API/Foundation approvals, verified deployed/previous Web+API SHA, private host/unit UID, PG17 version and target, migration ledger and per-file Blob SHA, staging role inventory before/after (booleans only), Backup/PITR+restored-clone proof, read-only verifier exit code for session_core/private_no_dispatch/live_011, real signed A/B 202/replay/status/no-generation, and if 011 later authorized, real synthetic staging Claim/STATUS/UNKNOWN evidence without Gateway network. Stop if C023 safety would be affected.

PACKAGE_IMPLEMENTED=DB-SOURCE-RUNBOOK+READONLY-VERIFIER+EXPLICIT-GRANT/ROLLBACK-TEMPLATES.
STAGING_EXECUTION=NOT_RUN. STAGING_DB_SCHEMA=NOT_OBSERVED. STAGING_GRANTS=NOT_APPLIED.
STAGING_MIGRATIONS=NOT_APPLIED. GATEWAY_CALLS=ZERO_BY_THIS_PACKAGE.
ACCEPTANCE=NONE_NEW/SUPERVISOR_PENDING. NO MERGE/DEPLOY.
