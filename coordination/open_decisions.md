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
