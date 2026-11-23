# CODEX-REPORTING-01

## 2026-11-23 / CODEX-REPORTING-01-01

Status is review. Supervisor approval is pending.

- Roadmap evidence reference is P3M22-A06 and operational P3OP11-R07, launch checklist backup and restore. This reporting mission adds no roadmap completion credit.
- Baseline is Shahbazi-Amir/RAG_finance_app, report branch codex created at 67ffa71f4dc43b29e8df7b74bd40f7bd16875cde. Existing backup report revisions and evidence provenance are in the [baseline](../../docs/codex_execution/BASELINE.md).
- Implemented files are this checkpoint and README.md, BASELINE.md, WORK_LOG.md, BACKUP_STATUS_FA.md, RECOVERY_PLAN.md and CURRENT_STATUS.md under docs/codex_execution. A separate worktree protects the working checkout. Sanitized summaries preserve the historical evidence while keeping operational artifacts local.
- Git identity, access retry and verification methods are recorded in the [work log](../../docs/codex_execution/WORK_LOG.md). Runtime and restore testing were outside this mission. Git history and remote ref inspection identify the publication.
- Remaining dependency is authorization for isolated full-stack recovery verification. Supervisor acceptance is separate.

### MAC-FIRST-START-01

- P3M22-A06 / P3OP11-R07, launch checklist backup and restore. No completion credit.
- Baseline: RAG_finance_app detached at 67ffa71f4dc43b29e8df7b74bd40f7bd16875cde. Reporting branch codex started at 552ab762736dfb9df3d6c428e056cec0b282d9d6. Backup sets 20261122T225147Z and 20261122T230515Z-docker. Live API image 2de6c25d8bd1.
- Implemented operationally: started the existing demo-db and retried the existing API. Added the Persian Markdown and RTL HTML reports under docs/codex_execution. Tested: both SHA256SUMS lists passed, demo-db became healthy and pg_isready accepted connections, original API repeated exit 78. Supervisor acceptance pending.
- Diagnostic helper failed to import with PermissionError. docker diff and metadata comparison confirmed the original has application changes in its writable layer. Retain the existing container pending a recoverable baseline. The API denial within the original remains unresolved.
- Commands, rollback, evidence and dependencies are in [the Persian report](../../docs/codex_execution/MAC_FIRST_START_FA.md). Isolated full restore and end-to-end retrieval remain open.

### MAC-FIRST-START-01 — writable-layer and API correction

- P3M22-A06 / P3OP11-R07, launch checklist backup and restore. Reports start at 84d58b1. Product execution branch ops/mac-first-start starts at 5fe21e9 and carries local 4752c2b.
- Implemented: encrypted inspect/diff, local snapshot 6c6a05dcd26a and offline permission/readiness correction in infra/mac-first-start/{Dockerfile.api,compose.api.yaml}; updated both Persian reports. API container and original volumes retained.
- Tested: Compose resolves seven services with profiles enabled. Snapshot diagnostic reproduced protected-schema PermissionError after config and read-only preflight; fixed build imports schema under UID 11001. Restore archive pipeline, fixed runtime check and supervisor acceptance remain open.
- [Reproducible evidence and rollback context](../../docs/codex_execution/MAC_FIRST_START_FA.md). No gated completion credit.
