# Phase 3 production decision and hypercare handoff

**Disposition: NO-GO for production.** This is an operator decision aid for a future approved change window. The current authorization covers the frozen invited pilot and local App-only verification.

## Source of truth and deployment boundary

- The frozen pilot tag is `v0.1-arvan-100users-live` at `4edadd3e784e1f9500dd9da8d4b6f6e40833cd13`. The `phase3/completion` branch contains later source changes and local evidence. An operator must identify a candidate SHA explicitly before approving any deployment. [Pilot handoff](../../infra/arvan-staging/ARVAN_STAGING_HANDOFF.md) · [Live #143 receipt](../reports/SPEC-01B-arvan-live-deploy.md)
- The historical rollout contains DB55 preparation, offline build and rollback context. Its old IdP hostname, discovery probe and legacy Nginx install examples belong to the earlier topology. For the frozen same-domain topology, use issuer `https://ragfinance.ir/realms/finance-staging`, the exact Web callback and the same-domain/deny-only deploy templates. The legacy IdP host returns 404. Do not use the historical cutover commands as the current ingress instructions. [Historical rollout](../../infra/arvan-staging/ROLLOUT.md) · [Deploy entrypoint](../../infra/arvan-staging/deploy-arvan.sh) · [Same-domain template](../../infra/arvan-staging/templates/ragfinance.ir.conf)
- The deploy dry-run prints the expected sequence. A successful dry-run provides source-level evidence. The approved isolated rehearsal must still validate path ownership, offline cache, realm, units, nginx, PostgreSQL and rollback. [App-only staging evidence](../reports/SPEC-P3-07-reproducible-staging-app-load.md)

## Go/No-Go record

| Input to decision | Required evidence | Current disposition |
| --- | --- | --- |
| Candidate and provenance | Exact source/image digests, migration chain and engine Release/manifest pins. Receipts must cite the candidate source. | Open. Pilot SHA exists. Same-SHA image and engine evidence are pending. |
| Backup and recovery | Approved RPO/RTO, checksum and restore/PITR results on independent isolated copies, plus a compatible rollback plan. | Open. Historical lab receipts exist. Current source has static pin evidence. |
| Security and privacy | #143 mTLS, RS256, S256, exact callback and blocked routes on the nominated target. Signed two-owner and replay tests, resolved or explicitly dispositioned image findings, consent/retention and incident approval. | Open. Pilot #143 passed. Production evidence is pending. |
| UAT and capacity | Named independent UAT owner, authorized two-account journey, approved SLO/workload and evidence for signed History, failures, recovery and real provider cost/safety. | Open. Current loopback metrics are capability-only. The 100-user workload remains unverified. |
| Change authority | Named release approver, executing operator, DBA, Security and on-call escalation contacts. Record UTC window, go/no-go, linked receipts and the approved rollback trigger. | Unassigned in this handoff. Obtain explicit approval before changing live systems. |

## Containment and rollback rehearsal

1. On security boundary failure, ambiguous provider outcome, data-isolation failure, or an approved threshold breach, stop promotion and record UTC time, SHA, redacted correlation IDs and affected components. Security/Ops and the DBA decide containment under the approved window.
2. Apply the approved fail-closed Send posture and verify the capability endpoint. Preserve claim state and evidence through any in-flight ambiguity. Do not replay a provider operation or drop migration 011 to clear a claim. Use the procedure and restrictions in the rollout's stop-condition section.
3. Restore reviewed vhosts, image and configuration from the approved release record. Validate Nginx before reloading. Practice DB restores independently and check compatibility, catalog, grants, owner A/B and restart behavior before any traffic can return. A live database rollback or restore requires DBA approval. [PostgreSQL evidence](../reports/SPEC-P3-02-postgres-migrations-isolation.md) · [Rollout stop conditions](../../infra/arvan-staging/ROLLOUT.md#5-enable-smoke-and-stop-conditions)
4. Repeat the candidate smoke: five service states, exact HTTP status, issuer/RS256/S256, 404/405 boundaries and mTLS positive/negative pairs on both private interfaces. Validate signed owner A/B, restore parity and the release decision before resuming any rollout.

## Hypercare and Phase 4 boundary

- Assign a primary on-call owner, backup owner, handoff recipient and Security/DB escalation roles. Record the approved incident severity and response targets, daily review cadence and exit criteria. No named owner or numerical SLA is asserted here.
- Review redacted errors, latency, cost, Citation and Safety, backup health and invited feedback during the approved window. Keep the work to Phase 3 stabilization. Document incidents, unresolved risk and deferred decisions in the handoff.
- Handoff sign-off requires a stable same-version baseline, approved runbook, verified training/ownership transfer, and the Phase 4 input contract for Profile, Assessment, Goals and Action Plan. Record scope and data permissions with the owner before any activation. [Owner decisions](../../coordination/OWNER_DECISIONS_20261126.md)
