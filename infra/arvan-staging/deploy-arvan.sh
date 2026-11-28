#!/usr/bin/env bash
set -euo pipefail
set +x

fail() { printf 'Arvan deployment failed: %s\n' "$1" >&2; exit 1; }
step() { printf '%s\n' "$1"; }
dry_run=false
case "${1:-}" in
    '') ;;
    --dry-run) dry_run=true ;;
    *) fail 'usage: deploy-arvan.sh [--dry-run]' ;;
esac
[[ $# -le 1 ]] || fail 'usage: deploy-arvan.sh [--dry-run]'

infra=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
release=/opt/rag-finance-staging/phase3/arvan-candidate
tools=/opt/rag-finance-staging/phase3/tools/bin
config=/etc/rag-arvan-candidate
admin_env=${KEYCLOAK_ADMIN_ENV_FILE:-/root/rag-arvan-backups/keycloak-admin.env}
theme=/opt/rag-finance-staging/phase3/themes/moshaver-mali
compose=$infra/keycloak.compose.yml
units=(rag-arvan-worker rag-arvan-api rag-arvan-bootstrap-oidc rag-arvan-web)
vhosts=(ragfinance.ir idp-staging.ragfinance.ir)

if "$dry_run"; then
    cat <<'PLAN'
Preflight Linux host, staged release, offline build tools, restricted inputs and Keycloak admin credentials.
Build and check Web as the release operator using offline dependencies.
Install the four versioned systemd units and reload the systemd manager.
Sync the read-only Keycloak theme and restart Keycloak if the theme changed.
Reconcile existing realm theme, locale, registration policy and client PKCE S256 over container loopback.
Render the protected Nginx proof include, install same-domain and deny-only vhosts, validate with nginx -t.
Restart candidate services and reload Nginx.
Smoke active services, public login/discovery/capabilities, ingress 404s and private mTLS.
PLAN
    exit 0
fi

[[ $EUID == 0 && $infra == "$release/infra/arvan-staging" ]] ||
    fail 'run as root from the staged candidate directory'

node_bin_dir=""
if [[ -e $tools/node ]]; then
    node_bin_dir=$(dirname -- "$(readlink -f -- "$tools/node")")
fi
export PATH="$tools${node_bin_dir:+:$node_bin_dir}:/usr/sbin:/usr/bin:/sbin:/bin"
export KEYCLOAK_ADMIN_ENV_FILE="$admin_env"

for cmd in npm node python3.13 systemctl nginx docker curl jq rsync runuser stat flock install cmp mv mktemp sha256sum sort find xargs readlink getent; do
    command -v "$cmd" >/dev/null || fail "missing tool $cmd"
done
exec 9>/run/lock/rag-arvan-deploy.lock
flock -n 9 || fail 'another deployment is running'

for name in api-private.json bootstrap-private.json web-private.json gateway.env keycloak.env keycloak-db.env; do
    file=$config/$name
    [[ -f $file && ! -L $file && -s $file && $(stat -c %a -- "$file") == 600 ]] ||
        fail "missing or insecure credential input $name"
done
[[ -f $admin_env && ! -L $admin_env && -s $admin_env && $(stat -c %a -- "$admin_env") == 600 ]] ||
    fail 'missing or insecure keycloak admin env input'

python3.13 "$infra/templates/protected-profile-check.py" ||
    fail 'private profile, same-domain issuer or referenced credentials failed preflight'
docker compose -f "$compose" version >/dev/null
bash "$infra/templates/realm-sync.sh" "$compose" --check ||
    fail 'Keycloak realm/client #143 preflight check failed (verify PKCE S256 and admin env)'

build_user=${ARVAN_BUILD_USER:-$(stat -c %U -- "$release")}
[[ $build_user != root ]] || fail 'select an unprivileged release operator'
build_home=$(getent passwd "$build_user" | cut -d: -f6)
[[ -n $build_home && -d $build_home ]] || fail "missing home directory for $build_user"
npm_cache=${ARVAN_NPM_CACHE:-$build_home/.npm}
[[ -d $npm_cache ]] || fail "missing offline npm cache at $npm_cache"

step 'Checking and building staged Web release'
(
    cd "$release/apps/web"
    runuser -u "$build_user" -- env PATH="$PATH" HOME="$build_home" npm_config_cache="$npm_cache" NEXT_TELEMETRY_DISABLED=1 \
        npm ci --offline --no-audit --no-fund
    runuser -u "$build_user" -- env PATH="$PATH" HOME="$build_home" npm_config_cache="$npm_cache" NEXT_TELEMETRY_DISABLED=1 \
        node node_modules/next/dist/bin/next typegen
    for check in lint typecheck build; do
        runuser -u "$build_user" -- env PATH="$PATH" HOME="$build_home" npm_config_cache="$npm_cache" NEXT_TELEMETRY_DISABLED=1 \
            npm run "$check"
    done
) || fail 'offline Web install, lint, typecheck or build'

step 'Installing systemd units'
for unit in "${units[@]}"; do
    install -m 0644 "$infra/systemd/$unit.service" "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload

step 'Synchronizing Keycloak theme'
install -d -m 0755 "$theme"
rsync -rc --delete --chmod=D755,F644 "$infra/themes/moshaver-mali/" "$theme/"
theme_digest=$(cd "$theme" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum)
theme_stamp=/var/lib/rag-arvan-deploy/theme.sha256
install -d -m 0755 /var/lib/rag-arvan-deploy
if [[ ! -f $theme_stamp || $(<"$theme_stamp") != "$theme_digest" ]]; then
    docker compose -f "$compose" restart keycloak >/dev/null 2>&1 ||
        fail 'Keycloak restart'
    curl -qfsS --retry 20 --retry-all-errors --retry-delay 2 --max-time 5 \
        http://127.0.0.1:18081/realms/finance-staging/.well-known/openid-configuration \
        >/dev/null 2>&1 || fail 'Keycloak readiness'
    printf '%s\n' "$theme_digest" > "$theme_stamp"
fi
bash "$infra/templates/realm-sync.sh" "$compose" --apply || fail 'realm reconciliation'

step 'Installing and testing Nginx configuration'
backup=$(mktemp -d)
cleanup() {
    rm -f -- "$backup/"*.conf
    rmdir "$backup"
}
trap cleanup EXIT
for host in "${vhosts[@]}"; do
    dest=/etc/nginx/conf.d/$host.conf
    [[ ! -L $dest ]] || fail 'unexpected vhost symlink'
    if [[ -f $dest ]]; then
        [[ $(stat -c %a -- "$dest") == 644 ]] || fail 'unexpected vhost mode'
        install -m 0644 "$dest" "$backup/$host.conf"
    fi
done
restore_nginx() {
    for host in "${vhosts[@]}"; do
        dest=/etc/nginx/conf.d/$host.conf
        if [[ -f $backup/$host.conf ]]; then
            mv -f "$backup/$host.conf" "$dest"
        else
            rm -f -- "$dest"
        fi
    done
}
apply_nginx() {
    python3.13 "$infra/render-nginx-proof.py" || return
    for host in "${vhosts[@]}"; do
        install -m 0644 "$infra/templates/$host.conf" "/etc/nginx/conf.d/$host.conf" || return
    done
    nginx -t >/dev/null 2>&1
}
if ! apply_nginx; then
    restore_nginx
    fail 'Nginx config validation'
fi

step 'Restarting candidate services'
for unit in "${units[@]}"; do
    if ! systemctl restart "$unit"; then
        restore_nginx
        fail "restart failed: $unit"
    fi
done
if ! systemctl reload nginx; then
    restore_nginx
    nginx -t >/dev/null 2>&1 && systemctl reload nginx
    fail 'Nginx reload'
fi

step 'Checking service readiness and #143 ingress'
for unit in "${units[@]}" nginx; do
    systemctl is-active --quiet "$unit" || fail "$unit is not active"
done
expect_status() {
    local expected=$1 url=$2 status
    shift 2
    status=$(curl -qsS --max-time 10 -o /dev/null -w '%{http_code}' "$@" "$url") ||
        fail "unreachable: $url"
    [[ $status == "$expected" ]] || fail "expected $expected, received $status: $url"
}
expect_status 200 https://ragfinance.ir/api/product-capabilities \
    --fail --retry 20 --retry-all-errors --retry-delay 2 --max-time 5
expect_status 200 https://ragfinance.ir/login
discovery=$(curl -qfsS --max-time 10 -w '\n%{http_code}' \
    https://ragfinance.ir/realms/finance-staging/.well-known/openid-configuration) ||
    fail 'public OIDC discovery request'
[[ ${discovery##*$'\n'} == 200 ]] || fail 'public OIDC discovery status'
jq -e '.issuer == "https://ragfinance.ir/realms/finance-staging" and
    (.id_token_signing_alg_values_supported | index("RS256") != null) and
    (.code_challenge_methods_supported | index("S256") != null)' \
    <<<"${discovery%$'\n'*}" >/dev/null || fail 'public OIDC discovery policy'
blocked=(/internal/ /admin/ /realms/master/ /auth/)
for path in "${blocked[@]}" /realms/nonexistent/; do
    expect_status 404 "https://ragfinance.ir$path"
done
for path in / "${blocked[@]}" /realms/finance-staging/.well-known/openid-configuration /resources/; do
    expect_status 404 "https://idp-staging.ragfinance.ir$path"
done
expect_status 405 https://ragfinance.ir/api/auth/logout
python3.13 "$infra/templates/protected-profile-check.py" --smoke-mtls ||
    fail 'private mTLS smoke'
step 'Arvan smoke gate passed'
