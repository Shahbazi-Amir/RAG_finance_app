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
