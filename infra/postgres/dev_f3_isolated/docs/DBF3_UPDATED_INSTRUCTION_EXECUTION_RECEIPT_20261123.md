# DATABASE_F3 — Updated instruction: exact-source execution receipt
**Date:** 2026-11-23 | **Owner:** DATABASE_F3, Draft PR #59. CI proves a limited disposable test environment only, NOT Mac product acceptance.

## Precise source chronology

| Type | SHA / observation |
|---|---|
| Historical Foundation pin | b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 |
| Older tested DATABASE_F3 source | 0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5 — [CI 45109023781](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781) |
| Latest tested DATABASE_F3 base executable | 996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba — [CI 45202743968 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968) |
| Tested two-baseline comparator executable | b3ce51f88c80a3d0cc713d8de088f7db485e5bbd — [CI 45209570132 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209570132) |
| PR HEAD prior to this report | 5e8a3a7ff5f761e06014a8e8adb446d41e0f0c41 (eight docs-only commits past comparator, verified Git compare); final HEAD read GitHub PR #59 |
| Integrated source | ce899c26a27fa0e913584384f9dac8980bb77c33, branch integration/f3-ui65-db996-phase3-20261123, 65/65 DB blobs identical to tested 996dfc9 |
| Actually deployed / Mac exact SHA | NOT_ATTESTED; no signed Mac HTTP/IdP or actual installed-source receipt |

**FOUNDATION provenance defect:** integrated source file integration/F3_SOURCE_PINS.json is stale and still lists DB tested 57b5d007c86deb7003610605d305bdc942a31312 and head db14943d6e96bc53c416862889ad57cc0b53c3ee. Physical integration uses current matching executable 996dfc9; Foundation must update its own source pin records. Product/Bootstrap Python verifier blobs imported by CI from c5e271 also match the integrated source byte-for-byte (Product 6072e7586d922737117dee27d61798df0cb9a6fc; Bootstrap 3df807f53c865ebb29f8e8f26d0a8819149b46f9). This is source parity, NOT actual Mac process or HTTP startup.

## Executable Git blob repin and order

| Component | Git Blob SHA1 |
|---|---|
| 03 installer CURRENT | 9cc9458c55b82f03811b346259ccf2ae3dce318d |
| 03 installer OLD | a30dbebe5b787db61b4f91c035d255f8160029d1 |
| Main DB CI workflow | 288ab2f05dd6f1bfd972598972d6c56a7af62fb1 |
| 11 sanitized exporter | 9f0908fef1f93dd66856fde6285ea5a60031aab2 |
| 15 populated pre009 upgrade | f3877b0aeb280fa9c577e40d809546c0ace1555c |
| 16 fake/partial migration Ledger negative | aa7f51303c906f1b5b9d900759a23bb17b24977e |
| 17 populated two-owner EXPLAIN | 4fec6eb70fa1240f409658c0dd67e29b50489279 |
| 18 two exact baseline comparator | e1e3aaf334c465e7168d23706ad4b090ad7dcf92 |
| Two-baseline workflow | b4c863f21832fe4e2df528c7a99992fd987ee70d |
| 20 SQL manifest | Git blob f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf; SHA256 9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7 |

PostgreSQL 17.11 platform linux/amd64, image public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a. SQL 001–010, image digest, 20 Git source blobs and 2 Product/7 Bootstrap role mapping did NOT change. Installer 03 DID change: no-rerun must match SQL SHA256/source/cluster/time/TX and actual 14-table FORCE RLS state, while STARTED and ambiguous migration never auto replay.

**Script 11 now requires more than the historical pre-14 runbook.** Mandatory order on a NEW isolated runner: 00, 01, 02, 03, 03 no-rerun, 04, 05, 09, 06, 10, 13, 12, 14, 15, 16, 17, then 11. The 11 exporter requires 4 original Product/Bootstrap source and restore process DB-preflight witnesses, original ten-entry Ledger, distinct cluster restore receipt, backup checksum, catalog inventory+SHA, synthetic 2-owner restore, fake-Ledger negative and two populated EXPLAIN JSON reports. Log of script 15 is an exact CI witness but has no separate JSON output in 11. Full executable commands and inputs: contracts/DBF3_EXACT_PINS_SCRIPT11_PREREQUISITES_20261123.md. A candidate preflight through step 10 is narrower valid DB evidence; it is NOT equivalent to the full sanitized 11 artifact.

