# SPEC-P3-02 — PostgreSQL migrations, isolation and recovery

**Status: PARTIALLY ACHIEVED.** Migration identity and static safeguards were verified on the exact source. PostgreSQL execution remains pending.

## Baseline and scope

- Branch `phase3/completion`, tested source `c6f55f67bb98c359ff210aa2a2461280e64a68c6`. The only delivered path is this report. No SQL, tests, coordination register or project state changed.
- Scope from [P3-00](SPEC-P3-00-phase3-audit.md) and [P3-01](SPEC-P3-01-baseline-reconciliation.md): M04, M06 and the PostgreSQL slice of M22. P3-01 baseline itself remains partial. This run used the local app repository and made no connection to live Arvan or the engine repository.
- macOS preflight found no `psql`, `pg_isready`, `postgres`, `initdb`, `pg_ctl`, `pg_dump`, `pg_restore` or `pg_basebackup` on PATH. Standard Homebrew, Postgres.app, MacPorts and EnterpriseDB locations checked did not provide PostgreSQL binaries. Docker CLI was present, but the daemon was unreachable during the normal and approved checks. Python 3.11 and psycopg 3.3.4 were available as a client toolchain. No temporary DB was created, so no service or data cleanup was required.

## Inventory and evidence boundary

- [Migrations](../../infra/postgres/migrations/) contain 20 files for 001–010, split into 10 up/down pairs. History and attempt uniqueness, Auth sessions, epoch fences, replay protection, reset flows and initial login claim material are covered by the chain. The [pin manifest](../../infra/postgres/dev_f3_isolated/MIGRATIONS_001_010_PINNED.tsv) identifies the exact source trees. The [migration runner](../../infra/postgres/dev_f3_isolated/scripts/03_apply_pinned_001_010.sh) tracks STARTED/APPLIED and fails closed on partial state. [Full cycle](../../infra/postgres/dev_f3_isolated/scripts/23_m04_migration_full_cycle.sh), [populated upgrade](../../infra/postgres/dev_f3_isolated/scripts/15_populated_pre009_upgrade_restore.sh), [fault injection](../../infra/postgres/dev_f3_isolated/scripts/16_fault_injected_migration_ledger.sh), [query plans](../../infra/postgres/dev_f3_isolated/scripts/17_populated_query_plan_and_owner.sh) and [rollback constraints](../../infra/postgres/dev_f3_isolated/scripts/12_rollback_rls_constraints_probe.sh) are runtime witnesses to execute later.
- [Role provisioning](../../infra/postgres/dev_f3_isolated/scripts/02_provision_roles.sh), [TLS/RLS matrix](../../infra/postgres/dev_f3_isolated/scripts/05_test_roles_tls_rls.sh), [History negatives](../../infra/postgres/dev_f3_isolated/scripts/19_history_rls_negative_matrix.sh) and the [owner/idempotency runner](../../tests/phase3/integration/api/db_idempotency_owner_scope_ci.py) cover the app/migrator boundary, role grants, owner A/B and replay. The [concurrency probe](../../infra/postgres/dev_f3_isolated/scripts/24_m10_idempotency_concurrency_probe.sh) and [HTTP DB suite](../../tests/phase3/integration/api/test_http_postgres.py) require provisioned isolated roles and DSNs.
- [011 SQL](../../infra/postgres/migrations/011_external_dispatch_claim.up.sql) adds forced RLS and role-scoped claim/status and reporter/reconciler functions. Its wire/recovery tests are [011 HTTP](../../tests/phase3/integration/api/test_external_dispatch_claim_011_http.py) and [claim bridge](../../tests/phase3/api/test_staging_claim_bridge.py). The [DB55 verifier](../../infra/postgres/staging/db55_verify_staging.sql) and [no-dispatch bridge](../../infra/postgres/staging/db55_no_dispatch_bridge.sql) are separate inputs. The [optional compatibility lab](../../infra/postgres/dev_f3_isolated/scripts/08_optional_011_compat_only.sh) is separate from the App-only 001–010 baseline. The supplied 011 SQL has an up migration only. No rollback ability for 011 or real dispatch was established.
- [Independent logical restore](../../infra/postgres/dev_f3_isolated/scripts/06_backup_restore_independent.sh), [corruption detection](../../infra/postgres/dev_f3_isolated/scripts/20_backup_integrity_corruption_probe.sh), [restore catalog parity](../../infra/postgres/dev_f3_isolated/scripts/22_restore_catalog_parity_probe.sh), [crash recovery](../../infra/postgres/dev_f3_isolated/scripts/25_pg_crash_recovery_probe.sh), [physical PITR](../../infra/postgres/dev_f3_isolated/scripts/29_physical_pitr_ci.sh) and [signed restore](../../tests/phase3/integration/foundation/test_history_restore_signed.py) were identified as DB-runtime checks. The existing DB lab receipts are historical and remain tied to their recorded source and environment.

