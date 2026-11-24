# Recovery plan

1. Select the backup revision and review its local manifest, checksum list and restore report. Confirm authorization and use isolated storage.
2. Check the encrypted artifacts against the manifest and verify authentication using the existing local key procedure. Extract into temporary storage and check the Git bundle, expected commit, file modes and SQLite integrity against the documented baseline.
3. For a separately authorized Docker drill, use a separate daemon and fresh volumes with the documented PostgreSQL major version. Review private Compose paths before starting anything. Test image loading, role restoration, physical and logical database recovery, and compare restored schemas and data to the expected baseline.
4. Run isolated service health and end-to-end checks for the authorized scope. Record commands, outcomes and limitations in the local evidence and publish a sanitized summary.
5. Obtain supervisor acceptance before treating the result as a recovery point. Preserve source volumes and originals during the drill.

The historical reports document component checks. Full recovery remains open. Container writable layers and Docker.raw are outside the documented backup coverage.

## Docker_3 — isolated logical restore

The disposable session database passed a custom dump and restore into a separate database. Conversation, message, Attempt and session-state counts and FORCE RLS and test-definer policy counts matched. Full rollback, physical recovery and immutable baseline restoration remain pending. Before restarting the isolated product stack, account for loss of tmpfs provisioning. [Commands and historical evidence](MAC_FIRST_START_FA.md#docker_3--بازیابی-پس-از-انتقال-حساب)
