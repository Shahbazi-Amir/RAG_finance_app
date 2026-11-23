# DATABASE_F3 — exact-source consumer pins and script 11 export prerequisites
**Recorded 2026-11-23, bounded evidence only.** This is an executable handoff for a NEW fully disposable authorized DB lab. Not Mac demo admission, not app HTTP acceptance and not permission to start C018/011/Gateway. No existing Mac DB/volume may be modified.

## SHA transition and integrated candidate
| Layer | Evidence |
|---|---|
| Old working DB baseline | 0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5, CI 45109023781 |
| New source exact BASE DB executable | 996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba, CI 45202743968 PASS |
| Two-baseline same isolated runner | CI 45209570132 PASS; four distinct PG cluster identifiers, separate source+restore, DB55 and 001–010 |
| Newer Foundation integrated commit (source content verified) | ce899c26a27fa0e913584384f9dac8980bb77c33: 65/65 compared DB files identical to executable 996dfc9 |
| Deployment/Mac | NOT_ATTESTED / NO SOURCE-BOUND signed Mac HTTP or full-service receipt |
| PR head | Consult Draft PR #59; do not use arbitrary docs HEAD as executable tested SHA |
| Official register | coordination/phase3_checklist.md only Foundation/CENTRAL may update acceptance |
| Stale consumer metadata | integration/F3_SOURCE_PINS.json in ce899c still records DB head db14943... and tested 57b5d007...; must be repinned by Foundation; the physical DB blobs on this integrated source are correct, but this provenance manifest is not |

## Exact migration and executable inputs
| Path | Exact Git blob SHA-1 at source 996dfc9 | Consumer instruction |
|---|---|---|
| scripts/03_apply_pinned_001_010.sh | 9cc9458c55b82f03811b346259ccf2ae3dce318d | CRITICAL executable changed from old a30dbebe5b787db61b4f91c035d255f8160029d1; enforce digest, cluster and physical schema on no-rerun |
| scripts/11_export_sanitized_receipt.sh | 9f0908fef1f93dd66856fde6285ea5a60031aab2 | New required receipts include ALL scripts 12–17; old Foundation runbook exporting after 14 alone will FAIL |
| scripts/15_populated_pre009_upgrade_restore.sh | f3877b0aeb280fa9c577e40d809546c0ace1555c | pre-009 synthetic History/Auth populated backup, restore + 009–010 on both |
| scripts/16_fault_injected_migration_ledger.sh | aa7f51303c906f1b5b9d900759a23bb17b24977e | second disposable cluster, STARTED/duplicate/digest/metadata/forged complete Ledger fail closed |
| scripts/17_populated_query_plan_and_owner.sh | 4fec6eb70fa1240f409658c0dd67e29b50489279 | EXPLAIN ANALYZE on 2400 synthetic conversations/4800 messages with two owners, not production SLO |
| MIGRATIONS_001_010_PINNED.tsv | f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf | SHA256 9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7; all 20 UP/DOWN old/new identical |
| PostgreSQL image | public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a | linux/amd64, PostgreSQL 17.11, internal Docker network, no public PG port |
| DB55 bridge / verifier | a79e46c87857eb2b77fd26863e1cf85fead31b38 / e2115d8cebc649fdf05d3fbee4ef435ad5f39a47 | pin at bfd6b1d9ed23e5f4cc6f126b579f90d7c877a7a6; db55_phase=private_no_dispatch |

Test source imports pinned Product/Bootstrap code at c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a. Nine constrained PG roles: Product 2 (history_app, auth_revoker), Bootstrap 7 (auth_trust_api, auth_login_bootstrap, auth_login_claim_reader, auth_login_issuer, auth_mapper, auth_login_binder, auth_login_reader). In lab all check verify-full; role/function matrix is in FOUNDATION_API_DB_CONTRACT.md. This proves DB verifier code, NOT HTTP listeners.

## Strict order and prerequisites of script 11

On isolated GH Actions runner or newly authorized **separate** disposable DB lab, run as an operator with Docker/Compose, Bash, Git full history, openssl, shasum, Python 3 and writable out directory. Never run on existing accepted Mac demo or its volume. LAB_ROOT must be NEW absolute path, with no existing lab.env. SOURCE_REPO must be full checkout containing pinned SQL refs d93dcf..., 656604..., 1678e..., bfd6b1... and API source c5e271d...

~~~bash
export SOURCE_REPO=/absolute/full/RAG_finance_app_checkout
export LAB_ROOT=/absolute/new/disposable-db-work
cd "$SOURCE_REPO/infra/postgres/dev_f3_isolated"

