# Gate 3 / Phase 3 — SOURCE-MAPPED STATUS (2026-11-22)

This document maps the **provided** `Gate3_Docker_Execution_Checklist_Foundation_2026-11-20(4).md` and the actual pinned `RAG_finance_app` sources; it does **not** claim a more recent checklist exists. `DONE` = observed/accepted evidence at its stated boundary; `OPEN` = implementation/evidence needed; `BLOCKED` = cannot complete without missing connection/contract/host.

## Full G3 dependencies (all owners, source evidence)

| ID | Status | Owner | Evidence / outstanding work |
|---|---|---|---|
| G3-00 | DONE | Ops | Reported Mac daemon 28.0.4 / Arvan 29.1.3, note: not re-observed in this turn |
| G3-01 | DONE | Ops/Engine | Runner/C011/Chunks pins and historical C007 artifact PASS as reported in attached checklist; logical Qdrant not yet validated |
| G3-02 | BLOCKED | Phase2/Ops | `NO_WRITE_WINDOW_ATTESTED` missing; cannot copy active Qdrant |
| G3-03 | BLOCKED | Phase2/Ops | No consistent index snapshot attested yet |
| G3-04 | BLOCKED | Phase2/Ops | Qdrant logical hash and embedded client 1.18.0 runtime not proved |
| G3-05 | OPEN | CENTRAL | `NO_DISPATCH_ONLY` smoke target is agreed historically; formal one-question target/pass rules still need final reference |
| G3-06 | OPEN | Foundation | Product code branch/worktree and pin-compatible Docker package beyond DB scope |
| G3-07 | OPEN | Foundation | Product-wide docker-compose Web/API/runner absent at source 5fe21e9; this package is only a standalone DB lab |
| G3-08 | BLOCKED | Foundation/API | Shared network namespace or approved API loopback design |
| G3-09 | BLOCKED | Foundation/UI/API | Real BFF/Keycloak/OIDC/PKI and browser signed mTLS proof |
| G3-10 | DONE | Database/Ops | **Accepted Mac demo DB as stipulated by owner**, prior local PG17.11 001–010/TLS/RLS/restore Ops evidence; not touched in this task. Fresh 001–010 DB development tests PASS on isolated GitHub Actions; accepted demo unchanged |
| G3-11 | OPEN | Foundation | Linux-native complete product runtime/image pins; lab PG17.11 digest is only one component |
| G3-12 | OPEN | CENTRAL/Ops | Isolated DB experimental SQL is authorized in this request; whole product image/build/Runner authorization is separate |
| G3-13 | BLOCKED | Foundation/Ops | Docker Mac build, UID/volumes/per-service health actual output not accessible here |
| G3-14 | BLOCKED | Foundation/UI/API/DB | Signed UI→BFF→API→C018 no-generation test not performed by this DB package |
| G3-15 | BLOCKED | Foundation/Ops | Product-complete export/restore/recovery package not delivered |
| G3-16 | BLOCKED | CENTRAL/Ops | Arvan transfer explicitly out of current scope |

## Database_F3 delivery checklist

| ID | Status | Evidence / target |
|---|---|---|
| DB-F3-01 source inventory | DONE | Up-to-date source tree inspected at `RAG_finance_app@5fe21e922...`; DB55 source verified at `bfd6b1d9...`; #44/#47/#56 draft SQL refs |
| DB-F3-02 original immutable 001–010 pins | DONE | Corrected 20-row TSV SHA256 `9ff95a...`; 007 DOWN exact 40-hex git blob; GitHub independent read earlier 20/20 |
| DB-F3-03 001–010 offline materializer | DONE | `scripts/00_prepare_source.sh`; checks each `git hash-object` before copying 20 SQL + 2 DB55; STATIC only |
| DB-F3-04 isolated test Compose | DONE | `compose.lab.yaml`; fixed PG17.11 ECR digest, `linux/amd64`, two new unique volumes, no host ports; STATIC only |
| DB-F3-05 TLS setup + 20 SQL roles | DONE | `01_create_isolated_lab.sh` / `02_provision_roles.sh`; ephemeral CA/SAN, deny nonTLS, strict role flags; STATIC only |
| DB-F3-06 durably journalled 001–010 | DONE | `03_apply_pinned_001_010.sh`: pre-commit STARTED row, exact hashes and transaction ID, partial state STOP; STATIC only |
| DB-F3-07 scoped Bridge and DB55 | DONE | `04_bridge_and_db55.sh`: exact source pins, separate limited auditor, read-only verification; STATIC only |
| DB-F3-08 role/RLS/TLS negative test program | DONE | `05_test_roles_tls_rls.sh`: 9/9 TLS, nonTLS reject, 72/72 Auth SELECT denials, 9/9 API function signatures, RLS; STATIC only |
| DB-F3-09 independent backup/restore program | DONE | `06_backup_restore_independent.sh`: pg_dump -Fc / SHA256 / second cluster+volume / restored DB55; STATIC only |
| DB-F3-10 **real test lab fresh install** | DONE | Separate real Docker PG17.11 CI on SHA `57b5d007c86deb7003610605d305bdc942a31312`, Run `45052366022`: 10/10 pinned migrations, DB55, 9/9 TLS, 72/72 SELECT denies, backup/restore PASS. Not Mac. |
| DB-F3-11 source branch / CI validation | DONE | Branch `agent/database-f3-fresh-install-isolated-20261122`, CI `45052366022` both jobs PASS on source SHA `57b5d007c86deb7003610605d305bdc942a31312`; Mac Docker runtime remains Foundation/Ops scope |
| DB-F3-12 post-010 migrations | DONE | Optional 011 source SHA `b0ba6dbf6100109cb58f8cb49da808839d68c5f0` tested separately after all 001–010 in Run `45052366022` (`DB55/live_011`, ACL/RLS, denied bogus Claim). Also standalone 011 13/13 CI `43710425019` PASS. Product dispatch deployment remains BLOCKED, 012+ not specified. |
| DB-F3-13 Foundation/API integration | OPEN | Complete DB role/DSN/ACL contract prepared; real PRODUCT/BOOTSTRAP private network + CA + deploy pin validation pending |
| DB-F3-14 accepted Mac demo invariant | DONE | No Docker, SSH, SQL, migration, backup, restore or transfer was executed against accepted Mac demo in this task |

## Runtime evidence boundary

`CI_PASS` Run `45052366022` attests actual isolated disposable PostgreSQL 17.11 Docker execution on source commit `57b5d007c86deb7003610605d305bdc942a31312`, NOT Mac host/production, Product API, paid Gateway, Arvan or accepted demo. A separate CI job validates optional 011 on a second fresh 001–010 lab; no changes to base no-dispatch SQL. Earlier failed development runs were corrected before PASS. Do not rerun partial migrations or reuse accepted demo.

## Dependency / acceptance order

1. Exact local Git refs + source hashes. 2. Separate Docker lab project/new volumes. 3. Ephemeral TLS/role provisioning and admin intent ledger. 4. Fresh 001..010 SQL. 5. Scoped bridge + DB55. 6. Real 9-role verify-full/72 negatives and RLS. 7. Separate PG17.11 restore/DB55. 8. Foundation/API consume versions/ACL and exact runtime receipt. 9. Any 011/paid/live feature remains a separate branch and gate.
