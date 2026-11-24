# F3 Evidence Gate — same-SHA cross-artifact integrity

This gate verifies the four sanitized Foundation CI ZIP artifacts using one
fully specified git SHA. It checks all 393 source IDs, 262 primary activities,
26 independent Gates, 105 operational noncounting rows, valid owner/criterion,
per-row historical vs current SHA, SPDX bytes and scan counts, secret totals,
and explicit release HOLD. It does not approve a user story or Gate.

From the source repo at a protected checkout:

python -m unittest discover -s tests/phase3/foundation -p 'test_f3_exact_sha_artifacts.py' -v

When artifact ZIPs have been independently obtained from GitHub CI, run:

python scripts/phase3/verify_f3_evidence_bundle.py --ledger LEDGER.zip --scan SCAN.zip --secret SECRET.zip --provenance PROVENANCE.zip --expected-sha EXACT_40_CHAR_SHA --output RECEIPT.json

Optionally append --master-prompt PHASE3_MASTER_PROMPT_FA.md to check the
393 literal criteria. If the prompt is missing, that comparison remains
NOT_VERIFIED. ZIP names do not authenticate the GitHub run by themselves.

Per-job image IDs may differ. A green security scan is not an accepted
security policy. The test does not execute Engine, SQL011, Mac or production,
and cannot create an SBOM or registry digest. All gates remain HOLD until
authorized owner decisions and independent target evidence exist.
