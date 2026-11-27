#!/usr/bin/env bash
set -euo pipefail
set +x

# Non-interactive realm/client verification and reconciliation over container loopback.
# Reads admin credentials only from a root-owned 0600 env file without logging or argv exposure.
compose_file=${1:?Compose file required}
mode=${2:---check}
admin_env=${KEYCLOAK_ADMIN_ENV_FILE:-/root/rag-arvan-backups/keycloak-admin.env}

case "$mode" in
    --check|--apply) ;;
    *) printf 'usage: realm-sync.sh <compose-file> [--check|--apply]\n' >&2; exit 2 ;;
esac

[[ -f $admin_env && ! -L $admin_env && -s $admin_env && $(stat -c %a:%u -- "$admin_env") == 600:0 ]] || {
    printf 'missing or insecure keycloak admin env file\n' >&2
    exit 1
}

KEYCLOAK_ADMIN_USERNAME=''
KEYCLOAK_ADMIN_PASSWORD=''
while IFS= read -r line || [[ -n $line ]]; do
    line=${line%$'\r'}
    [[ -z $line || $line == \#* ]] && continue
    key=${line%%=*}
    val=${line#*=}
    key=${key#export }
    if [[ $val == \"*\" && $val == *\" ]]; then
        val=${val#\"}; val=${val%\"}
    elif [[ $val == \'*\' && $val == *\' ]]; then
        val=${val#\'}; val=${val%\'}
    fi
    case "$key" in
        KEYCLOAK_ADMIN_USERNAME) KEYCLOAK_ADMIN_USERNAME=$val ;;
        KEYCLOAK_ADMIN_PASSWORD) KEYCLOAK_ADMIN_PASSWORD=$val ;;
    esac
done < "$admin_env"

[[ -n $KEYCLOAK_ADMIN_USERNAME && -n $KEYCLOAK_ADMIN_PASSWORD ]] || {
    printf 'incomplete keycloak admin env keys\n' >&2
    exit 1
}

tmp_dir=$(docker compose -f "$compose_file" exec -T keycloak mktemp -d </dev/null)
[[ $tmp_dir == /tmp/* && $tmp_dir != /tmp/ ]] || exit 1
tmp_cfg="$tmp_dir/kcadm.config"
cleanup() {
    docker compose -f "$compose_file" exec -T keycloak sh -c 'rm -f -- "$1/kcadm.config"; rmdir -- "$1"' _ "$tmp_dir" </dev/null >/dev/null 2>&1 || true
    unset KEYCLOAK_ADMIN_USERNAME KEYCLOAK_ADMIN_PASSWORD KC_CLI_PASSWORD
}
trap cleanup EXIT

export KC_CLI_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD"
if ! docker compose -f "$compose_file" exec -T -e KC_CLI_PASSWORD keycloak sh -c '
        umask 077
        exec /opt/keycloak/bin/kcadm.sh config credentials \
            --config "$1" --server http://127.0.0.1:8080 \
            --realm master --user "$2"
    ' _ "$tmp_cfg" "$KEYCLOAK_ADMIN_USERNAME" </dev/null >/dev/null 2>&1; then
    printf 'Keycloak admin authentication failed\n' >&2
    exit 1
fi
unset KEYCLOAK_ADMIN_USERNAME KEYCLOAK_ADMIN_PASSWORD KC_CLI_PASSWORD

kc() {
    local operation=$1
    shift
    docker compose -f "$compose_file" exec -T keycloak \
        /opt/keycloak/bin/kcadm.sh "$operation" --config "$tmp_cfg" "$@" </dev/null 2>/dev/null
}

client_json() {
    local matches client_id representation
    matches=$(kc get clients -r finance-staging -q clientId=rag-finance-web --fields id,clientId) || return
    client_id=$(jq -er 'select(length == 1) | .[0] |
        select(.clientId == "rag-finance-web") | .id |
        select(type == "string" and test("^[A-Fa-f0-9-]{36}$"))' <<<"$matches") || return
    representation=$(kc get "clients/$client_id" -r finance-staging) || return
    jq -c '[{id,clientId,protocol,publicClient,standardFlowEnabled,directAccessGrantsEnabled,
        implicitFlowEnabled,redirectUris,attributes}]' <<<"$representation"
}

realm_json() {
    kc get realms/finance-staging \
        --fields realm,enabled,loginTheme,defaultLocale,registrationAllowed,defaultSignatureAlgorithm
}

check_client_base='length == 1 and (.[0] |
    .clientId == "rag-finance-web" and .protocol == "openid-connect" and
    .publicClient and .standardFlowEnabled and
    .directAccessGrantsEnabled == false and .implicitFlowEnabled == false and
    .redirectUris == ["https://ragfinance.ir/api/auth/callback"] and
    ((.attributes["id.token.signed.response.alg"] // "") | IN("", "RS256")))'

check_client_pkce='length == 1 and (.[0].attributes["pkce.code.challenge.method"] == "S256")'

client=$(client_json) || { printf 'Keycloak client query failed\n' >&2; exit 1; }
jq -e "$check_client_base" <<<"$client" >/dev/null || { printf 'Keycloak client policy mismatch\n' >&2; exit 1; }

if [[ $mode == --apply ]] && ! jq -e "$check_client_pkce" <<<"$client" >/dev/null; then
    client_uuid=$(jq -r '.[0].id' <<<"$client")
    [[ -n $client_uuid && $client_uuid != null ]] || exit 1
    # Preserve the existing attribute map and pass the JSON through stdin.
    if ! jq -c '{attributes: ((.[0].attributes // {}) +
        {"pkce.code.challenge.method": "S256"})}' <<<"$client" |
        docker compose -f "$compose_file" exec -T keycloak \
            /opt/keycloak/bin/kcadm.sh update "clients/$client_uuid" --config "$tmp_cfg" \
            -r finance-staging --merge -f - >/dev/null 2>&1; then
        printf 'Keycloak client PKCE update failed\n' >&2
        exit 1
    fi
    client=$(client_json) || { printf 'Keycloak client query failed\n' >&2; exit 1; }
fi

# Strict #143 invariant: PKCE S256 must be enforced on the client in both --check and --apply.
jq -e "$check_client_base and $check_client_pkce" <<<"$client" >/dev/null ||
    { printf 'Keycloak client PKCE S256 verification failed\n' >&2; exit 1; }

current=$(realm_json)
jq -e '.realm == "finance-staging" and .enabled and .defaultSignatureAlgorithm == "RS256"' \
    <<<"$current" >/dev/null

desired='.loginTheme == "moshaver-mali" and .defaultLocale == "fa" and .registrationAllowed == false'
if [[ $mode == --apply ]] && ! jq -e "$desired" <<<"$current" >/dev/null; then
    kc update realms/finance-staging -s loginTheme=moshaver-mali -s defaultLocale=fa \
        -s registrationAllowed=false >/dev/null
    realm_json | jq -e "$desired" >/dev/null
fi
