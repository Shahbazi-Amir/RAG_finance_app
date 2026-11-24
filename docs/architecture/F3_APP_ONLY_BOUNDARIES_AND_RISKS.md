# F3 app-only boundary and nonbinding release readiness matrix

Status: candidate CI only. Neither the architectural ADRs nor the canonical Gate criteria are replaced by this document. Source owner choices remain in ADR 0001, the master prompt and four-chat delivery.

## Context and containers
- Actor A and actor B → Chromium → Next.js HTTPS ingress/BFF. The public boundary is a lab ingress, not a target domain.
- BFF → Bootstrap (separate trusted authentication exchange) → standard lab Keycloak; signed BFF → private mTLS API → TLS PostgreSQL 17.11.
- The API owns authorization, error contract and transaction entry. The storage module owns scoped PostgreSQL operations and never imports application, UI or RAG runtime.
- The Web client consumes only BFF HTTP paths and canonical DTO validation, not direct database or provider access.
- The app-only composition cannot import the RAG runtime directly; its normal Send fence refuses before body consumption. Engine-specific provider, Qdrant, Redis, object storage and phase-four profile modules are not deployed by this candidate.
- Internal History L1 OpenAPI 3.1.0 view embeds the original product.v1 schema exactly with adjusted local references; public signed app-only docs are denied. This is not a full product OpenAPI acceptance.

## Risks and dependencies (not accepted)
| Risk | Evidence/guard | Required decision |
|---|---|---|
| Incorrect peer, identity or role | mTLS, signed readiness, scoped transaction, cross-owner denial | API/DB owner and target Ops review |
| Concurrent retries and duplicate effects | eight signed POSTs in separate CI persistence profile, SQL T1/T2 and restart replay; app-only Send remains denied | approved dispatch/unknown/cancel policy and live provider contract |
| Backup stale, unsafe rollback | distinct PG system identifier, no-write rollback, encrypted synthetic backup | approved RPO/RTO and target authority |
| Compromised package or credential | exact-image SBOM and source/history scanning; findings never auto-waived | Security owner dispositions and target digest |
| Outage and resource saturation | bounded real History ramp, actual PG fault and recovery, offline CI dashboard | approved workload, limits, monitoring/notification and alert ownership |
| Source authority/financial advice | app-only never generates Answer | accepted NB23, real locator and policy |
| Privacy lifecycle and phase-four scope | no active financial profile/assessment tables; policy-specific commands fail closed | CENTRAL privacy and lifecycle decisions |

## Go/No-Go
Candidate can proceed only with a verified same-SHA isolated regression and redacted receipts. Production and Mac remain NO-GO until the human owners deliver approved NB23 and policy, target access, approved digests, resolved security findings, verified installation/restore/rollback and Gate acceptance. Never infer those from the lab. Technical debt: actual target ingress and Bootstrap, full signed provider generation path, approved performance/retention/incident policy, and the 16 historical owner decisions remain separately tracked.
