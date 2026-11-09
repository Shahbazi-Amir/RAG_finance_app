"""BND-DB-03 durable service assertion replay: synthetic PG17 CI ONLY.

No real BFF/JWT/IdP, cookie, real user, production DB, or raw token logging.
"""
import hashlib,os,secrets,sys,time,unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InsufficientPrivilege,UniqueViolation,InFailedSqlTransaction
from psycopg.rows import dict_row

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src/phase3/storage/postgres"))
from test_auth_session import db,owner,issue,observed_wait,digest as session_digest
from src.phase3.storage.postgres.service_replay import (
    PostgresDurableReplayStore,cleanup_expired
)
from src.phase3.storage.postgres import auth_session

STORE=PostgresDurableReplayStore()

def role(name):
    roles={"API":("history_ci","auth_trust_api"),"CLEANER":("history_ci","auth_replay_cleaner")}
    if os.getenv("CI")!="true" or name not in roles: raise RuntimeError("CI_ONLY")
    value=os.environ["REPLAY_"+name+"_DSN"]
    spec=conninfo_to_dict(value)
    database,user=roles[name]
    if not (spec.get("host")=="127.0.0.1" and spec.get("port")=="5432"
            and spec.get("dbname")==database and spec.get("user")==user
            and set(spec).issubset({"host","port","dbname","user","password","connect_timeout"})):
        raise RuntimeError("UNSAFE_TEST_DATABASE")
    return psycopg.connect(value,autocommit=True,row_factory=dict_row)

def pg_epoch():
    with db("MIG") as m:
        return m.execute("SELECT EXTRACT(EPOCH FROM clock_timestamp())::bigint AS n").fetchone()["n"]

def proof(issuer=None,jti=None,seconds=15):
    return SimpleNamespace(
        issuer=issuer or "urn:synthetic:trusted-service",
        jti=jti or secrets.token_urlsafe(24),
        expires_at=pg_epoch()+seconds
    )

def key(p):
    return hashlib.sha256((p.issuer+"\x00"+p.jti).encode("utf8")).hexdigest()

def count(p):
    with db("MIG") as m:
        return m.execute("SELECT count(*) AS n FROM auth_l1.service_assertion_replays WHERE issuer_jti_sha256=%s",(key(p),)).fetchone()["n"]

def action(c,marker):
    c.execute("INSERT INTO service_replay_ci.protected_actions(marker) VALUES(%s)",(marker,))

def actions(marker):
    with db("MIG") as m:
        return m.execute("SELECT count(*) AS n FROM service_replay_ci.protected_actions WHERE marker=%s",(marker,)).fetchone()["n"]

def pg_wait_expired(timestamp):
    with db("MIG") as m:
        end=time.monotonic()+9
        while m.execute("SELECT clock_timestamp()>=to_timestamp(%s) AS expired",(timestamp,)).fetchone()["expired"] is not True:
            if time.monotonic()>end: raise AssertionError("db timestamp wait exceeded bound")
            m.execute("SELECT pg_sleep(0.03)")

class AbortSynthetic(Exception): pass

