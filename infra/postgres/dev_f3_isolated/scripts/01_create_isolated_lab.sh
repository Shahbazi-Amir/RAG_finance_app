#!/usr/bin/env bash
# Only creates uniquely named disposable Docker volumes/cluster in LAB_ROOT.
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"
require_lab_ready(){ command -v docker >/dev/null || { echo 'STOP_DOCKER_NOT_AVAILABLE' >&2; exit 70; }; test -d "$LAB_SOURCE" && test -s "$LAB_SOURCE/SHA256SUMS" || { echo 'STOP_SOURCE_BUNDLE_MISSING' >&2; exit 70; }; }
require_lab_ready
[[ ! -e "$LAB_WORK/cluster-created.marker" ]] || { echo 'STOP_LAB_ALREADY_CREATED' >&2; exit 70; }
if docker volume inspect "$LAB_VOLUME" >/dev/null 2>&1 || docker volume inspect "$LAB_RESTORE_VOLUME" >/dev/null 2>&1; then
 echo 'STOP_EXISTING_VOLUME_NAME' >&2; exit 70
fi
if docker ps -a --filter "label=com.docker.compose.project=$LAB_PROJECT" -q | grep -q .; then
 echo 'STOP_PROJECT_ALREADY_HAS_CONTAINERS' >&2; exit 70
fi
cd "$LAB_SOURCE" && shasum -a 256 -c SHA256SUMS >/dev/null
secure_log
[[ ! -e "$LAB_SECRETS/server.key" ]] || { echo 'STOP_TLS_ALREADY_INITIALIZED' >&2; exit 70; }
openssl rand -hex 32 > "$LAB_SECRETS/superuser_password"
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 3 \
 -keyout "$LAB_WORK/lab-ca.key" -out "$LAB_SECRETS/ca.crt" \
 -subj '/CN=F3 DB LAB EPHEMERAL CA' >/dev/null 2>&1
openssl req -newkey rsa:3072 -sha256 -nodes \
 -keyout "$LAB_SECRETS/server.key" -out "$LAB_WORK/server.csr" \
 -subj '/CN=demo-db' >/dev/null 2>&1
cat > "$LAB_WORK/cert.ext" <<'EXT'
subjectAltName=DNS:demo-db
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EXT
openssl x509 -req -sha256 -days 3 -in "$LAB_WORK/server.csr" \
 -CA "$LAB_SECRETS/ca.crt" -CAkey "$LAB_WORK/lab-ca.key" -CAcreateserial \
 -extfile "$LAB_WORK/cert.ext" -out "$LAB_SECRETS/server.crt" >/dev/null 2>&1
openssl verify -CAfile "$LAB_SECRETS/ca.crt" "$LAB_SECRETS/server.crt" >/dev/null
openssl x509 -in "$LAB_SECRETS/server.crt" -noout -ext subjectAltName | grep -Fq 'DNS:demo-db'
cat > "$LAB_SECRETS/pg_hba.conf" <<'HBA'
# ISOLATED LAB ONLY; no host port published.
local all postgres trust
local all all reject
hostnossl all all 0.0.0.0/0 reject
hostnossl all all ::0/0 reject
hostssl all all 0.0.0.0/0 scram-sha-256
hostssl all all ::0/0 scram-sha-256
HBA
chmod 0600 "$LAB_SECRETS/"* "$LAB_WORK/lab-ca.key" "$LAB_WORK/server.csr" "$LAB_WORK/cert.ext"
: > "$LAB_SECRETS/pgpass"
chmod 0600 "$LAB_SECRETS/pgpass"
# Compose syntax, image platform/digest, internal network and unique volume guard.
compose config -q
compose up -d --pull missing lab-db
for i in {1..45}; do
  if dbpsql -Atc 'SELECT current_database()' 2>/dev/null | grep -Fxq rag_finance_f3_lab; then break; fi
  sleep 2
done
[[ "$(dbpsql -Atc 'SHOW server_version')" == 17.11* ]] || { echo 'STOP_POSTGRES_17_11_REQUIRED' >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")" == f ]] || { echo 'STOP_UNEXPECTED_LOCAL_SSL' >&2; exit 70; }
[[ "$(dbpsql -Atc 'SHOW ssl')" == on ]] || { echo 'STOP_TLS_OFF' >&2; exit 70; }
[[ "$(dbpsql -Atc 'SELECT current_database()')" == rag_finance_f3_lab ]] || { echo 'STOP_TARGET_DB' >&2; exit 70; }
dbpsql -Atc "SELECT system_identifier FROM pg_control_system()" > "$LAB_WORK/source_cluster_id.txt"
printf '%s\n' 'F3_LAB_CREATED_ISOLATED=PASS' 'PG_VERSION=17.11' 'TLS_CONFIGURED=YES' 'NO_HOST_PORT=YES' 'NO_DEMO_VOLUME_TOUCHED=YES'
touch "$LAB_WORK/cluster-created.marker"; chmod 0600 "$LAB_WORK/cluster-created.marker"
