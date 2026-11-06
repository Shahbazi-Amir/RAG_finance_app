# Proposed Phase 3 architecture overview

Status: **limited employer Stack choice approved**; architecture/product implementation and all Module Gates remain unaccepted. Pinned source: `7c74783c3dcda897b010ba9ea358d113f172ed1f`.

- UI: responsive RTL, consent/chat/history/source drawer/privacy and safe offline/retry views, without inventing full NB23 Citation/streaming.
- API: product-owned identity/authorization/error/idempotency/trace envelope, adapter to Phase 2 **only after** accepted release and Module 00 checks.
- Database: per-user users/consent/sessions/conversations/messages/citations/feedback/audit/deletion records with strict isolation; schema and RLS tests later.
- RAG boundary: Draft NB23 request only `contract_version` and `question`; no history/context/filter inputs. Outcome enums only candidate consumer vocabulary. Synthetic Citation IDs not production source resolver.
- Security and operations: shared foundation coordination, human final operations owner pending, least privilege, no logs with PII, source-use controls, backup/restore, load and incidents untested.

Employer-approved Stack choices: **Next.js + TypeScript**, **FastAPI**, **PostgreSQL**, **Modular Monolith**, **Docker Compose for a future separately authorized initial service run** ([ADR 0001](../adr/0001-architecture-proposal.md)). Qdrant, Redis and Object Storage remain reference components with no service activation under this mission. This is not Module 01 Gate acceptance; versions, Auth, Retention, provider/model, hosting, cost, capacity and SLO remain open. Phase 4 functions remain explicitly excluded. Parallel UI/DB design and foundation docs do not unblock NB23/Module 00.

## Explicit parallelism and non-overlap

- Approved UI and DB **onboarding** documents are recorded; no product implementation has started. After Foundation acceptance and a specific specialist mission, UI/History and PostgreSQL Persistence may be developed and tested independently with provisional versioned contracts/Mocks.
- PostgreSQL product schema, migration, RLS and local restore are the DB agent's responsibility. Qdrant, Object Storage and total Retrieval/release acceptance have separate responsibilities; Foundation coordinates, final operations owner **assignment pending**.
- Real RAG adapter/live engine compatibility, Streaming/Cancellation runtime semantics, Module 00 Gate and launch stay blocked. Streaming and Cancellation nevertheless remain requirements and should be tested at L1 Mock before L2 live integration.
- Deletion policy and workflows are independent of Export approval. Phase 4 financial entities remain reserved documentation/extension points; no active tables in Phase 3 MVP.
- Illustrative SLO targets from the roadmap are **proposed/nonbinding**, not accepted targets without workload and infrastructure decisions.
