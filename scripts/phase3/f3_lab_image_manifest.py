#!/usr/bin/env python3
"""Allowlisted, secret-free evidence of actual locally built lab image IDs.
Never claims registry or approved target release digests for local images.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

def run(*args):
    return subprocess.check_output(args,text=True).strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--image",action="append",required=True)
    args=p.parse_args()
    commit=run("git","rev-parse","HEAD")
    args.out.mkdir(parents=True,exist_ok=True)
    images=[]
    for item in args.image:
        role,ref=item.split("=",1)
        info=json.loads(run("docker","image","inspect",ref))[0]
        label=(info.get("Config",{}).get("Labels") or {}).get("org.opencontainers.image.revision")
        if (role in ("api","web") or (role=="pg" and os.environ.get("F3_PG_IMAGE"))) and label!=commit:
            raise SystemExit("SOURCE_LABEL_MISMATCH_"+role)
        images.append({"role":role,"reference":ref,"local_image_id":info["Id"],
            "registry_digests":info.get("RepoDigests") or [],
            "architecture":info["Architecture"],"os":info["Os"],
            "configured_user":info["Config"].get("User") or None,
            "revision_label":label,"base_image_ref":(info.get("Config",{}).get("Labels") or {}).get("org.opencontainers.image.base.name"),"size_bytes":info["Size"]})
    for role in ("api","web"):
        row=next(x for x in images if x["role"]==role)
        assert row["configured_user"] in ("11001:11001","11003:11003")
        assert row["os"]=="linux" and row["architecture"]=="amd64"
    paths=["locks/requirements-api.lock","apps/web/package-lock.json",
           "infra/phase3_l1/Dockerfile.api.signed","infra/phase3_l1/Dockerfile.api.slim-lab","infra/phase3_l1/Dockerfile.web",
           "infra/phase3_l1/lab/resolve_python_slim_base.sh","infra/phase3_l1/lab/Dockerfile.browser",
           "infra/phase3_l1/lab/patch_slim_os_ci.sh",
           "infra/phase3_l1/compose.app-only.browser-lab.yml",
           "infra/postgres/dev_f3_isolated/scripts/27_browser_app_only_pg_journey.sh",
           "packages/contracts/product.v1.schema.json",
           "apps/api/private_app_only_asgi.py",
           "apps/api/product_session_api.py",
           "apps/web/src/ui/runtime-capability.ts",
           "apps/web/src/history/proxy.ts"]
    if os.environ.get("F3_PG_IMAGE"):
        paths += ["infra/postgres/dev_f3_isolated/Dockerfile.pg-security-ci","infra/postgres/dev_f3_isolated/compose.lab.yaml","infra/postgres/dev_f3_isolated/scripts/06_backup_restore_independent.sh"]
    manifest={"schema":"f3.app_only.ci_candidate_manifest.v1","commit":commit,
       "environment":"disposable Linux CI, not an approved deployment",
       "images":images,"source_file_sha256":{path:sha(Path(path)) for path in paths},
       "engine":"DISABLED","target_release_digest":"NOT_APPROVED",
       "version_binding":{"product_contract":"product.v1",
           "product_contract_sha256":sha(Path("packages/contracts/product.v1.schema.json")),
           "app_only_policy_source_sha256":{path:sha(Path(path)) for path in (
               "apps/api/private_app_only_asgi.py","apps/api/product_session_api.py",
               "apps/web/src/ui/runtime-capability.ts","apps/web/src/history/proxy.ts")},
           "policy_approval":"NOT_APPROVED","knowledge_release":"NOT_CONNECTED",
           "retrieval_version":"NOT_CONNECTED","model_version":"NOT_CONNECTED"},
       "acceptance":"NOT_ACCEPTED"}
    (args.out/"ci_candidate_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("F3_ACTUAL_IMAGE_MANIFEST_PASS",commit,len(images))
if __name__=="__main__":
    main()
