# Arvan Staging Handoff & Status Report (`ragfinance.ir`)

- **Branch:** `deploy/arvan-100users-candidate`
- **Last app commit before infra sync:** `7f0c54d`
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

## 2. Remaining Backlog (Next Pass)

1. **Clear Keycloak SSO cookies on logout (`KEYCLOAK_IDENTITY`, `KEYCLOAK_SESSION` on path `/realms/finance-staging/`):**
   - Currently `/api/auth/logout` clears only the BFF session cookie, so re-login triggers Keycloak re-authentication locked to the previous user unless the user clicks restart.
2. **One-click logout from chat sidebar:**
   - Replace two-step navigation (`/login` -> click logout again) with direct CSRF-protected logout action (and align Playwright test selectors if needed).
3. **Keycloak login theme (`moshaver-mali`) visual polish:**
   - Remove inherited `styles.css` duplicate top blue border on `.pf-v5-c-login__main`.
   - Hide `.pf-v5-c-form-control__utilities` (error icon overlapping LTR username text on invalid password).
   - Fix `.mm-badge` 3-bar ascending chart icon visibility and unify card header spacing.
4. **Chat UI palette & chart icon direction:**
   - Soften blue accents (`#2563eb` -> lighter sky/soft blue + very light yellow) across both chat (`apps/web/app/history/history.css`, `apps/web/app/login/route.ts`) and login theme.
   - Add `direction: ltr` to `.advisor-mark` in `history.css` so the 3 bars ascend left-to-right.
5. **Password Reset (Forgot Password):**
   - Configure SMTP in Keycloak `finance-staging` realm and enable `resetPasswordAllowed=true` once real user emails & SMTP credentials are ready.
6. **Source Corpus Typo:**
   - Fix raw dataset typo (`واریس` -> `واریز`) in a future corpus/index rebuild.

## 3. Deploy Reminder for Future Syncs

- Do NOT overwrite `/opt/rag-finance-staging/phase3/themes/moshaver-mali` or `/etc/nginx/conf.d/ragfinance.ir.conf` with legacy `idp-staging.ragfinance.ir` configs.
- Always sync `infra/arvan-staging/themes/moshaver-mali/` to `/opt/rag-finance-staging/phase3/themes/moshaver-mali/` before recreating `rag-arvan-idp-keycloak-1`.
