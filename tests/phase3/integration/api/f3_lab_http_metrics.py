"""Bounded read-only timing on the actual authenticated browser request clients.
No provider call, load/soak claim, approved SLO, or new authentication mechanism.
"""
import hashlib
import json
import re
import time

OPAQUE = re.compile(r"[0-9a-f]{32}$")
ROUNDS = 12


def percentiles(ns):
    if not ns or any(type(x) is not int or x < 0 for x in ns):
        raise ValueError("invalid timings")
    s = sorted(ns)
    out = {"samples": len(s), "min_ms": round(s[0] / 1e6, 3), "max_ms": round(s[-1] / 1e6, 3)}
    for p in (50, 95, 99):
        out[f"p{p}_ms"] = round(s[(len(s) * p + 99) // 100 - 1] / 1e6, 3)
    return out


def measure_read_baseline(pa, pb, list_url, owner_a, owner_b, stage, rounds=ROUNDS):
    if stage not in ("source", "restore") or not 1 <= rounds <= ROUNDS or owner_a == owner_b:
        raise ValueError("invalid lab baseline")
    detail_url = list_url + "/browser-a-1/messages?limit=30"
    plan = (("owner_a_list", pa, list_url + "?limit=2", 200, owner_a),
            ("owner_b_list", pb, list_url + "?limit=2", 200, owner_b),
            ("owner_a_detail", pa, detail_url, 200, owner_a),
            ("owner_b_foreign_detail", pb, detail_url, 404, None))
    samples = {name: [] for name, *_ in plan}
    ids = {"request_id": [], "trace_id": []}
    pairs = []
    spoof = "f" * 32
    for _ in range(rounds):
        for name, actor, url, expected, owner in plan:
            start = time.perf_counter_ns()
            r = actor.request.get(url, timeout=5000, headers={"X-Request-ID":spoof,"X-Trace-ID":spoof})
            elapsed = time.perf_counter_ns() - start
            try:
                assert r.status == expected, "baseline unexpected HTTP status"
                assert r.headers.get("cache-control") == "no-store", "baseline private cache fence"
                if expected == 200:
                    d = r.json()
                    if name.endswith("list"):
                        assert d["scope_user_id"] == owner, "baseline owner mismatch"
                        wanted = ["browser-a-3", "browser-a-2"] if name == "owner_a_list" else ["browser-b-1"]
                        assert [x["conversation_id"] for x in d["items"]] == wanted, "baseline list changed"
                    else:
                        assert d["owner_user_id"] == owner, "baseline detail owner mismatch"
                        assert [(x["message_id"], x["text"]) for x in d["items"]] == [("browser-msg-a", "lab browser A")], "baseline detail changed"
                else:
                    assert "lab browser A" not in r.text(), "baseline foreign detail leaked"
                pair = []
                for key in ids:
                    v = r.headers.get("x-"+key.replace("_","-"))
                    assert isinstance(v,str) and OPAQUE.fullmatch(v) and v != spoof, "missing or client-selected correlation"
                    assert v not in ids[key], "reused correlation"
                    ids[key].append(v)
                    pair.append(v)
                assert pair[0] != pair[1], "request and trace must differ"
                pairs.append(hashlib.sha256(("|".join(pair)+"|"+str(r.status)).encode()).hexdigest())
                samples[name].append(elapsed)
            finally:
                r.dispose()
    # No owner IDs, correlation IDs, URLs, bodies, credentials or user data.
    receipt = {"stage": stage, "scope": "sequential CI read-only baseline; not load/soak or approved SLO",
               "rounds": rounds, "requests": rounds * len(plan),
               "routes": {name: percentiles(values) for name, values in samples.items()},
               "correlation_fields": {key: {"present_valid": len(values), "distinct": len(set(values)),
                                              "expected_responses": rounds * 4}
                                      for key, values in ids.items()},
               "retrieval_generation": "NOT_AVAILABLE", "target_acceptance": "NOT_ACCEPTED"}
    print("F3_LAB_CORRELATION_HASHES", json.dumps({"stage":stage,"hashes":sorted(pairs)},sort_keys=True), flush=True)
    print("F3_LAB_HTTP_BASELINE", json.dumps(receipt, sort_keys=True), flush=True)
    return receipt
