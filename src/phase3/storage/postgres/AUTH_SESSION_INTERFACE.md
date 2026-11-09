# BND-DB-01 — Owner Mapping / Session Store internal interface

**Status:** synthetic PostgreSQL foundation only; *not* Product Auth, not BFF, not IdP reset proof. This file belongs to DB-owned `src/phase3/storage/postgres/**`, not the shared contracts directory.

## Entry points and role permissions

| Python entry point | SQL operation | Dedicated service role / trusted input |
|---|---|---|
| `map_identity(conn, issuer, subject)` | `auth_l1.map_identity` | `auth_mapper`; issuer+subject **already verified** by server OIDC callback, never browser-supplied choice |
| `issue(conn, owner_id, expected_epoch, idle_seconds, absolute_seconds)` | `issue_session` | `auth_sessions`; matched owner+epoch from trusted callback; 256-bit CSPRNG raw opaque is returned to **server RAM** only |
| `inspect(conn, opaque)` | `validate_session` | `auth_sessions`; session opaque obtained from trusted server cookie processing, no activity mutation |
| `touch(conn, opaque, expected_epoch)` | `touch_session` | `auth_sessions`; trusted valid activity, DB clock; idle deadline capped by absolute deadline |
| `rotate(conn, opaque, expected_epoch, expected_generation)` | `rotate_session` | `auth_sessions`; atomic CAS and old digest invalidation |
| `revoke_one(conn, opaque, expected_epoch)` | `revoke_one` | `auth_sessions`; revokes one digest, not other sessions |
| `revoke_all(conn, owner_id, expected_epoch)` | `revoke_all` | `auth_revoker`; monotonic epoch++ and reset_gate pending in same transaction |
| `suspend_owner(conn, owner_id, expected_epoch)` | `suspend_owner` | `auth_revoker`; no identity remapping or auto-resume |
| `finish_simulated_reauth(conn, owner_id, expected_epoch)` | `finish_simulated_reauth` | **`auth_reauth` only**; CI role substitution for a real fresh credential verification; DB cannot verify authentication assurance |
| `fence_owner(conn, owner_id, expected_epoch)` | `fence_owner` | `auth_sessions`; owner-row lock through caller's encompassing product DB transaction |

PostgreSQL receives only `sha256(opaque)` digests (64 lowercase hexadecimal digits), never raw Cookie or IdP tokens. No raw session/token values may be logged or stored. No user-supplied clock; PostgreSQL `clock_timestamp()` is authoritative. Test TTL values are explicit and bounded **only as CI fixture policy**, not a Production decision. `auth_l1` has `FORCE RLS`, default-deny direct policies, **zero direct table privileges** for app roles and `history_app`, and narrowly granted `SECURITY DEFINER` functions owned by a CI-only migration role. A leaked trusted service credential would still be dangerous; actual OIDC validation and service trust are required before Production.

## API/BFF package requirements — NOT implemented here

Next.js BFF must perform verified Code+PKCE/nonce/issuer/audience, CSRF/Origin, cookie handling, fresh reauth proof, no IdP token exposure, and **trusted** attribution of owner+epoch; FastAPI must validate authenticated BFF assertions and live session/epoch fencing before sensitive History actions. The source of identity, IdP reset event correctness, credential-change/outbox reconciliation, remote issuance policy, inter-service revocation and retention remain separately blocked/OPEN under ADR 0005. The DB guarantees only local atomicity and deny-after-local-commit *on new correctly checked DB admissions*. `fence_owner` is not a cross-database or HTTP guarantee.
