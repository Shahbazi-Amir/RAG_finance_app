#!/usr/bin/env python3
"""Verify exactly sourced Phase-3 CI evidence, never grant security/Gate approval.

Inputs are already-downloaded ZIP artifacts from a *single* pinned GitHub SHA.
A generated register SHA is not per-ID run evidence; local OCI IDs from
different jobs are not interchangeable, and neither is a registry digest.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

SHA = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
ACT = re.compile(r"^P3M\d{2}-A\d{2}$")
GATE = re.compile(r"^P3M\d{2}-GATE$")
OPS = re.compile(r"^P3OP\d{2}-R\d{2}$")
COUNTS = {"primary_activity":262, "independent_module_gate":26,
          "operational_crosswalk_non_counting":105}
FIELDS=("id","kind","owner","canonical_criterion","dependency","app_only_slice",
        "implementation_status","tested_scope","acceptance_status","git_sha",
        "run_or_env","artifact_link","blocker","next_action")
class EvidenceError(ValueError):
    pass

def require(cond, msg):
    if not cond: raise EvidenceError(msg)

def zip_json(path, name, max_size=12000000):
    try:
        with ZipFile(path) as z:
            entry=z.getinfo(name)
            require(entry.file_size <= max_size,"OVERSIZE_EVIDENCE")
            data=json.loads(z.read(entry))
    except (BadZipFile, KeyError, OSError, json.JSONDecodeError) as exc:
        raise EvidenceError("BROKEN_EVIDENCE_ZIP:"+name) from exc
    require(isinstance(data,dict),"EVIDENCE_NOT_JSON_OBJECT")
    return data

def spdx_images(path):
    result={}
    try:
        with ZipFile(path) as z:
            for kind in ("api","web"):
                member=kind+"-image.spdx.json"
                info=z.getinfo(member)
                require(0 < info.file_size <= 75000000,"SPDX_SIZE_INVALID")
                raw=z.read(info)
                result[kind]=(hashlib.sha256(raw).hexdigest(),json.loads(raw))
    except (OSError,KeyError,BadZipFile,json.JSONDecodeError) as exc:
        raise EvidenceError("INVALID_SPDX_ARCHIVE") from exc
    return result

def verify(ledger,scan,spdx,secret,provenance,sha,prompt=None):
    require(isinstance(sha,str) and SHA.fullmatch(sha),"EXPECTED_SHA_INVALID")
    require(ledger.get("generated_source_sha")==sha,"LEDGER_SHA_MISMATCH")
    require(ledger.get("acceptance_claim")==
        "NONE_GENERATED_LEDGER_IS_NOT_OWNER_ACCEPTANCE","UNAPPROVED_LEDGER_STATUS")
    rows=ledger.get("rows")
    require(isinstance(rows,list) and len(rows)==393,"LEDGER_NOT_393")
    ids=set()
    counts=Counter()
    main=set()
    crosswalk=[]
    old=[]
    exact=[]
    for row in rows:
        require(isinstance(row,dict) and all(k in row for k in FIELDS),
                "INCOMPLETE_LEDGER_ROW")
        ident=row["id"]
        require(isinstance(ident,str) and ident not in ids,"DUPLICATE_ID")
        ids.add(ident)
        kind=row["kind"]
        require(kind in COUNTS,"UNKNOWN_REGISTER_KIND")
        counts[kind]+=1
        require(row.get("generated_from_git_sha")==sha,"ROW_GENERATION_SHA_MISMATCH")
        require(row["acceptance_status"]==
           "NOT_ACCEPTED_NO_INDEPENDENT_SIGNED_RECEIPT","FORGED_ACCEPTANCE")
        require(all(isinstance(row[f],str) and row[f].strip() for f in
                    ("owner","dependency","canonical_criterion","next_action")),
                "MISSING_OWNER_OR_CRITERION")
        if kind=="primary_activity":
            require(bool(ACT.fullmatch(ident)) and row["counts_as_activity"]=="true",
                    "ACTIVITY_ID_OR_COUNTING_INVALID")
            main.add(ident)
        elif kind=="independent_module_gate":
            require(bool(GATE.fullmatch(ident)) and row["counts_as_activity"]=="false",
                    "GATE_ID_OR_COUNTING_INVALID")
        else:
            require(bool(OPS.fullmatch(ident)) and row["counts_as_activity"]=="false",
                    "CROSSWALK_DOUBLE_COUNT")
            crosswalk.append(row)
        witness=row["git_sha"]
        if witness:
            require(bool(SHA.fullmatch(witness)),"BAD_PER_ID_SOURCE_SHA")
            (exact if witness==sha else old).append(ident)
    require(all(counts[k]==n for k,n in COUNTS.items()),"CANONICAL_CARDINALITY")
    for row in crosswalk:
        require(not (set(row["dependency"].split(","))-main),
                "ORPHAN_CROSSWALK:"+row["id"])
    if prompt is not None:
        hits={}
        patt=re.compile(
            r"^\| (P3M\d{2}-(?:A\d{2}|GATE)|P3OP\d{2}-R\d{2}) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$",
            re.MULTILINE)
        for match in patt.finditer(prompt):
            require(match[1] not in hits,"PROMPT_DUPLICATE_ID")
            require(match[4]=="NOT_ACCEPTED","PROMPT_ACCEPTANCE_NOT_PERMITTED")
            hits[match[1]]=match[2]
        require(set(hits)==ids,"MASTER_PROMPT_ID_SET_MISMATCH")
        byid={row["id"]:row for row in rows}
        for ident,original in hits.items():
            actual=re.sub(r"^\[L\d+\]\([^)]*\):\s*","",byid[ident]["canonical_criterion"])
            norm=lambda s:re.sub(r"\s+"," ",s).strip().rstrip(".")
            require(norm(original)==norm(actual),"CRITERION_DRIFT:"+ident)
    for key,obj in (("SCAN",scan),("SECRET",secret),("PROVENANCE",provenance)):
        require(obj.get("git_sha")==sha,"MIXED_SHA_"+key)
    require(scan.get("release_decision")==
            "HOLD_PENDING_SECURITY_OWNER_TRIAGE_AND_APPROVED_THRESHOLDS",
            "RELEASE_HOLD_MISSING")
    require(scan.get("production_security_gate_accepted") is False and
            scan.get("policy_approved") is False,"FORGED_SECURITY_APPROVAL")
    require(secret.get("raw_report_uploaded") is False and
            secret.get("security_gate_accepted") is False and
            secret.get("owner_security_triage_complete") is False,
            "UNTRIAGED_SECRETS_PROMOTED")
    rules=secret.get("rules")
    require(isinstance(rules,dict) and
            all(type(n)==int and n>=0 for n in rules.values()) and
            sum(rules.values())==secret.get("total_potential_findings"),
            "SECRET_SCAN_COUNT_MISMATCH")
    require(provenance.get("approved_release") is False and
            provenance.get("human_signed_release") is False and
            provenance.get("registry_digest_verified") is False,
            "FORGED_RELEASE_PROVENANCE")
    images={}
    for kind in ("api","web"):
        sbom=scan.get("sboms",{}).get(kind)
        source=provenance.get("local_images",{}).get(kind)
        findings=scan.get("findings",{}).get(kind)
        require(all(isinstance(x,dict) for x in (sbom,source,findings)),
                "MISSING_IMAGE_ARTIFACT:"+kind)
        doc_hash,document=spdx[kind]
        require(doc_hash==sbom.get("sha256") and
                document.get("spdxVersion")=="SPDX-2.3" and
                isinstance(document.get("packages"),list) and
                len(document["packages"])>0 and
                len(document["packages"])==sbom.get("package_count"),
                "SBOM_INVALID_OR_TAMPERED:"+kind)
        require(sbom.get("registry_digest") is None and
                source.get("registry_manifest_digest") is None,
                "UNVERIFIED_REGISTRY_DIGEST:"+kind)
        sid=sbom.get("local_image_id")
        tid=source.get("local_content_image_id")
        require(isinstance(sid,str) and HASH.fullmatch(sid) and
                isinstance(tid,str) and HASH.fullmatch(tid),"IMAGE_ID_INVALID:"+kind)
        severity=findings.get("by_severity")
        require(isinstance(severity,dict) and
                all(type(n)==int and n>=0 for n in severity.values()) and
                sum(severity.values())==findings.get("total_vulnerabilities"),
                "SECURITY_TOTAL_INVALID:"+kind)
        critical_high=severity.get("CRITICAL",0)+severity.get("HIGH",0)
        triage=findings.get("critical_high_fix_triage")
        require(isinstance(triage,list) and len(triage)==critical_high,
                "CRITICAL_HIGH_DETAILS_MISSING:"+kind)
        for item in triage:
            require(isinstance(item,dict) and item.get("severity") in ("HIGH","CRITICAL")
                    and item.get("advisory") and item.get("package") and
                    not any(key in item for key in ("Secret","Match","Line","Token")),
                    "UNSAFE_OR_EMPTY_TRIAGE:"+kind)
        images[kind]={
          "critical":severity.get("CRITICAL",0),"high":severity.get("HIGH",0),
          "all_scanner_matches":findings["total_vulnerabilities"],
          "spdx_packages":len(document["packages"]),
          "scan_local_oci_id":sid,"tested_local_oci_id":tid,
          "same_binary_in_two_independent_jobs":sid==tid,
          "registry_release_equivalence":False,
        }
    return {
        "schema":"foundation.f3.offline_artifact_consistency.v1",
        "sha":sha,
        "ids":len(ids),"activities":counts["primary_activity"],
        "gates":counts["independent_module_gate"],
        "noncounting_crosswalks":counts["operational_crosswalk_non_counting"],
        "per_id_witness_same_sha":len(exact),
        "per_id_witness_old_sha":len(old),
        "per_id_unwitnessed":len(ids)-len(exact)-len(old),
        "exact_source_criteria_verified":len(ids) if prompt is not None else None,
        "security":images,"potential_secret_matches":secret["total_potential_findings"],
        "owner_accepted":False,"release_decision":"HOLD",
        "main_P0_accepted":0,"main_P0_total":6,
        "activity_accepted":0,"gate_accepted":0,
        "not_target_verification":True,
    }

def main():
    p=argparse.ArgumentParser()
    for field in ("ledger","scan","secret","provenance","expected-sha","output"):
        p.add_argument("--"+field,required=True)
    p.add_argument("--master-prompt")
    a=p.parse_args()
    scan=zip_json(Path(a.scan),"f3_sanitized_security_scan.json")
    ledger=zip_json(Path(a.ledger),"f3_393_evidence_ledger.json")
    secret=zip_json(Path(a.secret),"gitleaks_sanitized_summary.json")
    provenance=zip_json(Path(a.provenance),"app_only_local_source_provenance.json")
    prompt=Path(a.master_prompt).read_text() if a.master_prompt else None
    answer=verify(ledger,scan,spdx_images(Path(a.scan)),secret,provenance,
                  a.expected_sha,prompt)
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(answer,ensure_ascii=False,sort_keys=True,indent=2)+chr(10))
    print("F3_ARTIFACT_SHA_AND_393_CONSISTENCY_PASS_RELEASE_HOLD")

if __name__=="__main__":
    main()
