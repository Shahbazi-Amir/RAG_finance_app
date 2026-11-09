"""Real CI-only HTTPS/mTLS FastAPI fixture consuming existing API+DB trust.
Never a product History route. No public actor/session/seed/token endpoint.
"""
import asyncio,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from fastapi import FastAPI,Request,Response
from fastapi.responses import RedirectResponse,StreamingResponse
from psycopg import connect,Error as PgError
from psycopg.rows import dict_row
from src.phase3.auth.service_proof import BFFServiceVerifier,TrustRejected,assertion_from_asgi_headers,wire_request
from src.phase3.auth.transactional_admission import protected_operation
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore

if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
    raise RuntimeError("CI_ONLY")
dsn=os.environ["BFF_API_DSN"]
if ("host=127.0.0.1" not in dsn or "dbname=history_ci" not in dsn
        or "user=auth_trust_api" not in dsn):raise RuntimeError("CI_ISOLATION_REQUIRED")
keypath=Path(os.environ["BFF_TRUST_PUBKEY_FILE"])
if keypath.parent!=Path(os.environ["RUNNER_TEMP"]):raise RuntimeError("CI_ONLY")
verifier=BFFServiceVerifier(
    issuer="urn:rag-finance:synthetic-bff",
    audience="urn:rag-finance:api:internal-ci",
    public_keys={"ci-rsa-1":keypath.read_bytes()},
)
app=FastAPI(openapi_url=None,docs_url=None,redoc_url=None)
store=PostgresDurableReplayStore()

@app.api_route("/{tail:path}",methods=["GET","POST","PUT","PATCH"])
async def fixture(request:Request,tail:str):
    # Diagnostic responses never trigger a DB operation and remain mTLS-gated.
    if request.url.path=="/fixture-redirect":
        return RedirectResponse("/fixture",status_code=307)
    if request.url.path=="/fixture-invalid":
        return Response(content="not-json",media_type="application/json")
    if request.url.path=="/fixture-timeout":
        await asyncio.sleep(2)
        return {"ok":True}
    if request.url.path=="/fixture-disconnect":
        async def broken():
            yield b'{"ok":'
            raise RuntimeError("intentional CI fixture truncation")
        return StreamingResponse(broken(),media_type="application/json")
    try:
        token=assertion_from_asgi_headers(request.scope)
        method,path,query,body=wire_request(request.scope,await request.body())
        doc=json.loads(body)
        if (not isinstance(doc,dict) or type(doc.get("marker")) is not str
                or not doc["marker"].isascii() or len(doc["marker"])>64
                or not doc["marker"].startswith("bff_")
                or type(doc.get("idempotency_key")) is not str):
            raise TrustRejected()
        marker=doc["marker"]
        with connect(dsn,autocommit=True,row_factory=dict_row) as c:
            def protected(conn,owner):
                conn.execute("INSERT INTO auth_trust_ci.protected_actions(marker,owner_id) VALUES(%s,%s)",
                             (marker,owner))
                return True
            permitted=protected_operation(c,verifier=verifier,replay_store=store,
                compact_assertion=token,method=method,raw_path=path,
                raw_query=query,body=body,action=protected)
        if permitted is not True:raise TrustRejected()
        return {"ok":True}
    except (TrustRejected,ValueError,UnicodeError,TypeError,KeyError):
        return Response(status_code=401,headers={"Cache-Control":"no-store"})
    except PgError:
        return Response(status_code=503,headers={"Cache-Control":"no-store"})

if __name__=="__main__":
    import ssl,uvicorn
    folder=Path(os.environ["BFF_TLS_DIR"])
    if folder.parent!=Path(os.environ["RUNNER_TEMP"]):raise SystemExit("CI_ONLY")
    uvicorn.run(app,host="127.0.0.1",port=8443,access_log=False,log_level="error",
        ssl_certfile=str(folder/"api.crt"),ssl_keyfile=str(folder/"api.key"),
        ssl_ca_certs=str(folder/"ca.crt"),ssl_cert_reqs=ssl.CERT_REQUIRED)
