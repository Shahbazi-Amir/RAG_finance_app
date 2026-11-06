# AGENT-CONTRACTS-01 — provisional product contract v1

**Status:** `READY_FOR_REVIEW` (foundation contracts preparation only; **NOT ACCEPTED**). **Repo:** `Shahbazi-Amir/RAG_finance_app`. **Starting main HEAD:** `2f59c3e3d571aedeef907b944b8273762338cf4e`. **Task branch:** `prep/product-contracts-v1` (Draft PR only). Parent `RAG_finance` stays read-only.

## Checklist — accepted as an executed documentation/test task only, NOT Module 03 Gate

| ID | Canonical map | Deliverable | Evidence/check | Implementation | Acceptance |
|---|---|---|---|---|---|
| CT-01 | P3M03, P3M13; UI-02, DB01-04A | Shared product v1 JSON Schema with one `$defs` registry | `packages/contracts/product.v1.schema.json`; `Draft202012Validator.check_schema` | implemented | supervisor pending |
| CT-02 | P3M03, P3M04, P3M06, P3M15 | Conversation/Message/Answer/Feedback ownership and references | snapshot and consistency tests | implemented/tested locally | supervisor pending |
| CT-03 | P3M03, P3M10, P3M13; UI-06, DB01-10A | Send request, trusted-user boundary and idempotency receipt | fingerprint, replay, conflict, owner scope tests | implemented/tested locally | supervisor pending |
| CT-04 | P3M11, P3M14; UI-08, DB01-04A | Claim/Citation two-way references and independent attribution roles | synthetic unresolved-source positive/negative tests | implemented/tested locally | supervisor pending |
| CT-05 | P3M10, P3M12, P3M14; UI-07 | Confidence null/error/no-answer/partial/unknown distinction | schema + semantic failure cases | implemented/tested locally | supervisor pending |
| CT-06 | P3M13, P3M14; UI-10 | Proposed Streaming completion/error/cancel events | stream order, exclusive terminal and server/display distinction tests | implemented/tested locally | supervisor pending |
| CT-07 | P3M15, P3M21; UI-05, UI-13, DB01-11, DB01-13 | Pagination, deletion request and confirmation states | page ownership, deletion success without Export tests | implemented/tested locally | supervisor pending |
| CT-08 | P3M03; P3M00 remains blocked | Synthetic positive/negative fixture suite and runnable tests | 22 positive, 40 negative fixture validations; 12 unittest methods pass | tested locally, synthetic only | supervisor pending |

**Canonical progress:** the table describes this **task** only. No ticks or status changes to `coordination/phase3_checklist.md`; P3M03 Gate is **not** frozen/passed. UI/DB specialist tasks remain separate, and these tests do not count their implementation progress.

## Checkpoint A — repository and dependencies

- Inspected `main`/HEAD, `AGENTS.md`, ownership, main checklist and approved UI v1.1 / DB v2 task records. Starting `main` matched the requested SHA. The task branch and PR did not exist before this mission, so no previous implementation was replaced.
- Source requirements preserve NB23 Draft `question+contract_version` only. Product history/filter/context and Streaming do not imply accepted NB23 support.
- No dependency installed. Authoring-container Python 3.13.5 and preinstalled `jsonschema==4.26.0` were used. No user Mac/environment or Phase 2 modifications.

## Checkpoint B — machine-readable contract and tests

- One draft-2020-12 machine-readable schema (`23` shared `$defs`, `14` wire-document kinds), one SYNTHETIC fixture set (`62` cases), 2 Python test files (`test_contracts.py` and `semantics.py`) and pinned `requirements.txt` (for optional isolated venv).
- **Actual command:** `python -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v` from task workspace root.
- **Actual result:** `Ran 12 tests in 0.242s — OK` (all 62 fixtures assessed inside suite: 22 expected valid accepted, 40 invalid rejected; 0 failed test methods).
- Verified a real SHA-256 canonical message request fingerprint is used in the synthetic receipt; idempotency scope and cross-user checks execute without runtime.
- **No external calls, Secret access, model download, paid operations, migration, DB or UI deployment.** Tests are synthetic L1 contract/relationship evidence only; no backend, RAG runtime, producer or final module Gate acceptance.

## Current provisional/blocked and next checkpoint

- `provenance.rag_binding.status=provisional`, `blocked_by=NB23`, `release_id=null`, `adapter_verified=false` in synthetic fixtures. Citation resolver, source identity/locator/author/roles from real sources, producer status, streaming/cancellation server confirmation and real confidence calibration: **BLOCKED_BY_NB23** for L2 integration.
- Decisions open: Auth method, consent, retention, Export scope, provider/hosting, idempotency TTL/error transport, streaming event transport/recovery, budget/SLO and runtime provenance. Deletion contract is independent of Export.
- **Next:** verify remote GitHub blob content and all source paths, open Draft PR against `main`, then return to supervisor. Do not change references, product code or main; do not merge.

## Checkpoint C — Supervisor-wide evidence/push policy applied