## Verification on the tested SHA

All commands ran at repository root. `PY` below is `/private/tmp/rag-arvan-pytest/bin/python`.

| Command or reproducible method | Actual result |
| --- | --- |
| `command -v` for the PostgreSQL tools above; check the standard locations listed above | No PostgreSQL executable found. |
| `docker info --format '{{.ServerVersion}}'`; approved retry with `docker version --format '{{if .Server}}{{.Server.Version}}{{end}}'` | No server version. Approved retry exited 1, Docker daemon unreachable. |
| `bash infra/postgres/dev_f3_isolated/tests/run_static.sh` | Exit 0. Static manifest, script syntax, Compose, TLS/RLS definitions, no-011 and no-demo checks passed. Protected-path negative passed. The script printed `REAL_POSTGRES_TESTS=NOT_RUN_IN_THIS_RUNTIME`. |
| For each manifest row, compare `git rev-parse --verify "$ref:$path"` with `git_blob_sha1`, using HEAD and the row's pinned source commit | 20/20 at HEAD and 20/20 at the pinned commits. 011 blob matched `031d2f438f000154eb4e2b374ce42181b3d812b3`. Both DB55 blobs matched the exact hashes in the bundle preparation script. |
| `$PY -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` | Exit 0, 71 passed. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_staging_claim_bridge.py` | Exit 0, 8 passed. Fake-connection claim/owner and receipt behavior only. |
| `$PY -B -m unittest discover -s tests/phase3/api -p test_full_binding_fence.py` | Exit 0, 5 passed. |
| `node --experimental-strip-types --test tests/phase3/ui/owner-fence.test.mjs` | Exit 0, 3 passed. |
| `env -i PATH="$PATH" "$PY" -B -m unittest discover -s tests/phase3/database -p 'test_*.py'` | Exit 1. Runner reported 100 tests and 114 errors, including cleanup errors. CI-only/runtime guards rejected the stripped, unprovisioned environment. No DB-backed assertion was credited. Repeat only with the pinned disposable DB and test-owned schema/roles. |

## Gate reconciliation and pending work

| Gate | Before | After | Pending evidence |
| --- | --- | --- | --- |
| P3M04-GATE | PARTIAL | PARTIAL | Apply up/down on clean and populated inputs; verify atomic interruption, ledger replay, foreign keys and query plans. Keep 011 compatibility separate. Retention decision and acceptance still needed. |
| P3M06-GATE | PARTIAL | PARTIAL | Run actual owner A/B SQL/HTTP and RLS/role/TLS negatives on the disposable instance. Unit and fake-connection checks provide bounded evidence. |
| P3M22-GATE | PARTIAL | PARTIAL | Independent logical restore and PG physical PITR with verified timeline/restore target, data/catalog parity, corruption negatives and measured durations. Approved destination RPO/RTO and Qdrant/producer restore evidence remain open. Qdrant/producer portion: `EXTERNAL_DEP (Codex-2)`. |

Totals stay **DONE 0, PARTIAL 22, PENDING 4** across 26 independent Gates. Next verification needs either provisioned isolated PostgreSQL for compatible local runtime checks or the repository's pinned Linux/amd64 PG 17.11 Docker/CI lab for the exact runtime witness. Follow the lab's ownership-checked cleanup and collect sanitized results. This run found no reproducible runtime migration defect that warrants changing a pin, guard or assertion.

## Proposed SPEC-P3-03 — OIDC session and history boundary

M05, M13 and M15 App-only slices. Allowed by the [audit](SPEC-P3-00-phase3-audit.md): `apps/api/`, `apps/web/app/api/auth/`, `apps/web/src/auth/`, `src/phase3/auth/`, `tests/phase3/integration/api/`, `tests/phase3/contracts/`, subject to path ownership. Acceptance requires HTTPS/mTLS/RS256/S256 and CSRF evidence, 401 after revocation, 404 across owners, History/Health, Send 503 with zero effects and separate expiry/revoke-all evidence. SMTP, complete reset and deferred mutations retain their separate approvals.
