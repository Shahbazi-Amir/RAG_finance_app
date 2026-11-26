# Arvan invited staging candidate

Execute on `rag-finance-arvan` only after approval of this Git diff, the deployment inputs, database grants, ingress change and one paid smoke request. The rollout targets `db55_empty_clone` on port 55437. Use a named two-account test window before opening the approved invite list. Confirm that the invited group may view quotes from the entire pinned corpus, and that operators have approved sending a question and its retrieved context to the pinned Arvan Gateway endpoint. Keycloak self-registration stays off. Four requests can be in flight across one serial retrieval process and at most two Gateway HTTP calls. A full queue returns 503 before a durable reservation. This rollout has no 100-user load evidence.

## 1. Review and stage the release

On the review machine:

```sh
git diff 0e46ef3..HEAD -- apps infra src tests coordination/tasks/AGENT-ARVAN-CANDIDATE-01.md
git rev-parse HEAD
git archive --format=tar HEAD apps infra src packages locks > /private/tmp/rag-arvan-candidate.tar
```

After approval, transfer that tar with
`scp /private/tmp/rag-arvan-candidate.tar rag-finance-arvan:/var/tmp/rag-arvan-candidate.tar`.
Independently approve the Ubuntu reference, dependency caches, Keycloak mirror reachability and the source SHA below. Retain the current image ID and release configuration in the privileged change record for rollback. Verify the source paths, topology, Unix IDs and free ports before making changes. The commands assume the clean release directory, one API instance and no other process advertising these ports.

```sh
sudo install -d -m 0755 -o "$(id -un)" -g "$(id -gn)" /opt/rag-finance-staging/phase3/arvan-candidate
tar --no-same-owner -xf /var/tmp/rag-arvan-candidate.tar -C /opt/rag-finance-staging/phase3/arvan-candidate
cd /opt/rag-finance-staging/phase3/arvan-candidate
TOOLS=/opt/rag-finance-staging/phase3/tools/bin
"$TOOLS/python3.13" --version
"$TOOLS/node" --version
docker compose version
sudo ss -ltn
```

The archive includes tracked source only. Stage the existing byte-identical engine as
`artifacts/nb23-v4-bundle/engine.py` in the candidate release from the approved
offline bundle. The same source goes into the image. Reuse the existing
`RAG_finance`, `.python`, ONNX venv, HF cache, NB22E output tree, verified C028
receipt inside NB22E outputs and the C340 template in its sibling directory.
The gateway-only API loads its configuration via a systemd credential. The
worker has no network and masks the repo's `.env` if that file exists.
Use the existing Python 3.13 API dependencies or install the checked lock from the
vetted linux/amd64 wheelhouse with the command below. Stage the input engine and
build Web as a release operator with access to the candidate directory. Never
copy the original source repository, `.env`, the corpus, or any logs into a Docker
build context.

```sh
printf '%s\n' '91a1a34628f221f7f8bc892a0fb6a917328817dae1328856d84aad7f880f406e  artifacts/nb23-v4-bundle/engine.py' | sha256sum -c -
"$TOOLS/python3.13" -m pip check
# Only if runtime dependencies are absent. WHEELHOUSE is an approved local directory.
"$TOOLS/python3.13" -m pip install --no-index --only-binary=:all: --find-links "$WHEELHOUSE" --require-hashes -r locks/requirements-api.lock
(
  cd apps/web
  export PATH="$TOOLS:$PATH" NEXT_TELEMETRY_DISABLED=1
  npm ci --offline
  npm run typecheck
  npm run build
)
ctx=$(mktemp -d)
install -D infra/nb23-v4/Dockerfile.arvan-worker "$ctx/infra/nb23-v4/Dockerfile.arvan-worker"
install -t "$ctx/infra/nb23-v4" infra/nb23-v4/{worker.py,worker_startup_state.py}
install -D -m 0444 artifacts/nb23-v4-bundle/engine.py "$ctx/artifacts/nb23-v4-bundle/engine.py"
sudo docker image tag rag-nb23-worker:arvan-cp45 rag-nb23-worker:arvan-cp45-before-candidate
sudo docker pull docker.arvancloud.ir/library/ubuntu:24.04
sudo env DOCKER_BUILDKIT=0 docker build --network none --build-arg UBUNTU_IMAGE=docker.arvancloud.ir/library/ubuntu:24.04 -f "$ctx/infra/nb23-v4/Dockerfile.arvan-worker" -t rag-nb23-worker:arvan-cp45 "$ctx"
```