- **Subtask:** `CT-DOC-01` (documentation and delivery governance), cross-reference `P3M03` — [phase3 modular plan Module 03, activities 7–9 and Gate](../../references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md); `P3M19` — same plan Module 19, release/test evidence requirements. This does **not** mark either Gate accepted.
- **Input version and starting baseline:** `RAG_finance_app` branch `prep/product-contracts-v1`, prior task HEAD `95f0f2e257e290cd0974951d80b65ee3096a2b84`; `main` observed at `2f59c3e3d571aedeef907b944b8273762338cf4e`. Existing product schema `product.v1`, SYNTHETIC fixtures, Python test suite and prior checkpoint preserved. This checkpoint is a **documentation-only follow-up** to the supervisor's global instruction.
- **Implemented:** appended mandatory per-push cumulative checkpoint/evidence policy to `AGENTS.md`; updated contract handoff instructions in `packages/contracts/README.md`; appended this checkpoint in `coordination/tasks/AGENT-CONTRACTS-01.md`. No changes to `product.v1.schema.json`, fixtures, tests, user-facing product code, `references/phase2/` or canonical Phase 3 checklist.
- **Decision / rationale:** accept supervisor's rule for all future mission pushes, including this push; do not retroactively rewrite older commits. Replace the historical `prep/foundation`-only instruction with a branch-by-current-authorized-mission restriction, preserving main and read-only parent repositories. Use the existing mission ledger and existing machine-readable task-owned artifacts; no redundant per-command report.
- **Checks/method and expected evidence:** check exact allowed changed paths with GitHub commit compare; inspect that AGENTS and contract handoff link to this cumulative record; confirm no checkbox/gate change and no reference/schema/test edit. New code tests are **NOT_RUN** for this documentation-only change; the **previously recorded** 12 local synthetic tests are historical evidence, **not** new test execution. The GitHub PR/commit diff is the evidence for this checkpoint.
- **Errors / fixes / rechecks:** no error or recheck claimed before remote verification; if the remote check identifies an issue, append a correction to this same mission file in a subsequent related change.
- **Open / next:** supervisor review of Draft PR, provisional NB23 runtime mapping, undecided Auth/Retention/Export/provider/transport, and separate L2 integration tests. Report canonical IDs and task-owned evidence to Foundation, not a self-approved Module Gate.
- **Acceptance accounting:** implemented = documentation update after GitHub recording; tested = document/diff checks only (pending remote verification at drafting time); accepted = supervisor pending. No product or NB23 Gate accepted.

## Checkpoint D — Completed remote evidence for CT-DOC-01

- **Subtask / source:** `CT-DOC-01` → `P3M03` (Phase 3 modular roadmap, Module 03 activities 7–9, contract compatibility/dependency governance), `P3M19` (Module 19 test/release evidence); these references are links for Foundation reconciliation, **not** Gate completions.
- **Verified input baseline:** previous branch HEAD `95f0f2e257e290cd0974951d80b65ee3096a2b84`; documentation-policy update commit `16f45055bcf414ed79caade9cf7f949ce0debd49`. `main` remains at starting `2f59c3e3d571aedeef907b944b8273762338cf4e` at the time of this check.
- **Actual method and result:** GitHub `compare_commits(base=95f0f2e..., head=16f4505...)` plus `fetch_file` and recursive Git tree for that commit. **PASS (documentation scope):** exactly 3 changed files — `AGENTS.md`, `packages/contracts/README.md`, `coordination/tasks/AGENT-CONTRACTS-01.md`; all reside in the authorized Foundation task scope. AGENTS contains the cumulative checkpoint rule, the contracts README contains the delivery/evidence link, and the mission checkpoint exists. The referenced files and roadmap link resolve in the GitHub tree. No `references/phase2/**`, product Schema, SYNTHETIC Fixture or test source was changed; PR #4 remains Draft/unmerged. **Evidence:** [GitHub compare](https://github.com/Shahbazi-Amir/RAG_finance_app/compare/95f0f2e257e290cd0974951d80b65ee3096a2b84...16f45055bcf414ed79caade9cf7f949ce0debd49) and [Draft PR #4](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/4).
- **Errors / corrections:** none observed in the remote structural check. This is a historical check on the referenced update, not a claim that code tests were repeated.
- **Implementation / tested / accepted:** implemented = policy, delivery, mission ledger; tested = GitHub document/path/compare checks only; product and NB23 runtime tests = NOT_RUN for this update; accepted = pending supervisor review. The earlier 12 synthetic unit tests belong to the original package checkpoint, not to this policy change.
- **Open / next:** keep one cumulative mission ledger for future working pushes and provide `CT-01..CT-08`, `CT-DOC-01`, their canonical `P3Mxx` mapping, test command/results and task-owned evidence paths to Foundation; no canonical checklist edit, no Model API/migration/deploy and no Phase 2/Module 00 acceptance.

## Checkpoint E — Exact three contract regressions (source: approved supervisor correction)

