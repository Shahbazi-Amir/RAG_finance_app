# Foundation proposal-only operational handoff

## Exact scope
The Wave 6 delta is restricted to CI workflows, tests, offline tooling and operational notes. Runtime apps/src, contracts, migrations, infrastructure and locks are unchanged against 5df84262fa3f6fab4b7a8fdbe63f458c3f3e1402. No engine, target, Phase 4 or SQL011. The new scope workflow enforces this on the candidate.

## Rehearse
Run `python3 -m unittest discover -s tests/phase3/foundation -p 'test_f3_policy_rehearsal.py' -v` from the clean checkout. Incident categories and proposed action sequences are nonbinding. A recovered dependency outage is not approval to launch; a duplicate/unknown operation requires GET-only reconciliation, no automatic replay. The synthetic backup planner takes explicit example keep/age values, retains legal/owner holds and newest verified encrypted backups, quarantines invalid records, and produces no delete command. No actual backup or user History retention policy has been selected. Ops/Security/DB owners must approve roles, incident response times, backup retention, real restore authority and RPO/RTO before target use. Security scan matches require owner triage; no waiver. The signed install, PITR, prior candidate rollback and browser receipts are all disposable CI, not target acceptance.

## Reproduce test evidence
Use the exact SHA run and artifact SHA256; compare image IDs within their own run, never across jobs. Preserve previous green evidence when a new test fails. Review native security-event capture, external alert routes, approved workload/SLO, actual target provisioning and NB23 as open.
