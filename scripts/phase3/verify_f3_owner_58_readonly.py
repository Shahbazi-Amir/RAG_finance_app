#!/usr/bin/env python3
"""Read-only 58-path frozen four-owner audit and 16 retained source diffs.

Never merge, execute a source file, grant approvals, or expose code in receipts.
The comparison is a *textual set* of lines, not semantic conflict resolution.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,os,re,subprocess
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"coordination/integration/FOUR_PR_58_PATH_THREE_WAY_AUDIT_20261124.json"
OUTPUT=ROOT/"ci_receipts/foundation/owner_58_source_readonly_audit.json"
PIN=re.compile(r"^[0-9a-f]{40}$")
ALLOWED={"EXACT_SOURCE_SELECTED":36,
         "FOUNDATION_SECURITY_COMPAT":6,
         "FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW":16}

class SourceAuditError(ValueError):pass

def require(condition,message):
    if not condition:raise SourceAuditError(message)

def safe_path(value):
    require(isinstance(value,str) and 0<len(value)<250 and
            "\0" not in value and not value.startswith("-"),"UNSAFE_PATH")
    path=PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and all(x not in (".git","") for x in path.parts),
            "PATH_ESCAPE")
    return value

def check_manifest(doc):
    require(isinstance(doc,dict),"BAD_MANIFEST")
    require(doc.get("kind")=="f3_four_pr_all_divergent_paths_review","WRONG_SOURCE_AUDIT")
    require(doc.get("contract_version")=="integration.f3.three_way_audit.v1","WRONG_VERSION")
    require(doc.get("owner_approval_required") is True and
            doc.get("p0_1_accepted") is False,"FALSE_ACCEPTANCE")
    require(isinstance(doc.get("baseline_sha"),str) and PIN.fullmatch(doc["baseline_sha"]),
            "NO_BASELINE_PIN")
    summary=doc.get("summary")
    require(isinstance(summary,dict) and
            summary.get("total_unique_divergent_paths")==58 and
            summary.get("retained_pending")==16 and
            summary.get("source_selected")==36 and
            summary.get("foundation_security")==6,"WRONG_DENOMINATOR")
    rows=doc.get("paths")
    require(isinstance(rows,list) and len(rows)==58,"NOT_58_SOURCE_FILES")
    paths=set()
    counts=Counter()
    for row in rows:
        require(isinstance(row,dict),"INVALID_ROW")
        path=safe_path(row.get("path"))
        require(path not in paths,"DUPLICATE_PATH")
        paths.add(path)
        decision=row.get("decision")
        require(decision in ALLOWED,"UNAUTHORIZED_DECISION")
        counts[decision]+=1
        require(row.get("owner_signed_acceptance") is False,"FORGED_OWNER_SIGNOFF")
        sources=row.get("source_options")
        require(isinstance(sources,list) and len(sources)>0,"MISSING_SOURCE_OPTION")
        for x in sources:
            require(isinstance(x,dict) and x.get("owner") in ("ui","api","db") and
                    isinstance(x.get("commit_sha"),str) and PIN.fullmatch(x["commit_sha"]) and
                    isinstance(x.get("blob_sha"),str) and PIN.fullmatch(x["blob_sha"]),
                    "SOURCE_BLOB_UNPINNED")
        require(isinstance(row.get("integrated_blob_sha"),str)
                and PIN.fullmatch(row["integrated_blob_sha"]),"MISSING_FROZEN_RESULT_BLOB")
    require(all(counts[k]==v for k,v in ALLOWED.items()),"58_PATH_CLASS_COUNTS_DRIFT")
    return [x for x in rows if x["decision"]=="FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW"]

def unique_source_lines(source,candidate):
    """Unique text lines only. Whitespace and line-order are intentionally ignored."""
    a={x.strip() for x in source.splitlines() if x.strip()}
    b={x.strip() for x in candidate.splitlines() if x.strip()}
    return {"owner_only_nonempty_line_kinds":len(a-b),
            "candidate_only_nonempty_line_kinds":len(b-a),
            "same_nonempty_line_kinds":len(a&b)}

def run_git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True,text=False,timeout=35)
    if p.returncode:
        raise SourceAuditError("MISSING_GIT_OBJECT_OR_INVALID_FROZEN_SOURCE")
    return p.stdout

def checked_source(commit,path,expected_blob):
    commit_sha=run_git("rev-parse",commit+":"+path).decode().strip()
    require(commit_sha==expected_blob,"SOURCE_BLOB_MISMATCH")
    data=run_git("show",commit+":"+path)
    # Validate Git blob metadata independently, not trust a path label.
    observed=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    require(observed==expected_blob,"SOURCE_CONTENT_HASH_MISMATCH")
    return data.decode("utf-8",errors="replace")

def main():
    require(os.getenv("CI")=="true" and os.getenv("GITHUB_ACTIONS")=="true",
            "DISPOSABLE_CI_ONLY")
    sha=os.getenv("GITHUB_SHA","")
    require(bool(PIN.fullmatch(sha)) and
            run_git("rev-parse","HEAD").decode().strip()==sha,
            "CHECKOUT_SHA_MISMATCH")
    require(run_git("rev-parse","--is-shallow-repository").decode().strip()=="false",
            "GIT_HISTORY_NOT_FULLY_FETCHED")
    doc=json.loads(INPUT.read_text(encoding="utf-8"))
    retained=check_manifest(doc)
    # Fetch remote refs is forbidden in this job: source refs must be
    # present in the verified checkout; no mutations of any branch/ref.
    results=[]
    for row in retained:
        path=row["path"]
        current=run_git("show","HEAD:"+path).decode("utf-8",errors="replace")
        options=[]
        for owner in row["source_options"]:
            origin=checked_source(owner["commit_sha"],path,owner["blob_sha"])
            line_counts=unique_source_lines(origin,current)
            options.append({
                "owner":owner["owner"],
                "frozen_source_commit":owner["commit_sha"],
                "frozen_source_blob":owner["blob_sha"],
                **line_counts,
                "owner_signoff":False})
        results.append({
            "path":path,
            "frozen_integration_blob":row["integrated_blob_sha"],
            "source_option_count":len(options),
            "owner_options":options,
            "review_state":"RETAINED_PENDING_OWNER_APPROVAL",
        })
    owner_only=sum(any(z["owner_only_nonempty_line_kinds"]>0 for z in row["owner_options"])
                   for row in results)
    result={
      "schema":"foundation.f3.58_source_16_retained_readonly_reconcile.v1",
      "checked_out_git_sha":sha,
      "frozen_source_baseline_sha":doc["baseline_sha"],
      "path_counts":{"all_divergent":58,"source_selected":36,
                     "foundation_security":6,"retained_reviewed":16,
                     "retained_with_owner_only_line_kinds":owner_only,
                     "retained_without_owner_only_line_kinds":16-owner_only},
      "owner_signed_acceptance":False,
      "p0_1_accepted":False,
      "product_paths_modified":False,
      "source_files_executed":False,
      "data_or_secrets_extracted":False,
      "source_line_content_uploaded":False,
      "semantic_equivalence_proven":False,
      "release":"HOLD",
      "retained_paths":results,
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print("F3_SOURCE_58_READONLY_16_OWNER_PENDING_AUDIT_PASS_NO_ACCEPTANCE")

if __name__=="__main__":
    main()
