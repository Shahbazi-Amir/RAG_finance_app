#!/usr/bin/env bash
set -euo pipefail

# The operator establishes the existing kcadm session interactively beforehand.
# Retain the existing realm, users, flows, redirect URIs and client settings.
compose_file=${1:?Compose file required}
mode=${2:---check}
kc() {
    docker compose -f "$compose_file" exec -T keycloak /opt/keycloak/bin/kcadm.sh "$@" 2>/dev/null
}
realm() {
    kc get realms/finance-staging --fields realm,enabled,loginTheme,defaultLocale,registrationAllowed,defaultSignatureAlgorithm
}
kc get clients -r finance-staging -q clientId=rag-finance-web \
    --fields clientId,protocol,publicClient,standardFlowEnabled,directAccessGrantsEnabled,implicitFlowEnabled,redirectUris,attributes |
    jq -e 'length == 1 and (.[0] |
        .clientId == "rag-finance-web" and .protocol == "openid-connect" and
        .publicClient and .standardFlowEnabled and
        .directAccessGrantsEnabled == false and .implicitFlowEnabled == false and
        .redirectUris == ["https://ragfinance.ir/api/auth/callback"] and
        .attributes["pkce.code.challenge.method"] == "S256" and
        ((.attributes["id.token.signed.response.alg"] // "") | IN("", "RS256")))' >/dev/null
current=$(realm)
jq -e '.realm == "finance-staging" and .enabled and .defaultSignatureAlgorithm == "RS256"' \
    <<<"$current" >/dev/null
desired='.loginTheme == "moshaver-mali" and .defaultLocale == "fa" and .registrationAllowed == false'
if [[ $mode == --apply ]] && ! jq -e "$desired" <<<"$current" >/dev/null; then
    kc update realms/finance-staging -s loginTheme=moshaver-mali -s defaultLocale=fa \
        -s registrationAllowed=false >/dev/null
    realm | jq -e "$desired" >/dev/null
fi
