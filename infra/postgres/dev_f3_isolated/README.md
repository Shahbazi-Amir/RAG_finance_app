# RAG_finance — F3 DATABASE isolated fresh install development bundle (2026-11-22)

**Status:** complete disposable PG17.11 Docker candidate including actual pinned Product/Bootstrap DB authority preflight and restored-cluster repeat **PASSED** on source commit `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74`, [CI run 45082326382](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45082326382) (two jobs: base 001–010 shared DB witness + restore, optional separate 011). The Mac demo was NOT touched. **Not** proof of Product/Bootstrap ASGI HTTP startup, C018 or Gateway.

**Purpose:** one fresh **isolated** PostgreSQL 17.11 lab with 001..010, 20 pinned Git blobs, 2 Product + 7 Bootstrap service-role TLS logins, DB55 `private_no_dispatch`, a durable per-migration `STARTED/APPLIED` ledger, and a backup restored into a **second independent PostgreSQL cluster with a different volume**. No existing demo or Arvan resource is modified. `011` is EXCLUDED from this path.

## Absolute separation

The accepted Mac demo is NOT a test target:

- Demo DB: `rag_finance_f3_demo`
- Demo Docker volume: `rag_finance_f3_demo_pg17_20261121`
- Demo evidence directory includes `PRODUCT_FIRST_START_PREP/CENTRAL_FIRST_START_20261121`

This bundle uses ONLY `rag_finance_f3_lab`, random unique `rag_finance_f3_LAB_...` and `rag_finance_f3_RESTORE_...` volumes, an internal-only Docker network, **no published ports**, and a separate `LAB_ROOT` directory. Source Git checkout is only read via `git show`; no changes to its worktree, branches or Docker/demo config.

## Source provenance

| Component | Immutable Git commit | Git blob SHA-1 |
|---|---|---|
| 001–008 UP/DOWN | `d93dcf7cbf9290acd4cd3aa0164ef05689049da4` | full `MIGRATIONS_001_010_PINNED.tsv` |
| 009 UP/DOWN | `656604356dadea953031fcdb74650a5d42df4e9b` | full manifest |
| 010 UP/DOWN | `1678e87b7984094b74ec995383b8d4383e5f5ae7` | full manifest |
| DB55 auditor | `bfd6b1d9ed23e5f4cc6f126b579f90d7c877a7a6` | `e2115d8cebc649fdf05d3fbee4ef435ad5f39a47` |
| DB55 bridge | same | `a79e46c87857eb2b77fd26863e1cf85fead31b38` |

`MIGRATIONS_001_010_PINNED.tsv` SHA-256 = `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7` (**locally checked**). The original 007 DOWN has the corrected 40-hex Git blob `440764eb11fb201a5d63b7742415cfe924d54a9e`.

Docker image expected pinned digest: `public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a`, `linux/amd64`, PostgreSQL 17.11. Digest-platform-runtime match requires Docker inspect on the executing host.

## Run on an authorized lab host with Docker Desktop/Compose

From an up-to-date local checkout with the **source commits fetched into local Git object storage**, e.g. a separate read-only Git clone `RAG_finance_app`:

```bash
# POSIX-compatible path without spaces. Do not use any accepted demo directory.
export SOURCE_REPO='/absolute/path/to/RAG_finance_app'
export LAB_ROOT='/absolute/new/f3-db-test-20261122'

# The following commands apply to THIS bundle's own script paths.
bash scripts/00_prepare_source.sh
bash scripts/01_create_isolated_lab.sh
bash scripts/02_provision_roles.sh
bash scripts/03_apply_pinned_001_010.sh
bash scripts/04_bridge_and_db55.sh
bash scripts/05_test_roles_tls_rls.sh
bash scripts/09_shared_stack_db_preflight.sh
bash scripts/06_backup_restore_independent.sh
bash scripts/10_restored_stack_db_preflight.sh
```

The first command requires **all** immutable commits `d93dcf...`, `656604...`, `1678e...`, `bfd6b1...` to be available locally; fetch them in the isolated checkout if necessary. It hashes all 20 SQL files AND 2 DB55 files with `git hash-object`, then writes a private SHA256SUMS. No SQL files are altered or rewritten. DOWN files are integrity inputs only.

**Expected milestones:** `SOURCE_BUNDLE=22_SQL_FILES_PIN_VERIFIED`, `F3_LAB_CREATED_ISOLATED=PASS`, `F3_LAB_PROVISION_ROLES_SERVICE=lab-db ROLE_COUNT=20 PASS`, `F3_LAB_MIGRATIONS_001_010_APPLIED=PASS`, `DB55_PRIVATE_NO_DISPATCH_LAB=PASS`, `TLS_VERIFY_FULL_NINE_ROLES=9/9_PASS`, `NEGATIVE_TABLE_SELECT=72/72_PASS`, `BACKUP_SHA256_VERIFIED=PASS`, `RESTORE_INDEPENDENT_CLUSTER=PASS`, `RESTORED_DB55=PASS`.

