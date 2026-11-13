"""010 claim encrypted material: disposable PostgreSQL 17.11 ONLY.

No IdP HTTP, KMS/decryption, BFF browser, Production roles or migrations.
SQL function may return encrypted bytes BEFORE caller commits: API MUST confirm
COMMIT before the first outbound IdP Code redemption; unknown COMMIT fails closed.
"""
import hashlib
import os
import secrets
import subprocess
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "infra/postgres/migrations/010_initial_login_claim_material.up.sql"
DOWN = ROOT / "infra/postgres/migrations/010_initial_login_claim_material.down.sql"
TEST_DATABASES = {"history_ci", "login_010_empty_ci", "login_010_evidence_ci"}
ROLES = {
    "MIG": ("AUTH_MIG_DSN", "auth_migrator"),
    "BOOT": ("LOGIN_BOOTSTRAP_DSN", "auth_login_bootstrap"),
    "CLAIM": ("LOGIN_CLAIM_DSN", "auth_login_claim_reader"),
    "STATUS": ("LOGIN_READER_DSN", "auth_login_reader"),
    "ISSUE": ("LOGIN_ISSUER_DSN", "auth_login_issuer"),
}


def checked_conn(role="MIG", db="history_ci"):
    if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("LOGIN010_DISPOSABLE_GITHUB_ACTIONS_ONLY")
    if db not in TEST_DATABASES:
        raise RuntimeError("LOGIN010_UNSAFE_DATABASE")
    env, username = ROLES[role]
    dsn = os.environ[env]
    params = conninfo_to_dict(dsn)
    if (params.get("host") != "127.0.0.1" or params.get("port") != "5432"
            or params.get("dbname") != "history_ci" or params.get("user") != username
            or set(params) - {"host", "port", "dbname", "user", "password", "connect_timeout"}):
        raise RuntimeError("LOGIN010_UNSAFE_ROLE_OR_ADDRESS")
    return psycopg.connect(make_conninfo(dsn, dbname=db), autocommit=True,
                           row_factory=dict_row)


def digest(s):
    return hashlib.sha256(s.encode("ascii")).hexdigest()


def make_attempt(ttl=180, db="history_ci"):
    a = {
        "id": uuid.uuid4(), "bff": uuid.uuid4(),
        "principal": "synthetic-bff-v1", "initiator": digest(secrets.token_urlsafe(24)),
        "state": digest(secrets.token_urlsafe(24)), "request": digest(secrets.token_urlsafe(24)),
        "start_key": secrets.token_urlsafe(24),
        "issuer": "https://synthetic.invalid/oidc-" + uuid.uuid4().hex,
        # Test bytes are DISTINCT synthetic ciphertext placeholders, never PKCE or nonce plaintext.
        "pkce": secrets.token_bytes(80), "nonce": secrets.token_bytes(80)
    }
    with checked_conn("BOOT", db) as c:
        started = c.execute("""SELECT auth_l1.start_initial_login_attempt(
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS accepted""",
            (a["id"], a["principal"], a["bff"], a["start_key"], a["request"],
             a["state"], a["initiator"], a["issuer"], a["pkce"], a["nonce"],
             ttl)).fetchone()["accepted"]
        assert started is True
    return a


def claim(c, a, *, ident=None, principal=None, bff=None, initiator=None, state=None):
    return c.execute(
        """SELECT expected_issuer,pkce_envelope,nonce_envelope,expires_at,claim_version
           FROM auth_l1.claim_initial_login_exchange_material(%s,%s,%s,%s,%s)""",
        (ident if ident is not None else a["id"],
         principal if principal is not None else a["principal"],
         bff if bff is not None else a["bff"],
         initiator if initiator is not None else a["initiator"],
         state if state is not None else a["state"])).fetchone()


def old_claim(c, a):
    return c.execute("""SELECT auth_l1.claim_initial_login_exchange(
        %s,%s,%s,%s) AS accepted""",
        (a["id"], a["principal"], a["initiator"], a["state"])
    ).fetchone()["accepted"]


def state_of(a, db="history_ci"):
    with checked_conn("MIG", db) as c:
        return c.execute("""SELECT state,state_version,session_digest,receipt_id,
            pkce_envelope,nonce_envelope,exchange_started_at,expires_at
            FROM auth_l1.initial_login_attempts WHERE attempt_id=%s""",
            (a["id"],)).fetchone()