class ServiceReplayDB(unittest.TestCase):
    def test_RPL01_commit_duplicate_aborts_tx_and_prevents_protected_action(self):
        p=proof()
        with role("API") as c:
            with self.assertRaisesRegex(RuntimeError,"REQUIRES_OUTER_TRANSACTION"):
                STORE.consume(c,p)
            with c.transaction():
                self.assertIs(STORE.consume(c,p),True)
                action(c,"rpl01_original")
            self.assertEqual(count(p),1)
            with self.assertRaises(UniqueViolation):
                with c.transaction():
                    STORE.consume(c,p)
            # When caller catches UNIQUE inside outer transaction, subsequent
            # SQL still fails until ROLLBACK; it cannot write an action.
            with c.transaction():
                with self.assertRaises(UniqueViolation): STORE.consume(c,p)
                with self.assertRaises(InFailedSqlTransaction): action(c,"rpl01_illicit")
        self.assertEqual(actions("rpl01_original"),1)
        self.assertEqual(actions("rpl01_illicit"),0)

    def test_RPL02_concurrent_multiple_connections_one_committed_jti(self):
        p=proof()
        def worker(_):
            with role("API") as c:
                try:
                    with c.transaction():
                        assert STORE.consume(c,p) is True
                        action(c,"rpl02_"+str(_))
                    return True
                except UniqueViolation:
                    return False
        with ThreadPoolExecutor(max_workers=7) as ex:
            results=list(ex.map(worker,range(15)))
        self.assertEqual(results.count(True),1)
        self.assertEqual(count(p),1)
        with db("MIG") as m:
            n=m.execute("SELECT count(*) AS n FROM service_replay_ci.protected_actions WHERE marker LIKE 'rpl02_%%'").fetchone()["n"]
            self.assertEqual(n,1)

    def test_RPL03_rollback_atomically_discards_jti_and_protected_write(self):
        p=proof()
        with role("API") as c:
            with self.assertRaises(AbortSynthetic):
                with c.transaction():
                    self.assertTrue(STORE.consume(c,p))
                    action(c,"rpl03_rolledback")
                    raise AbortSynthetic()
        self.assertEqual(count(p),0)
        self.assertEqual(actions("rpl03_rolledback"),0)
        with role("API") as c:
            with c.transaction():
                self.assertTrue(STORE.consume(c,p))
                action(c,"rpl03_committed")
        self.assertEqual(count(p),1)
        self.assertEqual(actions("rpl03_committed"),1)

    def test_RPL04_unique_wait_after_holder_commit_and_rollback(self):
        for outcome in ("commit","rollback"):
            with self.subTest(outcome=outcome):
                p=proof(seconds=18)
                label="rpl04_wait_"+outcome
                def waiter():
                    with role("API") as c:
                        c.execute("SELECT set_config('application_name',%s,false)",(label,))
                        c.execute("SET statement_timeout='9000ms'")
                        try:
                            with c.transaction():
                                STORE.consume(c,p)
                                action(c,"rpl04_new_"+outcome)
                            return "committed"
                        except UniqueViolation:
                            return "duplicate"
                with ThreadPoolExecutor(max_workers=1) as ex:
                    with role("API") as holder:
                        try:
                            with holder.transaction():
                                self.assertTrue(STORE.consume(holder,p))
                                waiting=ex.submit(waiter)
                                observed_wait([label])
                                self.assertFalse(waiting.done())
                                if outcome=="rollback": raise AbortSynthetic()
                        except AbortSynthetic: pass
                    result=waiting.result(timeout=12)
                self.assertEqual(result,"duplicate" if outcome=="commit" else "committed")
                self.assertEqual(count(p),1)
                self.assertEqual(actions("rpl04_new_"+outcome),0 if outcome=="commit" else 1)

    def test_RPL05_new_connection_new_adapter_persists_replay(self):
        p=proof()
        with role("API") as c:
            with c.transaction(): self.assertTrue(STORE.consume(c,p))
        with role("API") as new_connection:
            different_instance=PostgresDurableReplayStore()
            with self.assertRaises(UniqueViolation):
                with new_connection.transaction():
                    different_instance.consume(new_connection,p)
        self.assertEqual(count(p),1)
        # Reconnect/new Python instance is NOT a PostgreSQL server process restart.

    def test_RPL06_issuer_namespace_independent_same_jti(self):
        shared=secrets.token_urlsafe(24)
        first=proof(issuer="urn:synthetic:issuer-a",jti=shared)
        second=proof(issuer="urn:synthetic:issuer-b",jti=shared)
        self.assertNotEqual(key(first),key(second))
        with role("API") as c:
            with c.transaction(): self.assertTrue(STORE.consume(c,first))
            with c.transaction(): self.assertTrue(STORE.consume(c,second))
        self.assertEqual(count(first),1)
        self.assertEqual(count(second),1)
        with db("MIG") as m:
            rows=m.execute("""SELECT issuer_jti_sha256,expires_at,consumed_at
                  FROM auth_l1.service_assertion_replays
                  WHERE issuer_jti_sha256=ANY(%s)""",([key(first),key(second)],)).fetchall()
            self.assertEqual(len(rows),2)
            self.assertTrue(all(len(x["issuer_jti_sha256"])==64 for x in rows))
            self.assertNotIn(shared,str(rows))

    def test_RPL07_sql_and_wrapper_null_malformed_time_rejected(self):
        p=proof()
        good=key(p)
        with role("API") as c:
            bad=[
                (None,p.expires_at),("",p.expires_at),
                ("XYZ",p.expires_at),(good,None),
                (good,-1),(good,0),(good,253402300800),
                (good,pg_epoch()-1),(good,pg_epoch()+3600)
            ]
            for item in bad:
                with self.subTest(case="bad SQL input"):
                    with self.assertRaises(psycopg.Error):
                        with c.transaction():
                            c.execute("SELECT auth_l1.consume_service_assertion(%s,%s)",item)
            with c.transaction():
                for malformed in (
                    SimpleNamespace(issuer=None,jti=p.jti,expires_at=p.expires_at),
                    SimpleNamespace(issuer=p.issuer,jti=None,expires_at=p.expires_at),
                    SimpleNamespace(issuer=p.issuer,jti="a",expires_at=p.expires_at),
                    SimpleNamespace(issuer=p.issuer,jti=p.jti,expires_at=None),
                    SimpleNamespace(issuer=p.issuer,jti=p.jti,expires_at=True),
                    SimpleNamespace(issuer="a\x00b",jti=p.jti,expires_at=p.expires_at)
                ):
                    with self.assertRaises(ValueError): STORE.consume(c,malformed)
                self.assertTrue(STORE.consume(c,p))
        self.assertEqual(count(p),1)

    def test_RPL08_role_grants_security_definer_force_rls_and_table_denial(self):
        p=proof()
        with role("API") as c:
            attrs=c.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user").fetchone()
            self.assertTrue(all(not v for v in attrs.values()))
            for stmt in [
                "SELECT * FROM auth_l1.service_assertion_replays",
                "SELECT * FROM auth_l1.sessions",
                "SELECT * FROM history_l1.conversations",
                "CREATE TABLE auth_l1.unauthorized(a int)",
                "SELECT auth_l1.issue_session('bad',0,repeat('a',64),10,60)",
                "SELECT auth_l1.revoke_all('bad',0)",
                "SELECT auth_l1.map_identity('test','test')",
                "SELECT auth_l1.finish_simulated_reauth('bad',0)",
                "SELECT auth_l1.purge_expired_service_assertions(1)"
            ]:
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction(): c.execute(stmt)
        for role_name in ("MAP","SESSION","REVOKER","REAUTH"):
            with db(role_name) as c:
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction():
                        c.execute("SELECT auth_l1.consume_service_assertion(%s,%s)",(key(p),p.expires_at))
        with role("CLEANER") as c:
            with self.assertRaises(InsufficientPrivilege):
                with c.transaction(): c.execute("SELECT * FROM auth_l1.service_assertion_replays")
            with self.assertRaises(InsufficientPrivilege):
                with c.transaction(): c.execute("SELECT auth_l1.consume_service_assertion(%s,%s)",(key(p),p.expires_at))
            with self.assertRaises(InsufficientPrivilege):
                with c.transaction(): c.execute("SELECT auth_l1.admit_session_fenced('a',repeat('a',64),0,0)")
        with db("MIG") as m:
            tbl=m.execute("""SELECT relrowsecurity,relforcerowsecurity,
                   pg_get_userbyid(relowner) AS owner
                FROM pg_class WHERE oid='auth_l1.service_assertion_replays'::regclass""").fetchone()
            self.assertEqual(tbl["owner"],"auth_migrator")
            self.assertTrue(tbl["relrowsecurity"] and tbl["relforcerowsecurity"])
            functions=m.execute("""SELECT proname,prosecdef,proconfig,
                     pg_get_userbyid(proowner) AS owner
                 FROM pg_proc WHERE pronamespace='auth_l1'::regnamespace
                   AND proname IN ('consume_service_assertion','purge_expired_service_assertions')""").fetchall()
            self.assertEqual(len(functions),2)
            for f in functions:
                self.assertEqual(f["owner"],"auth_migrator")
                self.assertTrue(f["prosecdef"])
                self.assertIn("search_path=pg_catalog",f["proconfig"])

    def test_RPL09_cleanup_never_deletes_valid_and_purged_expired_stays_denied(self):
        fresh=proof(seconds=18)
        soon=proof(seconds=2)
        with role("API") as c:
            with c.transaction(): self.assertTrue(STORE.consume(c,fresh))
            with c.transaction(): self.assertTrue(STORE.consume(c,soon))
        with role("CLEANER") as cleaner:
            with cleaner.transaction():
                self.assertEqual(cleanup_expired(cleaner,100),0)
            with cleaner.transaction():
                for limit in (None,0,-1,1001):
                    with self.assertRaises(psycopg.Error):
                        # use savepoints to keep outer TX usable for the loop
                        with cleaner.transaction(): cleanup_expired(cleaner,limit)
        self.assertEqual(count(fresh),1)
        pg_wait_expired(soon.expires_at)
        with role("CLEANER") as cleaner:
            with cleaner.transaction():
                removed=cleanup_expired(cleaner,100)
                self.assertGreaterEqual(removed,1)
        self.assertEqual(count(soon),0)
        self.assertEqual(count(fresh),1)
        with role("API") as c:
            with self.assertRaises(psycopg.Error):
                with c.transaction(): STORE.consume(c,soon)
        self.assertEqual(count(soon),0)

    def test_RPL10_expired_after_unique_lock_wait_rollback_still_denied(self):
        p=proof(seconds=2)
        marker="rpl10_no_action"
        label="rpl10_unique_wait"
        def waiter():
            with role("API") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(label,))
                c.execute("SET statement_timeout='9000ms'")
                try:
                    with c.transaction():
                        STORE.consume(c,p)
                        action(c,marker)
                    return "unexpected-commit"
                except psycopg.Error:
                    return "denied"
        with ThreadPoolExecutor(max_workers=1) as ex:
            with role("API") as holder:
                try:
                    with holder.transaction():
                        self.assertTrue(STORE.consume(holder,p))
                        waiting=ex.submit(waiter)
                        observed_wait([label])
                        pg_wait_expired(p.expires_at)
                        raise AbortSynthetic()
                except AbortSynthetic: pass
            self.assertEqual(waiting.result(timeout=12),"denied")
        self.assertEqual(count(p),0)
        self.assertEqual(actions(marker),0)

    def test_RPL11_complete_same_tx_replay_session_action_and_rollback(self):
        oid=owner()["owner_id"]; session=issue(oid)
        p=proof()
        with role("API") as c:
            with c.transaction():
                self.assertTrue(STORE.consume(c,p))
                self.assertIs(auth_session.admit_session_fenced(
                    c,session.opaque,oid,0,0),True)
                action(c,"rpl11_commit")
        self.assertEqual(count(p),1)
        self.assertEqual(actions("rpl11_commit"),1)
        p2=proof()
        with role("API") as c:
            with self.assertRaises(AbortSynthetic):
                with c.transaction():
                    self.assertTrue(STORE.consume(c,p2))
                    self.assertTrue(auth_session.admit_session_fenced(
                        c,session.opaque,oid,0,0))
                    action(c,"rpl11_rollback")
                    raise AbortSynthetic()
        self.assertEqual(count(p2),0)
        self.assertEqual(actions("rpl11_rollback"),0)
        # API's independently accepted final proof-time recheck remains mandatory.
