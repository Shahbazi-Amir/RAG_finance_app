#!/usr/bin/env python3
"""Emit source-backed, bounded CI witnesses only AFTER three CI jobs pass.

The job dependency graph proves three existing test jobs completed. These
witnesses are narrower than canonical activities and not owner acceptance.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
MATRIX=ROOT/"coordination/integration/F3_42_NEW_BOUNDED_CI_LAB_SLICES.json"
SHA=re.compile(r"^[a-f0-9]{40}$")
ID=re.compile(r"^P3M\d{2}-A\d{2}$")
COMMAND={
 "WEB_UNIT":"npm --prefix apps/web run test",
 "API_UNIT":"python -m unittest discover -s tests/phase3/api",
 "CONTRACT_UNIT":"python -m unittest discover -s tests/phase3/contracts",
 "DB_LAB":"bash scripts/",
 "OCI_LAB":"Grype scan exact API image SPDX after test",
}
HOLD="NOT_ACCEPTED_NO_INDEPENDENT_SIGNED_RECEIPT"

def verified_repo_file(path: str, marker: str) -> bool:
    assert isinstance(path,str) and isinstance(marker,str)
    assert path and marker and len(marker)<=180
    p=PurePosixPath(path)
    assert not p.is_absolute() and ".." not in p.parts
    src=ROOT / path
    assert src.is_file() and src.resolve().is_relative_to(ROOT.resolve())
    return marker in src.read_text(encoding="utf-8")

def attest(original: dict, matrix: dict, sha: str, run: str, workflow: str) -> tuple[dict,dict]:
    assert isinstance(sha,str) and SHA.fullmatch(sha)
    assert isinstance(run,str) and run.isdecimal() and int(run)>0
    assert isinstance(original,dict) and isinstance(matrix,dict)
    assert original["generated_source_sha"]==sha
    assert original["counts"]=={
      "activities":262,"module_gates":26,"operational_non_counting":105,"rows":393}
    assert original["acceptance_claim"]=="NONE_GENERATED_LEDGER_IS_NOT_OWNER_ACCEPTANCE"
    assert matrix["schema"]=="foundation.f3.42_new_verified_bounded_ci_assertions.v1"
    assert matrix["owner_approved"] is False and matrix["gate_accepted"] is False
    assert len(matrix["rows"])==42
    assert len(original["rows"])==393
    by_id={x["id"]:x for x in original["rows"]}
    assert len(by_id)==393
    historical={x["id"] for x in original["rows"] if x["git_sha"]}
    assert len(historical)==20
    assert all(by_id[x]["git_sha"]!=sha for x in historical)
    assert all(x["acceptance_status"]==HOLD for x in original["rows"])
    assert "npm --prefix apps/web run test" in workflow
    assert "python -m unittest discover -s tests/phase3/api" in workflow
    assert "python -m unittest discover -s tests/phase3/contracts" in workflow
    assert "bash scripts/19_history_rls_negative_matrix.sh" in workflow
    assert "Grype scan exact API image SPDX after test" in workflow
    assert "Grype scan exact Web image SPDX after test" in workflow
    additions=[]
    ids=set()
    link=f"https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/{run}"
    for witness in matrix["rows"]:
        id=witness["id"]
        assert ID.fullmatch(id) and id not in ids and id not in historical
        ids.add(id)
        row=by_id[id]
        assert row["kind"]=="primary_activity" and row["counts_as_activity"]=="true"
        assert row["canonical_criterion"]==witness["canonical_criterion"]
        assert all(witness[x] is False for x in
                   ("owner_acceptance","full_criterion_satisfied","target_verified","engine_executed"))
        kind=witness["ci_job"]
        assert kind in COMMAND and COMMAND[kind] in workflow
        src=witness["source_file"]; marker=witness["literal_assertion"]
        assert verified_repo_file(src,marker), "SOURCE_PROOF_MISSING:"+id
        if kind=="DB_LAB":
            assert "bash scripts/"+Path(src).name in workflow, "DB_SCRIPT_NOT_IN_CI:"+id
        if kind=="WEB_UNIT": assert src.endswith(".mjs")
        if kind=="API_UNIT": assert src.startswith("tests/phase3/api/") or src=="apps/api/app_only_asgi.py"
        if kind=="CONTRACT_UNIT": assert src.startswith("tests/phase3/contracts/")
        # The CI job and source test are verified, but not every part of the
        # canonical criterion is. All canonical acceptance remains unchanged.
        current=by_id[id]
        current["app_only_slice"]="SOURCE_AND_DISPOSABLE_CI_BOUNDED_NOT_APPROVED_DENOMINATOR"
        current["tested_scope"]=current["source_tested_field"]+" ; CI_BOUNDED:"+marker
        current["git_sha"]=sha
        current["run_or_env"]="DISPOSABLE_SAME_SHA_GITHUB_ACTIONS_RUN "+run+" ; SOURCE_TEST_STEP "+kind
        current["artifact_link"]=current["artifact_link"]+" ; "+link
        current["next_action"]="OWNER_REVIEW_REAL_TARGET_AND_FULL_CRITERION_NOT_AUTOMATIC_ACCEPTANCE"
        additions.append({
           "id":id, "criterion":row["canonical_criterion"],
           "source_path":src,"assertion_marker":marker,"tested_ci_job":kind,
           "run_url":link,"git_sha":sha,
           "result":"BOUNDED_EXECUTED_CI_SLICE_ONLY_NOT_FULL_TASK",
           "target_verified":False,"owner_accepted":False})
    assert len(ids)==42
    witnessed={x["id"] for x in original["rows"] if x["git_sha"]}
    assert len(witnessed)==62
    assert len(witnessed-historical)==42
    out=copy.deepcopy(original)
    out["schema"]="foundation.f3.unified_register_393.plus_42_source_backed_ci_slices.v1"
    out["acceptance_claim"]="NONE_GENERATED_LEDGER_AND_CI_LAB_SLICE_NOT_OWNER_ACCEPTANCE"
    out["counts"]["historical_bounded_ci_rows"]=20
    out["counts"]["same_sha_additional_bounded_ci_rows"]=42
    out["counts"]["all_bounded_ci_rows"]=62
    report={
      "schema":"foundation.f3.42_actual_ci_subsets_same_sha.v1",
      "git_sha":sha,"run_id":int(run),"run_url":link,
      "environment":"DISPOSABLE_GITHUB_ACTIONS_JOBS_ALL_3_SUCCESS",
      "before_historical_witnessed":20,
      "additional_source_tested_on_this_sha":42,
      "after_total_bounded_witnessed":62,
      "increase_points_of_262_activity_denominator":round(100*42/262,4),
      "new_target_verified":0,"new_owner_accepted":0,
      "new_complete_canonical_activities":0,
      "owner_approved_denominator":False,
      "independent_module_gates_accepted":0,
      "security_release":"HOLD_PENDING_SECURITY_OWNER_TRIAGE",
      "actual_ci_subset_witnesses":additions}
    return out,report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    sha=os.environ.get("GITHUB_SHA","")
    run=os.environ.get("GITHUB_RUN_ID","")
    assert os.getenv("CI")=="true" and os.getenv("GITHUB_ACTIONS")=="true"
    assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==sha
    original=json.loads(a.ledger.read_text(encoding="utf-8"))
    matrix=json.loads(MATRIX.read_text(encoding="utf-8"))
    workflow=(ROOT/".github/workflows/f3-foundation-candidate-full-isolated-regression.yml").read_text(encoding="utf-8")
    combined,report=attest(original,matrix,sha,run,workflow)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"f3_393_62_ci_lab_rows_unaccepted.json").write_text(
       json.dumps(combined,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
    (a.out/"f3_42_additional_ci_lab_witnesses.json").write_text(
       json.dumps(report,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
    print("F3_42_NEW_SOURCE_TESTED_CI_BOUNDED_ROWS_62_TOTAL_NO_GATE_NO_OWNER_ACCEPTANCE")

if __name__=="__main__":
    main()
