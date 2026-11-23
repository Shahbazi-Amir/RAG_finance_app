# F3 APP_ONLY — unified candidate executable continuation and P0 owner blockers

**Status:** Integrated Draft [PR #84](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/84), not default or production. Compare **exact PR HEAD with its own CI run** before treating a receipt as current. No Mac/Arvan/IdP, paid model, Qdrant, Runner, destructive migration, 011 or existing demo volume was touched. This handoff is for P0-1..P0-6 of the exact `PHASE3_MASTER_PROMPT_FA(1).md`.

## Change/acceptance counters (separate; no fake %)

- Main phase-3 **262 activities**, **26 independent module gates**, **105 noncounting operational crosswalk IDs** = **393 individually indexed rows**, source-fidelity checked. **0/262 ACCEPTED**, **0/26 Gates ACCEPTED**, **0/105 crosswalk target witnessed by THIS integrated candidate**. The last figure does not create extra counted activities.
- UI specialist: **2/14 fully source-complete = 14.29%, 11/14 with source = 78.57%, 0/14 target accepted = 0%**; **deltas from user baseline all +0.00 percentage points**. Improvements to app-only modes are **separate source/CI slices**, not an automatic UI row closure.
- App-only denominator is **UNFROZEN**, cannot safely claim app-only readiness/acceptance %. Three status levels must be kept distinct: existing code, CI verification at exact SHA, and genuine target acceptance.
- `coordination/integration/PHASE3_393_CANONICAL_APP_ONLY_EXECUTION_LEDGER_20261124.csv` has owner, exact criterion, dependency, mode-slice placeholder, code, test, target, SHA, receipt and next action on every ID. It faithfully preserves source historical statuses. Only CENTRAL with fresh receipts may promote status `PARTIAL → CODE_DONE → CI_VERIFIED → TARGET_VERIFIED → ACCEPTED`.
- `coordination/integration/FOUR_PR_APP_ONLY_PINNED_SOURCE_MANIFEST_20261124.json` documents exact four incoming PR SHAs, **42 source file resolution candidates**, **six security-sensitive conflicts** resolved in favour of Foundation/UI existing protective behavior, and actual Git blob SHAs. A unit test checks those bytes on checkout. Do not overwrite these from an old subteam PR.

## P0 status at code/test boundary

| P0 | Implemented in this candidate | Still missing for real completion | Exact decision / owner |
|---|---|---|---|
| P0-1 | One Foundation-based integrated Draft PR with three-way chosen blobs, Node/API/DB/Browser CI suite, exact manifest, six downgraded-source repairs | All-green final exact-SHA unified workflow, owner sign-off on conflict resolutions | Foundation/CENTRAL: review manifest, preserve original trust order, run same candidate all jobs |
| P0-2 | FastAPI `apps/api/app_only_asgi.py` actual no-engine internal listener, `/health/live` 200, `/health/ready` **503** (truthful), `/v1/messages` **503 before body/T1/T2**, zero engine imports; non-root API Docker image + real healthcheck; real Web/BFF APP_ONLY disables Send and forbids POST; Web Docker build and private Compose | **REAL app readiness not achieved:** signed Product History ASGI adapter, trusted mTLS BFF, Bootstrap/IdP, PG transaction/owner, and ready=200 only once actually verified. Do not treat liveness as readiness | API #76 + Foundation #77 + Ops must deliver approved app-only signed entrypoint/version, SHA and IdP/PG host config; run negative forged peer/owner matrix |
| P0-3 | Copied DB #59 pinned scripts 001–010 (never 011); integrated CI job on uniquely named disposable PG17.11 and independent new-volume restore, RLS/role and M10 concurrency probes | NO Mac TLS/IdP/signed BFF→PG end-to-end owner A/B target receipt from this chat; validate migration ledger + retry under real signed sessions | DB #59 + API #76 + Ops: provide isolated PG17.11 DSNs/certs and two valid test owners, sanitized SQL receipt, service actor/grants evidence |
| P0-4 | Real Next source, Chromium at desktop/390/320px; app-only Send disabled, API/BFF refusal, 401/503/late-owner fixtures preserved; two physical no-port containers with internal DNS in CI | NOT a signed Browser→API→SQL journey; no real IdP login/logout/revoke, History page A/B, DB cursors, real Safari AT or signed negative Host/Cert | Foundation/Ops/UI/API/DB: provision approved private topology, A/B, signed mTLS, Safari/AT acceptance matrix and run fully correlated SQL journey |
| P0-5 | Repeatable `infra/phase3_l1/compose.app-only.internal.yml` with non-root, read-only, private internal network, no host ports, no external secrets, no engine services; CI builds/runs real Web+API images. Existing PG lab tests independent-volume backup/restore | NO approved Mac package, production TLS secrets, target image digests/SBOM/security scan, production restore/rollback E2E after real A/B login; not safe to invent RPO/RTO | Ops/DB/Foundation: sign isolated namespace/volume/digest/retention, dry-run restore on a fresh unique volume, record owner approval and times |
| P0-6 | Complete 393-row source-grounded ledger and exact-blob manifest, negative CI integrity gate | CENTRAL employer must freeze **versioned app-only slice denominator and acceptance rubric**; decisions for outstanding privacy/legal/product/ops SLO unknown | CENTRAL/Product/Legal/Foundation to approve policy and map each slice to concrete next test, then update the ledger with witnessed SHA and Run ID |

## Exact replay commands (clean checkout / no model, no deployment)

At a clean checkout of the **exact current** head from [PR #84](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/84), run in disposable Linux CI or isolated authorized worktree (do not target demo):

```bash
set -euo pipefail
git status --porcelain
git rev-parse HEAD
npm ci --prefix apps/web --no-audit --no-fund
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
python -m pip install -r apps/api/requirements-ci.txt 'PyJWT[crypto]==2.15.1' 'uvicorn==0.48.0' 'playwright==1.64.1'
python -m unittest discover -s tests/phase3/api -p 'test_*.py' -v
python -m unittest discover -s tests/phase3/integration -p 'test_integrated_393_registry.py' -v
bash infra/postgres/dev_f3_isolated/tests/run_static.sh
PHASE3_APP_MODE=APP_ONLY python -m uvicorn apps.api.app_only_asgi:app --host 127.0.0.1 --port 8118 --no-access-log
```

Expected public-safe local-only API responses: `GET /health/live` 200 (process only), `GET /health/ready` 503 (not integrated), `POST /v1/messages` 503 `ENGINE_NOT_AVAILABLE` and no body read, `GET /v1/conversations` 503 `SIGNED_HISTORY_NOT_CONFIGURED`. Even with forged browser owner headers no account data appears.

For **container-only** replay on a *new, unique* project with no existing volume and no public ingress:

```bash
export F3_PROJECT_NAME='f3-app-only-lab-unique-owner-approved'
export F3_RELEASE_TAG='<pinned-12-to-40hex>'
export F3_SOURCE_SHA="$(git rev-parse HEAD)"
docker compose -f infra/phase3_l1/compose.app-only.internal.yml config -q
docker compose -f infra/phase3_l1/compose.app-only.internal.yml build
docker compose -f infra/phase3_l1/compose.app-only.internal.yml up -d --no-build --pull never
docker compose -f infra/phase3_l1/compose.app-only.internal.yml ps
```

Do not use `docker compose down -v` on any existing namespace; no volume or demo cleanup instructions here. Only isolate a fresh transient CI namespace and inspect that neither Web nor API publishes a port. Docker health of API/Web proves actual HTTP liveness, **not PG/IdP/HTTPS product readiness**. The dedicated DB #59 CI has full safe 001–010 → DB55 → SQL/RLS → independent Restore → corruption/rollback controls; run on a **fresh LAB_ROOT and disposable Docker network/volumes**, never the Mac demo.

## Single-action owner requests — no invented approvals

1. **API/DB/Foundation — signed History integration:** frozen actor-bound versioned endpoint+blob SHA, mTLS CA+SAN, RS256 envelope/issuer/audience/key, immutable request and original same-T2 correlators; supply real DB ACL/owner RLS audit and A/B signed HTTP tests before enabling any account state. On failure keep `SIGNED_HISTORY_NOT_CONFIGURED` and `/health/ready 503`.
2. **Product/Legal/API/DB — Consent:** signed Persian policy/version/effective date, actor+session, legal hold/withdrawal rules, POST payload/CSRF/idempotency/401/404/409/503, terminal committed PG receipt. Until signed, `/account` remains read-only.
3. **Product/Legal/API/DB — Feedback/Delete/Export:** exact privacy/retention scope, resource ownership + FK, restore tombstone and backup, response codes and terminal receipt with signed persistence evidence, no manufactured 202 success or deletion.
4. **Product/Ops — UI accessibility:** approved Safari/Chrome/Firefox/VoiceOver/NVDA matrix, WCAG level and keyboard/focus/contrast rubric; L1 Chromium a11y alone cannot close UI-11.
5. **Ops/Foundation — target and safe rollout:** dedicated Mac candidate namespace, explicit approved non-demo secrets and DNS/HTTPS/IdP, staging SQL grants, empty-volume backup/restore trial, digest/SBOM/security checks, frozen SLO/RPO/RTO, rollback authorizer. Without evidence no deployment or accepted Gate.
6. **Phase2/Engine — deferred only:** after explicit user instruction and accepted Gate00/NB23, present engine lock/wheelhouse C018 index/Runner hashes; until then **NO_DISPATCH**, no generation, no T3/Claim/Citation or model call permitted.
7. **CENTRAL — denominator and evidence:** publish versioned app-only slice set and sign each acceptance. P3OP overlay 105 is not counted twice; an app-only P0 green does not accept the full 26 module gates.

**Hard boundary:** This file is a code/source and isolated CI plan with executable commands, NOT a claim that product is fully integrated. No Mac, external IdP, live PG actor or paid provider was contacted by the assistant.
