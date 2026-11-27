# SPEC-01B — Arvan live deployment of 355c664

## Fact

- Target source: `deploy/arvan-100users-candidate` at `355c66460b96f415456cc5c10ba7a9e85a03898c`. Local HEAD and the local `origin/deploy/arvan-100users-candidate` tracking ref matched. The working tree initially listed only the pre-existing untracked `docs/codex_execution/`; nothing was staged.
- The first SSH attempt inside the sandbox exited 255 with `Operation not permitted` on port 22. The approved read-only retry through `rag-finance-arvan` exited 0.
- The SSH identity was root. The candidate release directory, `apps`, and `apps/web` were owned by `root:root`. The release directory had no `.git` metadata or SHA in the checked `RELEASE_SHA`, `.release-sha`, or `REVISION` markers. Its previous SHA could not be verified; the handoff lists `7f0c54d` as a historical pre-infra-sync commit.
- `systemctl is-active rag-arvan-worker rag-arvan-api rag-arvan-bootstrap-oidc rag-arvan-web nginx` returned five `active` lines and exited 0. Both vhost files existed with mode 0644.
- The exact candidate `protected-profile-check.py` ran over SSH from stdin under the server's Python 3.13 and exited 0. This checks protected file metadata and the provisioned origins and OIDC endpoint configuration. The content of protected inputs was kept out of output.
- The exact candidate `realm-sync.sh --check` ran over SSH from stdin against the deployed Compose file and exited 4 with no output. A direct read-only `kcadm get clients` diagnostic exited 1 and was classified as `no_session` without printing the raw CLI response.

## Interpretation

The preflight reached Keycloak administration and stopped before the backup or source sync. The portal's service state is a pre-deployment observation. The protected-profile pass is configuration evidence. Live mTLS, RS256/S256, the blocked-route 404s, the theme CSS, and the logout GET 405 are still unverified for this deployment. Status is **NOT ACHIEVED**.

## Pending

1. The authorized operator must establish the existing Keycloak admin session in an interactive SSH terminal. Enter the approved administrator name and supply the password at the Keycloak prompt.

   ```bash
   ssh -t rag-finance-arvan
   cd /opt/rag-finance-staging/phase3/arvan-candidate
   read -r -p 'Keycloak administrator: ' KEYCLOAK_ADMIN_USER
   docker compose -f infra/arvan-staging/keycloak.compose.yml exec keycloak \
     /opt/keycloak/bin/kcadm.sh config credentials \
     --server http://127.0.0.1:8080 --realm master --user "$KEYCLOAK_ADMIN_USER"
   unset KEYCLOAK_ADMIN_USER
   ```

2. Repeat the read-only realm check. Verify the prior release SHA from the approved release record and identify the existing non-root build operator and usable offline npm cache. The observed root owner cannot serve as the script's default build user.
3. Back up the two vhosts and record the prior release identity. Sync the exact candidate, run the server dry-run and full deployment, then capture the live gate output. Update the handoff and commit/push the authorized files after the gate passes.

Server preflight only. The vhosts, release tree, running services, and handoff received no deployment changes. The engine repository and the two protected documentation paths were outside this operation.

## SPEC-01B-R1 retry

- **Fact** — Local branch and HEAD matched the requested baseline. Approved SSH connected. Candidate `realm-sync.sh --check` against the installed Compose file exited `4` without output. A direct client query with stdin closed exited `1` and returned the sanitized classification `no_session`.
- **Interpretation** — The R1 stop condition still applies. Status remains **NOT ACHIEVED**. The build user and offline cache checks, backup, sync, dry-run, deployment, and live gate were not reached in this retry.
- **Pending** — Establish the session with the interactive command above in the same Compose service on `rag-finance-arvan`, then repeat `realm-sync.sh --check` before proceeding.

## SPEC-01B-R2 retry

- **Fact** — Local HEAD and the local origin tracking ref matched `355c66460b96f415456cc5c10ba7a9e85a03898c`. Approved SSH connected. The exact candidate `realm-sync.sh --check`, streamed to Bash against the installed Compose file, exited `4` with no output.
- **Interpretation** — R2 required an immediate stop on this result. The exit code alone does not distinguish authentication failure from a realm/client check failure. The previous retry separately observed `no_session`. R2 performed no subsequent remote checks or deployment changes. Status remains **NOT ACHIEVED**.
- **Pending** — Confirm the interactive `kcadm` session using the command above and verify that the candidate realm check exits `0`. Then run the protected-profile, worker unit and offline-cache checks before backup and deployment with the specified `rag-arvan-web` build user.

## SPEC-01B-R5

