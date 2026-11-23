#!/usr/bin/env python3
"""Build a non-accepting, exact-SHA Foundation inventory of all 393 F3 IDs.

Canonical source is the two tracked, versioned project CSVs. This script
does NOT transform a provisional app-only slice, L1 coverage, or code presence
into an accepted roadmap activity, Gate, or operational crosswalk.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = Path("coordination/handoffs/UI_F3_CANONICAL_262_ACTIVITIES_26_GATES.csv")
OPERATIONAL = Path("coordination/handoffs/UI_F3_OPERATIONAL_105_MAP_80_FOCUS.csv")
COLUMNS = ("id", "owner", "canonical_criterion", "dependency", "app_only_slice",
           "implementation_status", "tested_scope", "acceptance_status",
           "git_sha", "run_or_env", "artifact_link", "blocker", "next_action")


class InventoryDenied(ValueError):
    pass


def _require(value, message):
    if not value:
        raise InventoryDenied(message)


def _read_csv(path):
    with (ROOT / path).open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    _require(rows and all(row.get("id") for row in rows), "empty_id_" + str(path))
    return rows


def validate(primary, operational):
    acts = [x for x in primary if x.get("type") == "P3M_ACTIVITY"]
    gates = [x for x in primary if x.get("type") == "P3M_INDEPENDENT_GATE"]
    _require(len(acts) == 262 and len(gates) == 26 and len(primary) == 288,
             "primary_count_262_26")
    _require(len(operational) == 105, "operational_count_105")
    ids = [x["id"] for x in acts]
    gids = [x["id"] for x in gates]
    ops = [x["id"] for x in operational]
    _require(len(set(ids)) == 262 and
             all(re.fullmatch(r"P3M\d{2}-A\d{2}", x) for x in ids),
             "invalid_activity_ids")
    _require(set(gids) == {f"P3M{i:02d}" for i in range(26)}, "invalid_gate_ids")
    _require(len(set(ops)) == 105 and
             all(re.fullmatch(r"P3OP\d{2}-R\d{2}", x) for x in ops),
             "invalid_operational_ids")
    _require(not set(ids).intersection(gids) and not set(ops).intersection(ids),
             "duplicate_canonical_ids")
    for row in acts:
        _require(row.get("canonical_counted") == "YES", "activity_denominator")
        _require(row.get("owner_and_dependency", "").strip(), "activity_owner")
        _require(row.get("specific_requirement", "").strip(), "activity_criterion")
        _require(row.get("registry_accepted", "").strip(), "activity_acceptance")
        _require(row.get("current_activity_accepted", "").strip() not in
                 {"ACCEPTED", "YES", "TRUE", "PASS"}, "unsigned_activity_acceptance")
    for row in gates:
        _require(row.get("canonical_counted") == "NO", "gate_denominator")
        _require(row.get("owner_and_dependency", "").strip(), "gate_owner")
        _require(row.get("specific_requirement", "").strip(), "gate_criterion")
        _require(row.get("registry_accepted", "").strip() not in
                 {"ACCEPTED", "YES", "TRUE", "PASS"}, "unsigned_gate_acceptance")
    for row in operational:
        _require(row.get("type") == "P3OP_OPERATIONAL_OVERLAY",
                 "operational_type")
        _require(row.get("canonical_counted") == "NO", "crosswalk_denominator")
        _require(row.get("criterion", "").strip(), "crosswalk_criterion")
        _require(row.get("accepted_now", "").strip() not in
                 {"ACCEPTED", "YES", "TRUE", "PASS"}, "unsigned_crosswalk_acceptance")
    return acts, gates, operational


def inventory(primary, operational, git_sha):
    acts, gates, ops = validate(primary, operational)
    by_id = {x["id"]: x for x in acts}
    rows = []
    for item in acts:
        rows.append({
            "id": item["id"],
            "owner": item["owner_and_dependency"],
            "canonical_criterion": item["specific_requirement"],
            "dependency": "See owner_and_dependency source; not independently approved",
            "app_only_slice": "NOT_FROZEN",
            "implementation_status": item.get("registry_implemented", "UNVERIFIED"),
            "tested_scope": item.get("registry_tested", "NOT_RUN"),
            "acceptance_status": "NOT_ACCEPTED",
            "git_sha": git_sha,
            "run_or_env": "SOURCE_REGISTRY_ONLY_NO_TARGET_L2",
            "artifact_link": str(PRIMARY),
            "blocker": item.get("source_blocker") or "CRITERION_RECEIPT_MISSING",
            "next_action": item.get("required_next_check") or "OWNER_REVIEW",
        })
    for item in gates:
        rows.append({
            "id": item["id"] + "-GATE",
            "owner": item["owner_and_dependency"],
            "canonical_criterion": item["specific_requirement"],
            "dependency": "Original module activities and signed owner Gate",
            "app_only_slice": "NOT_APPLICABLE_TO_WHOLE_GATE",
            "implementation_status": "NOT_VERIFIED",
            "tested_scope": "NO_SIGNED_TARGET_GATE_RECEIPT",
            "acceptance_status": "NOT_ACCEPTED",
            "git_sha": git_sha,
            "run_or_env": "SOURCE_REGISTRY_ONLY_NO_TARGET_L2",
            "artifact_link": str(PRIMARY),
            "blocker": "CENTRAL_SIGNOFF_AND_TARGET_WITNESS_MISSING",
            "next_action": item.get("required_next_check") or "CENTRAL_GATE_DECISION",
        })
    for item in ops:
        mapping = item.get("mapped_original_P3M_IDs", "")
        linked = [x for x in re.findall(r"P3M\d{2}-A\d{2}", mapping) if x in by_id]
        owners = sorted({by_id[x]["owner_and_dependency"].split(";")[0].strip()
                         for x in linked})
        owner = ("PROVISIONAL_MAPPED_OWNER:" + "/".join(owners)
                 if owners else "CENTRAL_TO_ASSIGN")
        rows.append({
            "id": item["id"],
            "owner": owner + "; CENTRAL_TO_CONFIRM",
            "canonical_criterion": item["criterion"],
            "dependency": mapping or "UNMAPPED_REQUIRES_CENTRAL",
            "app_only_slice": "NOT_FROZEN",
            "implementation_status": "MAPPED_ONLY_NOT_IMPLEMENTATION",
            "tested_scope": "NO_INDEPENDENT_OPERATIONAL_WITNESS",
            "acceptance_status": "NOT_ACCEPTED",
            "git_sha": git_sha,
            "run_or_env": "SOURCE_REGISTRY_ONLY_NO_TARGET_L2",
            "artifact_link": str(OPERATIONAL),
            "blocker": item.get("reg_status_GAP_CONFLICT") or "OWNER_REVIEW",
            "next_action": item.get("required_next_check") or "OWNER_WITNESS",
        })
    _require(len(rows) == 393 and len({x["id"] for x in rows}) == 393,
             "normalized_393_count")
    _require(all(set(x) == set(COLUMNS) and all(str(v).strip() for v in x.values())
                 for x in rows), "normalized_missing_required_column")
    return rows


def selftest(primary, operational, sha):
    for kind, index, field, value in [
        ("primary", 0, "id", primary[1]["id"]),
        ("primary", 0, "owner_and_dependency", ""),
        ("primary", 0, "specific_requirement", ""),
        ("primary", 0, "canonical_counted", "NO"),
        ("primary", 262, "canonical_counted", "YES"),
        ("primary", 262, "registry_accepted", "YES"),
        ("primary", 0, "current_activity_accepted", "ACCEPTED"),
        ("operational", 0, "canonical_counted", "YES"),
        ("operational", 0, "criterion", ""),
        ("operational", 0, "accepted_now", "ACCEPTED"),
        ("operational", 0, "id", "P3OP_FAKE"),
    ]:
        a, b = copy.deepcopy(primary), copy.deepcopy(operational)
        target = a if kind == "primary" else b
        target[index][field] = value
        try:
            inventory(a, b, sha)
        except InventoryDenied:
            pass
        else:
            raise InventoryDenied("negative_mutation_not_rejected:" + field)
    return 11


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    p, o = _read_csv(PRIMARY), _read_csv(OPERATIONAL)
    sha = os.getenv("GITHUB_SHA", "LOCAL_UNPINNED_NO_CI")
    checked = selftest(p, o, sha) if args.self_test else 0
    rows = inventory(p, o, sha)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "phase3_393_candidate_registry.csv").open(
            "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    sources = {}
    for path in (PRIMARY, OPERATIONAL):
        sources[str(path)] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    result = {
        "schema": "foundation.f3.integrated_393_registry.v1",
        "git_sha": sha,
        "sources_sha256": sources,
        "activity_criterion_inventory": 262,
        "independent_module_gates": 26,
        "noncounting_operational_crosswalks": 105,
        "unique_rows": len(rows),
        "rows_without_owner_or_criterion": 0,
        "accepted_activities": 0,
        "accepted_gates": 0,
        "independently_witnessed_crosswalks": 0,
        "app_only_denominator": "NOT_OWNER_FROZEN",
        "status": "SOURCE_COVERAGE_ONLY_NO_TARGET_OR_CENTRAL_ACCEPTANCE",
        "negative_mutation_tests": checked,
    }
    (out / "phase3_registry_summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print("FOUNDATION_F3_393_INVENTORY_AND_UNACCEPTED_STATUS_PASS",
          len(rows), "NEGATIVE_TESTS", checked)


if __name__ == "__main__":
    main()
