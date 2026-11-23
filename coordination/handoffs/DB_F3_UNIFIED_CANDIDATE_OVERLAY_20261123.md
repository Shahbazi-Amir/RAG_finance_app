# DB-F3 independent candidate overlay — source-bound, no live Mac/engine

Base Foundation PR #77 commit: `b7c8928e596001de83c5f8dbd1b86284f46a57a9`. Source DB PR #59 docs HEAD: `4461406829cdadc5a358b2af591c827e91e711ae`; tested executable `f302fbf0f4a00ae4fe80d914452906fe88029078`, [CI 45234862871 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45234862871).

Purpose: import only DB-owned scripts 22, 23, 24, exporter11, four DB documentation files, and execution/order changes into a **separate experimental branch**. No operator Mac change, no 011, no 012+, no engine, no Gateway, no deployment.

Founder/UI/API source overlays are not overwritten. The previous Foundation integrated snapshot omitted DB 22-24 despite prior individual DB CI. This candidate restores the exact DB-tested files and expands full workflow to include real PG17 tests, manifest and 15 sanitized receipts.

New candidate Foundation app contracts+Web/API build, source pin audit, isolated DB test and real API/Web image CI must pass on SAME candidate SHA; prior independent DB PASS alone is not integrated acceptance.

Owners: DB = this overlay, Foundation = final integrated candidate and signed pin/CI review, API/UI/Ops = actual HTTPS BFF→API→PG/Mac and browser evidence. No count inflation: 5 DONE limited / 28 OPEN / 24 BLOCKED out of 57, all shared Gates NOT_ACCEPTED.

## 2026-11-23 latest standalone DB test imported

Script25 actual independent restore PostgreSQL SIGKILL/WAL recovery PASS source `b3505f545054a7d5eaa745785195403191ad72c8` [CI45260469796](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45260469796), 16 sanitized files [artifact14860576246](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45260469796/artifacts/14860576246). Its source runner and docs are now carried into this independent integrated branch for exact-SHA retest. M22-A09 **OPEN**, real Mac/Qdrant/IdP disaster, PITR and RPO/RTO not tested; no 012+ migration and no Gate accepted.