bash scripts/00_prepare_source.sh
bash scripts/01_create_isolated_lab.sh
bash scripts/02_provision_roles.sh
bash scripts/03_apply_pinned_001_010.sh
bash scripts/03_apply_pinned_001_010.sh      # expects ALREADY_APPLIED_EXACT_PINS_NO_RERUN
bash scripts/04_bridge_and_db55.sh
bash scripts/05_test_roles_tls_rls.sh
bash scripts/09_shared_stack_db_preflight.sh # actual Product+Bootstrap DB verifier source
bash scripts/06_backup_restore_independent.sh
bash scripts/10_restored_stack_db_preflight.sh
bash scripts/13_catalog_erd_inventory.sh
bash scripts/12_rollback_rls_constraints_probe.sh
bash scripts/14_synthetic_owner_lifecycle_restore.sh
bash scripts/15_populated_pre009_upgrade_restore.sh
bash scripts/16_fault_injected_migration_ledger.sh
bash scripts/17_populated_query_plan_and_owner.sh
bash scripts/19_history_rls_negative_matrix.sh
bash scripts/20_backup_integrity_corruption_probe.sh
bash scripts/21_history_cursor_race_probe.sh
# The exporter below uses a metadata directory, NOT an installation command.
# For CI, GITHUB_WORKSPACE and GITHUB_SHA are supplied automatically; for local,
# use an isolated writable export root and explicitly label evidence as local.
export GITHUB_WORKSPACE="$LAB_ROOT/export"
mkdir -p "$GITHUB_WORKSPACE"
# Do NOT claim CI run identity on a manual host execution.
bash scripts/11_export_sanitized_receipt.sh
~~~

**11 will refuse to run unless ALL these output inputs exist and validate**:
1. After 06: work/restore_receipt.txt, work/backup.dump.sha256, work/source_cluster_id.txt, restore-tested.marker, source+restore genuinely different system IDs, original 10 APPLIED ledger rows and DB55 PASS.
2. After 09+10: four role code witness logs (product-db-witness.log, bootstrap-db-witness.log and restored-*), 2+7 distinct roles with verify-full, accurate DB names, runner_calls=0, gateway_calls=0 and ASGI listeners explicitly not started.
3. After 13: physical_erd_data_dictionary.jsonl (14 actual source tables), query_plan_empty_fixture.txt, catalog_snapshot_sha256.txt (SHA256 checks).
4. After 14: synthetic_owner_restore_receipt.json (two owners/two History messages, deletion_requested preserved, only soft deletion and sample time).
5. After 16: ledger_fault_injection_receipt.json (second-cluster STARTED, duplicate, bad digest, null metadata and forged-full rejection, owned resources deleted).
6. After 17: populated_plan_receipt.json, query_plan_populated_conversations.json, query_plan_populated_messages.json, with 2400/4800 synthetic fixture, 1200 A-owned rows and explicitly NOT approved production workload.
7. After 15: complete populated pre009 upgrade evidence appears in **CI log**; exporter currently does not include a separate 15 JSON artifact.
8. After 19: `history_rls_adversarial_receipt.json` proves two-owner six History table SELECT RLS, authorized title mutation and 7/7 negative forged owner/FK/immutable UPDATE/DELETE/unique cases. **It also demonstrates that a raw `history_app` SQL client can set the custom owner GUC and therefore cannot prove signed identity.** The real BFF/IdP/epoch fence remains OPEN.
9. After 20: `backup_integrity_fault_receipt.json` proves one-byte flipped and truncated copies of an already checksummed lab dump are denied by SHA256 *before* restore, while original backup and independent source/restore cluster IDs stay intact. **No corrupt restoration is attempted**; real storage faults, encrypted off-host backups, PITR, RPO/RTO and tombstone no-reappearance remain OPEN. To audit 15, retain GitHub Actions exact-SHA log and test script pin, not a fabricated JSON receipt. This distinction is deliberate.

10. After 21: `history_cursor_race_receipt.json` reproduces exact repository Git blob `14f97dd680425b74f8e12fa1696d423a20bf7d76` History keyset SQL predicates on a **separate real PG17 clone** with two artificial owners, both ASC/DESC cursor sequences, a new record inserted beyond anchor and cross-user RLS denial. Cursor HMAC, actual HTTP, full transaction session fence and realistic-load SLO stay NOT_RUN.

