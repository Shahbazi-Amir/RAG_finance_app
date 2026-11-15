# DB55-ARVAN-PG17-NEW-EMPTY-01 — private staging destination decision and empty-clone plan

STATUS: PREPARED / NO SERVER ACTION / INSTALL NOT AUTHORIZED. DATE: 2026-11-16.
Owner: DATABASE_F3 (#57). Approval: Foundation (#55), authorized Arvan Ops/SSH and DBA, Supervisor.
Scope: first invited \`NO_DISPATCH_ONLY\` smoke; requires **ordered 001–010**, not Migration011.
Repository: Shahbazi-Amir/RAG_finance_app. Engine Shahbazi-Amir/RAG_finance remains READ-ONLY.

## 1. New operator observation and evidence boundary

The user relayed successful **read-only local discovery** from Arvan:
- \`LOCAL_PG_NOT_EVIDENCED\`: \`pg_lsclusters\` absent; no PostgreSQL systemd unit, process, socket or container was observed.
- This is **not proof of absolute absence** (inaccessible namespace/off-host PG is possible), nor proof that a remote managed PG instance is or is not provisioned.
- GitHub/Foundation #55/#57 records contain **no confirmed managed staging endpoint, DB name or private transport**. Do not invent a managed provider, remote host, DSN, credential, port, or CA.
- Actual target \`UNKNOWN\`; actual PostgreSQL version \`UNKNOWN\`; actual Migration 001–010 \`NOT_ATTESTED\`; \`history_app/auth_revoker\` actual grants \`NOT_AUDITED\`; staging backup/PITR \`NOT_ATTESTED\`. Synthetic PG17.11 GitHub Actions 43729811005 is **not Arvan evidence**.
- API readiness reported by user is a separate component; it **does not imply** DB startup or database migration success. Do not fill \`api-private.json\` PostgreSQL values until the actual target is verified and its private connection method is operator-signed.
- Last reviewed Foundation #55 [inspection coordination](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/55#issuecomment-6897719655) reported \`READ_ONLY_INSPECTION=NOT_AUTHORIZED_YET\`. No server write permission can be inferred from the user's read-only result. Require current Ops/NB23 noninterference and separate **CHANGE/INSTALL** authorization before any installation or cluster start.

## 2. Architectural decision and first executable command

**Managed-existing branch (precedence):** If Foundation/Ops has an actual pre-existing managed staging target, return a privately verified service/provider+DB identity, PG17.x server version, private-link/network TLS mode, trusted CA/server-name (\`verify-full\` where relevant), firewall/no public PG route, service/role credentials from private Secret Store and existing backup/restore plan. Do NOT create another cluster. This branch remains \`NOT_ATTESTED\`.

**New-local branch (proposed; not a provisioned fact):**
- PostgreSQL **17.x** on a separately approved Arvan staging DB cluster, logically isolated from production and NB23. DB name proposal \`ragfinance_staging\`; verify no pre-existing collision and approve explicitly before CREATE.
- Private same-host Unix Socket: planned \`listen_addresses=''\` after review (no public or loopback TCP PG listener), restricted socket directory/group/permissions, \`pg_hba.conf\` local authenticated \`scram-sha-256\` or individually reviewed \`peer\`+pg_ident mapping, **never trust**. Use different DB roles and protected account/secret material per application and DBA; running API as a nonroot UID does not justify superuser PG. Avoid exposed PG port 5432. If API runs in a separate container/namespace with no socket reachability, **stop** and redesign as mutually approved private-network TLS with exact CA/identity and firewall instead of guessing the socket.
- Stage cluster disk/memory/performance/backup footprint approved by Ops and no interference with NB23. Record actual data volume, owner, PG data dir/socket path and SSL/policy privately; no secrets in Git.
- Required principal roles, created only by DBA before clone migration execution: \`history_app\`, \`history_migrator\`, auth mapper/sessions/revoker/reauth/trust_api/replay_cleaner/reset issuer/executor/lookup/idp recorder, auth login bootstrap/issuer/binder/reader/cleaner/claim_reader. Names and role privileges are as enumerated in \`DB55_STAGING_DB_RUNBOOK.md\`; \`NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE\` for service roles. Confirm real service identity for each connection; do not assume a role exists from source code.

**First copy/paste command, on ARVAN LINUX HOST shell, only with Ops-approved read-only inventory scope:** no \`sudo\`, SQL connection, writes, package installation or service changes:

~~~bash
printf '%s\n' '=== OS ==='
cat /etc/os-release | grep -E '^(ID|VERSION_ID|VERSION_CODENAME|PRETTY_NAME)='
printf '%s\n' '=== ARCH ==='
uname -m
printf '%s\n' '=== PACKAGE MANAGER ==='
for p in apt-get apt-cache dnf yum; do command -v "$p" || true; done
printf '%s\n' '=== POSTGRESQL 17 PACKAGE ==='
if command -v apt-cache >/dev/null 2>&1; then
  apt-cache policy postgresql-17
fi
printf '%s\n' '=== MEMORY ==='
free -h
printf '%s\n' '=== DISK ==='
df -h / /var /var/lib 2>/dev/null
~~~

**Required return:** OS ID/codename/architecture; apt/dnf support; whether \`postgresql-17\` is a candidate in configured repository; memory+disk footprint. Redact any confidential mount labels if necessary. Do not assume Debian/Ubuntu before this output. If unsupported/insufficient, STOP and request Ops distro-specific design. Ubuntu/Debian PostgreSQL official packages may come from the OS apt repository or PGDG if that release supports it. **Installing \`postgresql-17\` can auto-create/start a cluster: requires an explicit host-change window and package-origin/signature review**. Never run \`apt install postgresql\` unversioned and silently accept 18/other major. Authoritative upstream: https://www.postgresql.org/download/linux/ubuntu/ and https://www.postgresql.org/download/linux/debian/ .

## 3. Authorized staging rollout sequence (future only)

0. Foundation receives the above OS/resources response and gives **separate** explicit \`NEW_PG17_INSTALL_APPROVED\`, signed Ops non-overlap/write window, exact package origin/codename/version, DB resource limits, backup and rollback owner. Existing managed DB evidence takes precedence.
1. DBA/Ops install exactly PostgreSQL17 with verified signed package source appropriate to reported OS and provision a **dedicated** cluster. Confirm \`SHOW server_version_num\` in 170000–179999 and \`current_database()\`, actual socket identity and \`listen_addresses\`; no user-facing 5432. Do not export authentication material to stdout. Installation and start **not authorized in this plan**.
2. Approve protected PG volume/permissions, minimal authenticated Unix Socket access for actual API nonroot service account, non-superuser app/revoker and migrator roles, private backup/PITR and monitoring. Provision a **separate empty isolated PostgreSQL17 clone cluster** (not a second DB assumed to be isolated from shared resources) and signed \`NEW_EMPTY\` catalog attestation. The clone and staging DB have distinct ownership / ACL evidence, no customer data. Do not call an empty-clone test a restored real-backup test.
3. Freeze immutable release manifest. Files 001–008 are based on repository main snapshot \`d93dcf7cbf9290acd4cd3aa0164ef05689049da4\`. 009 from independent source commit \`656604356dadea953031fcdb74650a5d42df4e9b\`; 010 from \`1678e87b7984094b74ec995383b8d4383e5f5ae7\`. These are not automatically on main; Foundation must sign exceptional release input and all 001–010 **actual Git blob SHA** checks. Exact basename/blob manifest is in \`DB55_STAGING_DB_RUNBOOK.md\` §3. No rewriting, skipping, or renumbering.
4. On **that disposable clone only**: provision least-privilege real-equivalent roles and verify pre-grant ACL **six booleans**, then run 001→002→003→004→005→006→007→008→009→010 sequentially, with the correct \`history_migrator\` vs \`auth_migrator\` executing contexts as recorded by the DB runbook. \`002\` fails closed on historical duplicate attempts. Stop on first error; no ad-hoc \`IF NOT EXISTS\` drift hiding. Record migration order + immutable source SHA and DB receipt; absence of a migration ledger is not solved by object-existence checks.
5. Clone read-only auditor: USAGE on \`auth_l1\`/\`history_l1\` schemas for signature resolution, **NO direct table SELECT/DML, no app-function EXECUTE, no BYPASSRLS**. Source-pinned \`infra/postgres/staging/db55_verify_staging.sql\` first with \`db55_phase=session_core\`, then \`private_no_dispatch\`. A missing bridge is an **expected diagnostic denial**, not automatic permission to grant.
6. After signed **clone-only** approval and PRE-state proof, apply unchanged \`infra/postgres/staging/db55_no_dispatch_bridge.sql\` by authorized DBA on clone; run read-only \`session_core\` and \`private_no_dispatch\` audits again; require \`DB55_session_core_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS\` and \`DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS\`. Use actual private auditor connection configured by Ops; do NOT invoke proposed alias \`db55_target_ro\` unless it really exists.
7. Run role-negative effective privilege checks on clone using **real restricted role connections** (not a privileged DBA impersonation shortcut): history_app **DENIED** direct SELECT on \`auth_l1.sessions\`; auth_revoker **DENIED** direct SELECT on \`auth_l1.sessions\` and \`history_l1.messages\`. Verify 003 \`revoke_one\` for revoker only; 004 \`admit_session_fenced\` and 005 \`consume_service_assertion\` for both; no history_app \`revoke_one\`; other required 009/010 bootstrap/issuer/binder/reader/cleaner/claim_reader function-only grant matrix and FORCE RLS on History messages/attempts. A catalog PASS is not an authenticated invocation PASS. Later signed isolated A/B negative test remains a separate gate.
8. Conditional clone-only rollback rehearsal using unchanged \`db55_rollback_auth_bridge.sql\` ONLY if all six PRE bits were provably **FALSE**, no dependent services and DB+Foundation approve. Existing effective privileges must never be blind-revoked. Confirm post-rollback expected denial and restore clone if needed.
9. DBA signs \`EMPTY_CLONE_001_010_PASS\` with migration blobs, roles, denies, RLS, backup/restore approach. Only a later separately signed **staging WRITE/INSTALL authorization** allows installing 001–010 to the new dedicated staging DB, with ordered ledger and DB-level verification identical to clone. Take backup/PITR checkpoint per approved policy before staging change; preserve evidence.
10. Only after actual \`SERVER_VERSION\` and \`DB_NAME=ragfinance_staging\` (if approved) and private socket route/roles are confirmed may API/Ops privately fill the PostgreSQL config inside \`api-private.json\` using the **actual API schema** and private Secret Store; do not invent keys, DSN or file structure. API startup fail-closed until actual 004/005 and 009/010 access works. First invited A 202→CONTEXT_READY, generation_calls=0, GET-only replay and B404 remain separate live no-dispatch smoke.
11. **No Migration 011**, Claim, external Dispatch, paid Gateway, automatic retry, live Answer or T3 in the first smoke. Do not run CI synthetic harness on staging: \`tests/phase3/database/db55_backup_restore_validation.sh\` is explicitly guarded to run on disposable GitHub Actions PG and its existing green [Run 43729811005](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43729811005) proves only that environment.

## 4. DB handoff receipt to Foundation

Return only non-secret booleans/identifiers:

~~~text
LOCAL_PG_DISCOVERY=NOT_EVIDENCED_OPERATOR_REPORTED
MANAGED_STAGING_DB=NOT_ATTESTED
OS_ID=UNKNOWN
PG17_PACKAGE_CANDIDATE=UNKNOWN
NEW_LOCAL_PG17_INSTALL_APPROVED=NO_ATTESTATION
TARGET_DB_NAME_ACTUAL=UNKNOWN
TARGET_DB_NAME_PROPOSED=ragfinance_staging
PRIVATE_CONNECTION_ACTUAL=UNKNOWN
PRIVATE_CONNECTION_PROPOSED=UNIX_SOCKET_SAME_HOST
POSTGRES_REAL_VERSION=UNKNOWN
MIGRATION_001_010_REAL=NOT_INSTALLED_OR_ATTESTED
MIGRATION_001_010_EMPTY_CLONE=NOT_RUN
history_app_ROLE_ACL_REAL=NOT_AUDITED
auth_revoker_ROLE_ACL_REAL=NOT_AUDITED
AUTH_009_010_ROLE_ACL_REAL=NOT_AUDITED
BACKUP_PITR_REAL=NOT_ATTESTED
MIGRATION_011=NOT_REQUIRED_FOR_FIRST_NO_DISPATCH
READY_FOR_NO_DISPATCH_DB=BLOCKED
~~~

Operator next: read-only OS/package/resource command above → return sanitized results → Foundation+Ops approve specific PG17 method/write window → DBA creates isolated clone and executes source-verified 001–010; no install or service change in this handoff. No secret/DSN/password/cert/private IP or user data in any GitHub ticket.
