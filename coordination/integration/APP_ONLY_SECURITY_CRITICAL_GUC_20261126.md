# App-only critical findings and owner GUC trust boundary — 2026-11-26

Status: REVIEW_REQUIRED / NOT_ACCEPTED. Baseline exact SHA 31f01b78a41f5250c3a7a6a7e57f79dd224f6749; PR #143, run 45737234646, artifact 15080260281, verified SHA256 8489aea1701100beae8aa2d618b48c2f38fc5751554edcf33e12a8ca03e4280a. Source: four vulnerability_summary.json and PG CycloneDX in that artifact. Exclude Browser from product counts, not from scanner. All severities remain reported; no ignore list, severity threshold or acceptance change.

| Image | CRITICAL | HIGH |
|---|---:|---:|
| API | 2 | 44 |
| Web | 1 | 48 |
| PG | 4 | 136 |
| IdP | 0 | 6 |
| Total | 7 | 234 |

| Image | CVE | Package (installed) | Disposition |
|---|---|---|---|
| API | CVE-2023-45853 | zlib1g (1:1.2.13.dfsg-1) | no-fix on Bookworm |
| API | CVE-2025-7458 | libsqlite3-0 (3.40.1-2+deb12u2) | no-fix on Bookworm |
| Web | CVE-2023-45853 | zlib1g (1:1.2.13.dfsg-1) | no-fix on Bookworm |
| PG | CVE-2023-45853 | zlib1g (1:1.2.13.dfsg-1) | no-fix on Bookworm |
| PG | CVE-2025-68121 | stdlib (v1.24.6, gosu v1.19.0 in SBOM) | fixable; candidate rebuild of same upstream gosu source with Go 1.26.11; exact-image rescan pending |
| PG | CVE-2025-7458 | libsqlite3-0 (3.40.1-2+deb12u2) | no-fix on Bookworm |
| PG | CVE-2026-6653 | libxml2 (2.9.14+dfsg-1.3~deb12u6) | no-fix on Bookworm |

Debian tracker checked 2026-11-26: [zlib](https://security-tracker.debian.org/tracker/CVE-2023-45853) marks Bookworm ignored because contrib/minizip is not built by src:zlib; this is an applicability note, not a scanner exclusion. [sqlite3](https://security-tracker.debian.org/tracker/CVE-2025-7458) Bookworm no-DSA, minor issue, Trixie fixed. [libxml2](https://security-tracker.debian.org/tracker/CVE-2026-6653) Bookworm postponed, vulnerable backport, fixed in later upstream; Trixie still vulnerable. These are distribution-specific no-fix findings, NOT a claim that no global upstream fix exists. No unsupported mixed-distribution packages or untested OS-major upgrade; separately review compatible base migration/backport and exposure before release. High findings remain open for triage.

Go fix thresholds reported by baseline scanner: 1.24.13, 1.25.7, 1.26.0-rc.3. [Go downloads](https://go.dev/dl/) checksum-verified 1.26.11 linux/amd64; [upstream gosu release source](https://github.com/tianon/gosu/commit/6456aaa0f3c854d199d0f037f068eb97515b7513) exact 1.19 commit, module proxy/checksum DB verification, static CGO-disabled build. Only gosu executable replaced, unchanged PG 17.11 base digest and existing entrypoint, role switch tested during build. Both real browser PG volumes and independent clean-install/rollback job select the exact SHA-derived candidate. Assert both running images equal the image being scanned. Other CI-specific PG witnesses retain their original pinned image and do not certify this derived image. No target deployment approval. Before/after numbers require actual new scan; do not assume 6 Critical or a High reduction.

## M06 — owner GUC trust boundary (documented, not closed)

- Product is a service/configuration mode, not a separate SQL login in the current lab. Product History uses history_app; revocation uses auth_revoker. Separate restricted Bootstrap roles. `02_provision_roles.sh` creates service logins NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE, grants CONNECT only on the explicit lab DB; migrators NOLOGIN, separately owned; PUBLIC CONNECT/TEMP revoked on lab DB. `05_test_roles_tls_rls.sh` checks nine roles, verify-full, plaintext denial, 72/72 auth-table SELECT denials. Migration 001: SELECT/INSERT six History tables, UPDATE only named conversation metadata/attempt fields; no DELETE or immutable message/answer UPDATE. FORCE RLS owner_only uses current_setting('app.owner_id',true) for USING/WITH CHECK. See pinned migration and DB55 bridge/verification for exact function privileges.
- `apps/api/product_session_api.py::_signed_history` obtains owner only from verified wire-bound BFF proof; `src/phase3/auth/transactional_admission.py::protected_transaction` consumes durable 005 JTI and obtains 004 session/owner admission in one transaction, samples DB time after locks, rolls back on failure. `src/phase3/storage/postgres/repository.py::scoped` uses parameterized transaction-local set_config('app.owner_id', owner, true). Private ASGI checks mTLS peer, signer pin, app-only route fence; Product credentials remain server-only; PG verify-full, no public PG port in isolated Compose. App-only Send disabled before admission/mutation. These establish HTTP trust, not independent SQL-user identity.
- Actual baseline clean DB witness `19_history_rls_negative_matrix.sh`: `direct_history_role_can_set_owner_guc=true`; restricted role can set arbitrary owner and read that owner's rows. No owner => zero rows; correct owner context denies foreign row, invalid composite FK and forbidden update/delete. Arbitrary SQL / stolen history_app credentials therefore remain a cross-owner risk. No claim of zero RLS bypass under credential compromise.
- No small GRANT/REVOKE or SET LOCAL change can make a user-settable custom GUC an unforgeable owner while same role retains direct table grants and must set it. A DB-enforced actor capability with privileged verified admission and policy rewrite, or narrow SECURITY DEFINER RPCs plus revocation of direct grants, needs separate design, migration/rollback and real adversarial tests. Preserve all pinned 001–010 and existing negative tests. Until then enforce private network, no end-user DB login, isolated secrets, parameterized SQL, no arbitrary SQL endpoint, rotation/revocation and review of runtime role grants in target. Residual requires explicit owner security disposition; M06/M02/M18/M21 not accepted by this file.