**11 exports the historical nine sanitized files PLUS three separately gated negative/race SQL receipt JSON files (twelve total)** in ci_receipts; it must not embed secrets, private keys, DSNs, raw SQL row contents or pg_dump. It sets source_commit_tested to GITHUB_SHA, which in CI is the runner commit, and uses NO_CI_SHA if absent; NEVER relabel local evidence as exact CI attestation. The 18 two-baseline comparator is **separate** and exports three sanitized JSONs after two fresh+restore runs on the SAME disposable Runner; its results are in CI 45209570132, not produced by script 11.

## Latest newly tested CI evidence (2026-11-23)

- **CURRENT latest tested executable** SHA `76822ac273c3f5defbb7e5cd77d497f8d3305852`, [CI 45218702399 SUCCESS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45218702399), [sanitized artifact 14839553522](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45218702399/artifacts/14839553522). Added script 21 `infra/postgres/dev_f3_isolated/scripts/21_history_cursor_race_probe.sh` verifying asc/desc keyset anchor across concurrent new records; 12 sanitized receipts total. Prior tested 6d remains historical and new integrated sources do not automatically include 21.


- Latest executed source SHA `6d2339bc45ce52b4f60a50ced0bb04b588ba3748`, [CI 45216830775 SUCCESS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45216830775), sanitized [artifact 14839885728](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45216830775/artifacts/14839885728).
- New script 19 Git Blob `5d26843eaa129c923c4275e558c60627c15018c9`; script 20 `d7e5e1cb4bb0b04cf86e87e3eb8a232da78fc391`; enhanced exporter 11 `f3542ec51b7a5c7bea84bccb42e7eb894f804a55`; corresponding workflow version is source-bound to CI SHA above. These are **new executable changes** beyond 996dfc9, although 001–010 SQL, installer 03, PG image and DB55 remain the same. Foundation must not assume integrated commit c488837... contains scripts 19/20: observed those files absent and old 11 still present.
- Active code implementation remains DB-only adverse/backup checks, not a Mac acceptance or authorized 012+ policy change.

## Current CI exact comparison results
In [CI 45209570132](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209570132), the baseline 0e301a source and restore identifiers are 7711394723850833980 / 7711394851945500732; the 996dfc9 identifiers are 7711394933269237819 / 7711395017988198459. All four differ; both baselines installed 10, DB55 PASS, 2+7 role preflight and independent restore PASS; no Mac or real C018. Both install paths used THEIR OWN historical installer blob; no substitution of the hardened installer into the old baseline.

## Admission and requested Ops/Owner information
- Foundation must repin integrated SOURCE_PINS content for DB to 996dfc9 and 03 blob; record the separate integrated source commit and verify exact matching DB subtree. No silent assumption that an integration marker means the full Mac product was deployed.
- Ops must supply a separate sanctioned Mac candidate receipt binding container image digest, DB/Volume IDs, PG system ID, 001–010 full ledger, DB55 actual result, CA/SAN, role CURRENT_USER from real Product/Bootstrap processes, independent backup+restore and signed A/B HTTP 404/401 evidence.
- API+Security/Owner must authorize real consent/withdraw, feedback on a valid Answer, immutable owner mapping/session same-TX fence, deletion/tombstone anti-resurrection, retention/export and real source+version lineage **before** 012+.
- Engine/Ops must supply Qdrant no-write snapshot/release and actual C018 source/OS spawned-once evidence only under separate NO_DISPATCH_ONLY permit. 011 and Gateway are excluded.
- RPO/RTO, PITR, encryption/key custody, backup retention and real outage workload require numeric signed choices, not a 2-row synthetic restore measurement.

FINAL: CI-only technical evidence PASS; signed Mac HTTP/IdP, C018 and production-scale deletion/DR NOT_RUN; all 26 module Gates remain under Foundation/CENTRAL authority.

---
## Revision after exact successful CI 45226799736 — use over older prereq lists

**EXECUTABLE tested** 24b4def0efd16f33d3a8391a479978c0846490aa. CI [45226799736](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45226799736) SUCCESS; artifact [14842991989](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45226799736/artifacts/14842991989) stores **13 sanitized files**, not historical 9/12. The following is **inside private disposable DB test only**, no Mac accepted DB/volume touched and no 011 run.

