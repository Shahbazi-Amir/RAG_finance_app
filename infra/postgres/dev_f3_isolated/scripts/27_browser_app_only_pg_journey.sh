#!/usr/bin/env bash
# Full browser journey in one disposable runner, derived from DB lab and #85 Compose.
set -euo pipefail
[[ "${CI:-}" == true && "${GITHUB_ACTIONS:-}" == true && "${RUNNER_OS:-}" == Linux ]] || exit 70
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
: "${SOURCE_REPO:?}"
[[ "$LAB_ROOT" == "$RUNNER_TEMP"/f3-browser-pg-* && ! -e "$LAB_WORK/restore-tested.marker" ]] || exit 70
export F3_PRIVATE_NETWORK="${LAB_PROJECT}_private" F3_BROWSER_PROJECT="${LAB_PROJECT}_browser"
[[ "$(docker network inspect -f '{{.Internal}}' "$F3_PRIVATE_NETWORK")" == true ]] || exit 70
[[ "$(docker network inspect -f '{{index .Labels "com.docker.compose.project"}}' "$F3_PRIVATE_NETWORK")" == "$LAB_PROJECT" ]] || exit 70
sha="$(git -C "$SOURCE_REPO" rev-parse HEAD)"
export F3_SIGNED_IMAGE="f3-browser-api:$sha" F3_WEB_IMAGE="f3-browser-web:$sha" F3_BROWSER_IMAGE="f3-browser-probe:$sha"
export F3_BROWSER_ROOT="$LAB_WORK/browser-journey" F3_CURSOR_KEY="$(openssl rand -hex 32)"
export F3_STORE="$F3_BROWSER_ROOT/store-source"
mkdir -m 0700 "$F3_BROWSER_ROOT"
for dir in pki api bootstrap web ingress idp realm browser store-source store-restore; do mkdir -m 0700 "$F3_BROWSER_ROOT/$dir"; done
cd "$F3_BROWSER_ROOT"
stack(){ docker compose -f "$SOURCE_REPO/infra/phase3_l1/compose.app-only.browser-lab.yml" "$@"; }
cleanup(){
  stack --profile probe down --remove-orphans >/dev/null 2>&1 || true
  sudo rm -rf -- "$F3_BROWSER_ROOT"
}
trap cleanup EXIT
openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 1 -subj '/CN=F3 browser ephemeral CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign' -keyout pki/ca.key -out pki/ca.crt >/dev/null 2>&1
for peer in api bootstrap bff ingress idp; do
  openssl req -newkey rsa:2048 -nodes -subj "/CN=$peer" -keyout "pki/$peer.key" -out "pki/$peer.csr" >/dev/null 2>&1
  printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n' > "pki/$peer.ext"
  case "$peer" in
    api) printf 'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:signed-api\n';;
    bootstrap) printf 'extendedKeyUsage=serverAuth\nsubjectAltName=IP:127.0.0.1\n';;
    ingress) printf 'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:ragfinance.ir\n';;
    idp) printf 'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:lab-idp.test\n';;
    bff) printf 'extendedKeyUsage=clientAuth\n';;
  esac >> "pki/$peer.ext"
  openssl x509 -req -in "pki/$peer.csr" -CA pki/ca.crt -CAkey pki/ca.key -CAcreateserial -days 1 -sha256 -extfile "pki/$peer.ext" -out "pki/$peer.crt" >/dev/null 2>&1
  openssl verify -CAfile pki/ca.crt "pki/$peer.crt" >/dev/null
done
cp pki/{api.crt,api.key,ca.crt} api/
cp pki/{bootstrap.crt,bootstrap.key,ca.crt} bootstrap/
cp pki/{bff.crt,bff.key,ca.crt} web/
cp pki/{ingress.crt,ingress.key} ingress/
cp pki/{idp.crt,idp.key} idp/
cp pki/ca.crt browser/
cp "$LAB_SECRETS/ca.crt" api/pg-ca.crt
cp "$LAB_SECRETS/ca.crt" bootstrap/pg-ca.crt
cp "$SOURCE_REPO/infra/phase3_l1/lab/https-ingress.mjs" ingress/
for peer in api bootstrap; do
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "web/$peer-sign.key" >/dev/null 2>&1
  openssl pkey -in "web/$peer-sign.key" -pubout -out "$peer/sign.pub" >/dev/null 2>&1
