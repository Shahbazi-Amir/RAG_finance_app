"""Real listener + PG lab. Synthetic session fixture is NOT OIDC or browser."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import sys
import time
import uuid

ISSUER = "urn:rag-finance:isolated-bff"
AUDIENCE = "urn:rag-finance:isolated-history"
KID = "isolated-history-key"
BASE = "https://app-only-api:8443"
LIST = "/v1/conversations"
REVOKE = "/internal/auth/session/v1/revoke-one"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def openssl(*parts):
    subprocess.run(["openssl", *map(str, parts)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def prepare(root):
    os.umask(0o077)
    a, b = root / "api-secrets", root / "bff-secrets"
    ca_key, ca = b / "ca.key", b / "ca.pem"
    openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", ca_key, "-out", ca, "-days", "1", "-subj", "/CN=F3-API-CI",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    for name, folder in (("server", a), ("bff", b), ("other", b)):
        key, cert, csr, ext = (folder / (name + suffix)
                               for suffix in (".key", ".pem", ".csr", ".ext"))
        openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", key,
                "-out", csr, "-subj", "/CN=" + name)
        ext.write_text("basicConstraints=critical,CA:FALSE\n"
                       "keyUsage=digitalSignature,keyEncipherment\n"
                       + ("extendedKeyUsage=serverAuth\nsubjectAltName=DNS:app-only-api\n"
                          if name == "server" else "extendedKeyUsage=clientAuth\n"))
        openssl("x509", "-req", "-in", csr, "-CA", ca, "-CAkey", ca_key,
                "-CAcreateserial", "-out", cert, "-days", "1", "-extfile", ext)
        csr.unlink(); ext.unlink()
    # Never mount the BFF signing private key in API namespace.
    openssl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
            "-out", b / "sign.key")
    openssl("pkey", "-in", b / "sign.key", "-pubout", "-out", a / "sign.pub")
    (a / "ca.pem").write_bytes(ca.read_bytes())
    (a / "db-ca.pem").write_bytes((root / "secrets" / "ca.crt").read_bytes())
    pgpass = []
    for role in ("history_app", "auth_revoker"):
        pw = (root / "work" / (role + ".password")).read_text().strip()
        pgpass.append(f"demo-db:5432:rag_finance_f3_lab:{role}:{pw}\n")
    (a / "pgpass").write_text("".join(pgpass))
    (a / "cursor.key").write_text(secrets.token_hex(32))
    base_dsn = ("host=demo-db port=5432 dbname=rag_finance_f3_lab "
                "sslmode=verify-full sslrootcert=/run/secrets/db-ca.pem "
                "passfile=/run/secrets/pgpass connect_timeout=3 user=")
    config = {
        "contract_version": "api.private_app_only_asgi.v1",
        "listen_host": "0.0.0.0", "listen_port": 8443,
        "server_tls_cert_file": "/run/secrets/server.pem",
        "server_tls_key_file": "/run/secrets/server.key",
        "trusted_bff_ca_file": "/run/secrets/ca.pem",
        "bff_leaf_cert_sha256": digest(ssl.PEM_cert_to_DER_cert((b / "bff.pem").read_text())),
        "bff_issuer": ISSUER, "bff_audience": AUDIENCE, "bff_kid": KID,
        "bff_rs256_public_key_file": "/run/secrets/sign.pub",
        "history_dsn": base_dsn + "history_app", "revoke_dsn": base_dsn + "auth_revoker",
    }
    (a / "phase3-app-only.json").write_text(json.dumps(config))
    actors = {name: {"owner_id": "signed-lab-" + name,
                     "session_ref": secrets.token_urlsafe(32)}
              for name in ("A", "B")}
    (b / "actors.json").write_text(json.dumps(actors))
    # Only fixed, artificial IDs and a digest; no opaque value in SQL.
    sql = ["BEGIN;"]
    for name, actor in actors.items():
        owner = actor["owner_id"]
        h = digest(actor["session_ref"].encode("ascii"))
        sql.append(f"INSERT INTO auth_l1.owners(owner_id) VALUES ('{owner}');")
        sql.append("INSERT INTO auth_l1.sessions(digest_sha256,owner_id,session_epoch,generation,status,"
                   "created_at,last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)"
                   f" VALUES ('{h}','{owner}',0,0,'active',clock_timestamp(),clock_timestamp(),"
                   "clock_timestamp()+interval '30 minutes',clock_timestamp()+interval '1 hour',1800);")
        for n in (1, 2):
            cid = f"signed-lab-{name}-{n}"
            sql.append("INSERT INTO history_l1.conversations(owner_id,id,title,state)"
                       f" VALUES ('{owner}','{cid}','{cid}','active');")
            sql.append("INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)"
                       f" VALUES ('{owner}','msg-{cid}','{cid}','user','fixture-{name}-{n}');")
    sql.append("COMMIT;")
    (b / "seed.sql").write_text("\n".join(sql))
    ca_key.unlink()
    for folder in (a, b):
        for p in folder.iterdir():
            p.chmod(0o600)

def run(root, mode):
    import httpx
    import jwt
    actors = json.loads((root / "actors.json").read_text())
    def tls(name):
        context = ssl.create_default_context(cafile=str(root / "ca.pem"))
        if name:
            context.load_cert_chain(str(root / (name + ".pem")), str(root / (name + ".key")))
        return context
    def token(actor, method, path, q="", body=b"", **override):
        now = int(time.time())
        claims = dict(iss=ISSUER, aud=AUDIENCE, iat=now, nbf=now, exp=now+25,
                      jti=secrets.token_urlsafe(24), method=method,
                      raw_path_sha256=digest(path.encode("ascii")),
                      raw_query_sha256=digest(q.encode("ascii")), body_sha256=digest(body),
                      body_len=len(body), epoch=0, generation=0, **actor)
        claims.update(override)
        return jwt.encode(claims, (root / "sign.key").read_bytes(), algorithm="RS256",
                          headers={"typ": "JWT", "kid": KID})
    with httpx.Client(verify=tls("bff"), trust_env=False, timeout=15, follow_redirects=False) as c:
        if mode == "outage":
            res = c.get(BASE + "/health/ready")
            assert res.status_code == 503, "PG_OUTAGE_NOT_DENIED"
            print("SIGNED_API_REAL_PG_OUTAGE_503_PASS")
            return
        for _ in range(60):
            try:
                res = c.get(BASE + "/health/ready")
                if res.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise AssertionError("SIGNED_API_NOT_READY")
        assert res.json()["history_db"] == "verified"
        assert res.json()["bootstrap_idp"] == "not_probed"
        assert res.json()["generation"] == "unavailable"
        def call(actor, path=LIST, q="", method="GET", body=b"", proof=None, **override):
            proof = proof or token(actor, method, path, q, body, **override)
            headers = {"Authorization": "BFF-Assertion " + proof}
            if method == "POST":
                headers["Content-Type"] = "application/json"
            response = c.request(method, BASE + path + ("?" + q if q else ""),
                                 content=body, headers=headers)
            assert response.headers.get("cache-control") == "no-store"
            return response
        a, b = actors["A"], actors["B"]
        for own, name in ((a, "A"), (b, "B")):
            one = call(own, q="limit=1")
            assert one.status_code == 200, "LIST_NOT_200"
            d = one.json()
            assert d["scope_user_id"] == own["owner_id"]
            assert d["page"]["has_more"]
            cursor = d["page"]["next_cursor"]
            two = call(own, q="limit=1&cursor=" + cursor)
            assert two.status_code == 200, "PAGE_NOT_200"
            ids = {x["conversation_id"] for x in d["items"] + two.json()["items"]}
            assert ids == {f"signed-lab-{name}-1", f"signed-lab-{name}-2"}
            assert not two.json()["page"]["has_more"]
            first = call(own)
            again = call(own)
            assert first.status_code == again.status_code == 200
            assert first.json()["items"] == again.json()["items"]
        detail = LIST + "/signed-lab-A-1/messages"
        res = call(a, detail)
        assert res.status_code == 200 and res.json()["items"][0]["text"] == "fixture-A-1"
        assert call(b, detail).status_code == 404
        assert call(a, owner_id=b["owner_id"]).status_code == 401
        assert call(a, iss="urn:wrong").status_code == 401
        assert call(a, aud="urn:wrong").status_code == 401
        proof = token(a, "GET", LIST)
        assert call(a, proof=proof).status_code == 200
        assert call(a, proof=proof).status_code == 401
        assert c.get(BASE + LIST).status_code == 401
        for peer in (None, "other"):
            try:
                with httpx.Client(verify=tls(peer), trust_env=False, timeout=5) as wrong:
                    res = wrong.get(BASE + LIST, headers={"Authorization": "BFF-Assertion " + token(a, "GET", LIST)})
                    assert res.status_code != 200
            except httpx.TransportError:
                pass
        send = call(a, "/v1/messages", method="POST", body=b"not-json")
        assert send.status_code == 503
        assert "ENGINE_NOT_CONFIGURED" in send.text
        raw = json.dumps({"operation_id": str(uuid.uuid4())}, separators=(",", ":")).encode()
        assert call(a, REVOKE, method="POST", body=raw).status_code == 200
        assert call(a).status_code == 401
        assert call(b).status_code == 200
        assert call(b, detail).status_code == 404
        print("SIGNED_API_REAL_PG_LIST_DETAIL_PAGE_REFRESH_AB_REPLAY_REVOKE_SEND_PASS")

if __name__ == "__main__":
    mode, root = sys.argv[1], Path(sys.argv[2])
    if mode == "prepare":
        prepare(root)
    else:
        assert mode in ("journey", "outage")
        run(root, mode)
