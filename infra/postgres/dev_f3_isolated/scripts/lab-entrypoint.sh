#!/usr/bin/env bash
# Only for fresh isolated PostgreSQL development images.
set -euo pipefail
if [[ "$(id -u)" != 0 ]]; then
  echo 'STOP_LAB_ENTRYPOINT_REQUIRES_IMAGE_ROOT_FOR_TLS_PERMISSIONS' >&2; exit 70
fi
install -d -o postgres -g postgres -m 0700 /var/lib/postgresql/f3tls
for x in server.crt server.key ca.crt pg_hba.conf; do
  test -s "/run/lab_secrets/$x" || { echo "STOP_TLS_FILE_MISSING:$x" >&2; exit 70; }
  cp "/run/lab_secrets/$x" "/var/lib/postgresql/f3tls/$x"
  chown postgres:postgres "/var/lib/postgresql/f3tls/$x"
  chmod 0600 "/var/lib/postgresql/f3tls/$x"
done
exec /usr/local/bin/docker-entrypoint.sh "$@"