def observe_actual_blocker(app_name, expected_holder_pid):
    with checked_conn("MIG") as c:
        deadline = time.monotonic() + 9
        while time.monotonic() < deadline:
            row = c.execute("""SELECT pid,wait_event_type,wait_event,
                   pg_blocking_pids(pid) AS blockers
                FROM pg_stat_activity
                WHERE application_name=%s AND datname='history_ci'
                  AND wait_event_type='Lock'""",
                (app_name,)).fetchone()
            if row and expected_holder_pid in row["blockers"]:
                print("PKCE010_PG_BLOCKER"
                      f" holder_pid={expected_holder_pid}"
                      f" waiter_pid={row['pid']}"
                      f" pg_blocking_pids={row['blockers']}"
                      f" wait_event_type={row['wait_event_type']}"
                      f" wait_event={row['wait_event']}", flush=True)
                return row
            c.execute("SELECT pg_sleep(0.02)")
    raise AssertionError("PKCE010_REAL_POSTGRES_BLOCKER_NOT_OBSERVED")


def migration_sql(db, path):
    if db not in {"login_010_empty_ci", "login_010_evidence_ci"} or path not in {UP, DOWN}:
        raise RuntimeError("LOGIN010_DESTRUCTIVE_MIGRATION_REFUSED")
    migrator = conninfo_to_dict(os.environ["AUTH_MIG_DSN"])
    env = dict(os.environ)
    env.update(PGHOST="127.0.0.1", PGPORT="5432", PGDATABASE=db,
               PGUSER="auth_migrator", PGPASSWORD=migrator["password"])
    return subprocess.run(["psql", "-X", "-v", "ON_ERROR_STOP=1",
                           "-d", db, "-f", str(path)],
                          capture_output=True, text=True, timeout=20, env=env)


