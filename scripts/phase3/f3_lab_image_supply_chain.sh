#!/usr/bin/env bash
# CI image evidence only; never mounts runtime secrets, Docker socket or host data.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_OS:-}" == Linux ]] || exit 70
cd "${GITHUB_WORKSPACE:?}"
sha="$(git rev-parse HEAD)"
out="$GITHUB_WORKSPACE/ci_receipts/lab_image_supply_chain"
mkdir -p "$out"
scratch="$(mktemp -d "$RUNNER_TEMP/f3-image-scan.XXXXXX")"
trap 'sudo rm -rf -- "$scratch"' EXIT
scanner=aquasec/trivy:0.67.2

# Immutable image IDs and registry digests observed locally, not release pins.
idp=quay.io/keycloak/keycloak@sha256:7e66a96e4739239070aeaf72e4c5decf0f7f682cfc725b9f7ea2b336eaba38b3
pg=docker.io/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a
api="f3-browser-api:$sha"
web="f3-browser-web:$sha"
browser="f3-browser-probe:$sha"
python3 scripts/phase3/f3_lab_image_manifest.py --out "$out" \
  --image "api=$api" --image "web=$web" --image "idp=$idp" --image "pg=$pg" --image "browser=$browser"
docker pull "$scanner"
scanner_id="$(docker image inspect -f '{{.Id}}' "$scanner")"
docker image inspect -f '{{json .RepoDigests}}' "$scanner" > "$scratch/scanner-digests.json"
mkdir -p "$scratch/cache"
for role in api web idp pg browser; do
  ref="${!role}"
  # Saved OCI/Docker archive only; scanner has no Docker socket and cannot inspect
  # the running service or its per-container configuration or secrets.
  docker image save -o "$scratch/image.tar" "$ref"
  docker run --rm --mount "type=bind,source=$scratch,target=/scan" "$scanner_id" image \
    --cache-dir /scan/cache --timeout 8m --input /scan/image.tar \
    --scanners vuln --format cyclonedx --output "/scan/$role.cdx.json" --exit-code 0
  docker run --rm --mount "type=bind,source=$scratch,target=/scan" "$scanner_id" image \
    --cache-dir /scan/cache --timeout 8m --input /scan/image.tar \
    --scanners vuln --format json --output /scan/raw.json --exit-code 0
  sudo chown "$(id -u):$(id -g)" "$scratch/$role.cdx.json" "$scratch/raw.json"
  python3 - "$role" "$scratch" "$out" "$scanner_id" <<'PY'
import json,sys,hashlib
from pathlib import Path
role,root,out,scanner=sys.argv[1:]
root,out=Path(root),Path(out)
sbom=root/(role+".cdx.json")
d=json.loads(sbom.read_text())
assert d["bomFormat"]=="CycloneDX" and d.get("components"), "empty-image-sbom"
raw=json.loads((root/"raw.json").read_text())
assert isinstance(raw.get("Results"),list) and raw["Results"], "scan-results-missing"
counts={k:0 for k in ("UNKNOWN","LOW","MEDIUM","HIGH","CRITICAL")}
for result in raw["Results"]:
    for v in result.get("Vulnerabilities") or []:
        sev=v.get("Severity","UNKNOWN")
        counts[sev if sev in counts else "UNKNOWN"]+=1
# retain package/CVE IDs and severities only, not raw scanner documents.
findings=sorted({(v.get("VulnerabilityID",""),v.get("PkgName",""),v.get("InstalledVersion",""),v.get("FixedVersion",""),v.get("Severity","UNKNOWN")) for r in raw["Results"] for v in r.get("Vulnerabilities") or []})
summary=dict(role=role,scanner_image_id=scanner,scanner_registry_digests=json.loads((root/"scanner-digests.json").read_text()),
    scan_status="COMPLETED_REVIEW_REQUIRED" if any(counts.values()) else "NO_VULNERABILITIES_REPORTED",
    counts=counts,findings=[dict(id=x[0],package=x[1],installed=x[2],fixed=x[3],severity=x[4]) for x in findings],
    sbom_sha256=hashlib.sha256(sbom.read_bytes()).hexdigest(),sbom_components=len(d["components"]),
    target_acceptance="NOT_ACCEPTED")
(out/(role+".vulnerability_summary.json")).write_text(json.dumps(summary,indent=2)+"\n")
(out/(role+".cdx.json")).write_bytes(sbom.read_bytes())
print("F3_IMAGE_SCAN_COMPLETE",role,counts["HIGH"],counts["CRITICAL"],len(d["components"]))
PY
  rm -f "$scratch/image.tar" "$scratch/raw.json" "$scratch/$role.cdx.json"
done
echo F3_IMAGE_SBOM_SCAN_REPORTS_COMPLETE_NOT_RELEASE_APPROVAL