done
leaf="$(openssl x509 -in web/bff.crt -outform DER | sha256sum | cut -d' ' -f1)"
openssl rand -hex 32 > web/proof
cp web/proof ingress/proof
openssl rand -hex 32 > web/csrf
python3 - <<'PY'
import base64,json,secrets,uuid
from pathlib import Path
Path("web/alias").write_text(secrets.token_urlsafe(32))
Path("bootstrap/seal").write_bytes(base64.urlsafe_b64encode(secrets.token_bytes(32)))
users={k:dict(username="lab-"+k+"@example.invalid",password="Az9!"+secrets.token_urlsafe(24),subject=str(uuid.uuid4())) for k in ("a","b")}
Path("browser/users.json").write_text(json.dumps(users))
realm=dict(realm="f3-lab",enabled=True,sslRequired="all",registrationAllowed=False,verifyEmail=False,
  clients=[dict(clientId="f3-lab-web",enabled=True,protocol="openid-connect",publicClient=True,
    standardFlowEnabled=True,directAccessGrantsEnabled=False,implicitFlowEnabled=False,
    redirectUris=["https://ragfinance.ir/api/auth/callback"],attributes={"pkce.code.challenge.method":"S256"},
    defaultClientScopes=["profile","email","roles","web-origins","acr"])],
  users=[dict(id=u["subject"],username=u["username"],email=u["username"],enabled=True,emailVerified=True,
    firstName="Lab",lastName=k,credentials=[dict(type="password",value=u["password"],temporary=False)]) for k,u in users.items()])
Path("realm/f3-lab-realm.json").write_text(json.dumps(realm))
p=dict(public_origin="https://ragfinance.ir",idp_authorization_origin="https://lab-idp.test",
 bootstrap_origin="https://127.0.0.1:8444",product_origin="https://signed-api:8443",store_dir="/run/aliases",
 proxy_proof_file="/run/web/proof",csrf_secret_file="/run/web/csrf",alias_key_file="/run/web/alias",
 bootstrap_sign_key_file="/run/web/bootstrap-sign.key",product_sign_key_file="/run/web/api-sign.key",
 tls_ca_file="/run/web/ca.crt",tls_client_cert_file="/run/web/bff.crt",tls_client_key_file="/run/web/bff.key",
 bootstrap_issuer="urn:f3:lab:bootstrap-bff",bootstrap_audience="urn:f3:lab:bootstrap",bootstrap_kid="lab-bootstrap",
 product_issuer="urn:f3:lab:product-bff",product_audience="urn:f3:lab:product",product_kid="lab-product",send_mode="DISABLED")
