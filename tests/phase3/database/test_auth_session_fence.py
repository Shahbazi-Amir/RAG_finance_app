"""BND-DB-02: same-session admission + owner/session row-lock tests, synthetic CI ONLY.

No real user, cookie, HTTP, IdP, streaming, model, or Production DB.
The only protected writes go into a disposable CI-only table with INSERT-only
grant to auth_sessions; never grant History or real user-data access.
"""
import unittest
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import psycopg
from psycopg.errors import InsufficientPrivilege
from test_auth_session import db, owner, issue, observed_wait, digest
import auth_session as auth

class ExpectedRollback(Exception):
    pass

def admit(conn, session, *, owner_id=None, epoch=None, generation=None):
    return auth.admit_session_fenced(
        conn,session.opaque,session.owner_id if owner_id is None else owner_id,
        session.epoch if epoch is None else epoch,
        session.generation if generation is None else generation
    )

def protected(conn, identity, label):
    # Explicitly test-only table. Privilege: auth_sessions may INSERT only,
    # not read or modify product History, Auth Owner or Session rows.
    conn.execute("INSERT INTO auth_fence_ci.protected_actions(owner_id,marker) VALUES(%s,%s)",
                 (identity,label))

def written(label):
    with db("MIG") as admin:
        return admin.execute("SELECT count(*) AS n FROM auth_fence_ci.protected_actions WHERE marker=%s",(label,)).fetchone()["n"]

