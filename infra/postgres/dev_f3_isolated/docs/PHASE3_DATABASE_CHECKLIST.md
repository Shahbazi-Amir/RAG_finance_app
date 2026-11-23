# Gate 3 / Phase 3 — SOURCE-MAPPED STATUS (2026-11-23)

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
| DB-F3-03 001–010 offline materializer | DONE | `scripts/00_prepare_source.sh`; checks each `git hash-object` before copying 20 SQL + 2 DB55; CI runtime PASS in isolated lab, not Mac |
| DB-F3-04 isolated test Compose | DONE | `compose.lab.yaml`; fixed PG17.11 ECR digest, `linux/amd64`, two new unique volumes, no host ports; CI runtime PASS in isolated lab, not Mac |
| DB-F3-05 TLS setup + 20 SQL roles | DONE | `01_create_isolated_lab.sh` / `02_provision_roles.sh`; ephemeral CA/SAN, deny nonTLS, strict role flags; CI runtime PASS in isolated lab, not Mac |
| DB-F3-06 durably journalled 001–010 | DONE | `03_apply_pinned_001_010.sh`: pre-commit STARTED row, exact hashes and transaction ID, partial state STOP; CI runtime PASS in isolated lab, not Mac |
| DB-F3-07 scoped Bridge and DB55 | DONE | `04_bridge_and_db55.sh`: exact source pins, separate limited auditor, read-only verification; CI runtime PASS in isolated lab, not Mac |
| DB-F3-08 role/RLS/TLS negative test program | DONE | `05_test_roles_tls_rls.sh`: 9/9 TLS, nonTLS reject, 72/72 Auth SELECT denials, 9/9 API function signatures, RLS; CI runtime PASS in isolated lab, not Mac |
| DB-F3-09 independent backup/restore program | DONE | `06_backup_restore_independent.sh`: pg_dump -Fc / SHA256 / second cluster+volume / restored DB55; CI runtime PASS in isolated lab, not Mac |
| DB-F3-10 **real test lab fresh install** | DONE | Historical CI `45052366022` on `57b5d007...` PASS. Updated integrated candidate CI `45082326382` on `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74` PASS: 10/10, DB55, 9/9 TLS, 72/72 ACL denials, backup+separate restore. Not Mac. |
| DB-F3-11 source branch / CI validation | DONE | Draft PR #59, integrated DB+client CI `45082326382` both jobs PASS at source SHA `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74`, structured sanitized CI Artifact `f3-db-foundation-candidate-consumption`. Mac product Compose remains Foundation/Ops scope. |
| DB-F3-12 post-010 migrations | DONE | Optional 011 source SHA `b0ba6dbf6100109cb58f8cb49da808839d68c5f0` tested separately after all 001–010 in Run `45052366022` (`DB55/live_011`, ACL/RLS, denied bogus Claim). Also standalone 011 13/13 CI `43710425019` PASS. Product dispatch deployment remains BLOCKED, 012+ not specified. |
| DB-F3-13 Foundation/API database integration | DONE | Original pinned Product `verify_staging_database_authority` and Bootstrap `verify_bootstrap_roles` executed in two separate client containers on candidate's internal network, verified TLS `verify-full` 2+7; restored to second cluster and repeated actual same code with TLS 2+7, CI `45082326382`. Scope DB authority preflight ONLY, not signed ASGI HTTP. |
| DB-F3-15 full Product/Bootstrap HTTP/IdP/C018 stack | BLOCKED | Original apps bind `127.0.0.1`, need reviewed shared namespace/sidecar and real BFF/IdP/C018 prerequisites; DB-only CI intentionally did not start ASGI listeners. Owner Foundation/API, not DB migration. |
| DB-F3-14 accepted Mac demo invariant | DONE | No Docker, SSH, SQL, migration, backup, restore or transfer was executed against accepted Mac demo in this task |

## Runtime evidence boundary

`CI_PASS` Run `45082326382` attests actual disposable PostgreSQL 17.11 with pinned SQL, two **real application DB authority routines** in separate container processes, real TLS `verify-full`, independent restored cluster with matched ledger/role ACL and both service DB preflight routines. Tested source SHA `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74`, application source SHA `c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a`. No BFF/IdP/C018 HTTP startup; no accepted Mac demo or Arvan access; optional 011 separate on second lab. CI Artifact ID `14777896097` contains sanitized receipt; do not rerun partial migrations or reuse accepted demo.

## Dependency / acceptance order

1. Exact local Git refs + source hashes. 2. Separate Docker lab project/new volumes. 3. Ephemeral TLS/role provisioning and admin intent ledger. 4. Fresh 001..010 SQL. 5. Scoped bridge + DB55. 6. Real 9-role verify-full/72 negatives and RLS. 7. Separate PG17.11 restore/DB55. 8. Foundation/API actual shared-network DB-only preflight of original 2+7 role verification functions. 9. Independent restored 2+7 role DB preflight plus sanitized receipt. 10. Full signed HTTP BFF/API/Bootstrap and any paid 011 remain Foundation/API separate gates.
