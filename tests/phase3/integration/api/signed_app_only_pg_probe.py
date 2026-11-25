"""Real signed listener + disposable PG boundary probe. Not browser or OIDC."""
import hashlib
import json
import secrets
import ssl
import sys
import time
import uuid
from pathlib import Path

import httpx
import jwt

ROOT = Path("/run/probe")
URL = "https://signed-api:8443"
ISSUER = "urn:rag-finance:lab-bff"
AUDIENCE = "urn:rag-finance:lab-api"
KID = "lab-key"
LIST = "/v1/conversations"
REVOKE = "/internal/auth/session/v1/revoke-one"


def tls(peer="bff"):
    ctx = ssl.create_default_context(cafile=str(ROOT / "ca.crt"))
    if peer:
        ctx.load_cert_chain(str(ROOT / (peer + ".crt")), str(ROOT / (peer + ".key")))
    return ctx


def sign(actor, method, path, query="", body=b"", override=None):
    now = int(time.time())
    digest = lambda value: hashlib.sha256(value).hexdigest()
    owner, token = actor
    claims = dict(iss=ISSUER, aud=AUDIENCE, iat=now, nbf=now,
                  exp=now+25, jti=secrets.token_urlsafe(24), method=method,
                  raw_path_sha256=digest(path.encode()),
                  raw_query_sha256=digest(query.encode()),
                  body_sha256=digest(body), body_len=len(body),
                  owner_id=owner, session_ref=token, epoch=0, generation=0)
    claims.update(override or {})
    return jwt.encode(claims, (ROOT/"sign.key").read_bytes(), algorithm="RS256",
                      headers={"typ":"JWT","kid":KID})


def check(response, status):
    assert response.status_code == status, (response.request.method,
        response.request.url.path, response.status_code, status)
    assert response.headers.get("cache-control") == "no-store"
    return response


def main(stage):
    actors = json.loads((ROOT/"actors.json").read_text())
    with httpx.Client(verify=tls(), timeout=15, trust_env=False) as c:
        if stage == "outage":
            check(c.get(URL+"/internal/ready"), 503)
            print("SIGNED_REAL_PG_OUTAGE_503")
            return
        for _ in range(40):
            try:
                ready = c.get(URL+"/internal/ready")
                if ready.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise AssertionError("SIGNED_REAL_PG_READY_TIMEOUT")
        check(ready, 200)
        assert ready.json()["history_db"] == "verified"
        assert ready.json()["generation"] == "unavailable"
        a = ("signed-owner-a", actors["a-before" if stage=="source" else "a-after"])
        b = ("signed-owner-b", actors["b"])
        def request(actor, path=LIST, query="", method="GET", body=b"", override=None, token=None):
            proof = token or sign(actor, method, path, query, body, override)
            headers = {"Authorization":"BFF-Assertion "+proof}
            if body:
                headers["Content-Type"]="application/json"
            return c.request(method, URL+path+("?" + query if query else ""),
                             headers=headers, content=body)
        check(c.get(URL+LIST), 401)
        check(c.get(URL+LIST, headers={"X-Owner-ID":a[0]}), 401)
        for peer in (None, "other"):
            try:
                with httpx.Client(verify=tls(peer), timeout=5, trust_env=False) as wrong:
                    response = wrong.get(URL+"/internal/ready")
                    assert response.status_code != 200
            except httpx.TransportError:
                pass
        for _ in range(2):
            page = check(request(a, query="limit=1"), 200).json()
            assert page["scope_user_id"] == a[0]
            assert [x["conversation_id"] for x in page["items"]] == ["signed-a-2"]
            cursor = page["page"]["next_cursor"]
            assert cursor and page["page"]["has_more"]
            second = check(request(a, query="limit=1&cursor="+cursor), 200).json()
            assert [x["conversation_id"] for x in second["items"]] == ["signed-a-1"]
            assert not second["page"]["has_more"]
            detail = check(request(a, "/v1/conversations/signed-a-1/messages"), 200).json()
            assert detail["owner_user_id"] == a[0]
            assert [x["text"] for x in detail["items"]] == ["lab message A"]
            check(request(b, "/v1/conversations/signed-a-1/messages"), 404)
            other = check(request(b), 200).json()
            assert [x["conversation_id"] for x in other["items"]] == ["signed-b-1"]
            assert other["scope_user_id"] == b[0]
        check(request(a, override={"owner_id":b[0]}), 401)
        proof = sign(a, "GET", LIST)
        check(request(a, token=proof), 200)
        check(request(a, token=proof), 401)
        check(c.post(URL+"/v1/messages", content=b"malformed-not-read"), 503)
        if stage == "restore":
            check(request(("signed-owner-a", actors["a-before"])), 401)
        op = str(uuid.uuid4())
        body = json.dumps({"operation_id":op}, separators=(",",":")).encode()
        result = check(request(a, REVOKE, method="POST", body=body), 200).json()
        assert result == {"state":"REVOKED_COMMITTED","operation_id":op}
        check(request(a), 401)
        check(request(b), 200)
        print("SIGNED_REAL_PG_"+stage.upper()+"_LIST_DETAIL_PAGING_REFRESH_AB_REVOKE_SEND_PASS")


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("source","restore","outage")
    main(sys.argv[1])
