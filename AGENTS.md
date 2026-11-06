# Agent instructions — RAG_finance_app

Supervisor: «مغز فاز سوم». This repo is in preparatory mode; never claim Module 00/01 Gate PASS from docs or synthetic fixtures.

## File ownership

- Foundation agent is sole editor of `coordination/phase3_checklist.md` and owns shared README, AGENTS, architecture/ADRs, coordination ownership/open decisions and contract-boundary docs.
- UI and database agents edit only **their own task records** under `coordination/tasks/` and their expressly assigned future code areas; API agent owns API-specific mission files and future API work. Cross-file changes require foundation coordination.
- Specialists cite existing `P3Mxx` IDs. Progress is recorded **once**, in the canonical checklist. Operational `P3OPxx` IDs are overlays, not new progress counts.

## Git, references and safety

- Inspect branch, HEAD, status and existing work first. Foundation changes allowed only on `prep/foundation`; never write main or parent `AI-Agent-projects`, force-push, rewrite history or merge Draft PR.
- `RAG_finance` is strictly read-only. Manual Mac transfer was canceled by the user. Eight existing pinned reference copies are registered in `references/phase2/source_manifest.json`; do not change their bytes, re-copy them, or silently switch versions. A future update requires an explicit new source decision.
- Never introduce Secrets, PII, large notebook artifacts, model weights, cached data or indexes. No model API, purchase, paid operations, deploy, live migration or download.

## Evidence and handoff

Use statuses planned / active / blocked / review / accepted; keep implemented, tested and accepted distinct. Never tick a blocked or untested item. Add evidence link and test result before marking completion; record **supervisor approval separately**. Update owned mission checkpoint after meaningful batches only.

NB23 Draft request supports **only** `contract_version` and `question`. Do not assume history, filters, context, streaming, real source resolution or producer outcome mapping. `confidence: null` is not a score. Distinguish credited author, editorial supervisor and speaker; never fabricate page/timestamp and do not expose unauthorized sources. Isolate user data.

## Approved specialist checklist handoff (onboarding only)

- UI v1.1: `coordination/tasks/AGENT-UI-01.md`; DB v2: `coordination/tasks/AGENT-DB-01.md`. Their onboarding is accepted, but implementation waits for Foundation acceptance and an explicit specialist task/starting SHA. Use these exact DB IDs; avoid `AGENT-DATABASE-*` aliases.
- Ownership is path-specific in `coordination/ownership.md` (including namespaced tests; no exclusive owner for all integration tests). Shared Product schemas/contract paths, root configuration, and the canonical checklist are Foundation-only changes.
- Independent Mock/Fixture UI, history, and PostgreSQL design/testing may run after authorized missions without NB23 live readiness. Runtime integration and Module 00 remain blocked. Streaming/Cancellation are required by the roadmap, not verified producer features. Deletion does not depend on Export approval.
