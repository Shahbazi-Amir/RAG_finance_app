#!/usr/bin/env bash
# Installs ONLY the exact 003/004/005 function grants on a new lab and runs read-only DB55.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo 'STOP_MIGRATIONS_INCOMPLETE' >&2; exit 70; }
bridge="$LAB_SOURCE/db55_no_dispatch_bridge.sql"
verifier="$LAB_SOURCE/db55_verify_staging.sql"
[[ "$(git hash-object "$bridge")" == a79e46c87857eb2b77fd26863e1cf85fead31b38 ]] || { echo 'STOP_BRIDGE_BLOB' >&2; exit 70; }
[[ "$(git hash-object "$verifier")" == e2115d8cebc649fdf05d3fbee4ef435ad5f39a47 ]] || { echo 'STOP_VERIFIER_BLOB' >&2; exit 70; }
# A catalog auditor sees only schema names and function metadata, never user rows.
dbpsql -c 'GRANT USAGE ON SCHEMA auth_l1,history_l1 TO db55_lab_auditor' >/dev/null
[[ "$(dbpsql -Atc "SELECT has_table_privilege('db55_lab_auditor','auth_l1.sessions','SELECT') OR has_table_privilege('db55_lab_auditor','history_l1.messages','SELECT')")" == f ]] || { echo 'STOP_AUDITOR_UNSAFE' >&2; exit 70; }
count="$(dbpsql -Atc 'SELECT count(*) FROM db55_audit.bridge_runs')"
if [[ "$count" == 0 ]]; then
  # Do not silently overwrite unexpected existing privileges.
  pre="$(dbpsql -Atc "SELECT NOT has_schema_privilege('history_app','auth_l1','USAGE') AND NOT has_function_privilege('history_app','auth_l1.consume_service_assertion(text,bigint)','EXECUTE') AND NOT has_function_privilege('history_app','auth_l1.admit_session_fenced(text,text,bigint,integer)','EXECUTE') AND NOT has_function_privilege('auth_revoker','auth_l1.consume_service_assertion(text,bigint)','EXECUTE') AND NOT has_function_privilege('auth_revoker','auth_l1.admit_session_fenced(text,text,bigint,integer)','EXECUTE') AND NOT has_function_privilege('auth_revoker','auth_l1.revoke_one(text,bigint)','EXECUTE')")"
  [[ "$pre" == t ]] || { echo 'STOP_UNEXPECTED_PREEXISTING_GRANTS' >&2; exit 70; }
  dbpsql -c "INSERT INTO db55_audit.bridge_runs(id,bridge_sha1,status) VALUES(1,'a79e46c87857eb2b77fd26863e1cf85fead31b38','STARTED')" >/dev/null
  dbpsql -f /run/source/db55_no_dispatch_bridge.sql > "$LAB_WORK/bridge.log" 2>&1 || { echo 'STOP_BRIDGE_FAILED_NO_AUTORETRY' >&2; exit 70; }
  dbpsql -c "UPDATE db55_audit.bridge_runs SET status='APPLIED', applied_at=clock_timestamp() WHERE id=1 AND status='STARTED'" >/dev/null
elif [[ "$count" == 1 ]]; then
  [[ "$(dbpsql -Atc 'SELECT status FROM db55_audit.bridge_runs WHERE id=1')" == APPLIED ]] || { echo 'STOP_BRIDGE_INTENT_AMBIGUOUS' >&2; exit 70; }
  [[ "$(dbpsql -Atc 'SELECT bridge_sha1 FROM db55_audit.bridge_runs WHERE id=1')" == a79e46c87857eb2b77fd26863e1cf85fead31b38 ]] || { echo 'STOP_BRIDGE_PIN_MISMATCH' >&2; exit 70; }
else echo 'STOP_BRIDGE_LEDGER_CORRUPT' >&2;exit 70; fi
# SUPERUSER SET ROLE must persist for the -f script within this single psql process.
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
 -f /run/source/db55_verify_staging.sql > "$LAB_WORK/db55_private_no_dispatch.log" 2>&1 || { echo 'STOP_DB55_VERIFIER_FAILED' >&2; exit 70; }
grep -Fq 'DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS' "$LAB_WORK/db55_private_no_dispatch.log" || { echo 'STOP_DB55_PASS_MARKER_MISSING' >&2; exit 70; }
# Core table direct-select denial: read-only catalog checks.
[[ "$(dbpsql -Atc "SELECT NOT has_table_privilege('history_app','auth_l1.sessions','SELECT') AND NOT has_table_privilege('auth_revoker','auth_l1.sessions','SELECT') AND NOT has_table_privilege('auth_revoker','history_l1.messages','SELECT')")" == t ]] || { echo 'STOP_CORE_DIRECT_SELECT_NOT_DENIED' >&2; exit 70; }
# Required FORCE RLS on main tables.
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE (n.nspname,c.relname) IN (('history_l1','messages'),('history_l1','execution_attempts'),('auth_l1','sessions'),('auth_l1','initial_login_attempts')) AND c.relrowsecurity AND c.relforcerowsecurity")" == 4 ]] || { echo 'STOP_FORCE_RLS_REQUIRED_TABLES' >&2; exit 70; }
echo 'DB55_PRIVATE_NO_DISPATCH_LAB=PASS'