Markers were actually observed in CI `45082326382`: additionally `PRODUCT_API_REAL_DB_PREFLIGHT=2/2_PASS`, `BOOTSTRAP_API_REAL_DB_PREFLIGHT=7/7_PASS`, `RESTORED_MIGRATION_LEDGER_EXACT_MATCH=PASS`, restored nine-role TLS checks, and an uploaded `foundation.f3_db_candidate_shared.v1` sanitized JSON receipt. See `contracts/FOUNDATION_CANDIDATE_SHARED_DB_HANDOFF.md` for exact boundaries.

### Evidence / integrity / reproducibility

- All outputs and passwords stay under `LAB_ROOT/work` and `LAB_ROOT/secrets`, mode 0700/0600 where applicable. `source` contains nonsecret reviewed SQL and is world-readable inside the isolated PostgreSQL container.
- Role credentials are LAB-ONLY random passwords, never reusable in demo or deploy; the LAB CA has a 3-day lifetime. Validity must be checked for exact target host and mode.
- `db55_audit.migration_runs` is created **before** migrations; each attempt commits a `STARTED` row containing Git blob and SHA-256, then SQL runs, followed by `APPLIED`/timestamp/txid. Partial state is **STOP**, not a retry. A second invocation after ten exact APPLIED rows returns `ALREADY_APPLIED_EXACT_PINS_NO_RERUN`.
- SQL may contain its own BEGIN/COMMIT. The application transaction and ledger transaction are **not** one atomic transaction; the STARTED marker prevents an unsafe blind replay after a crash. Recovery requires examining a disposable snapshot or building a *new* lab from scratch.
- `db55_no_dispatch_bridge.sql` is installed once after verifying none of six preexisting grant bits were true. Bridge intent is recorded and must be reconciled before retry if ambiguous.
- `db55_verify_staging.sql` runs as a separate limited auditor via `SET ROLE` under a `READ ONLY` transaction. It is **not** a migration or installer.
- `05_test_roles_tls_rls.sh` tests `verify-full` for precisely 9 service roles, non-TLS rejection, 9 bootstrap function privileges, 72 catalog-level direct Auth table SELECT denials, role flags, critical FORCE RLS. These checks are lab-only. Real Product/Bootstrap configs must separately pass the actual API preflight.
- `06_backup_restore_independent.sh` creates a **different** PostgreSQL 17.11 container/volume with an independent `pg_control_system()` identifier, provisions matching roles, and `pg_restore`s the dump with original owners/grants (NOT `--no-owner`). It compares **all ten original Ledger rows**, DB55, nine role flags, 72 denied Auth SELECT grants, catalog counts and FORCE RLS. `09_shared_stack_db_preflight.sh` imports **actual** pinned Product/Bootstrap verifier functions in two separate DB client containers using distinct role-only passfiles on the private Docker network; `10_restored_stack_db_preflight.sh` exercises both original verifiers against the independent restore with `verify-full`. `11_export_sanitized_receipt.sh` creates an exportable CI JSON receipt with IDs, code pins, row-level Ledger, backup hash and four real-code client preflight witnesses; never outputs credentials.
- The lab snapshot and credentials are disposable. This is not a full product failover/PITR or credential+PKI disaster recovery test.

### No automatic cleanup

Cleanup is deliberately a separate action, gated by `ALLOW_DELETE_F3_LAB=YES`; it checks Compose project ownership and **only** deletes its own randomly named volumes and containers. Never invoke it against demo. No script in this bundle touches or asks Docker to stop running demo containers.

```bash
ALLOW_DELETE_F3_LAB=YES bash scripts/07_cleanup_lab_ONLY.sh
```

## Dependencies / stop conditions

1. **Executing host** needs Docker Engine + Compose, Git with the four source commits, Bash, OpenSSL, `shasum`, `grep`, `awk`. Host architecture may be Apple Silicon: Compose requests `linux/amd64` emulation, not a macOS venv.
2. If the pinned PG image is unreachable, Docker/Compose unavailable, source pin absent, volume exists, demo-like path detected, version mismatch, TLS/PG privileges fail, STOP. Do not replace the image, SQL or checks with a guessed version.
3. Docker Desktop VM free space for two full lab volumes + archive must be measured on Mac; `Docker.raw` logical size is not free VM space.
4. Do not use an approved demo DB/Volume for testing or rely on its old terminal logs as proof of the new lab. **The real Product/Bootstrap Python DB verifier functions run** in read-only DB client preflight processes. Actual ASGI HTTP servers, signed BFF, IdP, C018, Gateway and Arvan do **not** run.
5. **Separate post-010 migration:** pinned `011_external_dispatch_claim` remains outside the `private_no_dispatch` installation. `scripts/08_optional_011_compat_only.sh` passed after full 001–010 in an **independent** disposable lab, same CI run `45052366022`; Gateway calls = 0. Its live activation requires separate Product/API/Security approval.

## Contract handoff

See `contracts/FOUNDATION_API_DB_CONTRACT.md`, `contracts/FOUNDATION_CANDIDATE_SHARED_DB_HANDOFF.md` and `docs/PHASE3_DATABASE_CHECKLIST.md` for full tested consumption sequence, role/DSN mapping, source hashes, TLS SAN, restored receipt and remaining full HTTP dependencies. `foundation.dba_admission.v1` is a product admission gate and should only be issued for a *real* accepted target after actual evidence, not for the unexecuted scripts in this artifact.
