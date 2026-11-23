# DATABASE_F3 → FOUNDATION_F3 / API_F3 — contract for review

> **LATEST owner-contract CI provenance (2026-11-23):** This contract's 2 Product + 7 Bootstrap roles/function grants remain the same. Executable DB SHA 996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba, CI 45202743968 success, two-baseline same-runner comparison CI 45209570132 success; 14 FORCE RLS, 17 FK, 38 indexes, 72 denied private SELECT. Hardened 03 installer Git blob 9cc9458c55b82f03811b346259ccf2ae3dce318d; historical b6 evidence below is retained, not current. Actual integrated DB files at ce899c26a27fa0e913584384f9dac8980bb77c33 match exactly; integrated source metadata may still claim older DB pin. The proposed conceptual Consent/Feedback/deletion design is NOT an approved runtime schema; see docs/PHASE3_PHYSICAL_ERD_AND_FUTURE_POLICY_CONTRACT_v2_20261123.md. Mac BFF/IdP/C018 real HTTP remains NOT_RUN.


## Scope and version

- Development package: `f3.db.lab.fresh-install.v1` + real shared API/Bootstrap DB authority preflight `foundation.f3_db_candidate_shared.v1`, tested GitHub Actions Run `45082326382`, source SHA `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74`. The existing Mac demo was not tested or modified.
- Accepted Mac demo `rag_finance_f3_demo` / `rag_finance_f3_demo_pg17_20261121` is never modified.
- Tested historical source manifest: `MIGRATIONS_001_010_PINNED.tsv` SHA256 `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7`.
- Lab runtime pinned PG image: `public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a` `linux/amd64`, PostgreSQL 17.11 (verify on host).
- Exact application integration source **actually loaded in two isolated client containers**: commit `c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a`; pinned Product file blob `6072e7586d922737117dee27d61798df0cb9a6fc`, Bootstrap blob `3df807f53c865ebb29f8e8f26d0a8819149b46f9`, staging DB-profile blob `5fc1f3f64708ebb5f6756d5cf4d37d3acf9167b3`. This is actual DB verifier source but **not** launched HTTP service; do not treat it as deployed SHA.

## Product API credentials (distinct from Bootstrap)

| API private config | PostgreSQL role | Required functions / limits |
|---|---|---|
| `history_dsn` | `history_app` | `auth_l1.consume_service_assertion(text,bigint)`; `auth_l1.admit_session_fenced(text,text,bigint,integer)`; History functions scoped per migration 001/002; no direct auth_l1.sessions SELECT; no revoke_one |
| `revoke_dsn` | `auth_revoker` | Same 005/004 auth bridge and `auth_l1.revoke_one(text,bigint)`; no history_l1.messages SELECT |

## Bootstrap API credentials (seven, separate OS identity)

| Config DSN key | PostgreSQL role | Required function signatures |
|---|---|---|
| `dsn_replay` | `auth_trust_api` | `auth_l1.consume_service_assertion(text,bigint)` |
| `dsn_bootstrap` | `auth_login_bootstrap` | `auth_l1.start_initial_login_attempt(uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer)`; `auth_l1.mark_initial_login_unknown(uuid,text,text)` |
| `dsn_claim_reader` | `auth_login_claim_reader` | `auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)` |
| `dsn_issuer` | `auth_login_issuer` | `auth_l1.issue_initial_login_pending(uuid,text,text,text,text,text,bigint,text,integer,integer)` |
| `dsn_mapper` | `auth_mapper` | `auth_l1.map_identity(text,text)` |
| `dsn_binder` | `auth_login_binder` | `auth_l1.ack_initial_login_binding(uuid,uuid,text,text,text,bigint,text)`; `auth_l1.abort_initial_login_binding(uuid,uuid,text,text,text,bigint)` |
| `dsn_reader` | `auth_login_reader` | `auth_l1.status_initial_login_attempt(uuid,text,text)` |

