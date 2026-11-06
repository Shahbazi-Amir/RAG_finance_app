# ADR 0001 — employer-approved limited Phase 3 technology choice

**Status: APPROVED — STACK SELECTION ONLY.** The employer approved these choices for further work on 2026-11-06 under AGENT-PLAN-01. This replaces only the earlier *unselected technology hypothesis*. It does **not** approve Module 01 scope/architecture/SLO Gate or authorize installation, service execution, migration or deployment.

**Trace:** [modular Module 01 / activity 3](../../references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md#L176) (`P3M01-A03`) and [operational P3-01 ADR requirement](../../references/phase2/roadmaps/RAG_finance_phase3_operational_roadmap.md#L48) (`P3OP01-R05`).

| Layer | Approved | Not approved here |
|---|---|---|
| Frontend | **Next.js + TypeScript** | Implementation, exact versions, Router/PWA mode |
| Product API | **FastAPI** | Running API, Auth protocol, NB23 producer adapter |
| Product persistence | **PostgreSQL** | Schema, migration, RLS, running database or Retention policy |
| Application architecture | **Modular Monolith** | Application code or service deployment |
| Initial service runner in a later mission | **Docker Compose** | Installing/running containers or deploying now |

**Architecture references, not activated services:** Qdrant, Redis and Object Storage. Hosting mode and responsible human operators are pending.

**Rationale:** employer choice is consistent with pinned [modular §2](../../references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md#L31) and [operational §2](../../references/phase2/roadmaps/RAG_finance_phase3_operational_roadmap.md#L24) reference architecture; no unperformed benchmark or cost analysis is asserted. Existing architecture separation of Web, API, DB, RAG adapter and operational services remains.

**OPEN:** precise versions (Python/Node/Next.js/FastAPI/PostgreSQL/Qdrant/Redis/Docker), Auth/Consent, model/provider, Hosting/data location, Retention/Export, budget/capacity/SLO, RPO/RTO, threat review, operational ownership and launch approval. Module 00, 01 and 03 Gates and live NB23/RAG are unaccepted. The next environmental checks belong to a separately authorized M02/M18 mission.
