# OWNER DECISIONS — Phase 3 Readiness & Isolated Verification (2026-11-27)

- **Date Approved:** 2026-11-27
- **Approved By:** امیر شهبازی آراللو (Primary Owner)
- **Active Branch:** `phase3/completion` (Baseline: `1865994a81bcf37706636d9892f2ae313d125c7b`)
- **Frozen Live Pilot Tag:** `v0.1-arvan-100users-live` (`4edadd3e784e1f9500dd9da8d4b6f6e40833cd13`, untouched; no merge or deploy from `phase3/completion`)
- **Release Disposition:** `Production: NO-GO` | `Phase 4: LOCKED`

## Approved Decisions (6 Items)

1. **Named Operational Owners (Ops / Security / DBA / UAT / Release / Hypercare):**
   - **امیر شهبازی آراللو (Primary Owner)** is assigned as the named owner for all six roles until a dedicated operations team is formed.

2. **Approved SLO & Workload Targets:**
   - Monthly availability: `>= 99.5%`
   - Non-engine API latency (health, history, auth): `p95 <= 500ms`
   - Server error rate (`5xx`): `< 1%`
   - Approved pilot/staging workload profile: `100` invited users (up to `10` concurrent users).

3. **Disaster Recovery Targets (RPO / RTO):**
   - `RPO <= 24 hours` (scheduled daily PostgreSQL backup; tightened to `<= 15 minutes` once WAL/PITR archiving is enabled)
   - `RTO <= 2 hours` for full service and database restoration.

4. **Hypercare Window & Incident SLA:**
   - Post-Go-Live Hypercare period: `14 days`
   - Initial response SLA: `P0 / Security <= 30 minutes`, `P1 <= 4 hours`.

5. **Isolated Change Window & Immediate Rollback Criteria:**
   - Maintenance / change window: **Thursday/Friday 02:00–05:00 Tehran time (IRST)**
   - Immediate rollback trigger: any failure in `#143` security smoke checks or `5xx` error rate exceeding `2%`.

6. **Isolated Verification Environment (`SPEC-P3-09`) & Confirmed Deferrals:**
   - Execute `SPEC-P3-09` on isolated **GitHub Actions (`ubuntu-latest`)** with zero connectivity or credentials to the live Arvan server.
   - Confirmed deferrals remain in effect:
     - Password reset via SMTP: `DEFERRED` to post-pilot / Phase 4 (manual Keycloak admin reset remains active).
     - Corpus typo (`واریس ← واریز`) and index rebuild: `DEFERRED` to Priority 4 in `RAG_finance` (Owner: Codex-2).
