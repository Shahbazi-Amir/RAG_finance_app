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
| `fence_owner(conn, owner_id, expected_epoch)` | `fence_owner` | `auth_sessions`; checks **only** Owner state, epoch and reset gate; owner-row lock lives until end of the caller's enclosing PostgreSQL transaction |

PostgreSQL receives only `sha256(opaque)` digests (64 lowercase hexadecimal digits), never raw Cookie or IdP tokens. No raw session/token values may be logged or stored. No user-supplied clock; PostgreSQL `clock_timestamp()` is authoritative. Test TTL values are explicit and bounded **only as CI fixture policy**, not a Production decision. `auth_l1` has `FORCE RLS`, default-deny direct policies, **zero direct table privileges** for app roles and `history_app`, and narrowly granted `SECURITY DEFINER` functions owned by a CI-only migration role. A leaked trusted service credential would still be dangerous; actual OIDC validation and service trust are required before Production.

## API/BFF package requirements — NOT implemented here

Next.js BFF must perform verified Code+PKCE/nonce/issuer/audience, CSRF/Origin, cookie handling, fresh reauth proof, no IdP token exposure, and **trusted** attribution of owner+epoch; FastAPI must validate authenticated BFF assertions and live session/epoch fencing before sensitive History actions. The source of identity, IdP reset event correctness, credential-change/outbox reconciliation, remote issuance policy, inter-service revocation and retention remain separately blocked/OPEN under ADR 0005. The DB guarantees only local atomicity and deny-after-local-commit *on new correctly checked DB admissions*. `fence_owner` is not a cross-database or HTTP guarantee.

## Scope of `fence_owner` — security limitation and future session-aware admission

`fence_owner(conn, owner_id, expected_epoch)` **only** checks and locks the **Owner** row for its active state, expected nonnegative epoch and open reset gate. It does **not** validate the same opaque Session digest or session row; it cannot by itself fence **revoke-one**, rotation of the particular session, idle expiry, absolute expiry, or session theft/replay for the remainder of an operation. Passing an Owner/Epoch check is **not** proof of a valid current Session.

The `FOR SHARE` Owner row lock persists until the *outermost caller-controlled* PostgreSQL transaction ends **if and only if** the caller wraps both the `fence_owner` call and the protected work on the *same connection* in one explicit transaction. A standalone call using autocommit ends its lock immediately; no cross-connection, HTTP or remote service guarantee follows. See `test_auth_null_fence.py`: separate connections plus observed PostgreSQL lock wait check this precise claim.

**Future API/BFF requirement (NOT implemented):** the admission boundary must authenticate the caller and establish a **session-aware** transaction-fencing protocol, checking digest, session status, generation/rotation, individual revoke, server clock idle/absolute expiry and owner epoch/gate together, with a coherent race/locking rule for the entire protected operation and no authorization from a stale cached check. A `validate_session` read followed by `fence_owner` alone is not an atomic session-aware fence. Scope, lock ordering, session-row locks, renewal and in-flight policy require joint API/BFF/DB review and adversarial tests. No public DTO, API, BFF or other module was changed by this fix.
