# DB-F3 — M04-A07 exact tested closure and ordered 29 OPEN baseline

**Source of IDs:** 57-row audit on previous `322fc16`; **latest validated executable** `48110525aa9ac118b6b3749c956930c61cec11fe`, CI [45233599373 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45233599373), 14 sanitized artifacts (ID 14848595915). 29 were OPEN before this cycle; exactly **one** (rank #1) moved to limited DB_CI_ONLY DONE. Remaining **28 OPEN**, **24 BLOCKED**, **5 narrowly DONE**. No module Gate accepted, 171 parent/overlapping map not additive.

**Sorting key:** A = complete isolated DB acceptance achievable without external decision; B = runnable DB tests but full criterion needs API/Ops/workload; C = signed product policy/integration dependency; D = Foundation-owned/shared contracts. Rank is an execution queue, not a fabricated date or official Gate decision. The noncounting P3OP items remain outside this table.

| Priority | ID | Owner | Group | Exact remaining acceptance input / result |
|---:|---|---|:---:|---|
| 1 | P3M04-A07 | DB | A | Isolated empty+populated migration cycle now DONE limited; prod/Mac pending |
| 2 | P3M04-A02 | DB | B | Full FK/index negative suite with agreed representative workload and query-plan/SLO threshold |
| 3 | P3M10-A10 | API+DB | B | DB concurrent two-client null-key race + simulated lost ACK + two owners PASS in CI45234862871; still OPEN: signed API HTTP retry and real process crash/replay plus IdP same-TX |
| 4 | P3M15-A10 | DB+API+UI | B | Concurrent History/Feedback duplicates, API transactional receipt after crash |
| 5 | P3M06-A07 | DB+API | B | Direct Python repository calls with hostile GUC/signed actor context |
| 6 | P3M22-A09 | DB+Ops | B | Disposable partial/full outage and recovery; approved DR topology later |
| 7 | P3M15-A02 | DB+API+UI | B | Immutable message/answer identity across actual title update |
| 8 | P3M06-A06 | DB+API | B | Actual ID-enumeration negative HTTP/timing suite |
| 9 | P3M15-A03 | DB+API+UI | B | Signed HTTP HMAC cursor A/B under concurrent inserts and SLO |
| 10 | P3M04-A03 | DB+API | C | Owner_id→user_id canonical mapping/coverage approval |
| 11 | P3M04-A01 | DB+API | C | Signed ERD/Data Dictionary with consent, feedback, owner/retention policy |
| 12 | P3M06-A01 | DB+API | C | Approved missing entities RLS; signed route/worker owner matrix |
| 13 | P3M06-A02 | DB+API | C | Read/write/delete policy on approved entities; HTTP and worker negative matrix |
| 14 | P3M06-A03 | DB+API/Security | C | Signed BFF/IdP same-transaction session/epoch/revocation fence |
| 15 | P3M06-A04 | DB+API/Ops | C | Authenticated worker identity and least privilege tests |
| 16 | P3M06-A09 | DB+API | C | Completed signed HTTP + background all-owner isolation matrix |
| 17 | P3M10-A08 | API+DB/Engine | C | Real T3 Answer + Run/version same transaction with crash test |
| 18 | P3M10-A09 | API+DB | C | Cancellation and UNKNOWN recovery, no double paid dispatch |
| 19 | P3M15-A01 | DB+API+UI | C | Real source-bound Message and Answer immutable persistence |
| 20 | P3M15-A07 | DB+API+UI | C | Signed Mac A/B, 404 foreign owner and 401 revoked session |
| 21 | P3M22-A10 | Ops/Foundation+DB | C | Full app/PG/IdP/Qdrant independent Mac restore signed runbook |
| 22 | P3M03-A09 | Foundation | D | Integrated dependency-import graph CI and approval |
| 23 | P3M03-A01 | Foundation+API/UI/DB | D | Approve domain boundaries; integrated import tests |
| 24 | P3M03-A02 | Foundation+API/UI/DB | D | Canonical cross-service error-model acceptance |
| 25 | P3M03-A07 | Foundation+API/UI/DB | D | Approved forward-compatible wire schema variants |
| 26 | P3M03-A04 | Foundation+API | D | Versioned /v1 real Mac HTTP and release provenance |
| 27 | P3M03-A05 | Foundation+API/DB | D | Approved User/Answer/Citation schema and producer evidence |
| 28 | P3M03-A03 | Foundation+API/Ops | D | Signed Mac request/trace/alert correlation |
| 29 | P3M03-A08 | Foundation+API/UI/Engine | D | Signed real UI-BFF-API-DB-C018 contract L2 |

### M04-A07 bounded acceptance, precise limitations

A new scratch PostgreSQL 17.11 copy of the already DB55-verified source was granted the same database-level privileges and cleared of the inherited *experimental* migration/bridge ledger. All 10 pinned DOWN migrations executed in exact reverse order only on the **empty** copy; all 10 UP scripts executed in original order, rebuilding a ten-entry committed ledger, the exact approved DB55 no-dispatch bridge, 14/14 FORCE RLS tables and matching normalized schema-only SHA-256. This did **not** roll back any customer's data. A separate pre-009 data-bearing fixture with two fake owners, History rows and active/revoked sessions was backed up, independently restored and upgraded 009/010 on both real scratch clusters with RLS and DB55 PASS, and cleared. All tests run inside the current CI; no Mac DB/volume was mounted. Restrict full destructive 001/003 DOWN to disposable **empty** clone only; actual populated production rollback requires owner policy.

### Handoff

Foundation: use exact source `48110525aa9ac118b6b3749c956930c61cec11fe`; 03 blob `9cc9458c55b82f03811b346259ccf2ae3dce318d`; manifest blob `f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf`; new 23 blob `a547a58ac1555795dd73c18415973bbc955177d8`; exporter 11 `b9dff8a9f736d36af3916900995afb798826b3e5`; workflow `dadd5ec47d8f312b7de35533241c275961195821`; execution order as in workflow. This does not prove Foundation integrated/ran the candidate; do not update Foundation-owned Gate silently.

API/Security/Product: consent/withdrawal, feedback tied to persisted Answer, tombstone/retention/export, owner-id→user-id, real signed same-TX identity and Citation/Run-version producer contracts require approval BEFORE any 012+ SQL. Ops: Mac candidate separate, full encrypted backup/PITR/anti-resurrection, RPO/RTO and signed original role+HTTP receipts missing. 011 intentionally excluded, no dispatch or Arvan.


## Next-cycle bounded evidence on queue item #3 (not accepted)

M10-A10 actual real-PG script24 `395078707143c85de2d8f58c0b365445176bbf6a`, [CI 45234862871](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45234862871) exact source `f302fbf0f4a00ae4fe80d914452906fe88029078` SUCCESS, 15 sanitized receipts. SQL duplicate/one-attempt/owner RLS passed, **not** signed API HTTP request replay, actual process kill, runtime IdP or Mac. Queue #3 remains OPEN. Totals 5/57=8.77% retained. Contract/policy decisions 012+ remain HOLD.


## Next bounded DB witness 2026-11-23

M22-A09 actual isolated DB process outage and WAL recovery tested on `b3505f545054a7d5eaa745785195403191ad72c8` [CI45260469796 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45260469796), new script25 and 16th receipt. **NOT a real full-host/network disaster, RPO/RTO SLA, or Qdrant operation; no ID/Gate newly accepted**. Totals 5/57=8.77% unchanged.
