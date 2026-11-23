# Database scope after 010 — REVIEW ONLY

From current project source, **011 is the only later SQL migration explicitly identifiable**, and its source is in Draft #56, not in the accepted Mac demo. There is no verified specification requiring a new 012+ migration; do not invent tables or SQL.

| Object | Pinned source | SHA-1 Git blob |
|---|---|---|
| `infra/postgres/migrations/011_external_dispatch_claim.up.sql` | `b0ba6dbf6100109cb58f8cb49da808839d68c5f0` | `031d2f438f000154eb4e2b374ce42181b3d812b3` |
| `infra/postgres/migrations/011_external_dispatch_claim.down.sql` | same | `ce3e7d8a2394f4a090650623770ad261eee2f4c2` |

**Scope:** durable external Gateway dispatch Claim (`history_l1.external_dispatch_claims`), reporter and reconciler roles and non-reclaimable evidence handling. It is explicitly **NOT necessary for `DB55/private_no_dispatch`**. Its Down file refuses to erase committed claim evidence; do not treat rollback as an unconditional DROP.

**Separate development test track — PASSED:** `scripts/08_optional_011_compat_only.sh` runs in a second isolated PG17.11 lab with fresh pinned 001–010, creates separate reporter/reconciler roles, applies exact 011 and checks `DB55/live_011`, function-only ACL/FORCE RLS and invalid Claim denial. The existing #56 independent PG17.11 suite exercises Claim concurrency, crash UNKNOWN and reconciliation (Run 43710425019). Neither uses a Gateway. Do not use the base `private_no_dispatch` lab or accepted demo; CENTRAL/API/Security approval still required before any live paid integration.

**Status:** `011_SOURCE_IDENTIFIED`; `011_ISOLATED_RUNTIME_TEST=PASS` in two separate CI tracks: [full 001–010→011 compatibility run 45052366022](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45052366022) with `DB55/live_011`, function grants/RLS, denied unauthorized Claim; and [standalone concurrent 011 test run 43710425019](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43710425019) on exact pinned source. `011_PRODUCT_ACCEPTANCE=BLOCKED_EXTERNAL_DISPATCH_CONTRACT` for real paid Gateway. No schema 012+ identified. Any 012+ is `NOT_SPECIFIED` pending API requirements; no SQL written for it.
