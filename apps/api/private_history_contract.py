"""Offline signed History read contract. No public docs route or new DTO.

This view covers only list/detail/status on the existing signed app-only
listener. Send remains disabled; no Auth issue/rotation, engine or fixture
route is documented as a public capability. The canonical product.v1 schema
and the original History OpenAPI generator are the only DTO authority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

_PATHS = ("/v1/conversations", "/v1/conversations/{conversation_id}/messages",
          "/v1/message-requests/status")

def signed_history_openapi():
    from apps.api import history_api
    base=copy.deepcopy(history_api.openapi())
    base["info"].update(title="Private signed History — read subset",
                        description="Internal handoff only; mTLS pinned BFF leaf AND RS256 signed raw method/path/query/body and live PG owner/session. Not a public endpoint or target approval.",
                        version="product.v1")
    base["paths"]={path:{"get":base["paths"][path]["get"]} for path in _PATHS}
    base["components"]["securitySchemes"]={
        "TrustedBFFTLS":{"type":"mutualTLS","description":"Pinned BFF client leaf, verified TLS transport"},
        "BFFAssertion":{"type":"apiKey","in":"header","name":"Authorization",
                        "description":"BFF-Assertion <RS256 compact JWT>; never a browser token"}
    }
    for item in base["paths"].values():
        op=item["get"]
        op["security"]=[{"TrustedBFFTLS":[],"BFFAssertion":[]}]
        for code,response in op["responses"].items():
            response.setdefault("headers",{})["Cache-Control"]={"schema":{"type":"string","const":"no-store"}}
    return base

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(signed_history_openapi(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
