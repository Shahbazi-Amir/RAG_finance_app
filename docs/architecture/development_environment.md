# Development environment baseline — AGENT-ENV-01

**Status:** PARTIAL / FOR REVIEW. **Observed:** 2026-11-06, task executor only; not the employer's Mac. Repository baseline `main@81361c7c3781e0ca55dc66aee88f9c893606a7fd`, branch `prep/development-baseline`. No system/Mac/Phase2 environment modification.

## Observed executor (not a deployment or target requirement)

| Field | Actually observed | Interpretation |
|---|---|---|
| OS | Debian GNU/Linux 13 (trixie), Linux kernel 6.18.57 | Isolated task runner only |
| CPU architecture | x86_64 | Does not imply macOS architecture |
| Python | CPython 3.13.5 | Existing runtime, not freshly installed |
| Node / npm | Node.js 22.16.0 / npm 10.9.2 | Existing only; no JS packages installed |
| Python tooling | `uv 0.10.0`; pip present in executor base | uv used for offline diagnostic, pip prescribed for future isolated install |
| git / make | git 2.47.3 / GNU Make 4.4.1 | Used Make check; git observation does not imply local Mac status |
| Encoding / executor timezone | UTF-8 / UTC reported by Python | No OS locale or timezone changed |
| Docker, PostgreSQL, Qdrant, Redis | NOT_RUN / NOT_PINNED | No service checks or claimed deployments |

## Development series decision, based on official public sources (checked 2026-11-06)

- **Python 3.13** in `.python-version`: supported for security maintenance through **2029-10** according to [Python Developer's Guide versions](https://devguide.python.org/versions/). Local Python **3.13.5** was exercised. Exact Python patch is *not frozen* or installed by this mission.
- **Node.js 22** in `.nvmrc`: **Maintenance LTS** until **2027-04-30** according to the official [Node.js Release Working Group](https://github.com/nodejs/Release). The existing runner has **22.16.0**. This is a deliberately limited development baseline, **not** a long-term support decision; reassess Node 24/26 in the separately authorized Web implementation mission. Do not force-replace the executor runtime or infer any Mac runtime.
- **Next.js** [official install requirements](https://nextjs.org/docs/app/getting-started/installation) say Node >=20.9, so observed Node 22 meets this *documented minimum*, not a proof against an as-yet-unselected Next.js version. **Next.js + TypeScript and FastAPI remain approved stack choices**, but their exact package versions/dependencies are **PROPOSED FOR LATER REVIEW / NOT_INSTALLED**. Never create blank `package.json`, npm lock, FastAPI project or server from this manifest.
- Python test dependency management: existing `tests/phase3/contracts/requirements.txt` uses `jsonschema==4.26.0`; added **one root** `requirements-dev.lock` containing five exact observed distribution versions (including four transitives). A pip-compatible pinned snapshot, **not** a newly resolved, index-verified or wheel-hash-verified lock. [uv documentation](https://docs.astral.sh/uv/pip/compile/) explains dependency locking and reproducibility. No competing Node package manager or unneeded lockfile was introduced.

## Actual checks, failures and rechecks

**Source tested:** exact byte-equivalent contract Schema, Fixture and two Python test modules at accepted source `RAG_finance_app@81361c7c3781e0ca55dc66aee88f9c893606a7fd`; current source blob hashes checked against GitHub. The contract tests do not call a model, database, external API or service.

1. `UV_CACHE_DIR=.uv-cache uv pip sync --offline --python .venv/bin/python requirements-dev.lock` → **FAILED** (exit 1): `attrs==26.1.0` unavailable in the sandbox cache; network/official registry access unavailable. Therefore **fresh install from official index and cross-machine install reproducibility are NOT_VERIFIED**. Do not label this as PASS.
2. In a disposable `.venv` (no system-site-packages), copied the **pre-existing exact installed library and dist-info files** into the task-local venv for **test execution only**, without installation/download. First attempt failed with `ModuleNotFoundError: No module named 'attr'`; added the existing `attr` package directory belonging to `attrs` and retried.
3. `.venv/bin/python -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v` → **Ran 21 tests, OK (0 failures)**. Verified installed snapshot versions: `jsonschema==4.26.0`, `attrs==26.1.0`, `jsonschema-specifications==2025.9.1`, `referencing==0.37.0`, `rpds-py==2026.5.1`.
4. Second fresh venv `.venv_retest` using the same **offline local installed-file copy workaround**, then the same unittest command → **Ran 21 tests, OK (0 failures)**. This verifies local isolated *test execution twice*, **not reinstalling from official source**.
5. `make check` under `.venv` → **Ran 21 tests, OK**. `lint` and `typecheck`: **NOT_APPLICABLE** (no app source target). No project build, security scan, SBOM, RLS, model, CI workflow or Docker tested.

**Evidence:** versioned [Makefile](../../Makefile), [Python test pins](../../requirements-dev.lock), [original contract requirements](../../tests/phase3/contracts/requirements.txt), [contract tests](../../tests/phase3/contracts/test_contracts.py) and [cumulative mission checkpoint](../../coordination/tasks/AGENT-ENV-01.md). Local test logs/venvs/cache are not committed. External official distribution hashes and independent clean install are **NOT VERIFIED**.

## Environment variable, time and security policy — documented only

- `.env.example` intentionally includes **zero keys**, since the current isolated tests require **no env variables**. Never put passwords, API tokens, user IDs, private filesystem paths or real `.env` content in Git; `.gitignore` covers local env/venv/cache. No Auth/DB/model/host configuration selected.
- Text and JSON: **UTF-8**; preserve source/streaming whitespace and Unicode. Store/emit future machine timestamps as timezone-aware ISO 8601 in **UTC**; convert to the authenticated/selected user's IANA timezone only at presentation. Do not assume the developer host or end-user timezone or mutate OS timezone settings. This is a proposal pending API/DB review, not a live implementation.
- Toolchain wrappers: `make check` and `make test-contracts` run the **existing synthetic contract suite only**. Lint/typecheck targets are intentionally absent until code exists. `P3M02-A04` is **partial ignore/template hygiene only**; repository-wide historical secret scan or dependency/security scan is **NOT_RUN**.

## Status, exclusions and handoff

- **Partial evidence:** `P3M02-A01/A02/A03/A04/A06/A08/A10` below are in progress with the narrow subset implemented; they are **not accepted Gate completions**. **Still NOT_RUN:** `P3M02-A05` full dependency/secret scanning, `P3M02-A07` SBOM, `P3M02-A09` log redaction, plus PostgreSQL/Qdrant/Redis/Docker version selections and full Module 02 clean-build/security Gate.
- Reproduction on the employer's Mac is **NOT_RUN**. If Python 3.13 and Node.js 22 are already available, use the **copy-ready commands in root README**. Only a future authorized task may install/upgrade developer runtimes, choose Next/FastAPI version, set up Node project, Docker Compose, DB, model/host/Auth, security scanning or service execution.
- Runtime NB23 compatibility, accepted Phase 2 Release and Module 00 are **BLOCKED**. The approved technology stack does **not** authorize Module 01/02/18 Gate acceptance.