## Actual source-verified comparison evidence

[GitHub Actions 45209570132](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209570132), [artifact 14835123866](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209570132/artifacts/14835123866): TWO original code versions installed separately on the SAME disposable runner, each with unique Docker project and independent PG source/restore cluster. IDs for 0e301a source/restore: 7711394723850833980 / 7711394851945500732; IDs for 996dfc9: 7711394933269237819 / 7711395017988198459. Four unique IDs, both full 001–010 Ledger, DB55 private_no_dispatch, 2 Product+7 Bootstrap restricted verify-full source-code role preflight and independent restore PASS. No Mac execution.

[GitHub Actions 45202743968](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968), [artifact 14831408848](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968/artifacts/14831408848): 14 active Auth+History tables (all FORCE RLS), 17 FK, 38 indexes, 72/72 Auth private SELECT negative, populated pre-009 History+valid/revoked sessions backup/independent restore then upgrade 009–010 on BOTH clusters, second disposable cluster rejects incomplete/duplicate/corrupted/fake fully-applied Ledger, synthetic 2400 conversations/4800 messages with two owners, EXPLAIN uses both History cursor indexes; NOT production-scale workload/SLO.

DB optional 011 remains separate, historical CI 45108041850 attempt 2; no Gateway dispatch. No unauthorized 012+ SQL.

## ERD/data dictionary and exact status of 57 specialist items

The physical ERD and future policy design contract is in docs/PHASE3_PHYSICAL_ERD_AND_FUTURE_POLICY_CONTRACT_v2_20261123.md. Actual PostgreSQL catalog artifact file physical_erd_data_dictionary.jsonl has SHA256 03f1fba468680edad84e8901effc64f0b58c74ba8f4a3cbc0ecbffdf5bc74c8f. Existing implemented owner_id/Auth FKs and History are separate from NOT IMPLEMENTED Consent/withdrawal, Feedback FK to a valid committed Answer, real Citation/Attribution/versions, Audit, hard Delete/tombstone/Export. No final schema before joint API+Security/Owner contract and acceptance tests.

Exact denominator remains 57 specialist rows: **4 limited DONE, 29 OPEN, 24 BLOCKED**. Sixteen affected row witnesses were refreshed in docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md, with reason and exact next test for **every one of the 57** in docs/PHASE3_57_ROW_INDEPENDENT_RE_REVIEW_20261123.csv. There was NO automatic new accepted row or module Gate from a green CI. The canonical 262 activity / 26 independent Gates register is edited only by Foundation; P3OP mapping is non-counting and Foundation already owns 92→105 crosswalk. No re-count of this overlay here.

## Remaining named blockers and handoffs

- Foundation PR #55, comment 7106618986: correct stale integrated source pins; provide signed Mac HTTP/BFF/IdP Product+Bootstrap 2+7 actual current roles and TLS, A/B 404/401, candidate DB volume+image/cluster+ledger, independent restore, and only if separately authorized a single C018 no-dispatch OS spawn. No Mac demo modification.
- API PR #61, comment 7106620107: versioned owner_id/user_id mapping and same-TX session fence, Consent version+withdrawal, Feedback tied to committed Answer+idempotency, deletion/tombstone anti-resurrection and Export-independent scope, verified ENGINE source locators/versions/T3, audit redaction and negative tests. No speculative 012+.
- Ops/Security/Owner: signed numeric RPO/RTO and actual dataset/workload, encrypted off-host backup+KMS/key custody, retention/rotation, PITR/WAL and Qdrant no-write snapshot/release pointer.
- CENTRAL: independently review any Gate acceptance, Merge, Model/Gateway/Arvan; no such authorization within this scope.

**Final bounded status:** DB executable CI PASS, both-baseline same-runner CI PASS, latest integrated physical DB files 65/65 identical, integrated provenance pin metadata STALE, Mac real HTTP/IdP/C018 NOT_RUN, hard deletion and approved RPO/RTO NOT_RUN, Module Gate acceptance NOT_GRANTED, full Phase3 completion NOT_100_PERCENT. Protected Mac demo remains untouched.