Validate the installed runtime, offline build inputs and bind mounts before moving
to the database step. Docker 29's legacy builder can build this Dockerfile with
ordinary COPY. Record the resolved mirror image ID and clean the temporary build
context per host policy after the review.

## 2. Apply the exact 011 claim contract

The CI job `.github/workflows/api-session-011.yml` is a Login/History/Revoke test
number. The contract source is DB #56, commit
`b0ba6dbf6100109cb58f8cb49da808839d68c5f0`, as used in
`.github/workflows/foundation-api53-db56-claim011-http.yml`. The runbook applies and verifies the migration explicitly. An empty `history_l1`
function catalog is compatible with 001/002, which use table operations and RLS.
Inventory Auth functions and role attributes independently.

```sh
db55() { sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/lib/postgresql/db55_clone_socket -p 55437 -d db55_empty_clone "$@"; }
db55 -c "SELECT current_database(),current_setting('server_version_num'),to_regclass('history_l1.external_dispatch_claims') IS NOT NULL AS claim_table,to_regprocedure('history_l1.claim_external_dispatch(text,text,text)') IS NOT NULL AS claim_function"
db55 -c "SELECT rolname,rolsuper,rolbypassrls,rolinherit,rolcanlogin FROM pg_roles WHERE rolname IN ('history_migrator','history_app','history_dispatch_reporter','history_dispatch_reconciler') ORDER BY rolname"
test "$(git hash-object infra/postgres/migrations/011_external_dispatch_claim.up.sql)" = 031d2f438f000154eb4e2b374ce42181b3d812b3
```

Take and verify a restricted backup before DDL. Review
`infra/postgres/staging/db55_no_dispatch_bridge.sql` and only apply that exact
bridge if its approved grants are absent. Provision missing roles separately
through the existing DBA workflow. The two 011 audit roles can be NOLOGIN until
their independently approved operators are provisioned. Use the original
`history_migrator` schema owner with BYPASSRLS as the 011 definer; stop if the
clone's schema ownership or privileges differ. If both claim objects already
exist, verify the reviewed definition instead of reapplying SQL. A partial state
requires DBA reconciliation before cutover.

```sh
umask 077
install -d -m 0700 "$HOME/rag-arvan-backup"
sudo -u postgres pg_dump -Fc -h /var/lib/postgresql/db55_clone_socket -p 55437 db55_empty_clone > "$HOME/rag-arvan-backup/db55-before-011.dump"
chmod 0600 "$HOME/rag-arvan-backup/db55-before-011.dump"
pg_restore -l "$HOME/rag-arvan-backup/db55-before-011.dump" >/dev/null
# Run only for individually missing roles after explicit approval of cluster-wide DDL.
db55 -c 'CREATE ROLE history_dispatch_reporter NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE'
db55 -c 'CREATE ROLE history_dispatch_reconciler NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE'
# The next command is conditional on required grants and approval of the exact bridge.
db55 -f infra/postgres/staging/db55_no_dispatch_bridge.sql
# Run when both 011 objects were absent and the DBA verified roles and ownership.
db55 -c 'SET ROLE history_migrator' -f infra/postgres/migrations/011_external_dispatch_claim.up.sql
db55 -v db55_phase=live_011 -f infra/postgres/staging/db55_verify_staging.sql
```

Use each existing restricted Unix-socket DSN with its own identity and GUC
boundaries. The PostgreSQL verifier and both API startup checks must succeed before
enabling sends. Keep reporter and reconciler privileges separate from History.
An ambiguous generation leaves the one-shot DB claim reserved for separately
authorized reconciliation. A replay, process restart or poll consumes no
additional Gateway call.

## 3. Prepare TLS, credentials and Keycloak

