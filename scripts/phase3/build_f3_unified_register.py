#!/usr/bin/env python3
"""Render the canonical Phase-3 checklist as 393 evidence-aware rows.

No guessed acceptance, source SHA interpreted only as REGISTER provenance,
not proof that any individual activity or module Gate passed.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "coordination" / "phase3_checklist.md"
TICK = chr(96)
ACT = re.compile(
    r"^\| \*\*(P3M\d{2}-A\d{2})\*\* — (.*?) \| (.*?) \| "
    r"(\*\*Output:.*?\*\*Check:.*?) \| " + TICK +
    r"(blocked|planned|active|review|accepted)" + TICK + r" \| " + TICK +
    r"(.*?)" + TICK + r" \| " + TICK + r"(.*?)" + TICK +
    r" \| " + TICK + r"(.*?)" + TICK + r" \| (.*) \|$")
MODULE = re.compile(r"^### (P3M\d{2}) — ")
GATE = re.compile(r"^- \[([ x])\] \*\*Independent Module Gate — (NOT PASSED|PASSED):")
OP = re.compile(r"^\| \*\*(P3OP\d{2}-R\d{2})\*\*,\s*(.*?) \| (.*?) \| (.*?) \| (.*?) \|$")
REF = re.compile(r"P3M\d{2}-A\d{2}")
COLUMNS = (
    "id", "kind", "owner", "canonical_criterion", "dependency", "app_only_slice",
    "implementation_status", "tested_scope", "acceptance_status", "git_sha",
    "run_or_env", "artifact_link", "blocker", "next_action", "source_line",
    "source_acceptance_field", "source_tested_field", "generated_from_git_sha", "counts_as_activity"
)


def triage(state: str) -> str:
    return {
        "blocked":"RESOLVE_NAMED_DEPENDENCIES_THEN_RUN_CRITERION",
        "planned":"IMPLEMENT_CANONICAL_CRITERION_AND_RECORD_TEST",
        "active":"COMPLETE_MISSING_PARTIAL_ASSERTIONS",
        "review":"OBTAIN_EXACT_SHA_TARGET_AND_OWNER_REVIEW",
        "accepted":"REVERIFY_SIGNED_ACCEPTANCE",
    }[state]


def make(id: str, kind: str, number: int, sha: str, **kwargs: str) -> dict:
    row = {
        "id":id, "kind":kind, "owner":"UNASSIGNED_IN_SOURCE",
        "canonical_criterion":"", "dependency":"NOT_STATED_IN_SOURCE",
        "app_only_slice":"UNCLASSIFIED_OWNER_APPROVAL_REQUIRED",
        "implementation_status":"UNVERIFIED", "tested_scope":"NOT_VERIFIED_PER_ID",
        "acceptance_status":"NOT_ACCEPTED_NO_INDEPENDENT_SIGNED_RECEIPT",
        "git_sha":"", "run_or_env":"NO_PER_ID_LIVE_RUN_CLAIM",
        "artifact_link":"", "blocker":"PER_ID_ACCEPTANCE_UNVERIFIED",
        "next_action":"REVIEW_CANONICAL_CRITERION_WITH_OWNER",
        "source_line":str(number), "source_acceptance_field":"", "source_tested_field":"",
        "generated_from_git_sha":sha, "counts_as_activity":"false",
    }
    row.update(kwargs)
    return row


def gate_field(line: str, first: str, second: str) -> str:
    pattern = re.compile(r"\*\*" + re.escape(first) + r":\*\* (.*?) \*\*" +
                         re.escape(second) + r":\*\*")
    match = pattern.search(line)
    if not match:
        raise ValueError("Missing Gate source field " + first)
    return match.group(1).strip()


def build(lines: list[str], sha: str) -> list[dict]:
    rows: list[dict] = []
    current: str | None = None
    gate_seen: set[str] = set()
    for number, line in enumerate(lines, 1):
        heading = MODULE.match(line)
        if heading:
            current = heading.group(1)
            continue
        activity = ACT.match(line)
        if activity:
            id, original, owner_dep, criterion, state, impl, tested, accepted, evidence = activity.groups()
            if current is None or not id.startswith(current+"-"):
                raise ValueError("Activity not in expected module at line "+str(number))
            owner, separator, dependency = owner_dep.partition(";")
            rows.append(make(
                id, "primary_activity", number, sha, owner=owner.strip(),
                canonical_criterion=criterion.strip(),
                dependency=dependency.strip() if separator else "NOT_STATED_IN_SOURCE",
                implementation_status=impl, tested_scope=tested,
                source_tested_field=tested,
                source_acceptance_field=accepted,
                artifact_link=evidence.strip(),
                blocker="CANONICAL_STATUS_"+state.upper(),
                next_action=triage(state), counts_as_activity="true"))
            continue
        gate = GATE.match(line)
        if gate:
            if current is None or current in gate_seen:
                raise ValueError("Duplicate/missing module Gate at "+str(number))
            gate_seen.add(current)
            rows.append(make(
                current+"-GATE", "independent_module_gate", number, sha,
                owner=gate_field(line,"Owner","Dependencies"),
                dependency=gate_field(line,"Dependencies","Output"),
                canonical_criterion=gate_field(line,"Acceptance Gate","Status"),
                source_acceptance_field=gate.group(2),
                artifact_link="coordination/evidence/"+current+"/",
                blocker="GATE_NOT_PASSED_UNLESS_SIGNED_OWNER_WITNESS",
                next_action="CENTRAL_REVIEW_AFTER_ALL_CANONICAL_ASSERTIONS"))
            continue
        crosswalk = OP.match(line)
        if crosswalk:
            id, section, criterion, mappings, notes = crosswalk.groups()
            refs = sorted(set(REF.findall(mappings)))
            if not refs:
                raise ValueError("Crosswalk without canonical links: "+id)
            rows.append(make(
                id,"operational_crosswalk_non_counting",number,sha,
                owner="REFERENCED_CANONICAL_ACTIVITY_OWNERS",
                canonical_criterion=criterion.strip(),dependency=",".join(refs),
                implementation_status="MAPPING_ONLY",
                tested_scope="NOT_VERIFIED_PER_OPERATIONAL_ENTRY",
                source_acceptance_field=notes.strip(),
                artifact_link="coordination/phase3_checklist.md",
                blocker="CROSSWALK_DOES_NOT_COUNT_AS_ACCEPTED_ACTIVITY",
                next_action="COLLECT_SOURCE_AND_TARGET_OPERATIONAL_EVIDENCE"))
    identifiers = [row["id"] for row in rows]
    if len(identifiers)!=len(set(identifiers)):
        raise ValueError("Duplicate evidence ledger IDs")
    expected = {"primary_activity":262,"independent_module_gate":26,
                "operational_crosswalk_non_counting":105}
    for kind, count in expected.items():
        actual=sum(row["kind"]==kind for row in rows)
        if actual!=count:
            raise ValueError(f"Expected {count} {kind}, got {actual}")
    if len(rows)!=393 or len(gate_seen)!=26:
        raise ValueError("Canonical 393 items / 26 module Gate mismatch")
    valid_ids={row["id"] for row in rows if row["kind"]=="primary_activity"}
    for row in rows:
        if row["kind"]=="operational_crosswalk_non_counting":
            if not set(row["dependency"].split(",")) <= valid_ids:
                raise ValueError("Orphan operational mapping: "+row["id"])
        for field in ("id","owner","canonical_criterion","dependency","next_action"):
            if not str(row[field]).strip():
                raise ValueError("Empty "+field+" for "+row["id"])
        if row["acceptance_status"].startswith("ACCEPTED"):
            raise ValueError("Generated acceptance elevation prohibited: "+row["id"])
    return rows


def attach_bounded_ci_evidence(rows: list[dict]) -> None:
    """Add the 20 explicitly verified historical CI subsets; never accept a row.

    Checks exact source criterion fragments and prevents accidental promotion
    from a signed laboratory run to a full canonical activity or target Gate.
    """
    path=ROOT/"coordination/integration/F3_VERIFIED_CI_LAB_SLICES_20261124.json"
    if not path.is_file():
        raise ValueError("BOUNDED_CI_LAB_WITNESSES_FILE_MISSING")
    evidence=json.loads(path.read_text(encoding="utf-8"))
    if (evidence.get("schema")!="foundation.f3.bounded_ci_lab_slices.v1"
            or evidence.get("owner_approved") is not False
            or evidence.get("mac_target_tested") is not False
            or evidence.get("gates_accepted")!=0):
        raise ValueError("UNAPPROVED_BOUNDED_EVIDENCE_STATUS")
    evidence_sha=evidence["evidence_sha"]
    if not re.fullmatch(r"[a-f0-9]{40}",evidence_sha):
        raise ValueError("INVALID_EVIDENCE_SHA")
    by_id={row["id"]:row for row in rows}
    seen=set()
    for witness in evidence["rows"]:
        id=witness["id"]
        if id in seen or id not in by_id or by_id[id]["kind"]!="primary_activity":
            raise ValueError("DUPLICATE_OR_NON_ACTIVITY_CI_WITNESS "+id)
        seen.add(id)
        row=by_id[id]
        if (witness["criterion_fragment"] not in row["canonical_criterion"]
                or witness.get("owner_accepted") is not False
                or witness.get("target_verified") is not False
                or witness.get("full_criterion_satisfied") is not False):
            raise ValueError("CI_WITNESS_CRITERION_OR_ACCEPTANCE_MISMATCH "+id)
        run=witness["run_id"]
        url=witness["url"]
        expected_url="https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/"+str(run)
        if type(run) is not int or url!=expected_url:
            raise ValueError("CI_WITNESS_LINK_NOT_EXACT "+id)
        row["app_only_slice"]="BOUNDED_CI_LAB_ONLY_NOT_APPROVED_DENOMINATOR"
        row["tested_scope"]=(
            row["source_tested_field"]+" ; BOUNDED_CI_EVIDENCE:"+witness["subset"])
        row["git_sha"]=evidence_sha
        row["run_or_env"]="GitHub Actions "+str(run)+" ; DISPOSABLE_CI_LAB_ONLY"
        row["artifact_link"]=row["artifact_link"]+" ; "+url
        # Explicitly preserve the source acceptance and our NO-ACCEPTANCE result.
        if row["acceptance_status"]!="NOT_ACCEPTED_NO_INDEPENDENT_SIGNED_RECEIPT":
            raise ValueError("CI_WITNESS_PROMOTION_PROHIBITED "+id)
    if len(seen)!=20:
        raise ValueError("INCOMPLETE_20_BOUNDED_CI_EVIDENCE_ROWS")


def write(rows: list[dict], output: Path, sha: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output/"f3_393_evidence_ledger.csv").open(
            "w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    doc={
        "schema":"foundation.f3.unified_register_393.v1",
        "generated_source_sha":sha,
        "source":"coordination/phase3_checklist.md",
        "counts":{"activities":262,"module_gates":26,
                  "operational_non_counting":105,"rows":393},
        "acceptance_claim":"NONE_GENERATED_LEDGER_IS_NOT_OWNER_ACCEPTANCE",
        "app_only_denominator":"NOT_APPROVED",
        "rows":rows}
    (output/"f3_393_evidence_ledger.json").write_text(
        json.dumps(doc,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
    print("FOUNDATION_F3_393_CANONICAL_LEDGER_WRITTEN_NOT_ACCEPTED")


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--out",type=Path,default=ROOT/"ci_receipts/foundation")
    parser.add_argument("--sha",default=os.environ.get("GITHUB_SHA","LOCAL_SHA_UNVERIFIED"))
    args=parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("CANONICAL_REGISTER_MISSING")
    rows=build(args.source.read_text(encoding="utf-8").splitlines(),args.sha)
    attach_bounded_ci_evidence(rows)
    write(rows,args.out,args.sha)


if __name__=="__main__":
    main()
