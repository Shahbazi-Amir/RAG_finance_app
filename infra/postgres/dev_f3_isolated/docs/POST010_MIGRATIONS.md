# Database scope after 010 — REVIEW ONLY

From current project source, **011 is the only later SQL migration explicitly identifiable**, and its source is in Draft #56, not in the accepted Mac demo. There is no verified specification requiring a new 012+ migration; do not invent tables or SQL.

| Object | Pinned source | SHA-1 Git blob |
|---|---|---|
| `infra/postgres/migrations/011_external_dispatch_claim.up.sql` | `b0ba6dbf6100109cb58f8cb49da808839d68c5f0` | `031d2f438f000154eb4e2b374ce42181b3d812b3` |
| `infra/postgres/migrations/011_external_dispatch_claim.down.sql` | same | `ce3e7d8a2394f4a090650623770ad261eee2f4c2` |

**Scope:** durable external Gateway dispatch Claim (`history_l1.external_dispatch_claims`), reporter and reconciler roles and non-reclaimable evidence handling. It is explicitly **NOT necessary for `DB55/private_no_dispatch`**. Its Down file refuses to erase committed claim evidence; do not treat rollback as an unconditional DROP.

**Separate development test branch / environment required:** empty isolated PG17.11 clone with 001..010 already applied and proven, create `history_dispatch_reporter` / `history_dispatch_reconciler` limited roles, apply exact pinned 011 only there, run `db55_verify_staging.sql -v db55_phase=live_011`, test one Claim + status and crash/unknown/reconciliation negative paths. Do not use lab of the `private_no_dispatch` test or accepted demo; do not enable paid delivery. Pin a separate source SHA/contract and require CENTRAL/API/Security scope acceptance before live integration.

**Status:** `011_SOURCE_IDENTIFIED`; `011_ISOLATED_RUNTIME_TEST=NOT_RUN`; `011_PRODUCT_ACCEPTANCE=BLOCKED_EXTERNAL_DISPATCH_CONTRACT`. Any 012+ is `NOT_SPECIFIED` pending API requirements; no SQL written for it.