Path("web/config.json").write_text(json.dumps(p))
PY
# Keep only the required signing keys/CA and role DSNs in each service mount.
configs(){
  sudo chown -R "$(id -u):$(id -g)" api bootstrap
  python3 - "$LAB_WORK" "$1" "$2" "$leaf" <<'PY'
import json,sys
from pathlib import Path
work,host,db,leaf=sys.argv[1:]
def dsn(role):
    secret=(Path(work)/(role+".password")).read_text().strip()
    return f"host={host} port=5432 dbname={db} user={role} password={secret} sslmode=verify-full sslrootcert=ROOT/pg-ca.crt connect_timeout=3"
def base(service,port,bind,issuer,audience,kid):
    root="/run/secrets" if service=="api" else "/run/bootstrap"
    return dict(listen_host=bind,listen_port=port,server_tls_cert_file=root+"/"+service+".crt",
      server_tls_key_file=root+"/"+service+".key",trusted_bff_ca_file=root+"/ca.crt",
      bff_leaf_cert_sha256=leaf,bff_issuer=issuer,bff_audience=audience,bff_kid=kid,
      bff_rs256_public_key_file=root+"/sign.pub")
a=base("api",8443,"0.0.0.0","urn:f3:lab:product-bff","urn:f3:lab:product","lab-product")
a.update(contract_version="api.private_app_only_asgi.v1",history_dsn=dsn("history_app").replace("ROOT","/run/secrets"),revoke_dsn=dsn("auth_revoker").replace("ROOT","/run/secrets"))
Path("api/phase3-app-only.json").write_text(json.dumps(a))
b=base("bootstrap",8444,"127.0.0.1","urn:f3:lab:bootstrap-bff","urn:f3:lab:bootstrap","lab-bootstrap")
issuer="https://lab-idp.test/realms/f3-lab"
b.update(contract_version="api.private_oidc_bootstrap_asgi.v1",seal_key_file="/run/bootstrap/seal",
 seal_key_kid="lab-seal",idp_ca_file="/run/bootstrap/ca.crt",oidc_issuer=issuer,
 oidc_authorization_endpoint=issuer+"/protocol/openid-connect/auth",oidc_token_endpoint=issuer+"/protocol/openid-connect/token",
 oidc_jwks_uri=issuer+"/protocol/openid-connect/certs",oidc_client_id="f3-lab-web",
 oidc_redirect_uri="https://ragfinance.ir/api/auth/callback")
for label,role in dict(replay="auth_trust_api",bootstrap="auth_login_bootstrap",claim_reader="auth_login_claim_reader",
 issuer="auth_login_issuer",mapper="auth_mapper",binder="auth_login_binder",reader="auth_login_reader").items():
    b["dsn_"+label]=dsn(role).replace("ROOT","/run/bootstrap")
Path("bootstrap/config.json").write_text(json.dumps(b))
PY
  chmod 0600 api/* bootstrap/*
  sudo chown -R 11001:11001 api bootstrap
}
# Capture expected subjects before handing the credentials to the browser UID.
read -r sub_a sub_b < <(python3 -c 'import json; u=json.load(open("browser/users.json")); print(u["a"]["subject"],u["b"]["subject"])')
chmod 0600 web/* ingress/* browser/* idp/* realm/*
sudo chown -R 11003:11003 web ingress store-source store-restore
sudo chown -R 11005:11005 browser
sudo chown -R 1000:0 idp realm
configs demo-db rag_finance_f3_lab
docker build --platform linux/amd64 -f "$SOURCE_REPO/infra/phase3_l1/Dockerfile.api.signed" --build-arg BASE=docker.io/library/python:3.13.5 --build-arg "SOURCE_SHA=$sha" -t "$F3_SIGNED_IMAGE" "$SOURCE_REPO"
docker build --platform linux/amd64 -f "$SOURCE_REPO/infra/phase3_l1/Dockerfile.web" --build-arg "SOURCE_SHA=$sha" -t "$F3_WEB_IMAGE" "$SOURCE_REPO"
docker build --platform linux/amd64 -f "$SOURCE_REPO/infra/phase3_l1/lab/Dockerfile.browser" -t "$F3_BROWSER_IMAGE" "$SOURCE_REPO"
docker pull quay.io/keycloak/keycloak@sha256:7e66a96e4739239070aeaf72e4c5decf0f7f682cfc725b9f7ea2b336eaba38b3
stack --profile probe config -q
stack up -d --no-build idp api web bootstrap ingress
# Actual Keycloak discovery with verified CA before beginning browser login.
stack run --rm --no-deps browser python -c '
import ssl,urllib.request,time
ctx=ssl.create_default_context(cafile="/run/browser/ca.crt")
for i in range(90):
    try:
        with urllib.request.urlopen("https://lab-idp.test/realms/f3-lab/.well-known/openid-configuration",context=ctx,timeout=3) as r:
            if r.status==200: break
    except Exception: time.sleep(2)
else: raise SystemExit("IDP_DISCOVERY_NOT_READY")
print("REAL_IDP_DISCOVERY_TLS_PASS")
'
# Gate BOTH source and restored startup on the actual product DB and TLS
# listeners. No browser login retry, no mocked readiness or altered trust.
wait_stack() {
  local ready=0
  for i in {1..90}; do
    if stack exec -T web node -e '
const https=require("node:https"),fs=require("node:fs"),tls=require("node:tls");
const material={ca:fs.readFileSync("/run/web/ca.crt"),cert:fs.readFileSync("/run/web/bff.crt"),key:fs.readFileSync("/run/web/bff.key"),rejectUnauthorized:true};
const timer=setTimeout(()=>process.exit(1),5000);
const b=tls.connect({...material,host:"127.0.0.1",port:8444,checkServerIdentity:(_,c)=>tls.checkServerIdentity("127.0.0.1",c)},()=>{
  b.end();
  const q=https.get("https://signed-api:8443/internal/ready",material,r=>{
    let raw="";r.on("data",x=>raw+=x);r.on("end",()=>{
      try{const j=JSON.parse(raw);if(r.statusCode!==200||j.history_db!=="verified")process.exit(1);clearTimeout(timer);process.exit(0)}catch{process.exit(1)}
    });
  });q.on("error",()=>process.exit(1));
});b.on("error",()=>process.exit(1));' >/dev/null 2>&1; then
      ready=1; break
    fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo STACK_DEPENDENCY_READINESS_FAILED
    stack ps -a --format json | python3 -c 'import json,sys; [print(x.get("Service"),x.get("State"),x.get("ExitCode")) for l in sys.stdin if l.strip() for x in [json.loads(l)]]' || true
    return 70
  fi
  echo STACK_REAL_BOOTSTRAP_TLS_AND_PRODUCT_PG_READY_PASS
}
wait_stack
# Cross-service negative checks in the very same job as the browser witness.
probe_boundary(){
  stack exec -T web node -e '
const https=require("node:https"),fs=require("node:fs");
const ca=fs.readFileSync("/run/web/ca.crt");
const cert=fs.readFileSync("/run/web/bff.crt"),key=fs.readFileSync("/run/web/bff.key");
function get(url,opt={}){return new Promise((resolve,reject)=>{
  const q=https.get(url,{ca,rejectUnauthorized:true,servername:new URL(url).hostname,timeout:5000,...opt},r=>{r.resume();r.on("end",()=>resolve(r.statusCode));});
  q.on("timeout",()=>q.destroy(new Error("timeout")));q.on("error",reject);
});}
(async()=>{
  let live=false; for(let i=0;i<60;i++){try{live=(await get("https://ragfinance.ir/login"))===200}catch{} if(live)break;await new Promise(r=>setTimeout(r,1000));}
  if(!live)throw Error("ingress");
  console.log("BOUNDARY_INGRESS_TLS_PASS");
  if(await get("https://ragfinance.ir/login",{headers:{host:"wrong.invalid"}})!==421)throw Error("host");
  console.log("BOUNDARY_HOST_REJECT_PASS");
  if(await get("https://lab-idp.test/realms/f3-lab/.well-known/openid-configuration")!==200)throw Error("idp");
  console.log("BOUNDARY_IDP_TLS_PASS");
  if(await get("https://signed-api:8443/v1/conversations",{cert,key,headers:{Authorization:"BFF-Assertion invalid"}})!==401)throw Error("proof");
  console.log("BOUNDARY_INVALID_PROOF_401_PASS");
  let denied=false;
  try{denied=(await get("https://signed-api:8443/internal/ready"))!==200}catch{denied=true}
  if(!denied)throw Error("peer");
  console.log("BOUNDARY_NO_PEER_DENIED_PASS");
  const r=await fetch("http://127.0.0.1:3000/login",{headers:{"x-forwarded-host":"ragfinance.ir","x-forwarded-proto":"https","x-auth-staging-proxy-proof":"invalid"}});
  if(r.status!==503)throw Error("direct-web");
  console.log("SAME_STACK_TLS_HOST_IDP_INVALID_PROOF_NO_CERT_DIRECT_WEB_PASS");
})().catch(e=>{console.error("BOUNDARY_FAILED",["ingress","host","idp","proof","peer","direct-web"].includes(e.message)?e.message:typeof e.code==="string"&&/^[A-Z0-9_]+$/.test(e.code)?e.code:"transport");process.exit(1)});'
}
probe_boundary
stack run --rm --no-deps browser python /opt/probe.py map
# Identity links must have been created by real verified OIDC, not pre-seeded.
issuer=https://lab-idp.test/realms/f3-lab
owner_a="$(dbpsql -Atc "SELECT owner_id FROM auth_l1.identity_links WHERE issuer='$issuer' AND subject='$sub_a'")"
owner_b="$(dbpsql -Atc "SELECT owner_id FROM auth_l1.identity_links WHERE issuer='$issuer' AND subject='$sub_b'")"
[[ "$owner_a" =~ ^[A-Za-z0-9_-]{1,64}$ && "$owner_b" =~ ^[A-Za-z0-9_-]{1,64}$ && "$owner_a" != "$owner_b" ]] || { echo REAL_IDP_SUBJECT_MAP_DENIED; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM auth_l1.identity_links WHERE issuer='$issuer'")" == 2 ]] || exit 70
[[ "$(dbpsql -Atc 'SELECT count(*) FROM history_l1.conversations')" == 0 ]] || exit 70
dbpsql -q -v a="$owner_a" -v b="$owner_b" <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,created_at) VALUES
(:'a','browser-a-1','lab A1',clock_timestamp()-interval '3 minutes'),
(:'a','browser-a-2','lab A2',clock_timestamp()-interval '2 minutes'),
(:'a','browser-a-3','lab A3',clock_timestamp()-interval '1 minute'),
(:'b','browser-b-1','lab B1',clock_timestamp());
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body) VALUES
(:'a','browser-msg-a','browser-a-1','user','lab browser A'),
(:'b','browser-msg-b','browser-b-1','user','lab browser B');
SQL
echo REAL_OIDC_SUBJECTS_TO_SQL_HISTORY_SEED_PASS
snapshot(){
  dbpsql -Atc "SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||(SELECT count(*) FROM history_l1.messages)||'|'||(SELECT count(*) FROM history_l1.send_receipts)||'|'||(SELECT count(*) FROM history_l1.execution_attempts)||'|'||(SELECT count(*) FROM history_l1.answers)"
}
lineage(){
  dbpsql -Atc "SELECT owner_id||'|'||id||'|'||title FROM history_l1.conversations ORDER BY owner_id,id; SELECT owner_id||'|'||id||'|'||conversation_id||'|'||body FROM history_l1.messages ORDER BY owner_id,id"
}
revoked(){ dbpsql -Atc "SELECT count(*) FROM auth_l1.sessions WHERE owner_id='$owner_a' AND status='revoked'"; }
[[ "$(snapshot)" == '4|2|0|0|0' ]] || exit 70
before="$(lineage)"
[[ "$(revoked)" == 0 ]] || exit 70
stack run --rm --no-deps browser python /opt/probe.py source
[[ "$(snapshot)" == '4|2|0|0|0' && "$(lineage)" == "$before" && "$(revoked)" == 1 ]] || exit 70
# Witness the real Product dependency outage in the SAME browser job.
compose stop lab-db >/dev/null
stack exec -T web node -e '
const https=require("node:https"),fs=require("node:fs");
const material={ca:fs.readFileSync("/run/web/ca.crt"),cert:fs.readFileSync("/run/web/bff.crt"),key:fs.readFileSync("/run/web/bff.key"),rejectUnauthorized:true,timeout:15000};
const q=https.get("https://signed-api:8443/internal/ready",material,r=>{r.resume();r.on("end",()=>process.exit(r.statusCode===503?0:1));});
q.on("timeout",()=>q.destroy());q.on("error",()=>process.exit(1));'
echo SAME_STACK_PG_OUTAGE_503_PASS
compose start lab-db >/dev/null
wait_stack
[[ "$(snapshot)" == '4|2|0|0|0' && "$(lineage)" == "$before" ]] || exit 70
# Stop live clients, restore populated database into independent cluster, then
# recreate listeners with new DB hostname and fresh Web alias store.
stack stop ingress bootstrap web api
stack rm -f ingress bootstrap web api
bash "$BUNDLE_ROOT/scripts/06_backup_restore_independent.sh"
export DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore
[[ "$(snapshot)" == '4|2|0|0|0' && "$(lineage)" == "$before" && "$(revoked)" == 1 ]] || exit 70
configs restore-db rag_finance_f3_lab_restore
export F3_STORE="$F3_BROWSER_ROOT/store-restore"
stack up -d --no-build api web bootstrap ingress
wait_stack
probe_boundary
stack run --rm --no-deps browser python /opt/probe.py restore
[[ "$(snapshot)" == '4|2|0|0|0' && "$(lineage)" == "$before" && "$(revoked)" == 2 ]] || exit 70
printf 'BROWSER_SQL_LINEAGE_COUNTS_REVOKE_RESTORE=PASS\nSOURCE_SHA=%s\n' "$sha"
for image in "$F3_SIGNED_IMAGE" "$F3_WEB_IMAGE" "$F3_BROWSER_IMAGE" quay.io/keycloak/keycloak@sha256:7e66a96e4739239070aeaf72e4c5decf0f7f682cfc725b9f7ea2b336eaba38b3; do
  printf 'IMAGE_ID=%s\n' "$(docker image inspect -f '{{.Id}}' "$image")"
done
echo NO_ENGINE_NO_011_NO_PRODUCTION_NO_CENTRAL_ACCEPTANCE
