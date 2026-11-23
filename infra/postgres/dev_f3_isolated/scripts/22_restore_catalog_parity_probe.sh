#!/usr/bin/env bash
# SQL catalog parity: independent source/restore PG17.11 + two negative RLS drifts.
# Operates only on the private disposable lab; mutates only an extra restore clone.
# These are schema/role checks, NOT live HTTP, Mac, disaster recovery or Gate approval.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || { echo STOP_NOT_ISOLATED_LAB >&2; exit 70; }
[[ -s "$LAB_WORK/restore-tested.marker" ]] || { echo STOP_RESTORE_NOT_ATTESTED >&2; exit 70; }
[[ "$(dbpsql -Atc 'SHOW server_version')" == 17.11* ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore dbpsql -Atc 'SHOW server_version')" == 17.11* ]] || exit 70
source_id="$(dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
restore_id="$(DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ -n "$source_id" && -n "$restore_id" && "$source_id" != "$restore_id" ]] || { echo STOP_RESTORE_NOT_INDEPENDENT >&2; exit 70; }
for target in source restore; do
  if [[ "$target" == source ]]; then svc=lab-db; db=rag_finance_f3_lab
  else svc=restore-db; db=rag_finance_f3_lab_restore; fi
  [[ "$(DB_SERVICE="$svc" DB_NAME="$db" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo STOP_LEDGER_INCOMPLETE >&2; exit 70; }
  [[ "$(DB_SERVICE="$svc" DB_NAME="$db" dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('history_l1','auth_l1') AND c.relkind IN ('r','p') AND c.relrowsecurity AND c.relforcerowsecurity")" == 14 ]] || { echo STOP_FOURTEEN_FORCE_RLS_MISSING >&2; exit 70; }
done
# Canonical names/definitions and effective grants; no table rows, DSNs or secrets.
catalog_sql="$(cat <<'SQL'
SELECT item FROM (
 SELECT 'T|'||n.nspname||'.'||c.relname||'|'||pg_get_userbyid(c.relowner)||'|'||
        c.relrowsecurity::text||'|'||c.relforcerowsecurity::text||'|'||
        coalesce(c.relacl::text,'NULL') AS item
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('history_l1','auth_l1') AND c.relkind IN ('r','p')
 UNION ALL
 SELECT 'C|'||n.nspname||'.'||c.relname||'.'||a.attname||'|'||
        format_type(a.atttypid,a.atttypmod)||'|'||a.attnotnull::text||'|'||
        a.attidentity||'|'||a.attgenerated
 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
 JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('history_l1','auth_l1') AND c.relkind IN ('r','p')
 AND a.attnum>0 AND NOT a.attisdropped
 UNION ALL
 SELECT 'K|'||n.nspname||'.'||c.relname||'.'||k.conname||'|'||
        k.contype||'|'||pg_get_constraintdef(k.oid,true)
 FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
 JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('history_l1','auth_l1')
 UNION ALL
 SELECT 'I|'||schemaname||'.'||indexname||'|'||indexdef
 FROM pg_indexes WHERE schemaname IN ('history_l1','auth_l1')
 UNION ALL
 SELECT 'P|'||schemaname||'.'||tablename||'.'||policyname||'|'||
        permissive||'|'||roles::text||'|'||cmd||'|'||
        coalesce(qual,'NULL')||'|'||coalesce(with_check,'NULL')
 FROM pg_policies WHERE schemaname IN ('history_l1','auth_l1')
 UNION ALL
 SELECT 'F|'||n.nspname||'.'||p.proname||'('||
        pg_get_function_identity_arguments(p.oid)||')|'||md5(pg_get_functiondef(p.oid))
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN ('history_l1','auth_l1')
 UNION ALL
 SELECT 'R|'||rolname||'|'||rolsuper::text||'|'||rolbypassrls::text||'|'||
        rolinherit::text||'|'||rolcreatedb::text||'|'||rolcreaterole::text||'|'||rolcanlogin::text
 FROM pg_roles WHERE rolname IN
 ('history_app','auth_revoker','auth_trust_api','auth_login_bootstrap',
  'auth_login_claim_reader','auth_login_issuer','auth_mapper',
  'auth_login_binder','auth_login_reader')
 UNION ALL
 SELECT 'G-T|'||r.rolname||'|'||n.nspname||'.'||c.relname||'|'||
        has_table_privilege(r.rolname,c.oid,'SELECT')::text||'|'||
        has_table_privilege(r.rolname,c.oid,'INSERT')::text||'|'||
        has_table_privilege(r.rolname,c.oid,'UPDATE')::text||'|'||
        has_table_privilege(r.rolname,c.oid,'DELETE')::text
 FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE r.rolname IN
 ('history_app','auth_revoker','auth_trust_api','auth_login_bootstrap',
  'auth_login_claim_reader','auth_login_issuer','auth_mapper',
  'auth_login_binder','auth_login_reader')
 AND n.nspname IN ('history_l1','auth_l1') AND c.relkind IN ('r','p')
 UNION ALL
 SELECT 'G-F|'||r.rolname||'|'||n.nspname||'.'||p.proname||'('||
        pg_get_function_identity_arguments(p.oid)||')|'||
        has_function_privilege(r.rolname,p.oid,'EXECUTE')::text
 FROM pg_roles r CROSS JOIN pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE r.rolname IN
 ('history_app','auth_revoker','auth_trust_api','auth_login_bootstrap',
  'auth_login_claim_reader','auth_login_issuer','auth_mapper',
  'auth_login_binder','auth_login_reader')
 AND n.nspname IN ('history_l1','auth_l1')
) snapshot ORDER BY item;
SQL
)"
snapshot() {
  local svc="$1" db="$2" out="$3"
  DB_SERVICE="$svc" DB_NAME="$db" dbpsql -Atq -c "$catalog_sql" > "$out"
  [[ -s "$out" ]] || { echo STOP_EMPTY_CATALOG >&2; exit 70; }
}
source_file="$LAB_WORK/catalog_parity_source_private.txt"
restore_file="$LAB_WORK/catalog_parity_restore_private.txt"
drift_force="$LAB_WORK/catalog_parity_no_force_private.txt"
drift_off="$LAB_WORK/catalog_parity_rls_off_private.txt"
for file in "$source_file" "$restore_file" "$drift_force" "$drift_off" "$LAB_WORK/restore_catalog_parity_receipt.json"; do
  [[ ! -e "$file" ]] || { echo STOP_PARITY_PROBE_ALREADY_RAN >&2; exit 70; }
done
snapshot lab-db rag_finance_f3_lab "$source_file"
snapshot restore-db rag_finance_f3_lab_restore "$restore_file"
digest() { shasum -a 256 "$1" | awk '{print $1}'; }
[[ "$(digest "$source_file")" == "$(digest "$restore_file")" ]] || { echo STOP_RESTORE_CATALOG_OR_GRANTS_MISMATCH >&2; exit 70; }
# Modify ONLY a new disposable DB copied inside the already disposable restore cluster.
probe=rag_finance_f3_catalog_parity_probe
admin() { DB_SERVICE=restore-db DB_NAME=postgres dbpsql -Atq "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || { echo STOP_PARITY_DB_COLLISION >&2; exit 70; }
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab_restore OWNER postgres" >/dev/null
admin -c "SELECT datname FROM pg_database WHERE datname='$probe'" | grep -Fxq "$probe" || exit 70
DB_SERVICE=restore-db DB_NAME="$probe" dbpsql -q -c 'ALTER TABLE history_l1.conversations NO FORCE ROW LEVEL SECURITY' >/dev/null
snapshot restore-db "$probe" "$drift_force"
[[ "$(digest "$drift_force")" != "$(digest "$restore_file")" ]] || { echo STOP_FORCE_RLS_DRIFT_UNDETECTED >&2; exit 70; }
DB_SERVICE=restore-db DB_NAME="$probe" dbpsql -q -c 'ALTER TABLE history_l1.conversations DISABLE ROW LEVEL SECURITY' >/dev/null
snapshot restore-db "$probe" "$drift_off"
[[ "$(digest "$drift_off")" != "$(digest "$restore_file")" ]] || { echo STOP_DISABLED_RLS_DRIFT_UNDETECTED >&2; exit 70; }
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || { echo STOP_PROBE_DB_LEFT_BEHIND >&2; exit 70; }
# Re-verify untouched original source and restore catalogs.
snapshot lab-db rag_finance_f3_lab "$source_file"
snapshot restore-db rag_finance_f3_lab_restore "$restore_file"
[[ "$(digest "$source_file")" == "$(digest "$restore_file")" ]] || { echo STOP_ORIGINAL_CATALOG_DRIFT >&2; exit 70; }
python3 - "$source_file" "$restore_file" "$drift_force" "$drift_off" "$LAB_WORK/restore_catalog_parity_receipt.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
src,rest,bad_force,bad_off,out=map(Path,sys.argv[1:])
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(src)==digest(rest)
assert digest(src)!=digest(bad_force) and digest(src)!=digest(bad_off)
lines=src.read_text().splitlines()
assert sum(x.startswith("T|") for x in lines)==14
assert sum(x.startswith("R|") for x in lines)==9
assert sum(x.startswith("G-T|") for x in lines)==14*9
assert len(lines)>300
out.write_text(json.dumps({
 "contract_version":"f3.db.synthetic_restore_catalog_parity.v1",
 "environment":"actual_pg17.11_two_disposable_independent_clusters",
 "catalog_sections":["tables","columns","constraints","indexes","rls_policies","functions","roles","table_grants","function_grants"],
 "source_restore_catalog_sha256":digest(src),
 "restore_equals_source":True,"source_table_count":14,"checked_roles":9,
 "negative_no_force_rls":"DETECTED_IN_DISPOSABLE_CLONE",
 "negative_disabled_rls":"DETECTED_IN_DISPOSABLE_CLONE",
 "negative_probe_removed":True,"original_clusters_unchanged":True,
 "mac_runtime":"NOT_RUN","signed_actor_fence":"NOT_TESTED",
 "encrypted_offsite_backup":"NOT_TESTED","approved_rpo_rto":"NOT_DEFINED",
 "module_gate":"NOT_ACCEPTED"},sort_keys=True,indent=2)+"\n")
PY
chmod 0600 "$LAB_WORK/restore_catalog_parity_receipt.json"
echo 'RESTORED_SCHEMA_POLICY_AND_EFFECTIVE_GRANTS_EXACT_PARITY=PASS'
echo 'RESTORE_CLONE_RLS_DRIFT_NEGATIVES=2/2_DETECTED'
echo 'RESTORE_PARITY_MAC_HTTP_AND_PRODUCTION_DR=NOT_TESTED'
