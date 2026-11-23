# FOUNDATION_F3 — Receipt intake hardening and progress checkpoint (2026-11-23)

Base SHA: `97cadec0d92500a2cab022d6a384ceba065ac0a8` (PR #69 exact 4/4 CI SUCCESS). This branch changes only Foundation preflight checks, tests, CI branch selector and this note. No Docker/DB/Mac/Phase2/Arvan/paid Gateway.

## Concrete fix
- Reject **duplicate JSON members at every nesting level** for Release and Ops receipt inputs, including identical values. Previously Python JSON parser silently accepted the last value.
- Reject raw artifact paths containing repeated slashes or `./` segments before `pathlib.Path` normalizes them. Preserve traversal and symlink checks.
- Require exact three OCI **built service names** from `compose.product.yaml`: `product-api`, `auth-bootstrap`, `web-bff`. A structurally valid arbitrary three-image self-report must not pass.
- Reject non-string expected Git SHA/tree safely with `InvalidEvidence`, not an uncaught `TypeError`.
- Extend Foundation test suite from 32 to **42** with positive and negative cases. Local `python -m unittest discover -s tests/phase3/foundation -p 'test_*.py' -v` PASS 42/42. Re-run original exact-branch CI after commit.

**Security boundary:** This is STILL a **sanitized input structural preflight**, not cryptographic authentication of Mac executor, image contents, source provenance, external approval, signed receipts, real C018 or Gate acceptance. A synthetic/self-declared receipt must never be substituted for actual Ops evidence.

## Source-derived roadmap counts (independent of this patch)
The user-provided package's `FOUNDATION_121_EXECUTION_CHECKLIST.csv` has 121 unique direct Foundation IDs: **40 PARTIAL, 38 NOT_VERIFIED, 43 NOT_RUN, 0 ACCEPTED**. Direct source partial coverage: 40/121 = **33.06%**. Entire `FULL_PHASE3_262_EXECUTION_CHECKLIST.csv`: **151 PARTIAL,68 NOT_VERIFIED,43 NOT_RUN, 0 ACCEPTED** = 151/262 **57.63%** partial coverage; 26/26 independent Gates NOT_ACCEPTED, 105 P3OP aliases non-counting.
- This turn's code work: **4 hardening changes +10 regression tests**, source tests 42/42; coverage change on the frozen 121-row acceptance checklist **+0 activities/+0.00 percentage points** (because actual target admission remains absent), independent Gate acceptance **+0/26**.
- Percent reports must always distinguish **PARTIAL coverage** from **ACCEPTED completion** and show exact current-turn change.

## Next real gated sequence
1. ENGINE/CENTRAL Phase2 Release/NB23, full typed authority and locator + ORIGINAL Engine hash wheel lock/wheelhouse ABI.
2. SERVER/Ops approved separate Mac snapshot, Build/Start with pinned image DIGEST, UID/HOME/volumes/PKI; compare actual SBOM and OCI scans.
3. DBA/Auth signed real two-owner L2 through HTTPS/OIDC/mTLS and PG RLS with GET-only Refresh and no cross-owner access.
4. Separately authorized real C018 one OS child, verified ten sources, no generation and no extra child on Refresh.
5. Independent encrypted restore, RPO/RTO, signed policy and load/trace evidence; Security review.
6. CENTRAL decisions on all 26 Gates, then controlled release and Hypercare. No frozen Mac change, no Arvan release absent that decision.
