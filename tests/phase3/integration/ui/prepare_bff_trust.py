"""CI-only trusted fixture creator; CLI, not a web endpoint.
Opaque Session values exist only in a mode-0600 runner-local file and RAM.
No identity/actor choice, Session issuance or seed URL is exposed over HTTP.
"""
import json,os,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
import psycopg
from psycopg.rows import dict_row
from src.phase3.storage.postgres import auth_session as a

def conn(name):
    dsn=os.environ["BFF_"+name+"_DSN"]
    if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true" or "host=127.0.0.1" not in dsn or "dbname=history_ci" not in dsn:
        raise SystemExit("CI_ONLY")
    return psycopg.connect(dsn,autocommit=True,row_factory=dict_row)
def make(ttl=120):
    with conn("MAP") as c:
        owner=a.map_identity(c,"https://synthetic.invalid/"+uuid.uuid4().hex,"synthetic_"+uuid.uuid4().hex)["owner_id"]
    with conn("SESSION") as c:
        s=a.issue(c,owner,0,idle_seconds=ttl,absolute_seconds=max(ttl,ttl+120))
    return {"ownerId":s.owner_id,"sessionRef":s.opaque,"epoch":s.epoch,"generation":s.generation},s

def main():
    path=Path(os.environ["BFF_TRUST_SESSION_FILE"])
    if path.exists():raise SystemExit("NO_OVERWRITE")
    if path.parent!=Path(os.environ["RUNNER_TEMP"]):raise SystemExit("CI_ONLY")
    active,_=make()
    revoked,r=make()
    with conn("SESSION") as c:
        if a.revoke_one(c,r.opaque,r.epoch) is not True:raise SystemExit("FIXTURE_DENIED")
    rotated,r=make()
    with conn("SESSION") as c:
        a.rotate(c,r.opaque,r.epoch,r.generation)
    expired,_=make(ttl=1)
    data={"active":active,"revoked":revoked,"rotated":rotated,"expired":expired}
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,"w",encoding="utf8") as f:json.dump(data,f)
    # Never log the session, subject, JWT, bearer, PEM or identity.
    print("BFF_TRUST_FIXTURES_PREPARED")
if __name__=="__main__":main()