Verify current listeners, the staging IdP certificate and the host package
repository. If TCP 80 is available with Nginx still masked, use Certbot
standalone for the initial certificate. The vhost serves the webroot path for
renewal after cutover. Set `ACME_EMAIL` to the approved operator contact.
[Certbot standalone and webroot documentation](https://eff-certbot.readthedocs.io/en/stable/using.html)

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends certbot
sudo certbot certonly --standalone --non-interactive --agree-tos --email "$ACME_EMAIL" --cert-name ragfinance.ir -d ragfinance.ir
sudo install -d -m 0755 /var/lib/rag-arvan-acme
sudo openssl x509 -in /etc/letsencrypt/live/ragfinance.ir/fullchain.pem -noout -checkhost ragfinance.ir
sudo openssl x509 -in /etc/nginx/tls/ragfinance/idp-staging/fullchain.pem -noout -checkhost idp-staging.ragfinance.ir
```

With the approved Ops secret workflow, stage fresh candidate configs outside the
existing staging directory under `/etc/rag-arvan-candidate`. Give each systemd
service user read access to its own 0600 config and private key material only.
Existing files can be referenced if ownership and traversal already allow it.
The unit templates expect system users/groups `rag-arvan-api`,
`rag-arvan-bootstrap` and `rag-arvan-web`. Create or map those accounts before
installing units, verify only the approved account can access the worker socket,
and verify credential inputs are regular, non-symlink 0600 files. Never use shell tracing, `nginx -T`, an environment dump or CLI passwords
during this procedure.

| Candidate file | Non-secret settings |
| --- | --- |
| `api-private.json` | Retain the current configuration version, API bind `127.0.0.1:18443`, pinned BFF mTLS leaf, trusted CA, RS256 verifier and role-specific DSNs. Add `"execution_mode": "LIVE_DISPATCH"`. |
| `bootstrap-private.json` | Use `api.private_oidc_bootstrap_asgi.v1`, bind `127.0.0.1:18444`, a valid IP SAN server cert and matching private trust. Set the issuer and its exact /auth, /token and /certs endpoints, the public client ID `rag-finance-web` and fixed callback below. Provision seal key, IdP CA and seven DSNs through the existing Bootstrap contract. |
| `web-private.json` | Set `public_origin=https://ragfinance.ir`, `idp_authorization_origin=https://idp-staging.ragfinance.ir`, `bootstrap_origin=https://127.0.0.1:18444`, `product_origin=https://127.0.0.1:18443`, `store_dir=/var/lib/rag-arvan-web`. Retain exact independent Bootstrap and Product signer trust. Start with `send_mode=DISABLED`. |
| `gateway.env` | Root-owned 0600 file holding only the approved `ARVAN_GATEWAY_URL` and `ARVAN_GATEWAY_API_KEY`. Provision through the protected workflow. |
| `keycloak.env`, `keycloak-db.env` | Root-owned 0600 env files with a shared DB credential in `KC_DB_PASSWORD` and `POSTGRES_PASSWORD`. Keycloak can receive its initial temporary administrative credentials through `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` in the protected Keycloak file. Rotate/remove the temporary administrator after realm setup and recreate Keycloak without its bootstrap variables. |

Use production-mode Keycloak backed by a dedicated Postgres volume. Check the
Runflare Quay mirror and Arvan Docker Hub mirror from the host before proceeding.
The explicit proxy subnet must be free. Confirm Nginx's connection arrives from
the bridge gateway in this topology. Keep admin access on the host.
[Mirror routing](https://runflare.com/mirrors/docker-mirror/) · [Keycloak proxy settings](https://www.keycloak.org/server/reverseproxy)

```sh
sudo docker compose -f infra/arvan-staging/keycloak.compose.yml pull
sudo docker compose -f infra/arvan-staging/keycloak.compose.yml up -d --pull never --wait
sudo docker compose -f infra/arvan-staging/keycloak.compose.yml ps
curl --fail --silent --show-error --retry 30 --retry-delay 2 --retry-all-errors http://127.0.0.1:18081/realms/master/.well-known/openid-configuration >/dev/null
```

Use the loopback Keycloak administration connection via the existing protected
Ops export or Keycloak CLI within the container. If this is a fresh realm,
authenticate interactively so passwords stay out of history and argv.

```sh
kc() { sudo docker compose -f infra/arvan-staging/keycloak.compose.yml exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc config credentials --server http://127.0.0.1:8080 --realm master --user "$KEYCLOAK_ADMIN_USER"
kc create realms -s realm=finance-staging -s enabled=true -s registrationAllowed=false -s resetPasswordAllowed=false
kc create clients -r finance-staging -s clientId=rag-finance-web -s protocol=openid-connect -s publicClient=true -s standardFlowEnabled=true -s directAccessGrantsEnabled=false -s implicitFlowEnabled=false -s 'redirectUris=["https://ragfinance.ir/api/auth/callback"]' -s 'webOrigins=["https://ragfinance.ir"]' -s 'attributes={"pkce.code.challenge.method":"S256"}'
```

The realm issuer is `https://idp-staging.ragfinance.ir/realms/finance-staging`.
Append `/protocol/openid-connect/` and then `auth`, `token` or `certs` to the issuer. Admit only the approved smoke users first. For an
existing realm/client, compare and reconcile the exact settings without
recreating its users or rotating the issuer. Public access to master and admin
endpoints is denied by the candidate vhost.

## 4. Install services and validate with Send disabled

Verify existing vhost conflicts and the two certificate/key paths, and confirm
`conf.d/*.conf` is included by the active Nginx configuration. Resolve any
existing conflicting vhost under separate reviewed configuration. Use the
systemd and Nginx templates only after the path and permission checks.

```sh
sudo install -m 0644 infra/arvan-staging/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start rag-arvan-worker
sudo systemctl start rag-arvan-api
sudo systemctl start rag-arvan-bootstrap-oidc
sudo systemctl start rag-arvan-web
sudo "$TOOLS/python3.13" -B infra/arvan-staging/render-nginx-proof.py
sudo install -m 0644 infra/arvan-staging/nginx/*.conf /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl unmask nginx.service
sudo systemctl start nginx.service
curl --fail --silent --show-error https://idp-staging.ragfinance.ir/realms/finance-staging/.well-known/openid-configuration >/dev/null
curl --fail --silent --show-error https://ragfinance.ir/api/product-capabilities
sudo certbot reconfigure --cert-name ragfinance.ir --webroot --webroot-path /var/lib/rag-arvan-acme
sudo certbot renew --cert-name ragfinance.ir --dry-run
```

Wait for the worker's ready socket and the API unit to be active, with one
container and one API process. Compare the public capabilities response to
`DISABLED`. Check that public API and Bootstrap RPC paths return 404, signed
internals require trusted mTLS and direct loopback Web requests cannot supply
authentication authority. In a browser, verify initial login and owner-scoped
History, and verify the send control is disabled. Arrange Nginx reload on
successful renewal as part of the approved renewal configuration.

## 5. Enable, smoke and stop conditions

Only after the initial checks and budget approval, use the 0600 provisioning
workflow to publish the candidate `web-private.json` with
`send_mode=LIVE_DISPATCH`. It is read server-side on each request. If an app-only
policy flag is installed in the Web process, review its removal before proceeding.

```sh
curl --fail --silent --show-error https://ragfinance.ir/api/product-capabilities
sudo systemctl is-active rag-arvan-worker rag-arvan-api rag-arvan-bootstrap-oidc rag-arvan-web nginx
```

1. Log in as the first approved account and send exactly one approved Persian
   finance question. In Network, save only the POST status and opaque
   correlation for the privileged operator. Expect HTTP 202 and subsequent
   GETs, with one claim row and a provisional result. Confirm that an ANSWER
   carries Persian claim text and verbatim quotes attached to chunk IDs, or
   capture a producer NO_ANSWER reason as incomplete evidence for the ANSWER
   smoke. Record a provider count of one through the approved redacted audit.
2. Reload and confirm GET-only recovery in the same session within the
   15-minute result window. From the second account verify the first account's
   correlators yield 404. Revoke the first session and confirm its result is
   inaccessible. Review duplicate/unknown cases locally; avoid a second live
   POST merely to diagnose a timeout.
3. On unexpected TLS, Auth, PG, provider or usage evidence, set
   `send_mode=DISABLED` in the candidate Web profile immediately. Check the
   capability endpoint. Allow active work to settle or stop the API and
   worker with the caveat that in-flight provider outcomes may be ambiguous.
   Preserve claim rows. Restore the prior reviewed vhosts/configs and image as
   needed. If reverting ingress entirely, use the previous approved service
   state. Do not drop 011 to reset a claim.

```sh
curl --fail --silent --show-error https://ragfinance.ir/api/product-capabilities
sudo systemctl stop rag-arvan-api rag-arvan-worker
# After restoring the previous vhost files under the rollback change record:
sudo nginx -t
sudo systemctl reload nginx
```

This test scope covers an invited staging candidate. Semantic support, locator
openability, full security, durable live Product Answer history, Module 00/01
and a 100-user rollout require separate evidence and acceptance.
