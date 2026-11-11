# CR-DB-01B — scoped C1 identity lookup (DB-only)

**Status:** synthetic PostgreSQL-only; no public endpoint, no wiring to PR #26's API adapter, no real Recovery/Step-up, no IdP credentials, no Product Auth or Gate acceptance.

## Precondition and return

Use `src.phase3.storage.postgres.reset_identity_lookup.resolve` in an internal trusted, server-only caller with **dedicated `auth_reset_lookup`** PostgreSQL role. Caller supplies a high-entropy unconsumed synthetic C1 authorization value only in RAM plus **trusted** `owner_id`, operation `kind` (`RECOVERY` / `AUTHENTICATED_PASSWORD_CHANGE`), `expected_epoch`, and `expected_issuer` from verified service context. Python hashes opaque authority with SHA256; SQL receives **only the 64-hex digest** and scope fields. No raw authorization, Recovery link, password, Cookie, Session identifier, ID token or email enters SQL or logs.

`auth_l1.resolve_reset_identity(digest,owner,kind,purpose,epoch,issuer)` requires all of these: matching `reset_c1_authorizations` Owner/kind/purpose/expected epoch; authorization neither consumed nor expired against **PostgreSQL `clock_timestamp()`**; current Owner exists, is `active`, `reset_gate='open'`, current `session_epoch` matches; no active reset operation; when kind is `AUTHENTICATED_PASSWORD_CHANGE`, the bound Session digest/generation is observed currently active, same Owner+Epoch and unexpired (without row locks); and `identity_links` has the **expected issuer** for that exact Owner. `003.identity_links.owner_id UNIQUE` guarantees at most one pair. Missing/malformed/NULL/wrong issuer/owner/stale epoch/used proof returns **no identity** (SQL raises identical `RESET_IDENTITY_LOOKUP_DENIED`). The only successful payload is **exactly** `{'issuer': '...', 'subject': '...'}`, with no Owner, email, list/search/pagination, timestamps, authorization fields, operation ID or User data.

## Privileges

Preprovision `auth_reset_lookup` as a distinct **non-superuser, non-BYPASSRLS, NOINHERIT, NOCREATEDB, NOCREATEROLE** role in disposable CI. 007 migration grants schema USAGE + EXECUTE for only one named, SECURITY DEFINER `auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)`. Function has explicit `search_path=pg_catalog`; PUBLIC EXECUTE revoked. Existing `003/006` identity/Owner/authorization/operation FORCE RLS direct-deny tables and privileges remain unchanged. This role cannot query those tables directly, map owners, issue authorization, execute C1, issue or rotate Sessions, reopen Gate, access History, run replay cleanup or DDL; existing DB roles get no extra grants. CI `auth_migrator` with BYPASSRLS is **not** a production privilege model.

## Read-only snapshot, not a reservation

Lookup contains **one ordinary SELECT** over an MVCC statement snapshot, no `FOR UPDATE`, `FOR SHARE`, advisory lock, row mutation, token consumption or persisted state. A valid result can become stale immediately afterward. Never hold a lookup transaction/lock during network calls or treat the returned `issuer/subject` as authority for IdP Reset: **006.execute_reset_c1 independently revalidates the authorization, owner, gate, epoch and clock and atomically consumes + revokes**. An expired/consumed proof, a later epoch increase, or other competing C1 can make Lookup's result unusable. An expected issuer is a caller-supplied scope, not proof of a real IdP session; external caller trust is outside DB. No new endpoint or API adapter connection exists in this package.

## Migration and rollback

Version **007** installs only the single function and function/schema grants, depending on immutable 003 identity_links and 006 reset authorization. `007_scoped_reset_identity_lookup.down.sql` drops 007 routine and schema USAGE for lookup role; it never drops or edits 003/006 tables, Owner, Identity Links, Sessions, C1 authorization, operation evidence, epoch, pending Gate or 006 Gate trigger. Execute UP/DOWN with `psql -X -1 -v ON_ERROR_STOP=1` only on disposable CI PostgreSQL. Actual CI tests cover empty and prepopulated states plus C1/006 rollback races; do not take these tests as deployment or production backup/restore permission.