All nine roles: `NOSUPERUSER`, `NOBYPASSRLS`, `NOINHERIT`, `NOCREATEDB`, `NOCREATEROLE`. Never grant direct `SELECT` on private auth tables or attach 2 Product roles to Bootstrap OS identity or vice versa. Additional internal SQL roles from 003–010 exist but are **not** shared with API processes.

## TLS / DSN constraints

- Lab primary `demo-db` and independent restore `restore-db` on Docker **internal-only** network. TLS lab server cert `subjectAltName=DNS:demo-db,DNS:restore-db` signed by ephemeral lab CA. Both names were exercised by `verify-full` for all 9 roles from actual imported API/Bootstrap code.
- In real Product/Bootstrap environment, configure a private TLS server certificate with SAN covering the actual host, trusted CA and DSNs with `sslmode=verify-full` and an absolute `sslrootcert`; `sslmode=require`, `prefer`, `allow`, or `disable` do **not** satisfy this handoff.
- Each DSN must name the exact DB, exact PG role, and TLS endpoint. No password in source, logs or checked-in `.env`.
- Lab DB-client DSN shape: `host=demo-db dbname=rag_finance_f3_lab user=<one-of-nine> sslmode=verify-full sslrootcert=/run/role_secrets/ca.crt passfile=/run/role_secrets/pgpass`. Separate *role-only* files are supplied for 2 Product and 7 Bootstrap users in separate disposable client containers. After independent restore they use `host=restore-db dbname=rag_finance_f3_lab_restore` with matching certificate SAN; production must supply its own protected credentials and CA mounts.
- `POSTGRES_PASSWORD_FILE` is only for fresh lab DB superuser initialization; never expose its credential to Product or Bootstrap.

## Bridge / RLS / auditor

- Exact Bridge file `infra/postgres/staging/db55_no_dispatch_bridge.sql` from `bfd6b1d9...`, Git blob `a79e46c87857eb2b77fd26863e1cf85fead31b38`; preexisting grant matrix must be checked before its one-time use.
- Exact verifier `db55_verify_staging.sql` same source, blob `e2115d8cebc649fdf05d3fbee4ef435ad5f39a47`; invocation `-v db55_phase=private_no_dispatch`, `ON_ERROR_STOP=1`, read-only repeatable-read transaction.
- Independent `db55_lab_auditor` receives schema USAGE only; it must have zero direct private table SELECT and zero function EXECUTE. Restore clone verifies again. In CI `45082326382`, a complete ten-row migrated Ledger matches exactly after restore; the restored DB is a *different* cluster ID; the 9 role flag matrix and 72 SELECT negatives PASS on the restore. Both app verifiers reconnect to the restore with TLS.
- RLS/denials must be asserted against actual tables, not substituted with a DB55 pass marker alone.
- No `011` or external dispatch in this package.

## Evidence prerequisites for Foundation admission

`foundation.dba_admission.v1` must bind: exact accepted target DB and volume, PG version, immutable source pins, 10 ordered APPLIED records with timestamps/txids/cluster ID and SHA-256, actual DB55 output + actual TLS/negative SELECT/RLS receipts, independent restore system ID + SHA256 backup, and tested API role DSNs. Lab results alone are **not** permission to start the accepted demo product stack.

## Open integration requirements

- **DONE (DB authority only):** Actual pinned Product/Bootstrap verifier functions independently connect with all nine restricted roles over `verify-full` from two Docker client processes on the DB's internal network, and repeat on the restored cluster; `CI=45082326382`, Artifact `f3-db-foundation-candidate-consumption`. **OPEN (product HTTP):** Original ASGI servers bind `127.0.0.1`; Foundation must provide approved same-network-namespace BFF API topology and real BFF/IdP/C018 before full HTTP tests. Do not weaken TLS or publish PG publicly.
- Exact release SHA and confidential credential provisioning are owned by Foundation/Ops. Mac demo remains a protected baseline.
- Dedicated external dispatch 011 and its reporter/reconciler roles require a *different* acceptance contract. No live Gateway and no 011 on this path.
