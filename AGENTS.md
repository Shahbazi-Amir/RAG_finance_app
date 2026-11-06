# Agent instructions — RAG_finance_app

Supervisor: «مغز فاز سوم». This repo is in preparatory mode; never claim Module 00/01 Gate PASS from docs or synthetic fixtures.

## File ownership

- Foundation agent is sole editor of `coordination/phase3_checklist.md` and owns shared README, AGENTS, architecture/ADRs, coordination ownership/open decisions and contract-boundary docs.
- UI and database agents edit only **their own task records** under `coordination/tasks/` and their expressly assigned future code areas; API agent owns API-specific mission files and future API work. Cross-file changes require foundation coordination.
- Specialists cite existing `P3Mxx` IDs. Progress is recorded **once**, in the canonical checklist. Operational `P3OPxx` IDs are overlays, not new progress counts.

## Git, references and safety

- Inspect branch, HEAD, status and existing work first. Foundation's historical AGENT-FOUNDATION-01 work was restricted to `prep/foundation`; subsequent Foundation-owned tasks may write **only** on the specifically authorized mission branch (for AGENT-CONTRACTS-01: `prep/product-contracts-v1`); never write main or parent `AI-Agent-projects`, force-push, rewrite history or merge Draft PR.
- `RAG_finance` is strictly read-only. Manual Mac transfer was canceled by the user. Eight existing pinned reference copies are registered in `references/phase2/source_manifest.json`; do not change their bytes, re-copy them, or silently switch versions. A future update requires an explicit new source decision.
- Never introduce Secrets, PII, large notebook artifacts, model weights, cached data or indexes. No model API, purchase, paid operations, deploy, live migration or download.

## Evidence and handoff

Use statuses planned / active / blocked / review / accepted; keep implemented, tested and accepted distinct. Never tick a blocked or untested item. Add evidence link and test result before marking completion; record **supervisor approval separately**. Update owned mission checkpoint after meaningful batches only.

NB23 Draft request supports **only** `contract_version` and `question`. Do not assume history, filters, context, streaming, real source resolution or producer outcome mapping. `confidence: null` is not a score. Distinguish credited author, editorial supervisor and speaker; never fabricate page/timestamp and do not expose unauthorized sources. Isolate user data.

## Approved specialist checklist handoff (onboarding only)

- UI v1.1: `coordination/tasks/AGENT-UI-01.md`; DB v2: `coordination/tasks/AGENT-DB-01.md`. Their onboarding is accepted, but implementation waits for Foundation acceptance and an explicit specialist task/starting SHA. Use these exact DB IDs; avoid `AGENT-DATABASE-*` aliases.
- Ownership is path-specific in `coordination/ownership.md` (including namespaced tests; no exclusive owner for all integration tests). Shared Product schemas/contract paths, root configuration, and the canonical checklist are Foundation-only changes.
- Independent Mock/Fixture UI, history, and PostgreSQL design/testing may run after authorized missions without NB23 live readiness. Runtime integration and Module 00 remain blocked. Streaming/Cancellation are required by the roadmap, not verified producer features. Deletion does not depend on Export approval.

## Mandatory evidence with every task push — supervisor-wide rule

For **every future working push**, update the **same mission file** under `coordination/tasks/AGENT-<MISSION-ID>.md` **in the same meaningful change/commit**. This is a cumulative checkpoint ledger; do not open one new report per command. Preserve prior Git history; if an earlier push has incomplete documentation, close the gap in the **next related change**, never force-push/rewrite old commits.

Each meaningful checkpoint **must** record:

1. **Stable subtask ID** plus precise `P3Mxx` and source roadmap Module/section (and `P3OPxx` overlay, if relevant).
2. **Input version / starting baseline**: repository, branch, starting HEAD, source/contract/fixture versions actually used; distinguish live Git observations from user-reported local status.
3. **Implemented work** and exact changed paths, separately from tested/accepted.
4. **Decision and rationale**, especially any change relative to the previous proposal; do not silently override a frozen or pending decision.
5. **Exact check command or reproducible method**, real outcome and evidence path/link; machine-readable evidence, when necessary, belongs under the **task owner's permitted path** and is linked from the mission checkpoint. Never commit secrets, PII or large generated artifacts.
6. **Failures/errors, fix and re-check result** where they occurred. Never mark an unrun or blocked check as PASS.
7. **Open issues, external dependencies, next action** and any required supervisor decision.

**Evidence and Gate separation:** `implemented`, `tested`, `accepted` are independent fields. Mock/Fixture checks prove only the described local behavior; they do not verify NB23 producer, real citations, full security, Module 00 or live integration. Never tick blocked/unexecuted items. Only Foundation updates `coordination/phase3_checklist.md`; specialists report their canonical IDs and evidence for Foundation's reconciliation without double-counting. Supervisor acceptance remains separately recorded.

**Delivery convention:** Report mission branch, starting HEAD, new final HEAD/PR, changed files, exact checks/results, remaining dependencies and the list of canonical IDs/evidence ready for Foundation. The current commit's own SHA must **not** be written inside its own content; use Git history and the PR to map checkpoint to commit.