- **Baseline** — Application source at `355c66460b96f415456cc5c10ba7a9e85a03898c` plus reviewed R5 deployment-script and template changes. Synced only the tracked Web app/source, theme, templates and deploy script. The server release has no Git metadata.
- **Backup** — `/root/rag-arvan-backups/pre-spec01b-20261127T170629Z` contains the two Nginx vhosts and a 44-file Web/theme SHA-256 manifest. Prepared 112 MiB of offline npm cache data for the non-root Web build account, keeping npm diagnostic logs and user configuration out of the copy.
- **Ingress** — Both allowed Keycloak locations have 32 KiB body limits. The general realm prefix returns 404, with the exact finance-staging prefix taking precedence. The internal/admin/auth guards and dedicated deny-only legacy host remain in the templates.
- **Realm** — Prior live PKCE value was reported as unset. The standby realm check failure in R1/R2 preceded the R5 session fix. In R5, piped password input failed; the documented `KC_CLI_PASSWORD` mechanism authenticated without a password argument. Corrected the placement of `--config`. The dotted-field update and unmerged payload attempts failed the strict readback. Direct lookup by client UUID and a merged JSON update over stdin passed. Both `realm-sync.sh --apply` and an independent `--check` exited 0 and verified client PKCE S256, the exact callback and the realm RS256 default. The CLI config is isolated in a temporary container directory and removed on exit.
- **Local verification** — `bash -n` passed on both scripts, the deployment dry-run exited 0 and `git diff --check` passed. The server-side dry-run also exited 0.

Keycloak CLI password and update behavior are documented in the [Admin CLI guide](https://github.com/keycloak/keycloak/blob/main/docs/documentation/server_admin/topics/admin-cli.adoc) and [update command source](https://github.com/keycloak/keycloak/blob/main/integration/client-cli/admin-cli/src/main/java/org/keycloak/client/admin/cli/commands/UpdateCmd.java).

### R5 live results

| Check | Observed result |
| --- | --- |
| Full deployment | Offline npm installed 357 packages. Route generation, lint, typecheck and Next.js production build completed. Build reported two existing dynamic filesystem tracing warnings. systemd units were installed, the Keycloak theme was synced, Nginx validation proceeded to reload, and candidate services restarted. Script exited 1 at the last, private mTLS check. |
| systemd | `rag-arvan-worker`, `rag-arvan-api`, `rag-arvan-bootstrap-oidc`, `rag-arvan-web`, and `nginx` all returned `active`. |
| Public HTTP 200 | Capabilities, login, and finance-staging OIDC discovery. Login contained `brand-mark`, `#fff8d9` and `#dbeafe`. Discovery had the exact finance-staging issuer and advertised RS256 and S256. |
| Public HTTP 405 | GET `/api/auth/logout`. |
| Public HTTP 404 | `/internal/`, `/admin/`, `/realms/master/`, `/realms/nonexistent/`, `/auth/`, and both requested legacy IdP URLs. |
| Theme | HTTP 200 for `/resources/wwk3h/login/moshaver-mali/css/moshaver.css` linked by the live Keycloak authorization page. All three R5 CSS markers matched. |
| Private mTLS | The required `protected-profile-check.py --smoke-mtls` exited 1. An independent TLS 1.2 probe recorded `UNEXPECTED_EOF_WHILE_READING` without a client certificate on both 18444 and 18443. With the configured trusted client certificate, both returned HTTP 404 for GET `/`, proving TLS and HTTP completed. The checker accepts specific TLS certificate alerts and rejects this EOF result. A TLS 1.3 diagnostic without the certificate on 18444 observed a connection reset. |

**Interpretation** — PARTIALLY ACHIEVED. The candidate is serving live, client PKCE S256 was enforced and checked, and public verification passed. The required mTLS check exit code keeps the full gate open.

**Pending** — Authorize a focused change to `infra/arvan-staging/templates/protected-profile-check.py`, which is outside the R5 allowed edit paths. Verify the rejection behavior against both private endpoints while retaining the trusted-certificate positive control and fail-closed behavior. Repeat the complete gate before updating the handoff and committing/pushing.

### Follow-up on the mTLS gate

An automatic approval review rejected uploading a proposed checker change. The reviewer identified the checker as outside the R5 edit paths and flagged accepting a handshake EOF as a security-sensitive change. The local proposal was reverted. The server checker was unchanged, and the full gate remains open. Explicit authorization for the checker path and the verification approach is required before another upload attempt.

### Follow-up with explicit mTLS checker approval

- Pre-change diagnostic on ports 18444 and 18443 separated TCP, TLS and HTTP. TCP connected on both. Anonymous TLS 1.2 raised `SSLEOFError: UNEXPECTED_EOF_WHILE_READING` inside `SSLSocket.do_handshake()` before HTTP. With the configured client certificate, each negotiated TLS 1.2 and returned HTTP 404 for GET `/`.
- Updated and synced only the mTLS checker. It recognizes EOF in the handshake after TCP connects and still requires a valid HTTP response with the trusted client certificate on the same endpoint. Connection refusal, TCP/handshake timeout, successful anonymous TLS, certificate verification errors and an informational-only HTTP status failed the local simulated controls. The earlier local mock omitted the synthetic certificate error's reason field. The corrected fixture and all six controls passed.
- **Live gate PASS** — `nginx -t`, `realm-sync.sh --check` and `protected-profile-check.py --smoke-mtls` each exited 0. All five units were active. Capabilities, login and exact OIDC discovery returned 200. Discovery included RS256 and S256, and the realm check verified enforced S256 and the exact callback. GET logout returned 405. Every required blocked route returned 404, including the extra legacy-host paths checked by the deploy smoke. The live theme returned 200 and all CSS and login markers matched.
- Updated the handoff. Changes are held locally pending approval to push. No 100-user workload test was part of this gate.