class SessionAwareFence(unittest.TestCase):
    def test_BND16_session_admission_valid_bad_session_never_writes(self):
        actor=owner()["owner_id"]; session=issue(actor)
        with db() as c:
            with self.assertRaisesRegex(RuntimeError,"REQUIRES_OUTER_TRANSACTION"):
                admit(c,session) # standalone is not a multi-operation fence
            with c.transaction():
                self.assertTrue(admit(c,session))
                protected(c,actor,"bnd16_success")
            with c.transaction():
                self.assertFalse(admit(c,session,owner_id=owner()["owner_id"]))
                # Correctly scoped caller MUST NOT run a protected write on False.
            with c.transaction():
                self.assertFalse(auth.admit_session_fenced(c,"synthetic_unknown",actor,0,0))
        self.assertEqual(written("bnd16_success"),1)
        self.assertEqual(written("bnd16_denied"),0)

    def test_BND17_revoke_one_before_admission_and_same_owner_other_session(self):
        actor=owner()["owner_id"]; old=issue(actor); other=issue(actor)
        with db() as c:
            self.assertTrue(auth.revoke_one(c,old.opaque,0))
            with c.transaction():
                self.assertFalse(admit(c,old))
                self.assertTrue(admit(c,other))
                protected(c,actor,"bnd17_other_valid")
        self.assertEqual(written("bnd17_other_valid"),1)

    def test_BND18_rotation_first_stale_digest_and_generation_denied(self):
        actor=owner()["owner_id"]; old=issue(actor)
        with db() as c:
            rotated=auth.rotate(c,old.opaque,0,0)
            with c.transaction():
                self.assertFalse(admit(c,old))
                self.assertFalse(auth.admit_session_fenced(c,rotated.opaque,actor,0,0))
                self.assertTrue(admit(c,rotated))
                protected(c,actor,"bnd18_rotated_valid")
        self.assertEqual(written("bnd18_rotated_valid"),1)

    def test_BND19_revoke_all_reset_and_suspend_first(self):
        actor=owner()["owner_id"]; old=issue(actor)
        with db("REVOKER") as c:
            self.assertEqual(auth.revoke_all(c,actor,0),1)
        with db() as c:
            with c.transaction():
                self.assertFalse(admit(c,old))
                self.assertFalse(auth.admit_session_fenced(c,old.opaque,actor,1,0))
        with db("REAUTH") as c:
            self.assertTrue(auth.finish_simulated_reauth(c,actor,1))
        with db() as c:
            with c.transaction():
                self.assertFalse(admit(c,old))
        fresh=issue(actor,1)
        with db("REVOKER") as c: self.assertEqual(auth.suspend_owner(c,actor,1),2)
        with db() as c:
            with c.transaction():
                self.assertFalse(admit(c,fresh))
        self.assertEqual(written("bnd19_disallowed"),0)

    def test_BND20_admission_first_blocks_revokes_rotations_and_suspend_until_commit(self):
        # Every mutation locks Owner first; an accepted same-session fence locks
        # Owner FOR SHARE followed by Session FOR SHARE. These may not invert.
        for kind in ("revoke_one","rotate","revoke_all","suspend"):
            with self.subTest(kind=kind):
                actor=owner()["owner_id"]; session=issue(actor)
                name="bnd20_"+kind
                marker="bnd20_committed_"+kind
                def worker():
                    with db("REVOKER" if kind in ("revoke_all","suspend") else "SESSION") as c:
                        c.execute("SELECT set_config('application_name',%s,false)",(name,))
                        c.execute("SET statement_timeout='9000ms'")
                        if kind=="revoke_one": return auth.revoke_one(c,session.opaque,0)
                        if kind=="rotate": return auth.rotate(c,session.opaque,0,0)
                        if kind=="revoke_all": return auth.revoke_all(c,actor,0)
                        return auth.suspend_owner(c,actor,0)
                with ThreadPoolExecutor(max_workers=1) as ex:
                    with db() as admitted:
                        with admitted.transaction():
                            self.assertTrue(admit(admitted,session))
                            protected(admitted,actor,marker)
                            pending=ex.submit(worker)
                            observed_wait([name]) # actual pg_stat_activity wait_event_type=Lock
                            self.assertFalse(pending.done())
                        # COMMIT releases row locks; mutation can linearize next
                    result=pending.result(timeout=12)
                self.assertIsNotNone(result)
                self.assertEqual(written(marker),1)
                with db() as c:
                    with c.transaction():
                        self.assertFalse(admit(c,session))
        # Test proves DB local ordering, not HTTP cancellation or cross-DB fencing.

    def test_BND21_idle_absolute_expired_at_decision_and_later_crossing(self):
        actor=owner()["owner_id"]
        idle=issue(actor,idle=15,absolute=180)
        absolute=issue(actor,idle=15,absolute=180)
        with db("MIG") as admin:
            admin.execute("""UPDATE auth_l1.sessions
                SET created_at=clock_timestamp()-interval '3 hours',
                    last_activity_at=clock_timestamp()-interval '2 hours',
                    idle_expires_at=clock_timestamp()-interval '1 minute'
                WHERE digest_sha256=%s""",(digest(idle.opaque),))
            admin.execute("""UPDATE auth_l1.sessions
                SET created_at=clock_timestamp()-interval '3 hours',
                    last_activity_at=clock_timestamp()-interval '2 hours',
                    idle_expires_at=clock_timestamp()-interval '1 hour',
                    absolute_expires_at=clock_timestamp()-interval '1 minute'
                WHERE digest_sha256=%s""",(digest(absolute.opaque),))
        with db() as c:
            with c.transaction():
                self.assertFalse(admit(c,idle))
                self.assertFalse(admit(c,absolute))
        # Admission is checked once after both locks. Natural clock expiry is
        # not a revocation COMMIT. A pre-expiry accepted SQL txn may finish later.
        in_flight=issue(actor,idle=15,absolute=180)
        with db("MIG") as admin:
            until=admin.execute("""UPDATE auth_l1.sessions
                SET idle_expires_at=clock_timestamp()+interval '2 seconds'
                WHERE digest_sha256=%s RETURNING idle_expires_at""",
                (digest(in_flight.opaque),)).fetchone()["idle_expires_at"]
        with db() as c:
            with c.transaction():
                self.assertTrue(admit(c,in_flight))
                # PostgreSQL clock, not a sleep-only ordering claim, shows expiry
                # crossing during the existing accepted transaction.
                end=time.monotonic()+8
                while c.execute("SELECT clock_timestamp() AS t").fetchone()["t"]<until:
                    self.assertLess(time.monotonic(),end,"DB expiry clock did not cross")
                    c.execute("SELECT pg_sleep(0.03)")
                protected(c,actor,"bnd21_accepted_before_expiry")
            with c.transaction():
                self.assertFalse(admit(c,in_flight))
        self.assertEqual(written("bnd21_accepted_before_expiry"),1)

    def test_BND22_null_invalid_wrong_owner_and_stale_versions_SQL_wrapper(self):
        actor=owner()["owner_id"]; other=owner()["owner_id"]; session=issue(actor)
        digest_sha=digest(session.opaque)
        with db() as c:
            # Direct SQL with real restricted service-role privilege.
            invalid=[
                (None,digest_sha,0,0),
                ("",digest_sha,0,0),
                (actor,None,0,0),
                (actor,"NOT_A_SHA256_DIGEST",0,0),
                (actor,digest_sha,None,0),
                (actor,digest_sha,-1,0),
                (actor,digest_sha,0,None),
                (actor,digest_sha,0,-1),
            ]
            for args in invalid:
                with self.subTest(inputs="malformed SQL CAS"):
                    with self.assertRaisesRegex(psycopg.Error,"SESSION_ADMISSION_INVALID_INPUT"):
                        c.execute("SELECT auth_l1.admit_session_fenced(%s,%s,%s,%s)",args)
            with c.transaction():
                self.assertFalse(auth.admit_session_fenced(c,session.opaque,other,0,0))
                self.assertFalse(auth.admit_session_fenced(c,session.opaque,actor,1,0))
                self.assertFalse(auth.admit_session_fenced(c,session.opaque,actor,0,1))
                for args in [(None,actor,0,0),(session.opaque,actor,None,0),
                             (session.opaque,actor,0,None)]:
                    with self.assertRaises((ValueError,psycopg.Error)):
                        auth.admit_session_fenced(c,*args)
                self.assertTrue(admit(c,session))
        self.assertEqual(written("bnd22_invalid_write"),0)

    def test_BND23_rollback_protected_write_and_release_lock(self):
        actor=owner()["owner_id"]; session=issue(actor)
        def revoker():
            with db() as c:
                c.execute("SELECT set_config('application_name',%s,false)",("bnd23_rollback_wait",))
                c.execute("SET statement_timeout='9000ms'")
                return auth.revoke_one(c,session.opaque,0)
        with ThreadPoolExecutor(max_workers=1) as ex:
            with db() as c:
                with self.assertRaises(ExpectedRollback):
                    with c.transaction():
                        self.assertTrue(admit(c,session))
                        protected(c,actor,"bnd23_should_rollback")
                        future=ex.submit(revoker)
                        observed_wait(["bnd23_rollback_wait"])
                        raise ExpectedRollback("synthetic transaction abort")
            self.assertTrue(future.result(timeout=12))
        self.assertEqual(written("bnd23_should_rollback"),0)
        with db() as c:
            with c.transaction(): self.assertFalse(admit(c,session))

    def test_BND24_role_denials_and_session_table_isolation(self):
        actor=owner()["owner_id"]; session=issue(actor)
        for role in ("MAP","REVOKER","REAUTH"):
            with db(role) as c:
                with self.assertRaises(InsufficientPrivilege):
                    c.execute("SELECT auth_l1.admit_session_fenced(%s,%s,%s,%s)",
                              (actor,digest(session.opaque),0,0))
                with self.assertRaises(InsufficientPrivilege):
                    c.execute("INSERT INTO auth_fence_ci.protected_actions(owner_id,marker) VALUES(%s,%s)",
                              (actor,"unauthorized"))
        with db() as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SELECT * FROM auth_l1.sessions LIMIT 1")
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SELECT * FROM auth_fence_ci.protected_actions LIMIT 1")
            with c.transaction():
                self.assertTrue(admit(c,session))
                protected(c,actor,"bnd24_authorized")
        self.assertEqual(written("unauthorized"),0)
        self.assertEqual(written("bnd24_authorized"),1)
        # history_app has NO auth admission, and auth_sessions has NO History access.
        import os
        from psycopg.rows import dict_row
        with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,row_factory=dict_row) as history:
            with self.assertRaises(InsufficientPrivilege):
                history.execute("SELECT auth_l1.admit_session_fenced(%s,%s,%s,%s)",
                                (actor,digest(session.opaque),0,0))
        with db() as c:
            with self.assertRaises(InsufficientPrivilege):
                c.execute("SELECT * FROM history_l1.messages LIMIT 1")

    def test_BND25_specific_session_row_lock_held_through_commit(self):
        actor=owner()["owner_id"]; session=issue(actor)
        name="bnd25_session_specific_lock"
        def privileged_observer():
            # Disposable CI migrator bypasses Owner lock to prove Session row lock.
            with db("MIG") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(name,))
                c.execute("SET statement_timeout='9000ms'")
                return c.execute("""UPDATE auth_l1.sessions
                    SET last_activity_at=last_activity_at
                    WHERE digest_sha256=%s""",(digest(session.opaque),)).rowcount
        with ThreadPoolExecutor(max_workers=1) as ex:
            with db() as conn:
                with conn.transaction():
                    self.assertTrue(admit(conn,session))
                    pending=ex.submit(privileged_observer)
                    observed_wait([name])
                    self.assertFalse(pending.done())
                    protected(conn,actor,"bnd25_session_lock")
            self.assertEqual(pending.result(timeout=12),1)
        self.assertEqual(written("bnd25_session_lock"),1)
        with db() as conn:
            with conn.transaction():
                self.assertTrue(admit(conn,session))
