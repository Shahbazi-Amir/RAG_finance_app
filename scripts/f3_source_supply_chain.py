#!/usr/bin/env python3
"""Offline exact-lock CycloneDX source SBOM + high-confidence secret scan.
No vulnerability data, installed wheels, actual OCI images or runtime state inferred.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

KEY_PATTERNS = {
    "private_key_header": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "github_classic_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "aws_access_key_id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{24,}"),
}
SCAN_SUFFIX = {".py", ".ts", ".tsx", ".js", ".cjs", ".mjs", ".sh",
               ".yaml", ".yml", ".json", ".md", ".toml", ".sql", ".env"}
SKIP_SUFFIX = {".lock", ".svg", ".png", ".jpg", ".zip", ".pem", ".p12"}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pip_components(lock):
    result = []
    records = re.split(r"(?m)^(?=[A-Za-z0-9_.-]+==)", lock)
    for rec in records:
        m = re.match(r"\s*([A-Za-z0-9_.-]+)==([^\s\\]+)", rec)
        if not m:
            continue
        name, version = m.groups()
        hashes = sorted(set(re.findall(r"--hash=sha256:([0-9a-fA-F]{64})", rec)))
        if not hashes:
            raise ValueError("API dependency missing sha256: " + name)
        result.append({
            "type": "library", "name": name.lower().replace("_", "-"),
            "version": version, "purl": "pkg:pypi/" + name.lower().replace("_", "-") + "@" + version,
            "hashes": [{"alg": "SHA-256", "content": h.lower()} for h in hashes],
            "scope": "required",
        })
    if not result:
        raise ValueError("Empty API lock")
    return sorted(result, key=lambda c: c["purl"])

def npm_components(lock):
    doc = json.loads(lock)
    if doc.get("lockfileVersion") not in (2, 3):
        raise ValueError("Unsupported npm lockfileVersion")
    comps = []
    for path, info in doc.get("packages", {}).items():
        if not path or "node_modules/" not in path:
            continue
        if not isinstance(info, dict) or not info.get("version"):
            raise ValueError("npm unpinned package " + path)
        name = path.rsplit("node_modules/", 1)[-1]
        # package paths already include the @scope/name when applicable.
        version = str(info["version"])
        purl_name = name.replace("@", "%40", 1) if name.startswith("@") else name
        comp = {"type": "library", "name": name, "version": version,
                "purl": "pkg:npm/" + purl_name + "@" + version,
                "scope": "excluded" if info.get("dev") else "required"}
        integrity = str(info.get("integrity", ""))
        if integrity.startswith("sha512-"):
            # hash is base64, not hex, so do not mislabel a hash.
            comp["properties"] = [{"name": "npm:lock_integrity_sha512_base64", "value": integrity[7:]}]
        comps.append(comp)
    if not comps:
        raise ValueError("Empty Web npm lock")
    return sorted(comps, key=lambda c: c["purl"])

def scan_secrets(root):
    files = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).split(b"\0")
    scanned = 0
    findings = []
    for item in files:
        if not item:
            continue
        rel = item.decode("utf-8", "surrogateescape")
        p = root / rel
        if not p.is_file() or p.stat().st_size > 1024 * 1024:
            continue
        if p.suffix in SKIP_SUFFIX or (p.suffix not in SCAN_SUFFIX and not p.name.endswith(".env.example")):
            continue
        scanned += 1
        content = p.read_text("utf-8", errors="replace")
        for num, line in enumerate(content.splitlines(), start=1):
            for label, rule in KEY_PATTERNS.items():
                if rule.search(line):
                    # Never print, persist or upload the suspicious value itself.
                    findings.append({"path": rel, "line": num, "pattern": label})
    return {"contract": "f3.source_secret_scan.v1", "scanned_files": scanned,
            "findings": findings, "status": "FINDINGS" if findings else "NO_HIGH_CONFIDENCE_MATCHES",
            "coverage": "high-confidence literal patterns in tracked text only; not full secret detection"}

def generate(root, output):
    npm_lock = root / "apps/web/package-lock.json"
    api_lock = root / "locks/requirements-api.lock"
    components = pip_components(api_lock.read_text()) + npm_components(npm_lock.read_text())
    metadata = {"git_commit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
                "web_package_lock_sha256": digest(npm_lock),
                "api_requirements_lock_sha256": digest(api_lock),
                "engine_lock": "NOT_FURNISHED",
                "OCI_image_sbom": "NOT_RUN",
                "scope": "SOURCE_LOCK_ONLY_NOT_INSTALLED_ABI_OR_VULNERABILITY_PROOF"}
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "application", "name": "RAG_finance_app-source", "version": metadata["git_commit"]},
                         "properties": [{"name": k, "value": v} for k, v in metadata.items()]},
            "components": components}
    output.mkdir(parents=True, exist_ok=True)
    (output / "source_web_api_cyclonedx.json").write_text(json.dumps(sbom, indent=2, ensure_ascii=False) + "\n")
    scan = scan_secrets(root)
    (output / "source_secret_scan.json").write_text(json.dumps(scan, indent=2) + "\n")
    report = {"schema": "foundation.f3.source_supply_chain.v1", "commit": metadata["git_commit"],
              "api_dependencies": sum(x["purl"].startswith("pkg:pypi/") for x in components),
              "web_lock_packages": sum(x["purl"].startswith("pkg:npm/") for x in components),
              "source_scan": scan["status"], "source_scanned_files": scan["scanned_files"],
              "missing": ["Engine exact wheelhouse/CPython3.11.18 ABI", "actual OCI image digests and image vulnerability scan",
                          "signed target Mac source snapshot and live operator receipt"],
              "vulnerability_status": "NOT_AUDITED_IN_OFFLINE_STEP"}
    (output / "source_supply_chain_status.json").write_text(json.dumps(report, indent=2) + "\n")
    print("F3_SOURCE_SUPPLY_CHAIN_SBOM", report["api_dependencies"], report["web_lock_packages"],
          "SECRET", scan["status"], "FILES", scan["scanned_files"])
    if scan["findings"]:
        raise SystemExit(70)

def npm_audit(raw_file, output):
    output.mkdir(parents=True, exist_ok=True)
    try:
        doc = json.loads(raw_file.read_text())
    except Exception:
        doc = {}
    meta = doc.get("metadata", {}).get("vulnerabilities", {})
    if not isinstance(meta, dict) or "total" not in meta:
        report = {"scope": "npm production dependency audit", "status": "ERROR_OR_UNAVAILABLE",
                  "high": None, "critical": None, "gate": "NOT_ACCEPTED"}
        code = 70
    else:
        report = {"scope": "npm production dependency audit", "status": "COMPLETE",
                  "counts": {k: meta.get(k, 0) for k in ("info", "low", "moderate", "high", "critical", "total")},
                  "high": meta.get("high", 0), "critical": meta.get("critical", 0),
                  "gate": "REVIEW_REQUIRED_NOT_MODULE_ACCEPTANCE"}
        code = 1 if report["high"] or report["critical"] else 0
    (output / "npm_production_audit_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("F3_NPM_AUDIT", report["status"], "HIGH", report["high"], "CRITICAL", report["critical"])
    if code:
        raise SystemExit(code)

def selftest():
    fixture = ("httpx==0.28.0 \\\n    --hash=sha256:" + "a"*64 + "\n")
    assert len(pip_components(fixture)) == 1
    assert pip_components(fixture)[0]["name"] == "httpx"
    assert KEY_PATTERNS["github_classic_token"].search("ghp_" + "A"*31)
    sample = json.dumps({"lockfileVersion": 3, "packages": {"": {}, "node_modules/@scope/example": {"version": "1.2.3"}}})
    assert len(npm_components(sample)) == 1
    print("F3_SUPPLY_CHAIN_PARSER_SELFTEST_PASS")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", default="ci_receipts/supply_chain")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--npm-audit-json", default=None)
    opt = parser.parse_args()
    if opt.self_test:
        selftest()
    elif opt.npm_audit_json:
        npm_audit(Path(opt.npm_audit_json), Path(opt.out))
    else:
        generate(Path(opt.repo).resolve(), Path(opt.out))
