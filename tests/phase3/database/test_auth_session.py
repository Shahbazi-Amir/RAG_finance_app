"""BND-DB-01: disposable real PostgreSQL synthetic role tests, NO live Auth."""
import hashlib,os,sys,time,unittest,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InsufficientPrivilege
from psycopg.rows import dict_row
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src/phase3/storage/postgres"))
import auth_session as a

ROLES={"MAP":("history_ci","auth_mapper"),"SESSION":("history_ci","auth_sessions"),
       "REVOKER":("history_ci","auth_revoker"),"REAUTH":("history_ci","auth_reauth"),
       "MIG":("history_ci","auth_migrator")}
def db(role="SESSION"):
    if os.getenv("CI")!="true": raise RuntimeError("CI_ONLY")
    v=os.environ["AUTH_"+role+"_DSN"]
    s=conninfo_to_dict(v); d,r=ROLES[role]
    if not (s.get("host")=="127.0.0.1" and s.get("port")=="5432"
            and s.get("dbname")==d and s.get("user")==r
            and set(s).issubset({"host","port","dbname","user","password","connect_timeout"})):
        raise RuntimeError("UNSAFE_DB_TARGET")
    return psycopg.connect(v,autocommit=True,row_factory=dict_row)
def claims():
    return "https://synthetic.invalid/"+uuid.uuid4().hex,"subject_"+uuid.uuid4().hex
def owner():
    with db("MAP") as c: return a.map_identity(c,*claims())
def issue(oid,epoch=0,idle=40,absolute=400):
    with db() as c: return a.issue(c,oid,epoch,idle_seconds=idle,absolute_seconds=absolute)
def digest(raw): return hashlib.sha256(raw.encode("ascii")).hexdigest()
def observed_wait(names):
    with db("MIG") as c:
        end=time.monotonic()+12
        while time.monotonic()<end:
            rows=c.execute("""SELECT application_name FROM pg_stat_activity
              WHERE application_name=ANY(%s) AND wait_event_type='Lock'""",(names,)).fetchall()
            if {x["application_name"] for x in rows}==set(names): return
            c.execute("SELECT pg_sleep(0.03)") # Observation of Lock, never sleep-only ordering.
        raise AssertionError("Expected owner-row lock wait not observed")

