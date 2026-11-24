#!/usr/bin/env python3
"""Record the tested local container/source provenance, not an approved release.

Only reads repository files and locally built images on a disposable CI runner.
No registry push/pull, signing key, secret, Mac, production or Engine operation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"ci_receipts/foundation/app_only_local_source_provenance.json"
FIXED=(
    "infra/phase3_l1/Dockerfile.api",
    "infra/phase3_l1/Dockerfile.web",
    "infra/phase3_l1/compose.app-only.internal.yml",
    "infra/phase3_l1/Dockerfile.api.signed_history",
    "locks/requirements-api.lock",
    "apps/web/package-lock.json",
    "packages/contracts/product.v1.schema.json",
    "coordination/phase3_checklist.md",
    "scripts/phase3/app_only_candidate_preflight.sh",
)
IMAGE_TAGS=(("api","rag-f3-app-only-api:ci","11001:11001"),
            ("web","rag-f3-app-only-web:ci","11003:11003"))


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git",*args],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()


def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        while chunk:=f.read(1024*1024):
            h.update(chunk)
    return h.hexdigest()


def manifest() -> dict:
    sha=os.environ["GITHUB_SHA"]
    if len(sha)!=40 or git("rev-parse","HEAD")!=sha:
        raise ValueError("SOURCE_SHA_NOT_CHECKED_OUT")
    if (ROOT/"infra/postgres/migrations/011_product_answer_claims.up.sql").exists():
        raise ValueError("UNAPPROVED_SQL_011_IN_APP_ONLY")
    files={}
    for name in FIXED:
        path=ROOT/name
        if not path.is_file():
            raise ValueError("MISSING_PINNED_SOURCE_FILE "+name)
        files[name]={"sha256":sha_file(path),"size_bytes":path.stat().st_size}
    migrations={}
    root=ROOT/"infra/postgres/migrations"
    for number in range(1,11):
        found=list(root.glob(f"{number:03d}_*.up.sql"))
        if len(found)!=1:
            raise ValueError("MIGRATION_NOT_UNIQUE "+str(number))
        path=found[0]
        migrations[path.name]=sha_file(path)
    images={}
    for name,tag,expected_user in IMAGE_TAGS:
        info=json.loads(subprocess.check_output(
            ["docker","image","inspect",tag],text=True))[0]
        config=info["Config"]
        if (config["Labels"].get("org.opencontainers.image.revision")!=sha
                or config["User"]!=expected_user
                or not info["Id"].startswith("sha256:")):
            raise ValueError("LOCAL_IMAGE_PIN_OR_USER_MISMATCH "+name)
        if info["Os"]!="linux" or info["Architecture"]!="amd64":
            raise ValueError("IMAGE_PLATFORM_MISMATCH "+name)
        images[name]={
            "local_content_image_id":info["Id"],
            "registry_manifest_digest":None,
            "user":config["User"],
            "platform":"linux/amd64",
            "healthcheck_configured":bool(config.get("Healthcheck")),
        }
    return {
        "schema":"foundation.f3.tested_local_source_and_image_provenance.v1",
        "git_sha":sha,
        "git_tree_sha":git("rev-parse","HEAD^{tree}"),
        "tested_environment":"disposable-GitHub-Actions-local-images",
        "input_files":files,
        "postgres_migrations_001_010_sha256":migrations,
        "local_images":images,
        "approved_release":False,
        "registry_digest_verified":False,
        "sbom_scanner_gate_accepted":False,
        "mac_target_touched":False,
        "engine_lock_or_runner_imported":False,
        "postgres_migration_011_applied":False,
        "human_signed_release":False,
    }


def main() -> None:
    OUT.parent.mkdir(parents=True,exist_ok=True)
    result=manifest()
    OUT.write_text(json.dumps(result,sort_keys=True,indent=2)+chr(10))
    print("F3_FOUNDATION_TESTED_LOCAL_IMAGE_SOURCE_PROVENANCE_PASS_NOT_RELEASE")


if __name__=="__main__":
    main()
