# F3 app-only: isolated operational drill (not approved target)

Source: the ordinary Chromium/Keycloak/BFF/real signed API/PG lab. This is an executable CI procedure, not an Ops policy, external notification, deployment or human acceptance.

## Architecture and trust boundaries
Browser A/B → private HTTPS ingress → Next BFF → mTLS pinned API signer → PostgreSQL 17.11 scoped roles / 004+005 session admission. CI Bootstrap/IdP is separate; use its standard OIDC login, never a fabricated cookie. API does not get BFF private signing key; Web does not get database role credentials. Qdrant, Runner, model gateway and provider credentials are absent. No active phase-four tables.

## Reproduce
From the exact candidate checkout run the branch workflow `.github/workflows/f3-real-browser-keycloak-pg-single-runner.yml` in a disposable runner. The workflow builds real API/Web images from clean source; use only the lab PG service and new volume. Do not run commands against a Mac or target service. The load sample runs 1, 2, 4, 8 concurrent read requests and a short sustained two-request sample; actual 200/503, throughput, percentiles and Docker CPU/memory/PIDs/PG connection counts are recorded. These are observations, not an approved soak duration or capacity/SLO. Preserve each SHA, run and image ID. No question, cookie, account identifier, private config or raw trace is exported.

## Dependency incident drill / runbook
1. Record healthy signed API readiness and A/B History; record image IDs, source SHA and original PG system identifier.
2. Create a fresh independent volume and check owner rows before switching. Make a protected temporary backup of the synthetic DB and the app configuration/pointer; test wrong key and ciphertext tamper rejection. No durable plaintext backup export.
3. Stop ONLY the identified CI PG service after successful backup. Expect readiness 503 and both authenticated History BFF requests 503 with no-store; no false success or private body. An observed failure event is evidence, not a paged Ops alert. If either user sees a 200, treat as a security/consistency failure, preserve redacted evidence and stop the drill.
4. Restore on the empty volume; both browser contexts retain their sessions, same SQL/DOM and owner isolation. If ready fails or ownership differs, do not approve; switch to the original isolated service only with no intervening writes, compare PG system ID and rows, repeat history and revoke tests.
5. Retain JSON, offline HTML observation and exact CI run. Route any vulnerability/secret findings and open workload/retention/threshold decisions to the named owners. Do not interpret passing this drill as authorization for staging, production, paid provider calls, NB23 or SQL011.

## Explicit risks and deferred decisions
Wrong peer or signed owner, foreign cursor and cross-owner cache, disclosure of request payload in log, unauthorized Send/duplicate write, dependency outage and stale restore, credential leakage via build/mount. Tests cover bounded negative cases in the same lab. Production log policy, approved security response, RPO/RTO, performance thresholds, browser matrix, operator escalation, Qdrant snapshot, model cost and accepted Phase2 knowledge Release remain open. No live admin dashboard has been enabled.
