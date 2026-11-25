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
