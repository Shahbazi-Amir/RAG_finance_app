"""Verify browser-observed request/trace pairs against actual API structured logs.
Only counts escape; no raw service logs or request identifiers printed.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from collections import Counter

LIMIT=2*1024*1024
HEX=re.compile(r"[0-9a-f]{32}")
HASH=re.compile(r"[0-9a-f]{64}")
def match(browser, api, stage):
    if stage not in ("source","restore") or len(browser)>LIMIT or len(api)>LIMIT:
        raise ValueError("correlation scope")
    witness=[line.split("F3_LAB_CORRELATION_HASHES ",1)[1] for line in browser.splitlines() if line.startswith("F3_LAB_CORRELATION_HASHES ")]
    if len(witness)!=1:
        print("F3_LAB_BROWSER_WITNESS_COUNT",len(witness),file=sys.stderr)
        raise ValueError("missing browser witness")
    doc=json.loads(witness[0]); hashes=doc.get("hashes")
    if set(doc)!={"stage","hashes"} or doc["stage"]!=stage or not isinstance(hashes,list) or len(hashes)!=48 or not all(isinstance(x,str) and HASH.fullmatch(x) for x in hashes) or len(set(hashes))!=48:
        raise ValueError("invalid browser witness")
    counts=Counter()
    for line in api.splitlines():
        if "F3_HISTORY_EVENT " not in line: continue
        event=json.loads(line.split("F3_HISTORY_EVENT ",1)[1])
        if set(event)!={"event","route","status","elapsed_ms","request_id","trace_id"} or event["event"]!="signed_history_read" or event["route"] not in {"list","detail","status"} or type(event["status"]) is not int or not 100<=event["status"]<=599 or type(event["elapsed_ms"]) is not int or event["elapsed_ms"]<0:
            raise ValueError("invalid event")
        a,b=event["request_id"],event["trace_id"]
        if not all(isinstance(x,str) and HEX.fullmatch(x) for x in (a,b)) or a==b:
            raise ValueError("invalid identifiers")
        counts[hashlib.sha256(f"{a}|{b}|{event['status']}".encode()).hexdigest()]+=1
    missing=sum(counts[x]==0 for x in hashes)
    repeated=sum(counts[x]>1 for x in hashes)
    if missing or repeated:
        print("F3_LAB_TRACE_COUNTS",len(hashes),sum(counts.values()),missing,repeated,file=sys.stderr)
        raise ValueError("correlation missing or repeated")
    return len(hashes)

def main():
    try:
        stage,path=sys.argv[1:]
        with Path(path).open("rb") as f: browser=f.read(LIMIT+1)
        api=sys.stdin.buffer.read(LIMIT+1)
        count=match(browser.decode("utf-8"),api.decode("utf-8"),stage)
    except Exception as exc:
        print("F3_LAB_TRACE_CORRELATION_DENIED",type(exc).__name__,file=sys.stderr)
        return 70
    print(f"F3_LAB_TRACE_CORRELATION_PASS stage={stage} matched={count}")
    return 0
if __name__=="__main__":sys.exit(main())
