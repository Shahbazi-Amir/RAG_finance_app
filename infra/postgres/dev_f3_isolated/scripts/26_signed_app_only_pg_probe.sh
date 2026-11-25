#!/usr/bin/env bash
# One disposable CI environment: real signed listener, restricted PG TLS, source and restore.
# Deliberately no browser/IdP claims; session issuance is a trusted synthetic fixture.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${CI:-}" == true && "${RUNNER_OS:-}" == Linux ]] || { echo CI_ONLY; exit 70; }
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
: "${SOURCE_REPO:?}"
[[ "$LAB_ROOT" == "$RUNNER_TEMP"/f3-signed-pg-* ]] || exit 70
[[ ! -e "$LAB_WORK/restore-tested.marker" ]] || exit 70
network="${LAB_PROJECT}_private"
[[ "$(docker network inspect -f '{{.Internal}}' "$network")" == true ]] || exit 70
[[ "$(docker network inspect -f '{{index .Labels "com.docker.compose.project"}}' "$network")" == "$LAB_PROJECT" ]] || exit 70
name="${LAB_PROJECT}-signed-api"
image="f3-signed-pg:$(git -C "$SOURCE_REPO" rev-parse HEAD)"
scratch="$LAB_WORK/signed-api-probe"
mkdir -m 0700 "$scratch" "$scratch/api" "$scratch/client" "$scratch/pki"
cleanup() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  sudo rm -rf -- "$scratch"
}
trap cleanup EXIT
openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 1 -subj '/CN=F3 ephemeral signed lab CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign' -keyout "$scratch/pki/ca.key" -out "$scratch/pki/ca.crt" >/dev/null 2>&1
for peer in api bff other; do
  openssl req -newkey rsa:2048 -nodes -subj "/CN=$peer" -keyout "$scratch/pki/$peer.key" -out "$scratch/pki/$peer.csr" >/dev/null 2>&1
  printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n' > "$scratch/pki/$peer.ext"
  if [[ "$peer" == api ]]; then
    printf 'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:signed-api\n' >> "$scratch/pki/$peer.ext"
  else
    printf 'extendedKeyUsage=clientAuth\n' >> "$scratch/pki/$peer.ext"
  fi
  openssl x509 -req -in "$scratch/pki/$peer.csr" -CA "$scratch/pki/ca.crt" -CAkey "$scratch/pki/ca.key" -CAcreateserial -days 1 -sha256 -extfile "$scratch/pki/$peer.ext" -out "$scratch/pki/$peer.crt" >/dev/null 2>&1
done
cp "$scratch/pki/"{api.crt,api.key,ca.crt} "$scratch/api/"
cp "$scratch/pki/"{bff.crt,bff.key,other.crt,other.key,ca.crt} "$scratch/client/"
cp "$LAB_SECRETS/ca.crt" "$scratch/api/pg-ca.crt"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$scratch/client/sign.key" >/dev/null 2>&1
openssl pkey -in "$scratch/client/sign.key" -pubout -out "$scratch/api/sign.pub" >/dev/null 2>&1
leaf="$(openssl x509 -in "$scratch/client/bff.crt" -outform DER | sha256sum | cut -d' ' -f1)"
# Seed only this empty lab, never use browser-supplied actor or a real IdP subject.
python3 - "$scratch/client/actors.json" <<'PY'
import json, secrets, sys
with open(sys.argv[1], "w") as f:
    json.dump({label:secrets.token_urlsafe(32) for label in ("a-before","a-after","a-replay","b")},f)
PY
[[ "$(dbpsql -Atc 'SELECT count(*) FROM history_l1.conversations')" == 0 ]] || exit 70
dbpsql -q <<'SQL'
INSERT INTO auth_l1.owners(owner_id) VALUES ('signed-owner-a'),('signed-owner-b');
INSERT INTO history_l1.conversations(owner_id,id,title,created_at)
VALUES ('signed-owner-a','signed-a-1','lab title A1',clock_timestamp()-interval '1 minute'),
       ('signed-owner-a','signed-a-2','lab title A2',clock_timestamp()),
       ('signed-owner-b','signed-b-1','lab title B1',clock_timestamp());
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES ('signed-owner-a','signed-msg-a','signed-a-1','user','lab message A'),
       ('signed-owner-b','signed-msg-b','signed-b-1','user','lab message B');
SQL
python3 - "$scratch/client/actors.json" <<'PY' | dbpsql -q >/dev/null
import hashlib,json,sys
for label,token in json.load(open(sys.argv[1])).items():
    owner="signed-owner-b" if label=="b" else "signed-owner-a"
    digest=hashlib.sha256(token.encode()).hexdigest()
    print("SELECT auth_l1.issue_session('%s',0,'%s',3600,7200);" % (owner,digest))
