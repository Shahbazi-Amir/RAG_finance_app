# FOUNDATION_F3 | 2026-11-24 executable app-only candidate handoff

## Current contract and safe scope

The owner-sourced Foundation candidate is a **DRAFT** integrated test environment, not a Phase3 accepted release. Its four product paths are a shared SHA built from Foundation PR #77, UI PR #65, DB PR #59 and API PR #76. The exact newer owner deltas are UI **16** blobs, DB **10** blobs and API **8** blobs, transferred only where the previously pinned owner blob equaled the prior integrated blob (no changed-path conflicts). The versioned source manifest has **122 pinned files**; this is not a count of all tracked files or Gate accomplishments.

**No engine:** no live model, C018 Runner, Qdrant/index or paid Gateway. No SQL 011, no production approval/Arvan, no migration on the existing Mac. This build has an intentionally restrictive, separate CI app-only listener—not a signed Product API replacement. No supported source path supplies production secret material.

## Reproduce from a clean checkout

```bash
git clone https://github.com/Shahbazi-Amir/RAG_finance_app.git
cd RAG_finance_app
git fetch origin integration/f3-foundation-20261124-app-only-candidate
git checkout --detach <tested-integrated-40hex-sha>
python3 scripts/f3_candidate_registry.py --out ci_receipts/f3_registry --self-test
python3 scripts/f3_progress_checkpoint_verify.py coordination/f3_execution/progress_cycles/20261123.json --self-test
docker build --platform linux/amd64 -f infra/phase3_l1/Dockerfile.api --build-arg BASE=docker.io/library/python:3.13.5 --build-arg SOURCE_SHA="$(git rev-parse HEAD)" -t f3-api-l1:"$(git rev-parse HEAD)" .
docker build --platform linux/amd64 -f infra/phase3_l1/Dockerfile.web --build-arg BASE=docker.io/library/node:22.23.5 --build-arg SOURCE_SHA="$(git rev-parse HEAD)" -t f3-web-l1:"$(git rev-parse HEAD)" .
export F3_API_IMAGE=f3-api-l1:"$(git rev-parse HEAD)"
export F3_WEB_IMAGE=f3-web-l1:"$(git rev-parse HEAD)"
docker compose -p f3app-only-ci -f infra/phase3_l1/compose.app_only_isolated.yml config --quiet
docker compose -p f3app-only-ci -f infra/phase3_l1/compose.app_only_isolated.yml up -d --no-build
curl --fail http://127.0.0.1:3100/api/product-capabilities
docker compose -p f3app-only-ci -f infra/phase3_l1/compose.app_only_isolated.yml down --remove-orphans
```

The DockerHub version-tag override is **CI fallback only** after ECR HTTP 429; approved release digest parity and OCI vulnerability scan remain NOT_VERIFIED. The restricted Web exposes only a host-loopback test port. The API has no host port, remains on an internal-only network and has **process liveness 200, product readiness 503**, deliberately. BFF and API Send reject 503 `ENGINE_NOT_AVAILABLE`, before durable T1/T2 admission. No real product conversation reads succeed from this restricted listener.

The GitHub workflows `f3-completion-exact-source.yml` and `f3-m18-m19-real-image-http.yml` must both be green on the **same final commit**, not merely at an ancestor. The first executes exact blob/lock checks, Python/API/contract/Node/UI tests, independent disposable PG17.11 001–010 + DB55 + 22–25 restore/negative/WAL tests, 393-row registry and actual isolated Next Chromium app-only at 1280/390/320. The second builds real images, checks nonroot user, starts API HTTP and Compose API/Web, and emits only sanitized image IDs.

## Precise external blockers and first unblock checks

| Owner | Missing input and evidence | First check after delivery | Affected criteria |
|---|---|---|---|
| CENTRAL / Product / Legal | Signed scope for Send, Consent/Withdrawal, Feedback, retention, export/delete + browser and AT matrix | Contract version/ADR positive+negative tests, no false UI flows | M01, M14–M15, M21 |
| SERVER / Ops | Authorized isolated Mac namespace, HTTPS host and SAN/CA, OIDC credentials/IdP, signed BFF→API/Bootstrap, actual PG + two account A/B | Snapshot then install exact digest in new Compose project; login→History→revoke and adversarial B GET | M05–M06, M13–M15, M18, M20 |
| DBA / Ops | Target volume, approved migration ledger and two independent restore copies, approved RPO/RTO | Restore fresh volume and rerun signed A/B, consistency and timed rollback | M04, M22 |
| Security / Supply chain | Approved image/base digest, OCI image vulnerability scan, secret and dependency approvals, trace/SLO ownership | Validate digest provenance, scan, redacted incidents | M02, M16, M18–M21, M23 |
| PHASE2 / ENGINE (separate future mission) | Accepted NB23 release, precise engine lock/wheelhouse, C018/C011 index hashes and typed source authority | Gate00 hash checks, then separately authorized retrieval-only tests | M00, M07–M12 |
| CENTRAL / Launch | Target E2E, UAT, Go/No-Go, on-call/hypercare approvals | Audit complete Gate receipts and explicit launch decision | M24–M25 |

The registry is an execution inventory, **not** a pass matrix. It includes **262 module activities, 26 independent Gates and 105 non-counting crosswalks** (393 distinct). The frozen app-only denominator has not been set by CENTRAL; accepted/262, Gate accepted/26 and witnessed/105 must not increase from CI alone. The last reviewed Foundation snapshot was **40/121 partial, 38 not verified, 43 not run, 0 accepted**, and remains a *historical source coverage snapshot* rather than current per-row acceptance.

## Recovery / rollback rule

If new exact-SHA CI fails, inspect the first failed test/step and preserve current PR and all owner heads. Rebuild only changed source and rerun whole final integrated suite. Do not automatically call any engine or repeat an unknown paid request. For this isolated CI app, rollback is stopping **only** `f3app-only-ci` and returning to last green tested SHA; never use `down -v` on a pre-existing project, never write to the frozen Mac demo volume, and never claim production rollback without real destination evidence.
