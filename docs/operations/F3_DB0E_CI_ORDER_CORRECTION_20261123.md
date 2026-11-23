# Foundation DB 0e workflow-order correction
- First new integration source `0b8b75f11f7ae012947421ecf9a54839929405f4` run [45199639143](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45199639143) showed API/Web PASS, DB RED due `STOP_CATALOG_EVIDENCE_NOT_COLLECTED` after first 001-010/TLS/Restore complete.
- The new DB0e `11_export_sanitized_receipt.sh` requires exact preceding evidence scripts 13 (catalog), 12 (independent rollback/RLS/FK) and 14 (synthetic owner lifecycle restore). The failing Foundation workflow retained old DB59 order; **test harness**, not service source, was outdated.
- Repair copies the DB0e owner's exact [workflow order](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5/.github/workflows/f3-db-isolated-fresh-install.yml), 13→12→14→11. No SQL, API, UI, real Mac, Gateway or existing service touched.
- New exact-SHA CI must PASS all jobs. No Gate transition from CI.
