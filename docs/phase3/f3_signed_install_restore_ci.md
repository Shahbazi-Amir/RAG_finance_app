# Foundation: signed OCI local installation and PG restore — CI only

Root #84: 0fd1066945ef91a3913e040ab4c350bb645ea502. Last fully green #88: 9c14c56d847cc3657fc69327e4df59b002273719.
Run 45438123078 proves the five-step browser/SQL/restore and M10-A10 CI-only real signed POST with zero T3.

## Reproduce on authorized disposable GitHub runner

Run the workflow `.github/workflows/f3-foundation-integrated-signed-oci-browser.yml` on the exact working SHA. It checks out the source, stages pinned CI fixture overlays, builds both images using a clean git archive (not the overlays), saves both exact images locally, checks SHA256, rejects a tampered archive before load, removes only the two exact candidate tags, reloads and compares image IDs. It then starts the actual ordinary browser journey using the reimported images, performs the two-user independent PostgreSQL volume restore, repeats the journey, and scans those same image IDs with SPDX and Grype. The archive is local and deleted on exit; only sanitized receipts and SBOMs are uploaded. No archive of secrets, DB or user data is uploaded.

## Target / rollback boundary

This is a rehearsal of same-candidate local installation and independent data restoration, not a prior-release deployment rollback, signed registry digest, Mac install, or an approved RPO/RTO. The pinned CI Bootstrap worker is not deployable private staging. Existing deny-only compose and signed runtime entrypoints stay unchanged. Before any destination deployment, Ops must provide an approved namespace, snapshot/restore authority, prior release and registry digest, real Bootstrap/IdP/TLS/secret configuration, and security decisions. No production commands executed by this workflow. Release remains HOLD.
