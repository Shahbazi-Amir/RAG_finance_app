# Phase 3 execution history

- [Starting baseline](BASELINE.md)
- [Chronological work log](WORK_LOG.md)
- [وضعیت بکاپ](BACKUP_STATUS_FA.md)
- [Recovery plan](RECOVERY_PLAN.md)
- [Current status](CURRENT_STATUS.md)

At the end of each Phase 3 mission, use a separate worktree on the report branch `codex` in the independent RAG_finance_app repository. Verify the push destination and permissions, and continue from the current branch tip. Append a dated work-log entry with the mission ID, starting and final refs, actions, errors, fixes, exact checks, evidence, open dependencies and next action. Update current status and the Persian report, keeping the initial baseline and historical entries. Refresh the local RTL HTML beside the Persian Markdown in the secure backup folder.

Update the authorized mission checkpoint in the same working commit. Record implemented, tested and supervisor acceptance separately. Stage only reviewed, sanitized report text for the reporting branch. Keep private paths, backups, dumps, credentials, configuration contents and raw logs out of Git. Commit with mission ID and ISO date, push without force, and check the remote ref. Preserve earlier commits. The Foundation checklist remains canonical for roadmap progress.

Display this ASCII dashboard in Codex at mission close. List only applicable task lines. Use PARTIAL for incomplete verification and record the precise scope in the full report.

```text
MISSION: <name>

[PASS] Completed task
[PASS] Verified task
[PARTIAL] Incomplete task
[BLOCKED] Blocked task

BACKUP: PASS / PARTIAL / FAIL
RESTORE TEST: PASS / PARTIAL / FAIL
DOCKER: READY / NOT READY / NOT CHECKED
API: READY / NOT READY / NOT CHECKED
C018: VERIFIED / NOT VERIFIED / NOT CHECKED
GIT REPORT PUSH: PASS / FAIL / SKIPPED

NEXT STEP: <one clear action>
```
