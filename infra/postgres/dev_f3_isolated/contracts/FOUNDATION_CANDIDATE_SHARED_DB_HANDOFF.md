# DATABASE_F3 → Foundation + API: isolated candidate PostgreSQL consumption

Scope: **separate freshly initialized PostgreSQL 17.11** with Product + Bootstrap *real source DB authority preflight*. This document does not claim full signed ASGI HTTP traffic, BFF, live IdP, C018 or a Mac product startup. It explicitly excludes the accepted Mac demo database and volume.

## 1. Source and version boundary

- PR: https://github.com/Shahbazi-Amir/RAG_finance_app/pull/59 (Draft, not merged).
- Earlier runtime SHA: `57b5d007c86deb7003610605d305bdc942a31312`; CI `45052366022`.
- Earlier PR HEAD `db14943d6e96bc53c416862889ad57cc0b53c3ee` was five **documentation-only** commits ahead; Git compare confirmed no execution/SQL delta.
- **New** shared service witness and restore hardening are *effective changes* beyond that comparison and REQUIRE a NEW successful CI run. Do not claim older CI `45052366022` tests these new files.
- Product/Bootstrap application SOURCE exact immutable commit: `c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a`, never the base branch's absent ASGI files.
- Pinned application Git blobs: Product `apps/api/private_staging_asgi.py` = `6072e7586d922737117dee27d61798df0cb9a6fc`; Bootstrap `apps/api/private_staging_bootstrap_asgi.py` = `3df807f53c865ebb29f8e8f26d0a8819149b46f9`; trust/DB role profile = `5fc1f3f64708ebb5f6756d5cf4d37d3acf9167b3`.
- SQL source refs: 001–008 `d93dcf7cbf9290acd4cd3aa0164ef05689049da4`; 009 `656604356dadea953031fcdb74650a5d42df4e9b`; 010 `1678e87b7984094b74ec995383b8d4383e5f5ae7`. Exact Manifest `MIGRATIONS_001_010_PINNED.tsv`, SHA-256 `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7`.
- Base DB image pinned by digest `public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a`, platform `linux/amd64`, server version `17.11`. The Python 3.13 witness image is **testing only**, not an approved Product/Bootstrap runtime image.

## 2. Installation order on *new* candidate, never the accepted demo

