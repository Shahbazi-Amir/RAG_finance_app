# AGENT-ARVAN-CANDIDATE-01

## ARVAN-CANDIDATE-01.1 · Arvan invited staging dispatch

**Status** review · **Implemented** candidate source and templates · **Tested**
local evidence below · **Accepted** pending supervisor approval of the rollout.

**Baseline.** `RAG_finance_app`, authorized branch
`deploy/arvan-100users-candidate`, observed starting HEAD
`0e46ef318c41901ded4adc64480e2f78e38e0556` above worker integration `6bb08b5`
and PR #143 `2373078`. The upstream Engine SHA-256 is
`91a1a34628f221f7f8bc892a0fb6a917328817dae1328856d84aad7f880f406e`, observed in
the existing local bundle. The DB #56 claim source is `b0ba6dbf6100109cb58f8cb49da808839d68c5f0`,
blob `031d2f438f000154eb4e2b374ce42181b3d812b3`, as pinned by
[the Foundation workflow](../../.github/workflows/foundation-api53-db56-claim011-http.yml).
Arvan runtime, C340 inputs, DB socket inventory and server latency figures are
user-reported. Host operations and live calls were outside this checkpoint.

**Canonical links for Foundation.** Module 06 activity 3
(`P3M06-A03`, L333), Module 10 activities 5 and 9 (`P3M10-A05/A09`, L434/L438),
Module 11 activity 1 (`P3M11-A01`, L455), Module 14 activity 5 (`P3M14-A05`, L554),
and Module 18 activities 1, 4 and 9 (`P3M18-A01/A04/A09`, L658/L661/L666).
Source sections are in the [modular roadmap](../../references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md).
Operational overlays `P3OP04-R11`, `P3OP05-R07`, `P3OP06-R01/R03/R09` are
evidence links only. Scope is the claim/replay boundary, provisional quotes,
offline worker packaging and ingress template. The canonical checklist remains
under Foundation ownership.

**Implemented paths**

- `apps/api/private_staging_asgi.py`, `apps/api/product_session_api.py` and
  `src/phase3/rag_runtime/arvan_live_dispatch.py` select the live path through
  the protected startup config, existing mTLS/RS256 and signed DB session fence.
  A definitive 011 claim commit precedes an enqueue. A signed GET reads an
  owner/session/attempt-bound temporary staging result.
- `apps/web/app/api/product-capabilities/route.ts`,
  `apps/web/src/auth/server/private-staging.ts`,
  `apps/web/src/auth/server/product-session.ts`,
  `apps/web/src/history/client.ts`, `apps/web/src/history/proxy.ts`,
  `apps/web/src/ui/attempt-checkpoints.ts`, `apps/web/src/ui/product-chat.tsx`
  and `apps/web/src/ui/runtime-capability.ts` enable the protected policy,
  correlate the result GET and render producer-checked quotes.
- `infra/nb23-v4/Dockerfile.arvan-worker`, `infra/nb23-v4/worker.py` and
  `infra/nb23-v4/arvan_gateway.py` add legacy COPY/chmod, the private serial
  worker socket and exact Arvan response compatibility after Engine SHA verification.
- `infra/postgres/migrations/011_external_dispatch_claim.up.sql` is the
  unchanged DB #56 blob. The [API session 011 workflow](../../.github/workflows/api-session-011.yml)
  tests Login/History/Revoke and uses an independent numbering convention.
- `infra/arvan-staging/ROLLOUT.md`, `infra/arvan-staging/run-worker.sh`,
  `infra/arvan-staging/render-nginx-proof.py`,
  `infra/arvan-staging/keycloak.compose.yml`,
  `infra/arvan-staging/nginx/ragfinance.ir.conf`,
  `infra/arvan-staging/nginx/idp-staging.ragfinance.ir.conf`,
  `infra/arvan-staging/systemd/rag-arvan-api.service`,
  `infra/arvan-staging/systemd/rag-arvan-bootstrap-oidc.service`,
  `infra/arvan-staging/systemd/rag-arvan-web.service` and
  `infra/arvan-staging/systemd/rag-arvan-worker.service` provide the reviewable rollout.
- `tests/phase3/api/test_arvan_live_dispatch.py` and
  `tests/phase3/ui/arvan-live-dispatch.test.mjs` cover the overlay,
  serialized retrieval, independent HTTP lane, result scoping and mode fencing.

**Decisions.** The original Engine bytes pass their original SHA check before
a narrowly anchored Arvan overlay is applied. The response accepts the exact
Arvan Flash alias and accepts absent reasoning counts only for the approved
Flash profile with thinking disabled. Explicit invalid or nonzero reasoning
stays held. The worker remains offline. Four admitted requests share one
retrieval lane and two generation HTTP lanes. Results are held in process
memory for up to 15 minutes and use a staging-only DTO while semantic and
locator verification remain pending. Raw Gateway response files are confined
to request-scoped private scratch storage. The frozen Product Answer contract
and no-dispatch handler retain their existing behavior.

**Local evidence**

- `python -m pytest -q tests/phase3/api/test_arvan_live_dispatch.py tests/phase3/api/test_staging_preflight.py tests/phase3/api/test_staging_no_dispatch.py -rs`
  with Python 3.11 and a cache-only venv gave **27 passed, 1 skipped** (Linux
  pidfd test). Five subtests passed.
- With cached OpenSSL 3.5.9 first on PATH, `OPENSSL_CONF=/dev/null TMPDIR=/tmp
  python -m pytest -q tests/phase3/api/test_staging_private_asgi.py` gave
  **14 passed**. The initial default LibreSSL run failed at certificate setup.
  Cached OpenSSL also needed an explicit config path.
- The broader `python -m pytest -q --continue-on-collection-errors tests/phase3/api tests/phase3/contracts`
  recorded **232 passed, 10 skipped, 1 dependency failure and 20 errors**.
  Fourteen certificate setup errors were recovered in the focused rerun.
  Six collections still require PyJWT and one setup still requires cryptography.
  No dependencies were downloaded.
- With Node 22.16.0 in `apps/web`, `npm run typecheck`, `TMPDIR=/tmp npm test`
  and `npm run build` passed. The first Node test run used macOS's default
  temp path and hit two CI-store path guards. The corrected run passed
  **138 tests**. Build reported two existing filesystem-tracing warnings.
- `git diff --check`, `sh -n infra/arvan-staging/run-worker.sh`, `bash -n`
  on rollout command blocks, Python compilation and Keycloak Compose YAML
  parsing passed. `git hash-object infra/postgres/migrations/011_external_dispatch_claim.up.sql`
  matched the expected DB #56 blob. Docker service validation needs a Linux
  deployment test environment.

**Open and next action.** Explicit supervisor approval is pending for the
[exact rollout commands and preconditions](../../infra/arvan-staging/ROLLOUT.md).
Resolve host package and image reachability, Ubuntu/Keycloak pins, private
service-user material, PostgreSQL clone and least-privilege checks, and
certificate issuance before enabling the paid invited smoke. Confirm corpus
authorization, Gateway data/budget scope and two-account verification. No
Arvan mutation, benchmark, migration, provider request, or E2E staging test was
run. No Module 00/01, full security, durable live Product history, or 100-user
Gate is accepted.
