"""Disposable CI health/alert evidence. Not target monitoring or approved SLO."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

STAGES=("source","outage","recovery","restore")
EXPECTED=(200,503,200,200)
def build(events, sha):
    if not re.fullmatch(r"[a-f0-9]{40}",sha):
        raise ValueError("invalid source revision")
    if not isinstance(events,list) or len(events)!=4:
        raise ValueError("missing health transitions")
    active=False
    rows=[]
    last=-1
    for e,stage,status in zip(events,STAGES,EXPECTED):
        if not isinstance(e,dict) or set(e)!={"stage","http_status","monotonic_ns"}:
            raise ValueError("invalid health event")
        if e["stage"]!=stage or type(e["http_status"]) is not int or e["http_status"]!=status:
            raise ValueError("unexpected health transition")
        t=e["monotonic_ns"]
        if type(t) is not int or t<=last:
            raise ValueError("invalid event order")
        if stage=="source": start=t
        last=t
        transition="NONE"
        if status==503 and not active:
            active=True
            transition="OPEN"
        elif status==200 and active:
            active=False
            transition="RESOLVE"
        rows.append({"stage":stage,"dependency_http_status":status,
                     "elapsed_from_start_ms":(t-start)//1_000_000,
                     "alert_transition":transition})
    if active:
        raise ValueError("unresolved injected outage")
    return {"schema":"f3-lab-health-v1","source_sha":sha,"scope":"isolated synthetic readiness observations; no live notification",
            "health":rows,"alert_rule":"observed product dependency 503 opens; recovery 200 resolves",
            "alert_open_count":1,"alert_resolve_count":1,"availability_slo":"NOT_MEASURED",
            "target_alert_delivery":"NOT_RUN","db_pool_and_provider_consumption":"NOT_MEASURED",
            "acceptance":"NOT_ACCEPTED"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("events",type=Path)
    p.add_argument("--stage",choices=STAGES)
    p.add_argument("--status",type=int)
    p.add_argument("--sha")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
        return 70
    try:
        if a.stage:
            if a.status not in (200,503) or a.sha or a.out:
                raise ValueError("invalid observation")
            with a.events.open("a",encoding="utf8") as f:
                f.write(json.dumps(dict(stage=a.stage,http_status=a.status,monotonic_ns=time.monotonic_ns()))+"\n")
        else:
            if not a.sha or not a.out: raise ValueError("missing receipt parameters")
            if a.events.stat().st_size>8192:raise ValueError("oversize events")
            d=build([json.loads(l) for l in a.events.read_text().splitlines()],a.sha)
            a.out.parent.mkdir(parents=True,exist_ok=True)
            a.out.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
            print("F3_LAB_HEALTH_ALERT_TRANSITIONS_PASS 4 1 1")
    except (ValueError,OSError,TypeError,KeyError):
        print("F3_LAB_HEALTH_ALERT_TRANSITIONS_DENIED",file=sys.stderr)
        return 70
    return 0
if __name__=="__main__":sys.exit(main())