class InitialLoginClaimMaterial010(unittest.TestCase):
    def test_PKCE01_cross_connection_start_and_claim_same_material(self):
        a = make_attempt()
        with checked_conn("CLAIM") as other_worker:
            row = claim(other_worker, a)
        self.assertEqual(row["expected_issuer"], a["issuer"])
        self.assertEqual(bytes(row["pkce_envelope"]), a["pkce"])
        self.assertEqual(bytes(row["nonce_envelope"]), a["nonce"])
        self.assertEqual(row["claim_version"], 1)
        self.assertEqual(state_of(a)["state"], "EXCHANGE_STARTED")
        self.assertEqual(state_of(a)["state_version"], 1)
        # This is DB two-connection handoff, not two independent API processes/IdP.

    def test_PKCE02_two_claimers_actual_lock_one_ciphertext_winner(self):
        a = make_attempt()
        holder_is_ready, release = threading.Event(), threading.Event()
        label = "pkce010_loser_" + uuid.uuid4().hex[:8]
        holder_pid = {}
        def winner():
            with checked_conn("CLAIM") as c:
                with c.transaction():
                    row = claim(c, a)
                    holder_pid["pid"] = c.info.backend_pid
                    holder_is_ready.set()
                    if not release.wait(11):
                        raise AssertionError("claim holder timing out")
                return row
        def loser():
            with checked_conn("CLAIM") as c:
                c.execute("SELECT set_config('application_name',%s,false)", (label,))
                with self.assertRaisesRegex(psycopg.Error, "LOGIN_CLAIM_DENIED"):
                    with c.transaction():
                        claim(c, a)
                return "DENIED_WITHOUT_ROW"
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(winner)
            self.assertTrue(holder_is_ready.wait(9))
            second = pool.submit(loser)
            try:
                evidence = observe_actual_blocker(label, holder_pid["pid"])
                self.assertEqual(evidence["wait_event_type"], "Lock")
                self.assertFalse(second.done())
            finally:
                release.set()
            self.assertEqual(bytes(first.result(timeout=12)["pkce_envelope"]), a["pkce"])
            self.assertEqual(second.result(timeout=12), "DENIED_WITHOUT_ROW")
        self.assertEqual(state_of(a)["state_version"], 1)

    def test_PKCE03_legacy_and_new_cannot_both_win_in_either_order(self):
        a = make_attempt()
        with checked_conn("BOOT") as c:
            self.assertTrue(old_claim(c, a))
        with checked_conn("CLAIM") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                claim(c, a)
        b = make_attempt()
        with checked_conn("CLAIM") as c:
            self.assertIsNotNone(claim(c, b))
        with checked_conn("BOOT") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                old_claim(c, b)
        self.assertEqual(state_of(a)["state_version"], 1)
        self.assertEqual(state_of(b)["state_version"], 1)

    def test_PKCE04_two_attempt_swap_never_returns_foreign_material(self):
        a, b = make_attempt(), make_attempt()
        with checked_conn("CLAIM") as c:
            for fields in ({"state":b["state"]},{"bff":b["bff"]},
                           {"initiator":b["initiator"]},{"principal":"foreign-bff"}):
                with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                    claim(c, a, **fields)
            self.assertEqual(state_of(a)["state"], "INITIATED")
            got=claim(c, b)
            self.assertEqual(bytes(got["nonce_envelope"]), b["nonce"])
            self.assertNotEqual(bytes(got["nonce_envelope"]), a["nonce"])
        self.assertEqual(state_of(a)["state"], "INITIATED")

    def test_PKCE05_wrong_bff_and_original_browser_binding_deny(self):
        a = make_attempt()
        with checked_conn("CLAIM") as c:
            for changed in ({"principal":"another-authorized-service"},
                            {"initiator":digest(secrets.token_urlsafe(24))},
                            {"bff":uuid.uuid4()}):
                with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                    claim(c, a, **changed)
        self.assertEqual(state_of(a)["state"], "INITIATED")
        # This only tests DB tuple equality, not real cert or Cookie verification.

    def test_PKCE06_invalid_inputs_and_wrong_digest_are_closed(self):
        a=make_attempt()
        with checked_conn("CLAIM") as c:
            for changed in ({"state":digest("foreign")},{"state":"bad"},
                            {"initiator":"bad"},{"ident":uuid.uuid4()},
                            {"bff":uuid.uuid4()}):
                with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                    claim(c, a, **changed)
        self.assertEqual(state_of(a)["state_version"],0)
        # PKCE-vs-nonce ciphertext swap and client/redirect binding are
        # authenticated-envelope API tests; PostgreSQL cannot decrypt them.

    def test_PKCE07_expired_after_real_lock_wait_returns_no_material(self):
        a = make_attempt(ttl=1)
        held, release = threading.Event(), threading.Event()
        label = "pkce010_expired_" + uuid.uuid4().hex[:8]
        pids = {}
        def block_row():
            with checked_conn("MIG") as c:
                with c.transaction():
                    c.execute("""SELECT attempt_id FROM auth_l1.initial_login_attempts
                       WHERE attempt_id=%s FOR UPDATE""", (a["id"],))
                    pids["holder"]=c.info.backend_pid
                    held.set()
                    if not release.wait(9):
                        raise AssertionError("expire holder timing out")
        def claim_while_waiting():
            with checked_conn("CLAIM") as c:
                c.execute("SELECT set_config('application_name',%s,false)",(label,))
                with self.assertRaisesRegex(psycopg.Error, "LOGIN_CLAIM_DENIED"):
                    with c.transaction():
                        claim(c,a)
                return "EXPIRED_DENIED"
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(block_row)
            self.assertTrue(held.wait(8))
            second=pool.submit(claim_while_waiting)
            try:
                witness=observe_actual_blocker(label,pids["holder"])
                self.assertEqual(witness["wait_event_type"],"Lock")
                time.sleep(1.22)
                self.assertFalse(second.done())
            finally:
                release.set()
            first.result(timeout=8)
            self.assertEqual(second.result(timeout=8),"EXPIRED_DENIED")
        self.assertEqual(state_of(a)["state"], "INITIATED")

    def test_PKCE09_committed_claim_then_lost_reply_never_reclaims(self):
        a=make_attempt()
        with checked_conn("CLAIM") as c:
            with c.transaction():
                obtained=claim(c,a)
                self.assertEqual(obtained["claim_version"],1)
            # COMMIT succeeded; simulate API losing its response thereafter.
        with checked_conn("CLAIM") as other_worker:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                claim(other_worker,a)
        with checked_conn("BOOT") as c:
            with self.assertRaisesRegex(psycopg.Error,"LOGIN_CLAIM_DENIED"):
                old_claim(c,a)
        self.assertEqual(state_of(a)["session_digest"], None)
        # This does not establish what happens when a real COMMIT itself is uncertain.

    def test_PKCE10_unknown_cannot_resume_old_or_new_claim(self):
        a=make_attempt()
        with checked_conn("CLAIM") as c: claim(c,a)
        with checked_conn("BOOT") as c:
            self.assertTrue(c.execute("""SELECT auth_l1.mark_initial_login_unknown(
              %s,%s,%s) AS ok""",(a["id"],a["principal"],a["initiator"])
            ).fetchone()["ok"])
            with self.assertRaises(psycopg.Error): old_claim(c,a)
        with checked_conn("CLAIM") as c:
            with self.assertRaises(psycopg.Error): claim(c,a)
        self.assertEqual(state_of(a)["state"],"UNKNOWN_RECONCILIATION_REQUIRED")

    def test_PKCE11_identical_row_ciphertexts_not_other_attempt(self):
        a,b=make_attempt(),make_attempt()
        with checked_conn("CLAIM") as c:
            got=claim(c,a)
        self.assertEqual(bytes(got["pkce_envelope"]),state_of(a)["pkce_envelope"])
        self.assertEqual(bytes(got["nonce_envelope"]),state_of(a)["nonce_envelope"])
        self.assertNotEqual(bytes(got["pkce_envelope"]),state_of(b)["pkce_envelope"])
        # Tampering by the DB owner or cryptographic binding is outside SQL
        # without plaintext and must be tested by the API envelope verifier.

    def test_PKCE12_no_direct_select_or_public_execute_and_status_redacted(self):
        a=make_attempt()
        signature="auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)"
        with checked_conn("MIG") as c:
            role=c.execute("""SELECT rolsuper,rolbypassrls,rolinherit,rolcreatedb,
                rolcreaterole FROM pg_roles WHERE rolname='auth_login_claim_reader'""").fetchone()
            self.assertFalse(any(role.values()))
            grants=c.execute("""SELECT
                  has_schema_privilege('auth_login_claim_reader','auth_l1','USAGE') AS usage,
                  has_function_privilege('auth_login_claim_reader',%s,'EXECUTE') AS claim_yes,
                  has_function_privilege('auth_login_bootstrap',%s,'EXECUTE') AS old_no,
                  has_function_privilege('auth_login_reader',%s,'EXECUTE') AS status_no,
                  EXISTS (SELECT 1 FROM pg_proc p, LATERAL aclexplode(p.proacl) x
                     WHERE p.oid=%s::regprocedure AND x.grantee=0
                       AND x.privilege_type='EXECUTE') AS public_no""",
                (signature,signature,signature,signature)).fetchone()
            self.assertTrue(grants["usage"])
            self.assertTrue(grants["claim_yes"])
            self.assertFalse(grants["old_no"])
            self.assertFalse(grants["status_no"])
            self.assertFalse(grants["public_no"])
            rls=c.execute("""SELECT relrowsecurity,relforcerowsecurity
                FROM pg_class WHERE oid='auth_l1.initial_login_attempts'::regclass""").fetchone()
            self.assertTrue(rls["relrowsecurity"] and rls["relforcerowsecurity"])
        with checked_conn("CLAIM") as c:
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT * FROM auth_l1.initial_login_attempts")
            with self.assertRaises(psycopg.Error):
                c.execute("SELECT auth_l1.status_initial_login_attempt(%s,%s,%s)",
                          (a["id"],a["principal"],a["initiator"]))
        with checked_conn("STATUS") as c:
            payload=c.execute("""SELECT auth_l1.status_initial_login_attempt(
                 %s,%s,%s) AS status""",
                (a["id"],a["principal"],a["initiator"])).fetchone()["status"]
            self.assertEqual(payload["state"],"INITIATED")
            for forbidden in ("pkce","nonce","verifier","receipt","owner","alias","cipher"):
                self.assertNotIn(forbidden,str(payload).lower())
            with self.assertRaises(psycopg.Error):
                claim(c,a)

    def test_PKCE13_real_up_down_up_and_data_bearing_rollback_refused(self):
        for path in (DOWN,UP,DOWN,UP):
            completed=migration_sql("login_010_empty_ci",path)
            self.assertEqual(completed.returncode,0,completed.stderr[-1600:])
        with checked_conn("MIG","login_010_empty_ci") as c:
            present=c.execute("""SELECT to_regprocedure(
             'auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)')
              IS NOT NULL AS ok""").fetchone()["ok"]
            self.assertTrue(present)
        evidence=make_attempt(db="login_010_evidence_ci")
        snapshot=state_of(evidence,"login_010_evidence_ci")
        refused=migration_sql("login_010_evidence_ci",DOWN)
        self.assertNotEqual(refused.returncode,0)
        self.assertIn("LOGIN_010_DOWN_REFUSED_EVIDENCE_EXISTS",refused.stderr)
        self.assertEqual(state_of(evidence,"login_010_evidence_ci"),snapshot)
        with checked_conn("MIG","login_010_evidence_ci") as c:
            self.assertTrue(c.execute("""SELECT to_regprocedure(
             'auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)')
              IS NOT NULL AS ok""").fetchone()["ok"])
        print("PKCE010_EMPTY_UP_DOWN_UP_AND_EVIDENCE_DOWN_REFUSED",flush=True)

    def test_PKCE14_pending_admission_unaffected_by_claim(self):
        a=make_attempt()
        with checked_conn("CLAIM") as c: claim(c,a)
        self.assertEqual(state_of(a)["state"],"EXCHANGE_STARTED")
        self.assertIsNone(state_of(a)["session_digest"])
        # Real BFF alias/ACK/browser delivery and IdP cryptography are NOT_RUN.
