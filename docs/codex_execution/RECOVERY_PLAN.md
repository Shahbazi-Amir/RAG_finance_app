# Recovery plan

1. Select the backup revision and review its local manifest, checksum list and restore report. Confirm authorization and use isolated storage.
2. Check the encrypted artifacts against the manifest and verify authentication using the existing local key procedure. Extract into temporary storage and check the Git bundle, expected commit, file modes and SQLite integrity against the documented baseline.
3. For a separately authorized Docker drill, use a separate daemon and fresh volumes with the documented PostgreSQL major version. Review private Compose paths before starting anything. Test image loading, role restoration, physical and logical database recovery, and compare restored schemas and data to the expected baseline.
4. Run isolated service health and end-to-end checks for the authorized scope. Record commands, outcomes and limitations in the local evidence and publish a sanitized summary.
5. Obtain supervisor acceptance before treating the result as a recovery point. Preserve source volumes and originals during the drill.

The historical reports document component checks. Full recovery remains open. Container writable layers and Docker.raw are outside the documented backup coverage.

## Docker_3 — isolated logical restore

The disposable session database passed a custom dump and restore into a separate database. Conversation, message, Attempt and session-state counts and FORCE RLS and test-definer policy counts matched. Full rollback, physical recovery and immutable baseline restoration remain pending. Before restarting the isolated product stack, account for loss of tmpfs provisioning. [Commands and historical evidence](MAC_FIRST_START_FA.md#docker_3--بازیابی-پس-از-انتقال-حساب)

### NB23-SESSION-RESUME-11

A tmpfs restart replay exposed stale generated role setup. The three required grants now live in the guarded staging SQL used by the provisioning path. Apply it only to the verified disposable clone after restarting its PostgreSQL. Full frozen-stack recovery remains pending.

### NB23-SESSION-RESUME-12

If isolated API restarts and BFF cannot see its loopback listener, recreate only the disposable BFF and Bootstrap to attach to the current API network namespace, then restart the isolated edge. Verify both HTTPS routes before Chrome. This recovery was observed with status 200 and TLS verification 0.

### NB23-SESSION-RESUME-15

Keep the frozen C018 rollback intact. Stop only the independent nb23-session-product-local project and its dedicated temporary PostgreSQL when ending the local V4 test. Preserve the V4 ledger volume and pinned image. The full isolated start/stop drill remains pending.

### NB23-SESSION-RESUME-19

Version B keeps its running PostgreSQL while stopping or recreating isolated API, BFF and Worker services. The named SQLite volume retains retrieval outcomes. The operator procedure lives in the execution worktree at infra/nb23-v4/STAGING_RETRIEVAL.md. Full restore and accepted Freeze remain pending.

### NB23-SESSION-RESUME-22

The isolated API now starts independently of Worker warmup. Before an owner Send, confirm the WORKER_READY marker. Replaying an existing FAILED receipt was observed to leave the PostgreSQL deadline, Attempt count and isolated outcome unchanged.

### NB23-SESSION-RESUME-27

For a stopped Version B, restore its isolated PostgreSQL, start Keycloak first and wait for its private 8443 listener, then start the remaining project services. This order was exercised with one verified real retrieval. Preserve both stacks and existing volumes. Formal Freeze remains pending.

### NB23-SESSION-RESUME-28

Use the experimental-local-v4-product-fixes BFF tag for Version B. For this rollout only Bootstrap and BFF were recreated. Preserve the live Keycloak, PostgreSQL, API and Worker. Existing Chrome tabs require one sign-in after replacement so the new cookie and owner-bound correlation can be recovered.