**State:** implemented and locally tested; **NOT ACCEPTED** by supervisor; no `P3M00` or `P3M03` Gate tick. **Starting input:** `RAG_finance_app@c1a1257ea49641f78531af7c959877e024c4c1b6`, branch `prep/product-contracts-v1`, provisional product `product.v1`, pinned source roadmap `RAG_finance@7c74783c3dcda897b010ba9ea358d113f172ed1f`. These are task-local edits only; `main` remained at `2f59c3e3d571aedeef907b944b8273762338cf4e` before commit.

- **CT-FIX-01 → P3M13 / P3M14, phase3 modular roadmap Modules 13 (API Streaming/Cancellation) and 14 (UI stream states):** changed `packages/contracts/product.v1.schema.json` **delta-only** rule from non-whitespace pattern to `minLength:1`; existing final `answer_text` and ordered/terminal-event invariants unchanged. Added whitespace/newline/empty-delta and exact concatenation regressions to `tests/phase3/contracts/test_contracts.py` and `packages/contracts/fixtures/product.v1.cases.json`. **Reason:** whitespace-only chunks were incorrectly rejected and would corrupt exact stream reconstruction.
- **CT-FIX-02 → P3M03 / P3M10 / P3M13, modular roadmap Modules 03, 10, 13; DB01-04A/DB01-10A and UI-02/UI-10 consumer review needed:** renamed client `conversation_id` to `requested_conversation_id`; receipt now carries separate `requested_conversation_id` and `resolved_conversation_id`. Updated `tests/phase3/contracts/semantics.py` fingerprint/history/request-receipt checks to use **original requested ID**, enforce stable server-assigned conversation and message IDs across retries, existing-thread equality, conflict and trusted-user separation. Adjusted existing Fixture hashes and added new-thread/replay/conflict cases. **Reason:** old direct ID equality rejected valid new-thread server allocation. This is a breaking change within a **provisional**, not frozen, product.v1 contract; downstream API/UI/DB review still required. Exactly-once model execution is NOT guaranteed.
- **CT-FIX-03 → P3M11 / P3M14; P3M00 remains blocked, modular roadmap Modules 11/14 locator/attribution:** added explicit `source_type` and `book_anchor` (work+edition+stable anchor, no page) and `transcript_segment` (episode+segment anchor, no timestamp) while retaining existing URL, book_page and transcript_timestamp variants. Schema blocks mismatched type/locator. Unresolved metadata may remain known without resolved locator; verified locator and verified attribution are independent. Synthetic provenance cannot claim verified locator **or** attribution. Added positive/negative source-format and source-metadata regressions. **Reason:** source anchor variants and separately known metadata were incorrectly excluded.

**Changed paths (this single correction package):** `packages/contracts/product.v1.schema.json`, `packages/contracts/fixtures/product.v1.cases.json`, `tests/phase3/contracts/semantics.py`, `tests/phase3/contracts/test_contracts.py`, `packages/contracts/README.md`, `coordination/tasks/AGENT-CONTRACTS-01.md`. No `references/phase2/**` or canonical checklist changes.

**Actual verification and evidence:** created a disposable task-local `.venv`, reused an isolated copy of preinstalled `jsonschema==4.26.0` and dependencies without network or global installation. Command from repository-shaped task workspace:
```bash
.venv/bin/python -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v
```
**Result:** `Ran 15 tests in 1.390s — OK`, zero failures; 74 Fixture cases evaluated (31 expected-valid accepted; 43 expected-invalid rejected). See [Schema](../../packages/contracts/product.v1.schema.json), [SYNTHETIC Fixture cases](../../packages/contracts/fixtures/product.v1.cases.json), [semantic invariants](../../tests/phase3/contracts/semantics.py) and [executable regressions](../../tests/phase3/contracts/test_contracts.py) as machine-readable/reproducible evidence. The four GitHub blobs for these files were checked to have **exact byte-equivalent Git hashes** to the tested local files before commit.

**Errors, corrections, retests:** the initial disposable venv lacked `jsonschema` (`ModuleNotFoundError`); it was populated **locally** from already-installed pinned distribution files, never via external/network install or global modifications. A transitional run had 3 failures because old test/Fixture assumptions rejected newly permitted unresolved metadata and required pre-change receipt matching; the Fixture was explicitly reclassified, receipt conflict test updated and source-type test made schema-valid so the semantic rejection was observable. Full regression suite then passed (15/15), including the earlier healthy 12 tests.

**Implemented / tested / accepted:** implemented = only provisional product Schema/Fixture/validator/tests/README changes; tested = isolated synthetic contract tests above; accepted = **supervisor pending**. These tests neither prove real NB23 compatibility nor source authenticity, model outcome, real stream cancellation, DB persistence/RLS or deployed security.

**Open and next:** keep `product.v1` provisional; request API/UI/DB review of breaking requested/resolved conversation field naming and idempotency semantics; confirm server event transport/real cancellation and source locator/metadata authority from accepted NB23, without choosing Auth/Retention/Export/model/provider/SLO. Deliver this Draft PR #4 for review; no merge, migration, paid service or edits to read-only repositories.
