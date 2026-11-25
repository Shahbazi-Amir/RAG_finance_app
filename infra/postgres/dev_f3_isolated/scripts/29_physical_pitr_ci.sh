#!/usr/bin/env bash
# Physical PITR on the disposable, pinned 001-010 lab ONLY. No network
# or app listener on the physical recovery target; not an admission drill.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$CI" == true && "$GITHUB_ACTIONS" == true && "$GITHUB_RUN_ID" =~ ^[0-9]+$ && "$GITHUB_RUN_ATTEMPT" =~ ^[0-9]+$ ]] || exit 70
[[ "$LAB_ROOT" == "$RUNNER_TEMP/f3-db-pitr-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" ]] || exit 70
[[ "$(dbpsql -Atq -c "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
cid="$(compose ps -q lab-db)"
[[ "$cid" =~ ^[a-f0-9]{64}$ ]] || exit 70
[[ "$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$cid")" == "$LAB_PROJECT" ]] || exit 70
[[ "$(docker inspect -f '{{index .Config.Labels "com.docker.compose.service"}}' "$cid")" == lab-db ]] || exit 70
[[ "$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$cid")" == "$LAB_VOLUME" ]] || exit 70
image="$(docker inspect -f '{{.Image}}' "$cid")"
[[ "$image" =~ ^sha256:[a-f0-9]{64}$ ]] || exit 70
[[ "$(dbpsql -Atq -c 'SHOW data_directory')" == /var/lib/postgresql/data/pgdata ]] || exit 70
[[ "$(dbpsql -Atq -c 'SHOW server_version')" == 17.11* ]] || exit 70
[[ "$(dbpsql -Atq -c 'SHOW archive_mode')" == off ]] || exit 70
# Private local-socket replication solely for basebackup, no TCP replication.
if grep -Eq '^local[[:space:]]+replication' "$LAB_SECRETS/pg_hba.conf"; then echo STOP_EXISTING_REPLICATION_RULE >&2; exit 70; fi
printf '%s\n' 'local replication postgres trust' >> "$LAB_SECRETS/pg_hba.conf"
compose exec -T -u 0 lab-db bash -euc '
  cd /var/lib/postgresql/data
  test ! -e f3-pitr-wal && test ! -e f3-pitr-base
  install -d -o postgres -g postgres -m 0700 f3-pitr-wal f3-pitr-base
'
dbpsql -q -c "ALTER SYSTEM SET archive_mode='on'"
dbpsql -q -c "ALTER SYSTEM SET archive_command='test ! -e /var/lib/postgresql/data/f3-pitr-wal/%f && cp %p /var/lib/postgresql/data/f3-pitr-wal/%f || cmp -s %p /var/lib/postgresql/data/f3-pitr-wal/%f'"
compose restart lab-db >/dev/null
for n in $(seq 1 60); do
  if [[ "$(dbpsql -Atq -c 'SHOW archive_mode' 2>/dev/null || true)" == on ]]; then break; fi
  sleep 1
done
[[ "$(dbpsql -Atq -c 'SHOW archive_mode')" == on ]] || exit 70
# Distinct synthetic owners, never real identity or engine output.
a_digest="$(printf f3-pitr-synthetic-a | sha256sum | awk '{print $1}')"
b_digest="$(printf f3-pitr-synthetic-b | sha256sum | awk '{print $1}')"
dbpsql -q <<SQL
INSERT INTO auth_l1.owners(owner_id) VALUES('f3-pitr-a'),('f3-pitr-b');
INSERT INTO auth_l1.identity_links(issuer,subject,owner_id)
VALUES('https://pitr.synthetic.invalid','A','f3-pitr-a'),('https://pitr.synthetic.invalid','B','f3-pitr-b');
INSERT INTO auth_l1.sessions(digest_sha256,owner_id,session_epoch,generation,status,
 created_at,last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)
VALUES('$a_digest','f3-pitr-a',0,0,'active',clock_timestamp(),clock_timestamp(),clock_timestamp()+interval '1 hour',clock_timestamp()+interval '2 hours',3600),
('$b_digest','f3-pitr-b',0,0,'active',clock_timestamp(),clock_timestamp(),clock_timestamp()+interval '1 hour',clock_timestamp()+interval '2 hours',3600);
INSERT INTO history_l1.conversations(owner_id,id,title)
VALUES('f3-pitr-a','pitr-a-base','A base'),('f3-pitr-b','pitr-b-base','B base');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES('f3-pitr-a','pitr-a-msg','pitr-a-base','user','A base message'),
('f3-pitr-b','pitr-b-msg','pitr-b-base','user','B base message');
SQL
source_id="$(dbpsql -Atq -c 'SELECT system_identifier FROM pg_control_system()')"
ledger="$(dbpsql -Atq -c 'SELECT to_jsonb(t)::text FROM db55_audit.migration_runs t ORDER BY version' | sha256sum | awk '{print $1}')"
compose exec -T -u postgres lab-db pg_basebackup -h /var/run/postgresql -U postgres \
 -D /var/lib/postgresql/data/f3-pitr-base -X stream --checkpoint=fast --manifest-checksums=SHA256
compose exec -T -u postgres lab-db pg_verifybackup /var/lib/postgresql/data/f3-pitr-base >/dev/null
echo DB_PITR_REAL_PHYSICAL_BASEBACKUP_MANIFEST_VERIFIED=PASS
# Ensure the target transaction is in WAL generated strictly AFTER the
# streamed basebackup, not in pg_wal already included in that backup.
dbpsql -Atq -c "SELECT pg_create_restore_point('f3_after_base_before_switch')" >/dev/null
dbpsql -Atq -c 'SELECT pg_switch_wal()' >/dev/null
# Post-basebackup committed write and revocation before target; a physical
# restore that merely boots the basebackup must fail these assertions.
dbpsql -q -c "INSERT INTO history_l1.conversations(owner_id,id,title) VALUES('f3-pitr-a','pitr-a-before-target','A committed after base backup')"
[[ "$(dbpsql -Atq -c "BEGIN; SET LOCAL ROLE auth_sessions; SELECT auth_l1.revoke_one('$a_digest',0); COMMIT;")" == t ]] || exit 70
point="$(dbpsql -Atq -c "SELECT pg_create_restore_point('f3_after_a_revoke')")"
[[ "$point" =~ ^[A-F0-9]+/[A-F0-9]+$ ]] || exit 70
target_segment="$(dbpsql -Atq -c "SELECT pg_walfile_name('$point'::pg_lsn)")"
[[ "$target_segment" =~ ^[A-F0-9]{24}$ ]] || exit 70
compose exec -T -u postgres lab-db test ! -e "/var/lib/postgresql/data/f3-pitr-base/pg_wal/$target_segment"
target="$(dbpsql -Atq -c "SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS.US')||'+00'")"
[[ "$target" =~ ^[0-9-]{10}\ [0-9:.]{15}\+00$ ]] || exit 70
source_snapshot="$(dbpsql -Atq -c "SELECT to_jsonb(t)::text FROM history_l1.conversations t WHERE owner_id IN ('f3-pitr-a','f3-pitr-b') ORDER BY owner_id,id" | sha256sum | awk '{print $1}')"
source_msg="$(dbpsql -Atq -c "SELECT to_jsonb(t)::text FROM history_l1.messages t WHERE owner_id IN ('f3-pitr-a','f3-pitr-b') ORDER BY owner_id,id" | sha256sum | awk '{print $1}')"
sleep .3
# Later committed transactions MUST be absent at the chosen timestamp.
dbpsql -q -c "INSERT INTO history_l1.conversations(owner_id,id,title) VALUES('f3-pitr-b','pitr-b-after-target','B future write')"
[[ "$(dbpsql -Atq -c "BEGIN; SET LOCAL ROLE auth_sessions; SELECT auth_l1.revoke_one('$b_digest',0); COMMIT;")" == t ]] || exit 70
later="$(dbpsql -Atq -c "SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS.US')||'+00'")"
[[ "$later" > "$target" ]] || exit 70
segment="$(dbpsql -Atq -c 'SELECT pg_walfile_name(pg_current_wal_insert_lsn())')"
[[ "$segment" =~ ^[A-F0-9]{24}$ ]] || exit 70
dbpsql -Atq -c 'SELECT pg_switch_wal()' >/dev/null
for n in $(seq 1 60); do
 if compose exec -T -u postgres lab-db test -s "/var/lib/postgresql/data/f3-pitr-wal/$segment"; then break; fi
 sleep 1
done
compose exec -T -u postgres lab-db test -s "/var/lib/postgresql/data/f3-pitr-wal/$segment"
compose exec -T -u postgres lab-db test -s "/var/lib/postgresql/data/f3-pitr-wal/$target_segment"
[[ "$(dbpsql -Atq -c "SELECT count(*) FROM auth_l1.sessions WHERE digest_sha256 IN ('$a_digest','$b_digest') AND status='revoked'")" == 2 ]] || exit 70
echo DB_PITR_SOURCE_FUTURE_COMMIT_AND_WAL_ARCHIVED=PASS
# Own a new, unique clone volume. The source volume is only ever mounted RO
# by copy/recovery containers; no public port, no network, no service admission.
name="f3-pitr-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
vol="$name-data"
backupvol="$name-backup"
faultvol="$name-fault-data"
faultname="$name-missing-wal"
if docker volume inspect "$faultvol" >/dev/null 2>&1 || docker container inspect "$faultname" >/dev/null 2>&1; then
  echo STOP_EXISTING_PITR_FAULT_RESOURCE >&2; exit 70
fi
if docker volume inspect "$vol" >/dev/null 2>&1 || docker volume inspect "$backupvol" >/dev/null 2>&1 || docker container inspect "$name" >/dev/null 2>&1; then
  echo STOP_EXISTING_PITR_RESOURCE >&2; exit 70
fi
docker volume create --label "rag.finance.ci.pitr=$name" "$vol" >/dev/null
cleanup(){
  if docker container inspect "$faultname" >/dev/null 2>&1; then
    [[ "$(docker inspect -f '{{index .Config.Labels "rag.finance.ci.pitr"}}' "$faultname")" == "$name" ]] || return 70
    docker rm -f "$faultname" >/dev/null
  fi
  if docker volume inspect "$faultvol" >/dev/null 2>&1; then
    [[ "$(docker volume inspect -f '{{index .Labels "rag.finance.ci.pitr"}}' "$faultvol")" == "$name" ]] || return 70
    docker volume rm "$faultvol" >/dev/null
  fi
  if docker container inspect "$name" >/dev/null 2>&1; then
    [[ "$(docker inspect -f '{{index .Config.Labels "rag.finance.ci.pitr"}}' "$name")" == "$name" ]] && docker rm -f "$name" >/dev/null
  fi
  [[ "$(docker volume inspect -f '{{index .Labels "rag.finance.ci.pitr"}}' "$vol")" == "$name" ]] && docker volume rm "$vol" >/dev/null
  if docker volume inspect "$backupvol" >/dev/null 2>&1; then
    [[ "$(docker volume inspect -f '{{index .Labels "rag.finance.ci.pitr"}}' "$backupvol")" == "$name" ]] && docker volume rm "$backupvol" >/dev/null
  fi
}
trap cleanup EXIT
docker volume create --label "rag.finance.ci.pitr=$name" "$backupvol" >/dev/null
source_timeline="$(dbpsql -Atq -c 'SELECT timeline_id FROM pg_control_checkpoint()')"
# Copy verified base and WAL to a separately owned backup volume. Stop
# only the exact CI source; recovery cannot mount the original data volume.
docker run --rm --network none --pull never --entrypoint bash \
 --mount "type=volume,source=$LAB_VOLUME,target=/source,readonly" \
 --mount "type=volume,source=$backupvol,target=/backup" "$image" -euc '
  test ! -e /backup/base && test ! -e /backup/wal
  cp -a /source/f3-pitr-base /backup/base
  cp -a /source/f3-pitr-wal /backup/wal
  chown postgres:postgres /backup
  chmod 0700 /backup
  su postgres -s /bin/bash -c "pg_verifybackup /backup/base"
'
docker stop --time 5 "$cid" >/dev/null
[[ "$(docker inspect -f '{{.State.Running}}' "$cid")" == false ]] || exit 70
echo DB_PITR_DETACHED_BASE_WAL_VERIFIED_SOURCE_STOPPED=PASS
# Never damage the valid backup. Create a distinct negative-test volume
# with one actual target archive segment absent and a separate tampered
# base copy. Verify both failures before the ordinary positive restore.
docker volume create --label "rag.finance.ci.pitr=$name" "$faultvol" >/dev/null
docker run --rm --network none --pull never --entrypoint bash \
 --mount "type=volume,source=$backupvol,target=/backup,readonly" \
 --mount "type=volume,source=$faultvol,target=/fault" \
 -e TARGET_WAL="$target_segment" "$image" -euc '
  test -s "/backup/wal/$TARGET_WAL"
  test ! -e "/backup/base/pg_wal/$TARGET_WAL"
  test ! -e /fault/pgdata && test ! -e /fault/wal && test ! -e /fault/tampered
  cp -a /backup/base /fault/tampered
  printf "\nci-tamper\n" >> /fault/tampered/PG_VERSION
  set +e
  su postgres -s /bin/bash -c "pg_verifybackup /fault/tampered" >/fault/verify-private.log 2>&1
  rc=$?
  set -e
  test "$rc" -ne 0
  grep -Eiq "PG_VERSION.*(checksum|size)|((checksum|size).*PG_VERSION)" /fault/verify-private.log
  echo DB_PITR_TAMPERED_BASE_MANIFEST_REJECTED=PASS
  cp -a /backup/base /fault/pgdata
  cp -a /backup/wal /fault/wal
  rm -- "/fault/wal/$TARGET_WAL"
  test ! -e "/fault/wal/$TARGET_WAL" && test ! -e "/fault/pgdata/pg_wal/$TARGET_WAL"
  printf "local all postgres trust\nlocal all all reject\n" > /fault/pgdata/f3-pitr-hba.conf
  touch /fault/pgdata/recovery.signal
  chown postgres:postgres /fault/pgdata/f3-pitr-hba.conf /fault/pgdata/recovery.signal
  chmod 0600 /fault/pgdata/f3-pitr-hba.conf /fault/pgdata/recovery.signal
'
docker run -d --name "$faultname" --label "rag.finance.ci.pitr=$name" --network none \
 --pull never --user postgres --entrypoint postgres \
 --mount "type=volume,source=$faultvol,target=/var/lib/postgresql/data" \
 "$image" -D /var/lib/postgresql/data/pgdata \
 -c "listen_addresses=" -c ssl=off -c archive_mode=off \
 -c hba_file=/var/lib/postgresql/data/pgdata/f3-pitr-hba.conf \
 -c 'restore_command=cp /var/lib/postgresql/data/wal/%f %p' \
 -c "recovery_target_time=$target" -c recovery_target_action=promote >/dev/null
[[ "$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$faultname")" == none ]] || exit 70
[[ "$(docker inspect -f '{{range .Mounts}}{{println .Name}}{{end}}' "$faultname")" == "$faultvol" ]] || exit 70
for n in $(seq 1 45); do
  if [[ "$(docker inspect -f '{{.State.Running}}' "$faultname")" == false ]]; then break; fi
  sleep 1
done
[[ "$(docker inspect -f '{{.State.Running}}' "$faultname")" == false ]] || { echo STOP_MISSING_WAL_DID_NOT_FAIL_CLOSED >&2; exit 70; }
[[ "$(docker inspect -f '{{.State.ExitCode}}' "$faultname")" != 0 ]] || exit 70
# A startup error unrelated to the intended fault is NOT success.
docker logs "$faultname" 2>&1 | grep -F 'recovery ended before configured recovery target was reached'
if docker logs "$faultname" 2>&1 | grep -Eq 'archive recovery complete|selected new timeline ID'; then
  echo STOP_MISSING_WAL_PROMOTED >&2; exit 70
fi
echo DB_PITR_ACTUAL_MISSING_POST_BASE_WAL_REJECTED_NO_PROMOTION=PASS
docker rm "$faultname" >/dev/null
docker volume rm "$faultvol" >/dev/null
# Recheck original detached backup, never rewrite it after fault injection.
docker run --rm --network none --pull never --user postgres --entrypoint bash \
 --mount "type=volume,source=$backupvol,target=/backup,readonly" \
 -e TARGET_WAL="$target_segment" "$image" -euc '
  test -s "/backup/wal/$TARGET_WAL"
  pg_verifybackup /backup/base
' >/dev/null
echo DB_PITR_ORIGINAL_DETACHED_BACKUP_INTACT_AFTER_NEGATIVES=PASS
docker run --rm --network none --pull never --entrypoint bash \
 --mount "type=volume,source=$backupvol,target=/backup,readonly" \
 --mount "type=volume,source=$vol,target=/clone" "$image" -euc '
  test ! -e /clone/pgdata
  install -d -m 0700 -o postgres -g postgres /clone/pgdata
  cp -a /backup/base/. /clone/pgdata/
  printf "local all postgres trust\nlocal all all reject\n" > /clone/pgdata/f3-pitr-hba.conf
  touch /clone/pgdata/recovery.signal
  chown postgres:postgres /clone/pgdata/f3-pitr-hba.conf /clone/pgdata/recovery.signal
  chmod 0600 /clone/pgdata/f3-pitr-hba.conf /clone/pgdata/recovery.signal
'
start_ms="$(date +%s%3N)"
docker run -d --name "$name" --label "rag.finance.ci.pitr=$name" --network none \
 --pull never --user postgres --entrypoint postgres \
 --mount "type=volume,source=$backupvol,target=/backup,readonly" \
 --mount "type=volume,source=$vol,target=/var/lib/postgresql/data" \
 "$image" -D /var/lib/postgresql/data/pgdata \
 -c "listen_addresses=" -c ssl=off -c archive_mode=off \
 -c hba_file=/var/lib/postgresql/data/pgdata/f3-pitr-hba.conf \
 -c 'restore_command=cp /backup/wal/%f %p' \
 -c "recovery_target_time=$target" -c recovery_target_action=promote >/dev/null
[[ "$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$name")" == none ]] || exit 70
[[ "$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$name")" == "$vol" ]] || exit 70
[[ "$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/backup"}}{{.RW}}{{end}}{{end}}' "$name")" == false ]] || exit 70
[[ "$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/backup"}}{{.Name}}{{end}}{{end}}' "$name")" == "$backupvol" ]] || exit 70
if docker inspect -f '{{range .Mounts}}{{println .Name}}{{end}}' "$name" | grep -Fxq "$LAB_VOLUME"; then exit 70; fi
rec(){ docker exec -i "$name" psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d rag_finance_f3_lab "$@"; }
for n in $(seq 1 90); do
 if [[ "$(rec -c 'SELECT pg_is_in_recovery()' 2>/dev/null || true)" == f ]]; then break; fi
 sleep 1
done
[[ "$(rec -c 'SELECT pg_is_in_recovery()')" == f ]] || { echo STOP_PITR_TARGET_NOT_REACHED >&2; exit 70; }
elapsed_ms="$(($(date +%s%3N)-start_ms))"
# Physical restore intentionally shares system_identifier, unlike logical
# restore. Independent volume and promoted timeline are the proof.
[[ "$(rec -c 'SELECT system_identifier FROM pg_control_system()')" == "$source_id" ]] || exit 70
rec -c CHECKPOINT >/dev/null
[[ "$(rec -c 'SELECT timeline_id FROM pg_control_checkpoint()')" -gt "$source_timeline" ]] || exit 70
[[ "$(rec -c "SELECT count(*) FROM history_l1.conversations WHERE id='pitr-a-before-target'")" == 1 ]] || exit 70
[[ "$(rec -c "SELECT count(*) FROM history_l1.conversations WHERE id='pitr-b-after-target'")" == 0 ]] || exit 70
[[ "$(rec -c "SELECT status FROM auth_l1.sessions WHERE digest_sha256='$a_digest'")" == revoked ]] || exit 70
[[ "$(rec -c "SELECT status FROM auth_l1.sessions WHERE digest_sha256='$b_digest'")" == active ]] || exit 70
[[ "$(rec -c 'SELECT to_jsonb(t)::text FROM db55_audit.migration_runs t ORDER BY version' | sha256sum | awk '{print $1}')" == "$ledger" ]] || exit 70
[[ "$(rec -c "SELECT to_jsonb(t)::text FROM history_l1.conversations t WHERE owner_id IN ('f3-pitr-a','f3-pitr-b') ORDER BY owner_id,id" | sha256sum | awk '{print $1}')" == "$source_snapshot" ]] || exit 70
[[ "$(rec -c "SELECT to_jsonb(t)::text FROM history_l1.messages t WHERE owner_id IN ('f3-pitr-a','f3-pitr-b') ORDER BY owner_id,id" | sha256sum | awk '{print $1}')" == "$source_msg" ]] || exit 70
# Actual PostgreSQL RLS with SET ROLE; no claimed TLS LOGIN on isolated
# recovery target and no attempt to admit the stale B session.
for pair in a:2 b:1; do
 owner="f3-pitr-${pair%:*}"; expected="${pair#*:}"
 [[ "$(rec -c "BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='$owner'; SELECT count(*) FROM history_l1.conversations; COMMIT;")" == "$expected" ]] || exit 70
 [[ "$(rec -c "BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='$owner'; SELECT count(*) FROM history_l1.messages; COMMIT;")" == 1 ]] || exit 70
done
[[ "$(rec -c "BEGIN; SET LOCAL ROLE history_app; SELECT count(*) FROM history_l1.conversations; COMMIT;")" == 0 ]] || exit 70
echo DB_PITR_TIMESTAMP_WAL_REPLAY_LEDGER_HISTORY_RLS_REVOKE_PARITY=PASS
echo DB_PITR_STALE_POST_TARGET_REVOCATION_NOT_ADMITTED_NETWORK_NONE=PASS
export PITR_ELAPSED_MS="$elapsed_ms" PITR_TARGET="$target" PITR_LATER="$later" PITR_IMAGE="$image"
python3 - <<'PY'
import json,os,subprocess
from datetime import datetime
from pathlib import Path
p=Path(os.environ["GITHUB_WORKSPACE"])/"ci_receipts/f3_db_physical_pitr.json"
p.parent.mkdir(exist_ok=True)
delta=(datetime.fromisoformat(os.environ["PITR_LATER"])-datetime.fromisoformat(os.environ["PITR_TARGET"])).total_seconds()*1000
assert delta>0
p.write_text(json.dumps({
 "source_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "pg_image_id":os.environ["PITR_IMAGE"],"pg_version":"17.11",
 "migrations":"001-010","basebackup_manifest_verified":True,
 "recovery_target_kind":"timestamp","wal_after_basebackup_replayed":True,
 "later_commit_excluded":True,"same_physical_system_identifier":True,
 "new_volume_promoted_timeline":True,"ledger_exact":True,"history_exact":True,
 "detached_backup_volume_verified":True,"source_stopped_before_recovery":True,
 "source_volume_not_mounted_on_target":True,
 "tampered_base_rejected":True,"missing_post_base_wal_rejected_no_promotion":True,
 "original_detached_backup_verified_after_faults":True,
 "restricted_set_role_rls":True,"target_tls_login":"NOT_RUN_NETWORK_NONE",
 "a_revoked_at_target":True,"b_post_target_revocation_absent":True,
 "stale_session_admission":False,"network":"NONE",
 "pg_promotion_elapsed_ms":int(os.environ["PITR_ELAPSED_MS"]),
 "synthetic_target_to_later_observation_ms":round(delta,3),
 "operational_rpo_rto":"NOT_ATTESTED","retention_kms_topology":"NOT_APPROVED",
 "raw_backup_published":False,"engine_calls":0,"sql_011":False,
 "target_verified":False,"accepted":False
},indent=2)+"\n")
PY
cleanup
trap - EXIT
echo DB_PITR_DISPOSABLE_TARGET_CLEANUP=PASS
