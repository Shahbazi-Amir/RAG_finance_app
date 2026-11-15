#!/usr/bin/env bash
# DB55: synthetic backup restored to a disposable PostgreSQL17 database.
# Never Arvan/staging; no external DSN or Gateway.
set -euo pipefail
if [[ "$CI" != true || "$GITHUB_ACTIONS" != true || "$GITHUB_REF" != "refs/heads/agent/db55-staging-execution-package" || "$PGHOST" != "127.0.0.1" || "$PGPORT" != 5432 ]]; then
  echo DB55_REFUSE_NON_DISPOSABLE_RUNTIME >&2; exit 71
fi
TEST_DB=db55_restore_clone
ROOT=infra/postgres/staging
VERIFY="$ROOT/db55_verify_staging.sql"
GRANT_SQL="$ROOT/db55_no_dispatch_bridge.sql"
REVOKE_SQL="$ROOT/db55_rollback_auth_bridge.sql"
CAPTURE="$RUNNER_TEMP/db55_test_capture.log"
test -s "$RUNNER_TEMP/db55_synthetic_backup.dump"
test -f "$VERIFY" && test -f "$GRANT_SQL" && test -f "$REVOKE_SQL"
unset PGDATABASE PGUSER
snapshot() {
  local n
  n=$(PGUSER=postgres PGPASSWORD=synthetic_pg17_only psql -XAt -v ON_ERROR_STOP=1 -d "$TEST_DB" -c "SELECT count(*) FROM history_l1.conversations WHERE owner_id='db55_synthetic_backup_owner' AND id='db55_synthetic_backup_conv'")
  if [[ "$n" != 1 ]]; then echo DB55_SYNTHETIC_RESTORED_ROW_LOST >&2; exit 4; fi
}
audit() {
  local phase="$1"
  PGUSER=db55_auditor PGPASSWORD=synthetic_auditor_only \
    psql -X -v ON_ERROR_STOP=1 -v "db55_phase=$phase" -d "$TEST_DB" -f "$VERIFY"
}
fail_marker() {
  local phase="$1" marker="$2"
  if audit "$phase" > "$CAPTURE" 2>&1; then
    echo "DB55_UNEXPECTED_AUDIT_PASS $phase" >&2; exit 5
  fi
  if ! grep -Fq "$marker" "$CAPTURE"; then
    echo "DB55_WRONG_AUDIT_FAILURE $phase" >&2; tail -25 "$CAPTURE" >&2; exit 6
  fi
  echo "DB55_EXPECTED_DENIAL_"$phase"_"$marker"_PASS"
}
pass_marker() {
  local phase="$1"
  if ! audit "$phase" > "$CAPTURE" 2>&1; then
    echo "DB55_UNEXPECTED_AUDIT_FAIL $phase" >&2; tail -30 "$CAPTURE" >&2; exit 7
  fi
  if ! grep -Fq "DB55_"$phase"_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS" "$CAPTURE"; then
    echo "DB55_NO_PASS_MARKER $phase" >&2; tail -25 "$CAPTURE" >&2; exit 8
  fi
  echo "DB55_READONLY_AUDIT_"$phase"_PASS"
}
auth_file() {
  PGUSER=auth_migrator PGPASSWORD=synthetic_auth_migrator_only \
    psql -X -v ON_ERROR_STOP=1 -d "$TEST_DB" -f "$1" > "$CAPTURE" 2>&1 || {
       echo "DB55_AUTH_SCRIPT_FAILED $1" >&2; tail -25 "$CAPTURE" >&2; exit 9;
    }
}
history_file() {
  PGUSER=history_migrator PGPASSWORD=synthetic_history_migrator_only \
    psql -X -v ON_ERROR_STOP=1 -d "$TEST_DB" -f "$1" > "$CAPTURE" 2>&1 || {
       echo "DB55_HISTORY_SCRIPT_FAILED $1" >&2; tail -25 "$CAPTURE" >&2; exit 10;
    }
}
deny_table() {
  local role="$1" pwd="$2" table="$3"
  if PGUSER="$role" PGPASSWORD="$pwd" psql -X -v ON_ERROR_STOP=1 \
    -d "$TEST_DB" -At -c "SELECT count(*) FROM $table" > "$CAPTURE" 2>&1; then
    echo "DB55_DIRECT_SELECT_ALLOWED $role $table" >&2; exit 11
  fi
  grep -Eiq "permission denied|does not exist" "$CAPTURE" || {
    echo "DB55_WRONG_DIRECT_ERROR $role" >&2; tail -18 "$CAPTURE" >&2; exit 12;
  }
  echo "DB55_DIRECT_DENIED_"$role"_"$table"_PASS"
}
snapshot
deny_table db55_auditor synthetic_auditor_only auth_l1.sessions
deny_table db55_auditor synthetic_auditor_only history_l1.messages
echo DB55_SYNTHETIC_BACKUP_RESTORE_WITH_SEEDED_ROW_PASS
fail_marker session_core DB55_MISSING_APPROVED_004_005_003_BRIDGE_GRANTS
fail_marker private_no_dispatch DB55_MISSING_APPROVED_004_005_003_BRIDGE_GRANTS
fail_marker live_011 DB55_MISSING_APPROVED_004_005_003_BRIDGE_GRANTS
# A machine-checked PRE-state, only on synthetic restored database.
PGUSER=postgres PGPASSWORD=synthetic_pg17_only psql -XAt -v ON_ERROR_STOP=1 -d "$TEST_DB" -c "
  SELECT NOT has_schema_privilege('history_app','auth_l1','USAGE')
     AND NOT has_function_privilege('history_app','auth_l1.consume_service_assertion(text,bigint)','EXECUTE')
     AND NOT has_function_privilege('history_app','auth_l1.admit_session_fenced(text,text,bigint,integer)','EXECUTE')
     AND NOT has_function_privilege('auth_revoker','auth_l1.consume_service_assertion(text,bigint)','EXECUTE')
     AND NOT has_function_privilege('auth_revoker','auth_l1.admit_session_fenced(text,text,bigint,integer)','EXECUTE')
     AND NOT has_function_privilege('auth_revoker','auth_l1.revoke_one(text,bigint)','EXECUTE');
