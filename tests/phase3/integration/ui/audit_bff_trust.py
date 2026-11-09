"""Only CI local privileged observer. Prints numeric count or role booleans."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import psycopg
from psycopg.rows import dict_row
if os.getenv("CI")!="true" or os.getenv("GITHUB_ACTIONS")!="true":
    raise SystemExit("CI_ONLY")
dsn=os.environ["BFF_MIG_DSN"]
if "host=127.0.0.1" not in dsn or "dbname=history_ci" not in dsn or "user=auth_migrator" not in dsn:
    raise SystemExit("CI_ONLY")
with psycopg.connect(dsn,autocommit=True,row_factory=dict_row) as c:
    if sys.argv[1]=="count" and len(sys.argv)==3:
        print(c.execute("SELECT count(*) AS n FROM auth_trust_ci.protected_actions WHERE marker=%s",
          (sys.argv[2],)).fetchone()["n"])
    elif sys.argv[1]=="role" and len(sys.argv)==2:
        row=c.execute("""SELECT has_table_privilege('auth_trust_api','auth_l1.sessions','SELECT') AS sess,
               has_table_privilege('auth_trust_api','auth_l1.service_assertion_replays','SELECT') AS replay,
               has_table_privilege('auth_trust_api','auth_trust_ci.protected_actions','INSERT') AS action""").fetchone()
        if row!={"sess":False,"replay":False,"action":True}:raise SystemExit("ROLE_POLICY_FAIL")
        print("ROLE_POLICY_PASS")
    else:raise SystemExit("CI_ONLY")