1. Allocate absolute NEW `LAB_ROOT` and a Git checkout `SOURCE_REPO` containing all immutable commits, including the integrated API commit.
2. Set `SOURCE_REPO=/absolute/git/checkout`; `LAB_ROOT=/absolute/new/f3-candidate-lab`.
3. From `infra/postgres/dev_f3_isolated/`, execute:
   ```bash
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
4. `00` verifies all 20 UP/DOWN migration Git blobs + DB55 bridge/verifier before provisioning; `01` builds unique DB volume, private network, TLS CA and certificate; `02` provisions test-only roles and creates ledger; `03` runs 001–010 strict order with durable STARTED/APPLIED records, but refuses unsafe partial retries; `04` applies the *exact* function-only bridge once and runs read-only DB55; `05` runs 9 TLS role logins, denied non-TLS, 72 negative Auth direct SELECT and FORCE RLS; `09` invokes the ORIGINAL Python API DB authority functions in two isolated container processes with separate role-only passfiles on the same private network; `06` makes actual pg_dump/restore to different cluster ID and volume, compares full original migrated ledger and restricted-role/ACL/DB55/RLS state; `10` reconnects the same original Python API verifiers to the restored cluster with SAN-matched `restore-db` and TLS verify-full.
5. Client/witness environments use independent disposable credentials; NO production secrets and NO Gateway. All private files are under `LAB_ROOT/work` and `LAB_ROOT/secrets` with strict permissions. The accepted demo remains `rag_finance_f3_demo` in volume `rag_finance_f3_demo_pg17_20261121`, always excluded.

## 3. Role-to-service DSN mapping

Every role connects using `sslmode=verify-full`, absolute CA path, its OWN password source and `dbname=rag_finance_f3_lab` with `host=demo-db`. The server cert SAN contains **DNS:demo-db** and **DNS:restore-db**; the independent restore cluster lives at `restore-db` and database `rag_finance_f3_lab_restore`.

Product (2 distinct DB roles):
- Private Product API config `history_dsn` → `history_app`; needs 005 consume assertion and 004 admit_session_fenced, no direct private Auth table SELECT or 003 revocation authority.
- Private Product API config `revoke_dsn` → `auth_revoker`; needs 005/004 and 003 revoke_one; no History message table SELECT.
- Code invoked in actual Python process: `apps.api.private_staging_asgi.verify_staging_database_authority`, using `PrivateStagingProfile`; negative wrong-role and weak-TLS configs must be rejected.

Bootstrap (7 distinct DB roles):
- `dsn_replay` → `auth_trust_api`.
- `dsn_bootstrap` → `auth_login_bootstrap`.
- `dsn_claim_reader` → `auth_login_claim_reader`.
- `dsn_issuer` → `auth_login_issuer`.
- `dsn_mapper` → `auth_mapper`.
- `dsn_binder` → `auth_login_binder`.
- `dsn_reader` → `auth_login_reader`.
- Code invoked: `apps.api.private_staging_bootstrap_asgi.verify_bootstrap_roles`, which checks exact function grants plus three direct Auth SELECT denials per role. Wrong-role and weak-TLS configs must be rejected.

All nine service users are NOBYPASSRLS, NOSUPERUSER, NOINHERIT, NOCREATEDB, NOCREATEROLE. Application processes never use `postgres`, `history_migrator` or `auth_migrator`. No passwords should appear in CI logs, PRs, checked-in config or user-facing receipts.

## 4. Verification, restore and limits

- Normal DB55: `db55_verify_staging.sql` Git blob `e2115d8cebc649fdf05d3fbee4ef435ad5f39a47`; read-only `private_no_dispatch`.
- Exact Bridge: `db55_no_dispatch_bridge.sql` blob `a79e46c87857eb2b77fd26863e1cf85fead31b38`; one-time function grants only.
- Restore must have a **different PostgreSQL system_identifier**. The restored `db55_audit.migration_runs` contains the ORIGINAL source cluster's historical IDs, and is compared byte-for-byte at row-content level. This is an expected provenance property, not a sign the restore is the same physical cluster.
- Both primary and restored candidate verify DB55 and nine service roles via REAL application verifier source over PostgreSQL TLS.
- The ephemeral DB client containers are *preflight only*, with no Product/Bootstrap ASGI HTTP listener, no Next signed BFF, no Keycloak/IdP or C018 engine. They **do not** prove end-to-end product login/GET/POST or no second execution on Refresh.
- Actual ASGI services bind only to `127.0.0.1`. Foundation must implement/review same-network-namespace loopback topology with the BFF or an equivalent approved transport; merely putting separate API containers on the same Docker bridge will NOT make their loopback listeners reachable.
- Real Product API startup requires exact C018 runner SHA and offline HF preflight, plus BFF mTLS/RS256; Bootstrap startup requires real pinned IdP and callback. Do not bypass CI startup guards to fabricate an HTTP PASS. These dependencies are Foundation/API/Phase2 owners, not prerequisites to attest database connections.
- `011` is tested separately in its own disposable lab only and excluded from the no-dispatch base. Any 012+ requires a verified new product/API function and design, not numbering speculation.
- The accepted Mac DB55 historical-ledger exception is **not** a historical Migration execution ledger. It is not imported into this new candidate.

## 5. Acceptance criteria for Foundation

A true Foundation consumption receipt must include pinned candidate DB container ID/image and system identifier; Volume; migration 10/10 with ledger and source SHA; bridge SHA; DB55; nine-role TLS, exact Auth negative grants and FORCE RLS; role-specific Product/Bootstrap original code preflight markers; backup SHA-256 and *different* restore cluster ID; restored original ledger and role/DB55 checks; and real user-facing Product/Bootstrap HTTP only once its separate security/engine dependencies are available.

This draft is a DB-only integrated preflight handoff, NOT permission to merge an open Draft PR or start the accepted Mac demo.
