# Open decisions — no hidden freeze

1. **Reference provenance (closed for eight copies):** User reports clean local Mac checkout including `660566e`; manual transfer canceled. GitHub Blob SHAs and independently computed copy SHA-256 are recorded in `references/phase2/source_manifest.json`. Local Mac file bytes were not read by this agent; any future version replacement still requires approval.
2. **NB23/Phase2:** `formal_readiness=BLOCKED`, `accepted_for_phase3=false`; need accepted Release and Module00 evidence.
3. Auth/session method, consent wording, scope of support role and PII policy require employer approval.
4. Retention/deletion/backup and export: operational P3-04/P3-07/P3-11 expects export; modular M15 conditions it on Scope approval. Decide before implementation.
5. Hosting/provider/model/data-transfer policy, capacity/budget/SLO and RPO/RTO require workload and employer evidence; no assumptions here.
6. Draft NB23 request missing history, context and source/authority filters; real streaming, Citation resolution and outcome mapping not verified.
7. Advanced PWA versus responsive baseline, operations ownership and Gate delegation remain unresolved.

8. **Streaming and Cancellation:** required by Phase 3 map but live event protocol, server cancellation and recovery are unverified. May design L1 Mock only after specialist assignment; L2 blocked until real contract/runtime tests.
9. **Phase 4 reserved entities:** financial_profiles, financial_snapshots, assessments, scores, goals, action_plans, risk_flags and human_referrals remain design-only extension points; no active MVP table/migration.
10. **Ownership pending:** Qdrant operational, Object Storage operational, integrated security/operations/launch human owner still unassigned; Foundation coordinates, final decisions by supervisor.
11. **Deletion vs Export:** deletion is a separate privacy workflow. Export scope is unresolved, but must not block compliant deletion once privacy/retention decision is approved.

## AGENT-PLAN-01 — employer Stack and operational conflicts

- **Approved narrowly:** Next.js + TypeScript, FastAPI, PostgreSQL, Modular Monolith and Docker Compose for initial service execution only in a later approved mission. [ADR 0001](../docs/adr/0001-architecture-proposal.md). No software version, migration/service startup or Module 01 Gate is approved.
- **Export scope CONFLICT:** operational P3-04/P3-07/P3-11 expects Export, while modular `P3M15-A08` requires separate Scope approval. Do not assume Export; keep deletion independent.
- **Operational GAPs OPEN:** support/admin role policy, password reset, Consent version/withdrawal, landing page, Worker Docker image, Qdrant/Object Storage ownership and object/log lifecycle, tombstone/resurrection checks, limited admin operational view, safe output rendering, feature flags and consent-aware analytics are explicitly mapped in non-counting [P3OPxx-Ryy register](phase3_checklist.md).
- **NB23/Phase2 OPEN:** upstream Release and formal handoff BLOCKED; real Source resolver/attribution, stream/cancellation, engine integration and Module 00 unaccepted. Historical 21 synthetic Contract tests are not proof of real producer or DB.
- **Infrastructure/Policy OPEN:** exact versions, Auth, Consent, Retention, provider/model, Hosting, budget, capacity, RPO/RTO, SLO and operating/security owners. Availability 99.5%, 500ms and 15s sample values remain NONBINDING.
- **Persistence OPEN:** Receipt–Attempt and crash T1→T2 recovery, transaction boundary, TTL, Unique/NULL, Feedback retries, and safe deletion lookup after session invalidation; `NEEDS_API_DB_REVIEW`, no DB or migration acceptance.
