"""Real authenticated BFF negative tests, not semantic RAG safety evaluation."""
from collections import Counter
import asyncio
import json
from pathlib import Path
import secrets

ROOT=Path(__file__).resolve().parents[4]
CORPUS=ROOT/"tests/phase3/fixtures/f3_fa_redteam_cases.json"
def load_cases():
    d=json.loads(CORPUS.read_text())
    assert d["policy_approved"] is False
    cases=d["cases"];assert len(cases)==24 and len({r["id"] for r in cases})==24
    assert all(r["expected_app_only_status"]==503 and r["expected_engine_policy"] is None
               and any("\u0600"<=c<="\u06ff" for c in r["question"]) for r in cases)
    return cases

async def observe_redteam(page_a,page_b,origin,owners,ids_a,ids_b,phase):
    cases=load_cases()
    # Synthetic canary is not real credential, account or source.
    canary="F3_REDTEAM_CANARY_"+secrets.token_hex(12)
    results=Counter()
    async def denied(page,case):
        r=await page.request.post(origin+"/api/history/messages",
            data=json.dumps({"question":case["question"]+" "+canary},ensure_ascii=False),
            headers={"content-type":"application/json"})
        assert r.status==503 and r.headers.get("cache-control")=="no-store"
        assert await r.json()=={"error":"ENGINE_NOT_AVAILABLE"}
        assert canary not in await r.text()
        results[case["category"]]+=1
    # Two real independently authenticated browser sessions; no intercept.
    for offset in range(0,len(cases),4):
        await asyncio.gather(*(denied(page,c) for page in (page_a,page_b) for c in cases[offset:offset+4]))
    assert sum(results.values())==48
    # Cache/owner boundary: same URL alternates actual owners and sends
    # deliberately untrusted conditional and identity headers. No fake cookie.
    read_count=0
    for _ in range(4):
        for page,own,foreign,expected in (
            (page_a,owners["A"],owners["B"],ids_a),
            (page_b,owners["B"],owners["A"],ids_b)):
            r=await page.request.get(origin+"/api/history/conversations?limit=2",
                headers={"if-none-match":"\""+canary+"\"","x-owner-id":foreign,
                         "x-user-id":foreign,"cache-control":"max-age=86400"})
            assert r.status==200 and r.headers.get("cache-control")=="no-store"
            data=await r.json()
            assert data["scope_user_id"]==own
            actual={x["conversation_id"] for x in data["items"]}
            assert actual and actual<=expected
            assert canary not in await r.text()
            read_count+=1
    return {"phase":phase,"case_count":len(cases),"real_signed_session_requests_denied":sum(results.values()),
            "categories":dict(results),"conditional_header_cross_owner_reads":read_count,
            "no_raw_echo":True,"engine_policy_evaluated":False},canary
