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
