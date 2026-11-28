# SPEC-P3-12 — Image hardening and CI evidence

**Production: NO-GO. Phase 4: LOCKED.**

## Scope and cause

Branch `phase3/completion`, baseline `c87d5ce98664c5c970dc93ca848254aa27083539`. The [baseline scan artifact](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46102067648) attributes 2 CRITICAL and 44 HIGH API findings to Debian 12 system packages and five HIGH findings to Python packages inherited from the base: msgpack, setuptools and urllib3. Web had 1 CRITICAL and 38 HIGH in Debian packages and ten HIGH in the base's bundled npm dependency tree: brace-expansion, ip-address, pacote, picomatch and sigstore. The critical package findings were zlib in both images and SQLite in API. The Python and web application lockfiles required no change.

The official Python 3.13 and Node 24 build images and the Ubuntu 26.04 runtime are pinned by digest in `infra/phase3_l1/Dockerfile.api` and `infra/phase3_l1/Dockerfile.web`. Each final image installs runtime system dependencies and applies available OS updates. API installs the hashed lock in a pip-free virtual environment, carries Python and its interpreter libraries, and checks standard-library imports with the final runtime libraries. Web copies the Node binary and built application with production dependencies. Existing non-root users, health checks and App-only boundaries remain in effect. The workflow, vulnerability severity policy, #143 controls and `infra/nb23-v4/` were unchanged.

## Verification

- `0d11b1d07e0e44fc77e4233a831b80ab7dac630a` switched to Debian 13 and removed build tooling from the runtime. [Run 46103333915](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46103333915) hit HTTP 429 pulling the base from ECR.
- `38f227ce1088eb3769b87bb108d4ef2ae305029a` pulled from Docker Hub. [Run 46103461544](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46103461544) passed six jobs. Trivy reported zero CRITICAL but 53 API and 50 Web HIGH findings in Debian 13 packages. The artifact listed no fixed version for those system findings and no HIGH/CRITICAL in the language packages.
- `0c757953f46ec0ce1fd63a22a8ede4b009356d47` separated build toolchains from the Ubuntu runtime. [Run 46103757931](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46103757931) passed **7/7**: `postgres-migrations-rls`, `postgres-populated-recovery`, `python-security-and-api`, `web-playwright-cross-browser (chromium)`, `web-playwright-cross-browser (firefox)`, `web-playwright-cross-browser (webkit)` and `staging-and-image-check`. The [image job](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46103757931/job/140851795910) verified revision labels and scan/image IDs and uploaded scan JSON.
- Local Web from `apps/web`: `npm run lint`, `npm run typecheck`, `TMPDIR=/tmp npm test` (143 passed) and `npm run build` passed. Build emitted two filesystem tracing warnings.
- Local Python with `/private/tmp/rag-arvan-pytest/bin/python -B -m unittest discover -s tests/phase3/contracts -p 'test_*.py'` passed 71 tests. Discovery under `tests/phase3/api` reported 180 tests, eight errors and ten skips in the available environment, including missing PyJWT and cryptography. Targeted `-B -m pytest -q -p no:cacheprovider tests/phase3/api/test_arvan_turn_policy.py` reported 18 passed and one failed on missing PyJWT. The hosted Python job passed with the hashed runtime dependencies. Local Docker daemon was unavailable.

| Image | Baseline CRITICAL / HIGH | Verified CRITICAL / HIGH | Other findings in verified scan |
| --- | --- | --- | --- |
| API | 2 / 49 | **0 / 0** | 50 MEDIUM, 5 LOW |
| Web | 1 / 48 | **0 / 0** | 39 MEDIUM, 5 LOW |

## Gate disposition and release queue

| Gate | Before | After | Acceptance evidence still open |
| --- | --- | --- | --- |
| P3M02 | PARTIAL | PARTIAL | Exact-source SBOM, complete secret/dependency review and M01 acceptance. |
| P3M18 | PARTIAL | PARTIAL | Cross-build reproducibility and restart with durable state. |
| P3M21 | PARTIAL | PARTIAL | Target security/privacy assessment, incident runbook acceptance and M20. |
| P3M01, P3M03–P3M06, P3M16, P3M19 | PARTIAL | PARTIAL | Remaining criteria as itemized in the [P3-11 report](SPEC-P3-11-app-gates-closure-and-nb23-pin.md). |

Across 26 Gates, **DONE 0 / PARTIAL 22 / PENDING 4**. The Qdrant Snapshot Reuse and UI-polish work is recorded as **QUEUED — MANDATORY BEFORE NEXT ARVAN RELEASE** in [Project State](../PROJECT_STATE.md) for execution after the Phase 3 rail closes.
