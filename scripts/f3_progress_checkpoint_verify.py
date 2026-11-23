#!/usr/bin/env python3
"""GitHub CI checkpoint arithmetic guard (does NOT re-read off-repo source CSVs).
Full 393-row source integrity is checked separately by exported Python reporter ZIP.
No acceptance or runtime action follows from a valid checkpoint.
"""
import argparse
import copy
import json
import re
import sys

class InvalidProgress(ValueError):
    pass

def check(c):
    def need(test, code):
        if not test:
            raise InvalidProgress(code)
    need(c.get("schema")=="foundation.f3.cycle_checkpoint.v1", "schema")
    need(c.get("acceptance_scope")=="SOURCE_ONLY_NOT_ACCEPTED", "scope")
    for name, total in (("foundation",121),("full",262)):
        o=c[name]
        need(o["total"]==total,"denominator_"+name)
        need(all(type(o[x]) is int and o[x]>=0 for x in ("PARTIAL","NOT_VERIFIED","NOT_RUN","accepted")),"types_"+name)
        need(sum(o[x] for x in ("PARTIAL","NOT_VERIFIED","NOT_RUN"))==total,"sum_"+name)
        need(o["accepted"]==0,"unsigned_acceptance_"+name)
        need(abs(o["partial_coverage_pct"]-round(100*o["PARTIAL"]/total,2))<1e-8,"percent_"+name)
    need(c["gates"]=={"total":26,"accepted":0,"remaining":26},"gate_acceptance")
    need(c["aliases"]=={"total_noncounting":105,"accepted":0},"alias_noncounting")
    sha=c["source_csv_sha256"]
    need(set(sha)=={"FULL_PHASE3_262_EXECUTION_CHECKLIST.csv","FOUNDATION_121_EXECUTION_CHECKLIST.csv","26_INDEPENDENT_GATES.csv","105_OPERATIONAL_ALIASES_NONCOUNTING.csv"},"source_manifest")
    need(all(re.fullmatch("[0-9a-f]{64}",v) for v in sha.values()),"source_digests")
    rows=c["modules"]
    need(len(rows)==26 and len({x[0] for x in rows})==26,"module_count")
    need([r[0] for r in rows]==["P3M%02d"%i for i in range(26)],"module_ids")
    need(all(len(r)==5 and all(type(v) is int and v>=0 for v in r[1:]) and r[1]==sum(r[2:]) for r in rows),"module_row_sum")
    need([sum(r[i] for r in rows) for i in (1,2,3,4)]==[262,c["full"]["PARTIAL"],c["full"]["NOT_VERIFIED"],c["full"]["NOT_RUN"]],"module_totals")
    t=c["this_turn"]
    need(t["foundation_coverage_delta_pp"]==0 and t["full_coverage_delta_pp"]==0 and t["acceptance_delta"]==0 and t["accepted_gate_delta"]==0,"unverified_delta")
    need(t["arvan"]=="HOLD" and t["latest_mac_e2e"]=="NOT_RUN","environment_claims")
    return "F3_PROGRESS_CHECKPOINT_ARITHMETIC_PASS_NOT_ACCEPTANCE"

def selftest(c):
    check(c)
    for change in (
        lambda x:x["foundation"].__setitem__("PARTIAL",41),
        lambda x:x["full"].__setitem__("partial_coverage_pct",100),
        lambda x:x["gates"].__setitem__("accepted",1),
        lambda x:x["aliases"].__setitem__("total_noncounting",367),
        lambda x:x["modules"][0].__setitem__(1,10),
        lambda x:x["modules"][1].__setitem__(0,"P3M00"),
        lambda x:x["this_turn"].__setitem__("accepted_gate_delta",1),
        lambda x:x["this_turn"].__setitem__("arvan","LIVE"),
        lambda x:x.__setitem__("acceptance_scope","ACCEPTED"),
        lambda x:x["source_csv_sha256"].__setitem__("FULL_PHASE3_262_EXECUTION_CHECKLIST.csv","bad"),
    ):
        mutated=copy.deepcopy(c)
        change(mutated)
        try:
            check(mutated)
        except InvalidProgress:
            continue
        raise InvalidProgress("negative_test_failed")
    return "F3_PROGRESS_CHECKPOINT_NEGATIVE_TESTS_10_PASS"

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    try:
        data=json.load(open(a.file,encoding="utf-8"))
        print(check(data))
        if a.self_test:
            print(selftest(data))
    except (InvalidProgress,ValueError,KeyError,TypeError,OSError) as exc:
        print("F3_PROGRESS_BLOCKED:"+str(exc),file=sys.stderr)
        sys.exit(78)
