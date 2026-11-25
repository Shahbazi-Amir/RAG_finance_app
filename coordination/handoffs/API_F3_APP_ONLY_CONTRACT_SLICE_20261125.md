# API independent slice — proposed on #146
Baseline exact green 6cb193e255b25cc5ee6c8b4b95265f1b96e0dcd8, runs 45539526773 and 45539526849. This change does not alter the canonical product.v1 schema, accepted states or shared Foundation manifest.

| Canonical ID | Executable scope | Still open |
|---|---|---|
| P3M13-A01 | offline OpenAPI 3.1 document references canonical DTOs; signed read routes and disabled Send | consumer approval, complete future API, target |
| P3M05-A09 | fixed-label denial log; live synthetic HTTP canaries, no token/password | operational retention/alert policy and target |
| P3M11-A03 | synthetic canonical DTO author field required and lossless JSON | real producer/source authority |
| P3M11-A04 | distinct editor field, null author remains null | real producer/source authority |
| P3M11-A05 | transcript speaker field required and lossless JSON | real transcript source and UI |
| P3M11-A06 | authority/attribution enums and required fields | approved attribution, true source evidence |
| P3M13-A02/A03/A08 | actual signed status missing/invalid query for A/B | positive historical accepted Send status not supplied by this fixture |
| P3M17-A05 | status negative no-store | approved full cache topology |

P3M05-A08 additionally has historical exact #146 PG before/after rotation/expiry/no implicit refresh witness (45539526849); source target policy remains open. Do not count it twice with #139. Do not count synthetic metadata as real Citation, or mark any of these IDs accepted. No engine, SQL011, policy approval, target or main merge.

Replay from exact PR HEAD:
- python -m unittest discover -s tests/phase3/api -p test_app_only_offline_contract.py -v
- Existing API F3 signer continuity source and real isolated PG restore workflows.
- Foundation to transfer only missing changes and rerun shared real browser/SQL/restore on the selected common SHA.

## Evidence reconciliation (NOT acceptance)
- Exact source commit f83263fb51a585d2fefaa944fa56a2cefdb7819c: source CI 45545332473 success, 81/81 (13+7+11+11+30+9); new PG run 45545332409 not yet confirmed on this SHA at evidence commit.
- Previous PR #146 6cb193e255b25cc5ee6c8b4b95265f1b96e0dcd8 run 45539526849 SUCCESS, directly observed 200/503/200 role grant drift and before/after expiry/rotation, 24 disabled concurrent signed Send retries, restore and source cursor.
- Imported evidence-only fields from #140 2eec93c8ef91795f2782d167830b1b3ea02d0471; no other branch source changes transferred. All 91 IDs, owner, criterion, source, starting status, blocker and accepted NO are unchanged. Historical witnesses from #116 exact 9cacaede2fd67b5cf13331c7650532b8b408a8dc job 138521765309 run 45415865946 inspected against actual test source.
- 33 -> 43 direct bounded rows (+10/91, +10.99 percentage points): six source tests newly executed on f83263fb51a585d2fefaa944fa56a2cefdb7819c, four historical evidence reconciliations (A08 on #146 and M09-A07/M12-A03/M17-A03 on #116). NOT ten activities complete, no increase in full code/target acceptance. 48/91 not directly attested. 61 PARTIAL and 30 NOT_VERIFIED historical starting states unchanged.
- Evidence-only commit following f83263fb51a585d2fefaa944fa56a2cefdb7819c: does not automatically confer green status on new commit or integrated common tree. Foundation/CENTRAL must select one candidate, resolve remaining owner conflicts, rerun and accept exact scope.

## Persian red-team and contract continuation — 2026-11-25
- Baseline c0a578491297042c0dff1873446e6846f6460b8d: both CI workflows 45545595548 and 45545595440 completed SUCCESS.
- Executable change 0924ec3fa108f97915ed9fc543a4ec3d1e793548: canonical product.v1 unchanged; encoded and queried readiness rejected without PG admission; versioned synthetic Persian corpus, five locator types, confidence and output/outcome negatives. Source CI 45547610541: 90/90 PASS (13+7+11+11+31+9+8). PG CI 45547609767 not confirmed at this evidence checkpoint; no real PG credit for the new corpus. No actual inference, provider, source authority, policy approval, target or release approval.
- Verified historical #116 9cacaede2fd67b5cf13331c7650532b8b408a8dc, run 45415865946 job 138521765309, exactly three additional previously executed bounded assertions (retrieval synthetic timeout, count-only gateway timeout, malformed synthetic result gate). No rerun of a real engine.
- Matrix 43 -> 52/91 direct bounded subcases; 9 newly mapped IDs: P3M07-A05, P3M08-A05, P3M09-A02, P3M09-A09, P3M10-A04, P3M10-A06, P3M10-A07, P3M12-A05, P3M12-A08. Only 6 based on newly executed tests, three historical evidence reconciliations. 61 PARTIAL and 30 NOT_VERIFIED starting states, all 91 accepted NO remain unchanged. 39 without direct mapped evidence; not a completion metric. Release-ID schema test passed but does not prove M07-A06 index connection and is not counted for that row. Synthetic fixture labels are not a classifier; M12-A01/A02 remain open. No approved app-only denominator.
- Remaining per module: P3M05-: 2 (P3M05-A02, P3M05-A06); P3M07-: 8 (P3M07-A01, P3M07-A02, P3M07-A03, P3M07-A04, P3M07-A06, P3M07-A07, P3M07-A08, P3M07-A09); P3M08-: 6 (P3M08-A01, P3M08-A02, P3M08-A03, P3M08-A04, P3M08-A09, P3M08-A10); P3M09-: 6 (P3M09-A01, P3M09-A03, P3M09-A04, P3M09-A05, P3M09-A08, P3M09-A10); P3M10-: 3 (P3M10-A01, P3M10-A02, P3M10-A03); P3M11-: 3 (P3M11-A07, P3M11-A08, P3M11-A10); P3M12-: 5 (P3M12-A01, P3M12-A02, P3M12-A06, P3M12-A07, P3M12-A10); P3M13-: 0 (none); P3M17-: 6 (P3M17-A01, P3M17-A02, P3M17-A04, P3M17-A06, P3M17-A08, P3M17-A10).
- Transfer guidance for Foundation: #143 observed d2edeca685208f812cb3bc538264d4f54468d4fc had identical canonical Product.v1 blob and deny-only app_only_asgi.py; private listener differs, so do not wholesale replace it. Review scoped diff c0a578491297042c0dff1873446e6846f6460b8d..0924ec3fa108f97915ed9fc543a4ec3d1e793548, transfer corpus and tests plus only compatible readiness fixes, retain existing shared Bootstrap/BFF/PG and rerun integrated same-SHA browser→SQL→restore. No direct mutation of Foundation branch. New evidence-only commit must rerun exact-head CI, no old SHA promotion.
