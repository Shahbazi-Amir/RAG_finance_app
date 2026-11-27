# Arvan Staging Handoff & Status Report (`ragfinance.ir`)

- **Branch:** `deploy/arvan-100users-candidate`
- **Deployed application commit:** `355c66460b96f415456cc5c10ba7a9e85a03898c` with SPEC-01B-R5 deployment updates
- **Live URL:** `https://ragfinance.ir`
- **Server backup before same-domain cutover:** `/root/rag-arvan-backups/pre-same-domain-auth-20261126-204507`

## 1. Completed & Verified on Live Arvan Server

- **Same-Domain OIDC (Zero App Code Changes):**
  - Keycloak (`rag-arvan-idp-keycloak-1`, Keycloak 26.8.2) serves public realm `finance-staging` on `https://ragfinance.ir/realms/finance-staging` (matching `src/phase3/auth/bootstrap_oidc.py` regex `^/realms/[A-Za-z0-9._-]{1,100}$`).
  - Nginx (`/etc/nginx/conf.d/ragfinance.ir.conf`) proxies ONLY `/realms/finance-staging/` and `/resources/` to `127.0.0.1:18081`.
  - Security 404 boundaries verified: `/internal/`, `/admin/`, `/realms/master/`, `/auth/`, and old `idp-staging.ragfinance.ir` all return HTTP `404`.
  - `/etc/rag-arvan-candidate/bootstrap-private.json` and `/etc/rag-arvan-candidate/web-private.json` updated to `https://ragfinance.ir` with `0600` permissions preserved.
  - All 5 systemd units (`rag-arvan-worker`, `rag-arvan-api`, `rag-arvan-bootstrap-oidc`, `rag-arvan-web`, `nginx`) are `active` and `enabled`.
- **Custom Keycloak Login Theme (`moshaver-mali`):**
  - Stored in repo at `infra/arvan-staging/themes/moshaver-mali` and mounted read-only on Arvan at `/opt/rag-finance-staging/phase3/themes/moshaver-mali:/opt/keycloak/themes/moshaver-mali:ro`.
  - Realm `finance-staging`: `loginTheme=moshaver-mali`, `defaultLocale=fa`, `registrationAllowed=false`.
- **Accounts Provisioned & Live-Verified:**
  - `staging-smoke`: disabled.
  - `test1`..`test5` (`test1@ragfinance.local`..`test5@ragfinance.local`): enabled, verified, non-temporary, daily quota 20, real OIDC login verified for all 5.
  - `amiraralloo1@gmail.com`: enabled, unlimited quota (credentials stored root-only `0600` in `/root/rag-arvan-backups/amir-user.env`).
- **Chat UX & Runtime (`7f0c54d`):**
  - Full-pane scroll without poll scroll-lock, «مشاور مالی» branding, social/greeting fast router (< 3s), conversational advisor tone, multi-turn history, answer cache, offline worker build.

## 2. SPEC-01B live deployment

- Deployed Keycloak SSO cookie expiration on logout and the CSRF-protected one-click chat sidebar form.
- Deployed the polished Keycloak theme, the lighter chat and login palette, and left-to-right chart bars.
- The live gate verified PKCE S256 on the client, the exact callback, RS256, both private mTLS endpoints, the public HTTP boundaries and the served theme. See the [live deployment report](../../docs/reports/SPEC-01B-arvan-live-deploy.md).

## 3. Remaining Backlog

1. **Password Reset (Forgot Password):**
   - Configure SMTP in Keycloak `finance-staging` realm and enable `resetPasswordAllowed=true` once real user emails & SMTP credentials are ready.
2. **Source Corpus Typo:**
   - Fix raw dataset typo (`واریس` -> `واریز`) in a future corpus/index rebuild.

## 4. Deploy Reminder for Future Syncs

- Do NOT overwrite `/opt/rag-finance-staging/phase3/themes/moshaver-mali` or `/etc/nginx/conf.d/ragfinance.ir.conf` with legacy `idp-staging.ragfinance.ir` configs.
- Always sync `infra/arvan-staging/themes/moshaver-mali/` to `/opt/rag-finance-staging/phase3/themes/moshaver-mali/` before recreating `rag-arvan-idp-keycloak-1`.