- Exact new script: scripts/22_restore_catalog_parity_probe.sh, Git blob 5869b15413d058acb2424199d8fcaa9d274f822c.
- Revised exporter: scripts/11_export_sanitized_receipt.sh, Git blob 5872c2554c7704bda0eab97c6230b9a77c1c28eb, requires restore_catalog_parity_receipt.json and rejects absent/invalid content.
- Revised workflow: .github/workflows/f3-db-isolated-fresh-install.yml, Git blob ca1dbca48727f2b5786e90663e98289106773215.
- Unchanged 03: 9cc9458c55b82f03811b346259ccf2ae3dce318d; SQL manifest blob f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf, SHA256 9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7.
- Unchanged 19/20/21 Git blobs: 5d26843eaa129c923c4275e558c60627c15018c9 / d7e5e1cb4bb0b04cf86e87e3eb8a232da78fc391 / 8732a4788cb3ecf821c15d811119f8cacc3eedd1.

**Execution order (supersedes older list):** 00 → 01 → 02 → 03 → 03 exact no-replay → 04 → 05 → 09 → 06 → 10 → **22** → 13 → 12 → 14 → 15 → 16 → 17 → 19 → 20 → 21 → **11 last**. Step 22 needs source/restore complete, 10 APPLIED ledger rows in each, different PG system IDs, and empty-but-existing restore-tested.marker. It checks the physical catalog against a PostgreSQL semantic owner-default ACL (not raw relacl representation), performs NO FORCE RLS and DISABLE RLS negative mutations in a new restore-clone database, then removes the clone. A mismatch fails the workflow; sanitized artifact exports ONLY the SHA256 and bounded statuses; no private catalog/pg_dump is attached.

**Repin required:** Foundation snapshot f7d738aa763179eba28c7847e6225640bb88b176 has installer 03 and 20-file manifest identical, but 11 old blob 9f0908fef1f93dd66856fde6285ea5a60031aab2, scripts 19–22 absent and workflow older. Foundation owns integration/F3_SOURCE_PINS.json and must consume tested source commit and blob matrix on an explicit integrated candidate; verify fresh independent CI plus authorized Mac role/IdP L2 separately. 011 remains an OPTIONAL independent branch/test; do not run on base, no Gateway. This new DB CI does not grant module Gate, external deployment, RPO/RTO SLA or anti-resurrection.


---
## M04-A07 new tested version and 14th required receipt (latest, supersedes older 11-export counts)

Exact executable `48110525aa9ac118b6b3749c956930c61cec11fe`, [CI 45233599373 SUCCESS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45233599373), artifact [14848595915](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45233599373/artifacts/14848595915) with **14 sanitized files**.

| Consumer path | Git blob SHA | Execution requirement |
|---|---|---|
| `scripts/23_m04_migration_full_cycle.sh` | `a547a58ac1555795dd73c18415973bbc955177d8` | After script 15, before 16. Actual empty disposable clone 010..001 DOWN and 001..010 UP; schema-only SHA equality; NEW probe Ledger; replay exact post-migration DB55 bridge; drop clone |
| `scripts/11_export_sanitized_receipt.sh` | `b9dff8a9f736d36af3916900995afb798826b3e5` | Adds required `m04_migration_full_cycle_receipt.json` schema + consistency guard (14th file) |
| `.github/workflows/f3-db-isolated-fresh-install.yml` | `dadd5ec47d8f312b7de35533241c275961195821` | Run script 23 after 15 with protected standard PG17.11 runner, 011 remains SKIPPED |
| `scripts/03_apply_pinned_001_010.sh` | `9cc9458c55b82f03811b346259ccf2ae3dce318d` | Unchanged hardened installer |
| `MIGRATIONS_001_010_PINNED.tsv` | `f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf` | Unchanged 20 original UP/DOWN SQL blobs, SHA256 `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7` |

Order now: `00→01→02→03→03→04→05→09→06→10→22→13→12→14→15→23→16→17→19→20→21→11` (workflow actual order). Use original role/DB55/manifest pins. `CREATE DATABASE ... TEMPLATE` does not copy *database-level privileges*, hence script 23 recreates scoped lab grants on probe only. Docker Compose stdin can consume process substitution, hence manifest loops use FD3. A full-cycle reset loses POST-migration DB55 bridge function grants, hence exact bridge replay with new experimental ledger in probe is required. These code-fixes are part of validated source SHA, not speculative future policy.

No Mac/approved data-bearing full rollback, no live Gateway/011/Arvan, no 012+, no signed RPO/RTO, no app API/IdP/C018: **NOT_RUN / NOT_ACCEPTED**. Foundation must repin the exact executable and all new blobs, rerun on independent integrated candidate before Gate.
