# F3 — Forty-two additionally witnessed *bounded CI slices*, not forty-two accepted tasks

This matrix binds 42 additional canonical activity IDs to an exact already
executed CI test/source assertion *only when the three prerequisite regression
jobs succeed for one checkout SHA*. They are disjoint from the 20 historical
lab witnesses. A final job merges the same-SHA source-attested slices into the
393-ID ledger, producing 62 lab-witnessed IDs out of 262. Growth:
+42/262=16.0305 percentage points **in per-ID bounded evidence traceability**.
This is NOT +16% overall project completion, does not establish owner signoff,
and does not increase code completion, target acceptance or any Gate numerator.

Executed commands and actual DB-lab scripts are inside
.github/workflows/f3-foundation-candidate-full-isolated-regression.yml.
A passing unit fixture is not equivalent to positive evidence from Engine or a
real source. For example, the source attribution rows cover defensive rendering
and DTO shape only; source provenance in the accepted Phase2 Release remains
blocked. RLS/DB actions use isolated test PG only.

The original checklist, its full criteria, and all 393 IDs remain unmodified
and CANONICAL. A generated derived receipt only adds the CI run link, SHA,
source marker and environment to a copy of the baseline ledger.