PY
docker build --platform linux/amd64 -f "$SOURCE_REPO/infra/phase3_l1/Dockerfile.api.signed" --build-arg BASE=docker.io/library/python:3.13.5 --build-arg "SOURCE_SHA=$(git -C "$SOURCE_REPO" rev-parse HEAD)" -t "$image" "$SOURCE_REPO"
[[ "$(docker image inspect -f '{{.Config.User}}' "$image")" == 11001:11001 ]] || exit 70
printf 'API_CURSOR_KEY=%s\nAPI_CURSOR_TTL_SECONDS=300\n' "$(openssl rand -hex 32)" > "$scratch/api.env"
counts() {
  dbpsql -Atc "SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||(SELECT count(*) FROM history_l1.messages)||'|'||(SELECT count(*) FROM history_l1.send_receipts)||'|'||(SELECT count(*) FROM history_l1.execution_attempts)||'|'||(SELECT count(*) FROM history_l1.answers)"
}
start_api() {
  local host="$1" db="$2"
  sudo chown -R "$(id -u):$(id -g)" "$scratch/api" "$scratch/client"
  python3 - "$scratch/api/phase3-app-only.json" "$LAB_WORK" "$host" "$db" "$leaf" <<'PY'
import json,sys
from pathlib import Path
target,work,host,db,leaf=sys.argv[1:]
def dsn(role):
    password=(Path(work)/(role+".password")).read_text().strip()
    return f"host={host} port=5432 dbname={db} user={role} password={password} sslmode=verify-full sslrootcert=/run/secrets/pg-ca.crt connect_timeout=3"
d=dict(contract_version="api.private_app_only_asgi.v1",listen_host="0.0.0.0",listen_port=8443,
server_tls_cert_file="/run/secrets/api.crt",server_tls_key_file="/run/secrets/api.key",
trusted_bff_ca_file="/run/secrets/ca.crt",bff_leaf_cert_sha256=leaf,
bff_issuer="urn:rag-finance:lab-bff",bff_audience="urn:rag-finance:lab-api",bff_kid="lab-key",
bff_rs256_public_key_file="/run/secrets/sign.pub",history_dsn=dsn("history_app"),revoke_dsn=dsn("auth_revoker"))
with open(target,"w") as f: json.dump(d,f)
PY
  chmod 0700 "$scratch/api" "$scratch/client"
  chmod 0600 "$scratch/api/"* "$scratch/client/"*
  sudo chown -R 11001:11001 "$scratch/api" "$scratch/client"
  docker run -d --name "$name" --network "$network" --network-alias signed-api --read-only --cap-drop ALL --security-opt no-new-privileges --env-file "$scratch/api.env" --mount "type=bind,source=$scratch/api,target=/run/secrets,readonly" "$image" >/dev/null
}
probe() {
  docker run --rm --network "$network" --read-only --cap-drop ALL --security-opt no-new-privileges --mount "type=bind,source=$scratch/client,target=/run/probe,readonly" "$image" python3 tests/phase3/integration/api/signed_app_only_pg_probe.py "$1"
}
[[ "$(counts)" == '3|2|0|0|0' ]] || exit 70
start_api demo-db rag_finance_f3_lab
probe source
[[ "$(counts)" == '3|2|0|0|0' ]] || exit 70
compose stop lab-db >/dev/null
probe outage
compose start lab-db >/dev/null
# Wait for source PG before backup.
for i in {1..45}; do
  if dbpsql -Atc 'SELECT 1' 2>/dev/null | grep -Fxq 1; then break; fi
  sleep 2
done
[[ "$(counts)" == '3|2|0|0|0' ]] || exit 70
docker rm -f "$name" >/dev/null
bash "$BUNDLE_ROOT/scripts/06_backup_restore_independent.sh"
export DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore
[[ "$(counts)" == '3|2|0|0|0' ]] || exit 70
start_api restore-db rag_finance_f3_lab_restore
probe restore
[[ "$(counts)" == '3|2|0|0|0' ]] || exit 70
printf 'SIGNED_PG_SOURCE_RESTORE_ZERO_HISTORY_WRITES=PASS\nSOURCE_SHA=%s\nSIGNED_API_LOCAL_IMAGE_ID=%s\n' "$(git -C "$SOURCE_REPO" rev-parse HEAD)" "$(docker image inspect -f '{{.Id}}' "$image")"
# Separate historical-fixture phase AFTER the zero-write journey has passed.
# No POST admission route enabled. Only this disposable restored lab is mutated.
docker run --rm --network "$network" --read-only --cap-drop ALL --security-opt no-new-privileges --mount "type=bind,source=$scratch/api,target=/run/secrets,readonly" "$image" python3 tests/phase3/integration/api/m10_historical_replay_fixture.py
[[ "$(counts)" == '4|3|1|1|0' ]] || exit 70
sudo chown -R "$(id -u):$(id -g)" "$scratch/client"
dbpsql -Atc "SELECT json_build_object('owner_user_id',r.owner_id,'resolved_conversation_id',r.resolved_conversation_id,'message_id',r.user_message_id,'attempt_id',a.id,'attempt_request_id',a.attempt_request_id,'attempt_trace_id',a.attempt_trace_id,'reserved_answer_id',a.reserved_answer_id) FROM history_l1.send_receipts r JOIN history_l1.execution_attempts a ON a.owner_id=r.owner_id AND a.send_receipt_id=r.id WHERE r.client_message_id='m10-historical-client' AND r.owner_id='signed-owner-b'" > "$scratch/client/historical-expected.json"
python3 - "$scratch/client/historical-expected.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert len(d)==7 and all(d.values())
PY
chmod 0600 "$scratch/client/historical-expected.json"
sudo chown -R 11001:11001 "$scratch/client"
probe historical-replay
# Real hard stop of the disposable restored DB; not the source, never Mac.
compose kill -s SIGKILL restore-db >/dev/null
probe outage
compose start restore-db >/dev/null
probe historical-replay
[[ "$(counts)" == '4|3|1|1|0' ]] || exit 70
echo M10_HISTORICAL_STATUS_AFTER_REAL_PG_CRASH_COUNTS_STABLE_PASS
echo M10_POSITIVE_HTTP_SEND_PERSISTENCE_NOT_RUN_APP_ONLY_FENCE
echo 'BROWSER_OIDC_JOURNEY=NOT_RUN'
