# RAG_finance_app

Phase 3 **preparation** repository for a multi-user evidence-based financial education chat. This is not a working or launched service. Phase 2 Release and NB23 handoff are **not accepted** (`accepted_for_phase3=false`, `formal_readiness=BLOCKED`).

## Start

Read `AGENTS.md`, `coordination/ownership.md`, `coordination/phase3_checklist.md`, `docs/architecture/overview.md` and `packages/contracts/README.md`. Check existing work, use assigned branch/paths, record evidence in owned task records, and leave all supervisor Gate approvals pending.

The current source version is `Shahbazi-Amir/RAG_finance@7c74783c3dcda897b010ba9ea358d113f172ed1f`. The eight existing source copies are documented in [`references/phase2/source_manifest.json`](references/phase2/source_manifest.json) with source commit, Git Blob SHA and SHA-256. User confirms the `660566e` bundle is present on the Mac with a clean working tree. GitHub-side integrity was checked separately; local Mac files were not inspected by this agent. No manual transfer or repeated copy is required.

**MVP:** auth/consent, chat with Citation/Attribution, no-answer/safety, history, feedback, privacy and basic operations. **Phase 4 excluded:** exams, personal financial profile, coaching, action plans, extensive administration. No model, server, auth provider, retention, budget, SLO or capacity has been selected.

## Agent handoff and verification

- **API:** draft product envelope/adapter boundaries only; see [contract README](packages/contracts/README.md) and [ownership](coordination/ownership.md).
- **Database:** prepare isolated data model and consent/retention decision points without a migration.
- **UI:** prepare RTL, source-aware chat and failure-state designs without implying live NB23 streaming/Citation support.
- **Foundation:** sole editor of the [canonical checklist](coordination/phase3_checklist.md) and [checkpoint](coordination/tasks/AGENT-FOUNDATION-01.md).

No **product service** start command is provided because no API, database or UI implementation exists. The authorized **synthetic contract-test-only** development command is documented below. Inspect repository status on each worker's own machine; GitHub verification is not a local Git health check.

## Approved checklist onboarding (no implementation)

The approved [UI v1.1 task checklist](coordination/tasks/AGENT-UI-01.md) and [DB v2 task checklist](coordination/tasks/AGENT-DB-01.md) are recorded, but both remain `ONBOARDING_ACCEPTED — IMPLEMENTATION_WAITING_FOR_FOUNDATION`. Read [ownership boundaries](coordination/ownership.md) before creating specialist implementations. A separate approved mission may later authorize independent UI/History/PostgreSQL Mock/Fixture tests; real model/RAG integration and Module 00 acceptance remain blocked. Streaming/Cancellation remain required but not verified. Account/data deletion is independent of Export scope approval.

## AGENT-ENV-01 — contract-test-only development baseline (not a product runtime)

- Development series: **Python 3.13** (`.python-version`) and **Node.js 22 LTS** (`.nvmrc`); these are *major/minor-family selectors*, not frozen patch versions. The task runner actually had Python 3.13.5, Node.js 22.16.0, npm 10.9.2. This is **not an observation of the employer's Mac**. Node 22 LTS has limited remaining support; review a future upgrade in the web implementation mission.
- The **only installed Python development dependency required for the current executable code** is `jsonschema` and its four transitive libraries; exact snapshot pins are in `requirements-dev.lock`. The original test requirement remains in `tests/phase3/contracts/requirements.txt`. No Node packages or frontend code exist; therefore no `package.json`, npm lockfile, Next.js or FastAPI install has been manufactured. npm remains the candidate Node manager *if/when* a separately authorized UI project is created.
- Minimal env template: `.env.example` deliberately has no variables; contract tests do not need model/Auth/DB/host settings. Real `.env*` and local venv/cache files are ignored; this is not proof of a full repository secret scan.
- **Mac/local commands, only if Python 3.13 and Node 22 are already available:**

```sh
python3 --version
node --version
npm --version
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.lock
make check
```

These commands create **only a local virtual environment and run synthetic contract tests**; they do not run the product. Do not install runtimes or modify a Mac just to match these notes. If registry installation is blocked, **do not report reproduction as PASS**. `make check` intentionally runs contract tests only; lint/typecheck are `NOT_APPLICABLE` until source targets exist. `Makefile` assumes `.venv/bin/python`; it must fail if the env is missing.

See [development environment manifest and real evidence](docs/architecture/development_environment.md) and [ENV checkpoint](coordination/tasks/AGENT-ENV-01.md). **No Docker Compose, database, FastAPI or Next.js service was installed or started.** Module 02 Gate remains pending; NB23/Module 00 blocked.