" | grep -qx t
echo DB55_PRE_GRANT_ZERO_BRIDGE_PROVEN_PASS

auth_file "$GRANT_SQL"
echo DB55_BRIDGE_APPLIED_TO_SYNTHETIC_RESTORED_CLONE_ONLY_PASS
pass_marker session_core
pass_marker private_no_dispatch
fail_marker live_011 DB55_011_NOT_INSTALLED
deny_table history_app synthetic_history_app_only auth_l1.sessions
deny_table auth_revoker synthetic_auth_revoker_only auth_l1.sessions
deny_table auth_revoker synthetic_auth_revoker_only history_l1.messages
snapshot
echo DB55_POSITIVE_NEGATIVE_FUNCTION_AND_TABLE_ACL_PASS

# 011 is installed only in the disposable restored clone to exercise audit phase.
history_file infra/postgres/migrations/011_external_dispatch_claim.up.sql
pass_marker live_011
echo DB55_011_CATALOG_PHASE_NO_EXTERNAL_DISPATCH_PASS

# This rollback is safe only because six missing privileges were proven pre-grant.
auth_file "$REVOKE_SQL"
fail_marker private_no_dispatch DB55_MISSING_APPROVED_004_005_003_BRIDGE_GRANTS
snapshot
echo DB55_ROLLBACK_RETURNS_TO_PRE_GRANT_PRIVILEGES_PASS

# Deliberate bad grant on isolated clone: auditor must refuse it.
auth_file "$GRANT_SQL"
PGUSER=auth_migrator PGPASSWORD=synthetic_auth_migrator_only psql -X -v ON_ERROR_STOP=1 \
  -d "$TEST_DB" -c "GRANT SELECT ON auth_l1.sessions TO history_app" > "$CAPTURE" 2>&1
fail_marker private_no_dispatch DB55_DIRECT_AUTH_OR_CROSS_ROLE_PRIVILEGE_DENIED
PGUSER=auth_migrator PGPASSWORD=synthetic_auth_migrator_only psql -X -v ON_ERROR_STOP=1 \
  -d "$TEST_DB" -c "REVOKE SELECT ON auth_l1.sessions FROM history_app" > "$CAPTURE" 2>&1
pass_marker private_no_dispatch
pass_marker live_011
auth_file "$REVOKE_SQL"
fail_marker live_011 DB55_MISSING_APPROVED_004_005_003_BRIDGE_GRANTS
snapshot
echo DB55_BAD_GRANT_NEGATIVE_AND_REVERT_PASS
echo DB55_ALL_THREE_SCRIPTS_SYNTHETIC_BACKUP_RESTORED_POSTGRESQL17_PASS
