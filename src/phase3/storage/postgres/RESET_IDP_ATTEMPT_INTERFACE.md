# CR-DB-01C — Durable IdP Attempt + Outcome (Product PostgreSQL, synthetic only)

**Scope:** versioned 008 storage capability after immutable 003–007 and ADR 0006. **No** IDP transport/HTTP dispatch, retry/reconciliation, C2, Gate open, Password/Recovery proof assurance, API or UI adapter change. The successful synthetic lookup→C1→IdP dispatch from PR #28 does **not** durably record its IdP outcome yet; this DB package is deliberately **not connected to that adapter**.

## Trust boundary / eligibility

Dedicated **`auth_reset_idp_recorder`** is a non-superuser, non-BYPASSRLS, NOINHERIT, NOCREATEDB, NOCREATEROLE PostgreSQL role with `USAGE auth_l1` and `EXECUTE` **only** on `record_reset_idp_attempt` and `record_reset_idp_outcome`. It has no direct table SELECT/INSERT/UPDATE/DELETE rights, C1 authorization issuance/execution, identity lookup, mapping, Session issue/revoke, Gate opening, C2, History or schema DDL. Existing roles are unchanged; 008 table has FORCE RLS and direct-deny policy; both functions are SECURITY DEFINER with fixed `search_path=pg_catalog`, PUBLIC EXECUTE revoked. CI definer `auth_migrator` is privileged only inside disposable DB and is **not production approval**.

A new attempt must present `SHA256(consumed C1 opaque authorization)`, trusted Owner ID, C1 kind, constant `CONTROLLED_RESET_C1` purpose, **current post-C1 `revoked_epoch`**, an existing C1 `operation_id` and fresh `attempt_id UUID`. Operation UUID and Attempt UUID **alone** are never authority. The proof digest must link to an *already consumed* 006 Authorization with the **same** `consumed_operation_id`, scope and expected epoch; an immutable `REVOKED_PENDING_IDP` active C1 operation must exist and be **committed**, with matching Owner+Authorization+kind/purpose+expected/revoked epochs. Owner must remain `active`, current epoch equal C1 revoked_epoch and Gate `pending_reauth`. A speculative non-locking check refuses C1 still invisible/uncommitted on the independent executor connection (no postwait promotion). After Owner `FOR SHARE` lock, validations repeat; locks end with caller transaction, **never held across IdP network**. The separate recorder role cannot create its own C1 operation. The SQL only sees digest, no opaque authorization or raw credentials.

**Important:** 006's consumed proof is *not* a production-approved post-C1 continuation capability. Caller trust, proof origin, future proof rotation/TTL and authorization of an actual HTTP dispatch are outside this package; a stolen consumed proof combined with compromised recorder credentials would be dangerous. Do not wire this to a live caller without independent review.

## Durable one-attempt and fail-closed outcome semantics

`reset_idp_attempts` has `attempt_id UUID PRIMARY KEY` and **`operation_id UUID UNIQUE`**. `record_attempt()` returns `NO_OUTCOME_RECORDED` while holding an explicit caller outer transaction. **Only COMMIT makes the attempt durable; an IdP call must not start until that independent COMMIT is known.** No remote evidence is inferred from a committed row; it means only an intent/attempt slot was recorded.

The row initially has `outcome=NULL, outcome_code=NULL, finalized_at=NULL`. **Semantically this is UNKNOWN**, including after crash/connection loss or indefinite silence. No attempt TTL, automatic retry, replacement attempt, optimistic unlock or reconciliation is supplied. UNIQUE operation_id forbids a second row forever while evidence exists.

`record_outcome()` requires the **same exact** consumed C1 digest, Owner, kind, purpose, revoked_epoch, operation UUID and Attempt UUID, plus one allowlisted outcome/code pair. An atomic `UPDATE ... WHERE outcome IS NULL` is the CAS. Concurrent responses serialize on the row; only one wins. A duplicate, contradictory or late response fails and never overwrites a terminal result. Allowed **limited evidence**:

| Stored outcome | Allowed codes | Meaning |
| --- | --- | --- |
| `OBSERVED_REMOTE_SUCCESS` | `REMOTE_2XX_OBSERVED` | Caller says a 2xx was observed *in-process*; **not** durable proof IdP password changed or C2 assurance |
| `DEFINITIVE_REJECTION` | `POLICY_REJECTED`, `ACCOUNT_REJECTED` | Caller declares a separately verified definitive rejection; DB cannot establish certainty |
| `UNKNOWN` | `TIMEOUT`, `DISCONNECT`, `REMOTE_5XX`, `UNVERIFIABLE`, `OTHER_UNKNOWN` | Cannot prove whether remote write happened; **never** an IdP failure/retry authorization |

The table contains only UUID identifiers, Owner, consumed proof SHA256 digest reference, C1 kind/purpose/epoch, DB-generated `recorded_at`/`finalized_at`, outcome and restricted codes. It has **no** Password, Cookie, Email, ID token, recovery link, JWT, IdP response/request body, raw HTTP error or arbitrary error text. No C1 ledger status or Owner state is updated by 008. Gate stays closed; C2 remains blocked irrespective of observed success.

## Transaction, concurrency and rollback

Use `from src.phase3.storage.postgres import reset_idp_attempt`; only inside **explicit caller** `with conn.transaction(): ...` on a dedicated recorder connection. `record_attempt` / `record_outcome` never commit on caller's behalf. After committed attempt, network work is a **future API** concern on a **different** nontransactional path. After connection close/reopen, a committed attempt persists and blocks another; a rolled-back attempt leaves no row and may be claimed *only if no earlier evidence exists*. For outcome, one completed result never becomes unknown or retryable from a delayed response.

`008_durable_idp_attempt_outcome.down.sql` is **fail closed**: on a disposable primary with `psql -X -1 -v ON_ERROR_STOP=1`, it locks `auth_l1.owners ACCESS EXCLUSIVE` then `reset_idp_attempts ACCESS EXCLUSIVE` for the entire check+DROP transaction, following Owner-first ordering. If **any** attempt row (including NO_OUTCOME_RECORDED) exists, the rollback refuses with `RESET_IDP_ATTEMPT_ROLLBACK_REFUSED_EVIDENCE_EXISTS` and leaves 008, 006 ledger, owner Epoch, Gate and 006 trigger intact. Rollback is permitted only for unused 008 installations and drops **only** 008 function/table/grants. Existing 001–007 never change. No restoration or production down-migration permission.

## Explicit non-claims

One PostgreSQL primary + synthetic role fixtures is **not** an IdP response guarantee, exactly-once external password write, API receipt evidence, recovery/step-up, actual C2, Product Auth, auto retry, signed continuation or Production approval. The **same operation cannot acquire two attempts** without an externally reviewed future authorization/reconciliation migration. No live API adapter wiring is performed in CR-DB-01C.