class OwnerSessionL1(unittest.TestCase):
    def test_BND01_concurrent_mapping(self):
        iss,sub=claims()
        def f(_):
            with db("MAP") as c: return a.map_identity(c,iss,sub)
        with ThreadPoolExecutor(max_workers=6) as ex: vals=list(ex.map(f,range(12)))
        self.assertEqual(len({v["owner_id"] for v in vals}),1)
        self.assertEqual({v["epoch"] for v in vals},{0})
        with db("MIG") as c:
            self.assertEqual(c.execute("SELECT count(*) AS n FROM auth_l1.identity_links WHERE issuer=%s AND subject=%s",(iss,sub)).fetchone()["n"],1)

    def test_BND02_issuer_subject_independent_of_contact(self):
        iss,sub=claims()
        with db("MAP") as c:
            vals=[a.map_identity(c,iss,sub)["owner_id"],
                  a.map_identity(c,iss+"/other",sub)["owner_id"],
                  a.map_identity(c,iss,sub+"/other")["owner_id"]]
        self.assertEqual(len(set(vals)),3)
        with db("MIG") as c:
            cols={x["column_name"] for x in c.execute("""SELECT column_name FROM information_schema.columns
                WHERE table_schema='auth_l1' AND table_name='identity_links'""").fetchall()}
            self.assertTrue({"issuer","subject","owner_id"}.issubset(cols))
            self.assertTrue({"email","phone","username"}.isdisjoint(cols))

    def test_BND03_immutable_identity_suspension(self):
        iss,sub=claims()
        with db("MAP") as c: oid=a.map_identity(c,iss,sub)["owner_id"]
        with db("MIG") as c:
            with self.assertRaisesRegex(psycopg.Error,"IDENTITY_LINK_IMMUTABLE"):
                with c.transaction():
                    c.execute("UPDATE auth_l1.identity_links SET owner_id=%s WHERE issuer=%s AND subject=%s",(str(uuid.uuid4()),iss,sub))
            with self.assertRaisesRegex(psycopg.Error,"IDENTITY_LINK_IMMUTABLE"):
                with c.transaction(): c.execute("DELETE FROM auth_l1.identity_links WHERE issuer=%s AND subject=%s",(iss,sub))
        with db("REVOKER") as c: self.assertEqual(a.suspend_owner(c,oid,0),1)
        with db("MAP") as c:
            with self.assertRaisesRegex(psycopg.Error,"IDENTITY_SUSPENDED"): a.map_identity(c,iss,sub)
        with db("REAUTH") as c:
            with self.assertRaisesRegex(psycopg.Error,"REAUTH_GATE_DENIED"): a.finish_simulated_reauth(c,oid,1)
        with db("MIG") as c:
            self.assertEqual(c.execute("SELECT owner_id FROM auth_l1.identity_links WHERE issuer=%s AND subject=%s",(iss,sub)).fetchone()["owner_id"],oid)
            with self.assertRaisesRegex(psycopg.Error,"OWNER_IMMUTABILITY_OR_EPOCH_REGRESSION"):
                with c.transaction(): c.execute("UPDATE auth_l1.owners SET session_epoch=0 WHERE owner_id=%s",(oid,))
            with self.assertRaisesRegex(psycopg.Error,"OWNER_IMMUTABILITY_OR_EPOCH_REGRESSION"):
                with c.transaction(): c.execute("UPDATE auth_l1.owners SET state='active' WHERE owner_id=%s",(oid,))

    def test_BND04_digest_only_and_valid_session(self):
        oid=owner()["owner_id"]; s=issue(oid)
        self.assertGreaterEqual(len(s.opaque),43)
        self.assertNotIn(s.opaque,repr(s))
        with db("MIG") as c:
            stored=c.execute("SELECT * FROM auth_l1.sessions WHERE digest_sha256=%s",(digest(s.opaque),)).fetchone()
            self.assertEqual(stored["digest_sha256"],digest(s.opaque))
            self.assertNotIn(s.opaque,str(stored))
            cols={x["column_name"] for x in c.execute("""SELECT column_name FROM information_schema.columns
                WHERE table_schema='auth_l1' AND table_name='sessions'""").fetchall()}
            self.assertTrue({"digest_sha256","session_epoch","idle_expires_at","absolute_expires_at"}.issubset(cols))
            self.assertTrue({"cookie","raw_token","password","idp_refresh_token"}.isdisjoint(cols))
        with db() as c: self.assertEqual(a.inspect(c,s.opaque)["owner_id"],oid)

    def test_BND05_idle_absolute_clock_boundaries(self):
        oid=owner()["owner_id"]; first=issue(oid,idle=10,absolute=40)
        with db() as c:
            before=a.inspect(c,first.opaque); after=a.touch(c,first.opaque,0)
            self.assertEqual(before["absolute_expires_at"],after["absolute_expires_at"])
            self.assertLessEqual(after["idle_expires_at"],after["absolute_expires_at"])
        with db("MIG") as c:
            c.execute("""UPDATE auth_l1.sessions SET created_at=clock_timestamp()-interval '3 hours',
                last_activity_at=clock_timestamp()-interval '2 hours',
                idle_expires_at=clock_timestamp()-interval '1 minute'
                WHERE digest_sha256=%s""",(digest(first.opaque),))
        with db() as c:
            self.assertIsNone(a.inspect(c,first.opaque))
            with self.assertRaises(psycopg.Error): a.touch(c,first.opaque,0)
        second=issue(oid,idle=10,absolute=40)
        with db("MIG") as c:
            c.execute("""UPDATE auth_l1.sessions SET created_at=clock_timestamp()-interval '4 hours',
                last_activity_at=clock_timestamp()-interval '3 hours',
                idle_expires_at=clock_timestamp()-interval '2 hours',
                absolute_expires_at=clock_timestamp()-interval '1 hour'
                WHERE digest_sha256=%s""",(digest(second.opaque),))
        with db() as c:
            self.assertIsNone(a.inspect(c,second.opaque))
            with self.assertRaises(psycopg.Error): a.rotate(c,second.opaque,0,0)

    def test_BND06_rotation_cas_one_winner(self):
        oid=owner()["owner_id"]; old=issue(oid)
        def race(_):
            with db() as c:
                try: return a.rotate(c,old.opaque,0,0)
                except psycopg.Error: return None
        with ThreadPoolExecutor(max_workers=4) as ex: result=list(ex.map(race,range(8)))
        wins=[x for x in result if x]
        self.assertEqual(len(wins),1)
        self.assertEqual(wins[0].generation,1)
        self.assertEqual(wins[0].absolute_expires_at,old.absolute_expires_at)
        with db() as c:
            self.assertIsNone(a.inspect(c,old.opaque))
            self.assertEqual(a.inspect(c,wins[0].opaque)["owner_id"],oid)
        with db("MIG") as c:
            self.assertEqual(c.execute("SELECT count(*) AS n FROM auth_l1.sessions WHERE owner_id=%s",(oid,)).fetchone()["n"],2)

    def test_BND07_revoke_one_only(self):
        oid=owner()["owner_id"]; first,second=issue(oid),issue(oid)
        with db() as c:
            self.assertTrue(a.revoke_one(c,first.opaque,0))
            self.assertFalse(a.revoke_one(c,first.opaque,0))
            self.assertIsNone(a.inspect(c,first.opaque))
            self.assertEqual(a.inspect(c,second.opaque)["owner_id"],oid)

    def test_BND08_revoke_all_epoch_reset_gate(self):
        oid=owner()["owner_id"]; s1,s2=issue(oid),issue(oid)
        with db("REVOKER") as c:
            self.assertEqual(a.revoke_all(c,oid,0),1)
            with self.assertRaises(psycopg.Error): a.revoke_all(c,oid,0)
        with db() as c:
            self.assertIsNone(a.inspect(c,s1.opaque))
            self.assertIsNone(a.inspect(c,s2.opaque))
            for epoch in (0,1):
                with self.assertRaises(psycopg.Error): a.issue(c,oid,epoch,idle_seconds=10,absolute_seconds=30)
            with self.assertRaises(InsufficientPrivilege): a.finish_simulated_reauth(c,oid,1)
        with db("REAUTH") as c:
            with self.assertRaises(psycopg.Error): a.finish_simulated_reauth(c,oid,0)
            self.assertTrue(a.finish_simulated_reauth(c,oid,1))
        fresh=issue(oid,1)
        with db() as c:
            self.assertEqual(a.inspect(c,fresh.opaque)["owner_id"],oid)
            self.assertIsNone(a.inspect(c,s1.opaque))
        with db("REVOKER") as c: self.assertEqual(a.revoke_all(c,oid,1),2)
        with db("MIG") as c:
            self.assertEqual(c.execute("SELECT session_epoch FROM auth_l1.owners WHERE owner_id=%s",(oid,)).fetchone()["session_epoch"],2)

    def test_BND09_issue_rotate_versus_revoke_linearization(self):
        oid=owner()["owner_id"]; old=issue(oid)
        def worker(kind,name):
            with db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                try:
                    if kind=="issue": a.issue(c,oid,0,idle_seconds=20,absolute_seconds=100)
                    else: a.rotate(c,old.opaque,0,0)
                    return "unexpected"
                except psycopg.Error: return "denied"
        with ThreadPoolExecutor(max_workers=2) as ex:
            with db("REVOKER") as c:
                with c.transaction():
                    self.assertEqual(a.revoke_all(c,oid,0),1)
                    one=ex.submit(worker,"issue","auth_bnd_issue")
                    two=ex.submit(worker,"rotate","auth_bnd_rotate")
                    observed_wait(["auth_bnd_issue","auth_bnd_rotate"])
                # Revoker COMMIT precedes worker completion.
            self.assertEqual(one.result(timeout=12),"denied")
            self.assertEqual(two.result(timeout=12),"denied")
        with db() as c:
            self.assertIsNone(a.inspect(c,old.opaque))
            self.assertFalse(a.fence_owner(c,oid,0))
        with db("MIG") as c:
            self.assertEqual(c.execute("SELECT count(*) AS n FROM auth_l1.sessions WHERE owner_id=%s",(oid,)).fetchone()["n"],1)

    def test_BND10_old_epoch_worker_after_commit(self):
        oid=owner()["owner_id"]; old=issue(oid)
        with db() as c: self.assertTrue(a.fence_owner(c,oid,0))
        with db("REVOKER") as c: self.assertEqual(a.revoke_all(c,oid,0),1)
        with db() as c:
            self.assertFalse(a.fence_owner(c,oid,0))
            self.assertFalse(a.fence_owner(c,oid,1)) # pending gate
            self.assertIsNone(a.inspect(c,old.opaque))

    def test_BND11_role_denials_and_transaction_context(self):
        for role in ("MAP","SESSION","REVOKER","REAUTH"):
            with db(role) as c:
                info=c.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
                self.assertFalse(info["rolsuper"])
                self.assertFalse(info["rolbypassrls"])
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction(): c.execute("SELECT * FROM auth_l1.sessions LIMIT 1")
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction(): c.execute("CREATE TABLE auth_l1.bad(x int)")
        with db() as c:
            with self.assertRaises(InsufficientPrivilege): a.map_identity(c,*claims())
            with self.assertRaises(InsufficientPrivilege): a.revoke_all(c,str(uuid.uuid4()),0)
        with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,row_factory=dict_row) as history:
            with self.assertRaises(InsufficientPrivilege):
                with history.transaction(): history.execute("SELECT * FROM auth_l1.sessions")
            with history.transaction():
                history.execute("SELECT set_config('app.owner_id','synthetic_only',true)")
                self.assertEqual(history.execute("SELECT current_setting('app.owner_id',true) AS v").fetchone()["v"],"synthetic_only")
            with history.transaction():
                self.assertNotEqual(history.execute("SELECT current_setting('app.owner_id',true) AS v").fetchone()["v"],"synthetic_only")
        with db("MIG") as c:
            for name in ("owners","identity_links","sessions"):
                r=c.execute("""SELECT relrowsecurity,relforcerowsecurity,
                       pg_get_userbyid(relowner) AS owner
                    FROM pg_class WHERE oid=%s::regclass""",("auth_l1."+name,)).fetchone()
                self.assertTrue(r["relrowsecurity"])
                self.assertTrue(r["relforcerowsecurity"])
                self.assertEqual(r["owner"],"auth_migrator")

    def test_BND12_two_owner_isolation(self):
        first,second=owner()["owner_id"],owner()["owner_id"]
        self.assertNotEqual(first,second)
        s1,s2=issue(first),issue(second)
        with db("REVOKER") as c: self.assertEqual(a.revoke_all(c,first,0),1)
        with db() as c:
            self.assertIsNone(a.inspect(c,s1.opaque))
            self.assertEqual(a.inspect(c,s2.opaque)["owner_id"],second)
