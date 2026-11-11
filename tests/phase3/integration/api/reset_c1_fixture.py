"""CR-API-03A — independent CI-only authority/DB/IdP fixtures.

No public issuance, recovery, step-up, C2, persistent IdP result or Product
wiring. Generates only synthetic credentials in runner memory. Product PG and
Keycloak identity PG are two different isolated Postgres 17.11 containers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import secrets
import sys
import threading
import time
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from requests.exceptions import ConnectionError as RemoteConnectionError
from requests.exceptions import ReadTimeout

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/phase3/integration/auth_idp"))

from src.phase3.auth.reset_c1_dispatch import BoundSyntheticReset
from src.phase3.storage.postgres import auth_session, reset_c1
from controlled_reset import (initialize_clean_realm, create_user, issue_service,
                              clean_fgap_permission)
from evaluate import new_page, fill_login
from support import Admin, BASE, credentials, request


class IdpHarnessContext:
    """Only reuses read-only existing Keycloak/Playwright fixture helpers."""
    Admin = Admin
    new_page = staticmethod(new_page)
    fill_login = staticmethod(fill_login)

    def __init__(self):
        self.CURRENT = "CR-IDP-fixture"
        self.RESULTS = {}
        self.STAGES = {}

    def case(self, label, *_):
        self.STAGES[label] = "PASS"


@dataclass(repr=False)
class SyntheticIdp:
    root: object
    oidc: dict
    target_id: str
    other_id: str
    target_email: str
    other_email: str
    target_old: str
    other_old: str
    scoped_token: str
    e: IdpHarnessContext

    def __repr__(self):
        return "SyntheticIdp(<redacted>)"


def setup_clean_idp() -> SyntheticIdp:
    e = IdpHarnessContext()
    root, oidc, _ = initialize_clean_realm(e)
    target_email = "c1-allowed@example.test"
    other_email = "c1-unrelated@example.test"
    old = "Qa9!" + secrets.token_urlsafe(18)
    other_old = "Qb9!" + secrets.token_urlsafe(18)
    target = create_user(root, target_email, old)
    other = create_user(root, other_email, other_old)
    cid = "c1-executor-scoped"
    scoped_token = issue_service(root, cid)
    # Actual persisted FGAP readback, from the merged PR23 standard APIs.
    # This does not silently bestow manage-users/realm-admin on executor.
    assert clean_fgap_permission(e, root, target, cid, [other])
    return SyntheticIdp(root, oidc, target, other, target_email, other_email,
                        old, other_old, scoped_token, e)


class ProductFixture:
    """Creates dedicated non-BYPASSRLS issuer/executor roles and 003–006 schema."""

    def __init__(self):
        if os.environ.get("CI") != "true" or os.environ.get(
            "COMPOSE_PROJECT_NAME"
        ) != "authidpci":
            raise RuntimeError("RESET_FIXTURE_REQUIRES_ISOLATED_CI")
        self.root_password = credentials()["RESET_DB_PASSWORD"]
        self.roles = {}
        self.dbname = "product_ci"
        self.host = "product-db"

    def admin(self):
        return psycopg.connect(
            host=self.host, port=5432, dbname=self.dbname,
            user="product_ci", password=self.root_password,
            connect_timeout=5, autocommit=True, row_factory=dict_row,
        )

    def connect(self, name):
        return psycopg.connect(
            host=self.host, port=5432, dbname=self.dbname,
            user=name, password=self.roles[name],
            connect_timeout=5, autocommit=True, row_factory=dict_row,
        )

    def bootstrap(self):
        roles = ("auth_mapper", "auth_sessions", "auth_revoker",
                 "auth_reauth", "auth_trust_api", "auth_replay_cleaner",
                 "auth_reset_issuer", "auth_reset_executor")
        with self.admin() as conn:
            conn.execute("CREATE ROLE auth_migrator NOLOGIN BYPASSRLS NOSUPERUSER")
            conn.execute("GRANT CREATE ON DATABASE product_ci TO auth_migrator")
            # Unmodified 003 explicitly REVOKEs table rights from history_app.
            # The role is a NOLOGIN, unprivileged placeholder in this CI DB.
            conn.execute("CREATE ROLE history_app NOLOGIN NOSUPERUSER NOBYPASSRLS")
            for name in roles:
                password = secrets.token_hex(28)
                self.roles[name] = password
                conn.execute(sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS "
                    "NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD {}"
                ).format(sql.Identifier(name), sql.Literal(password)))
            for filename in (
                "003_auth_session.up.sql",
                "004_session_aware_fence.up.sql",
                "005_service_assertion_replay.up.sql",
                "006_atomic_reset_c1.up.sql",
            ):
                # Each versioned, UNMODIFIED migration runs in its own TX as
                # the same restricted CI BYPASSRLS definer used by DB tests.
                script = (ROOT / "infra/postgres/migrations" / filename).read_text(
                    encoding="utf-8")
                with conn.transaction():
                    conn.execute("SET LOCAL ROLE auth_migrator")
                    conn.execute(script)
            privileges = conn.execute("""
                SELECT
                  has_function_privilege(
                    'auth_reset_executor',
                    'auth_l1.execute_reset_c1(text,text,text,text,bigint,uuid)',
                    'EXECUTE') AS executor_yes,
                  has_function_privilege(
                    'auth_reset_executor',
                    'auth_l1.issue_reset_c1_authorization(text,text,text,text,bigint,bigint,text,integer)',
                    'EXECUTE') AS executor_issuer,
                  has_function_privilege(
                    'auth_reset_issuer',
                    'auth_l1.execute_reset_c1(text,text,text,text,bigint,uuid)',
                    'EXECUTE') AS issuer_executor
            """).fetchone()
            assert privileges == {
                "executor_yes": True,
                "executor_issuer": False,
                "issuer_executor": False,
            }, "RESET_DB_ROLE_SPLIT_UNPROVEN"

    def owner(self):
        with self.connect("auth_mapper") as conn:
            with conn.transaction():
                rec = auth_session.map_identity(
                    conn, "urn:synthetic-c1-fixture",
                    "fixture-" + uuid4().hex)
        return rec["owner_id"]

    def session(self, owner):
        with self.connect("auth_sessions") as conn:
            with conn.transaction():
                return auth_session.issue(conn, owner, 0,
                                          idle_seconds=300,
                                          absolute_seconds=1200)

    def authorization(self, owner, target_id):
        # The *separate* auth_reset_issuer role alone mints synthetic proof.
        # The returned capability is passed in RAM to auth_reset_executor.
        with self.connect("auth_reset_issuer") as conn:
            cap = reset_c1.issue_synthetic_verified_authorization(
                conn, owner, reset_c1.KIND_RECOVERY, 0, int(time.time()) + 300)
        return BoundSyntheticReset(cap, target_id)

    def state(self, owner, auth=None):
        with self.admin() as conn:
            row = conn.execute(
                "SELECT session_epoch,reset_gate,state FROM auth_l1.owners "
                "WHERE owner_id=%s", (owner,)).fetchone()
            session = conn.execute(
                "SELECT status,count(*) AS n FROM auth_l1.sessions "
                "WHERE owner_id=%s GROUP BY status", (owner,)).fetchall()
            ledger = conn.execute(
                "SELECT status,active,revoked_epoch FROM auth_l1.reset_c1_operations "
                "WHERE owner_id=%s", (owner,)).fetchall()
            consumed = None
            if auth is not None:
                consumed = conn.execute(
                    "SELECT (consumed_at IS NOT NULL) AS consumed "
                    "FROM auth_l1.reset_c1_authorizations "
                    "WHERE authorization_sha256=%s",
                    (reset_c1.digest_authorization(auth.authorization.opaque),)
                ).fetchone()
            return {
                "epoch": row["session_epoch"],
                "gate": row["reset_gate"],
                "owner_state": row["state"],
                "sessions": {x["status"]: x["n"] for x in session},
                "operations": len(ledger),
                "pending": all(x["status"] == "REVOKED_PENDING_IDP" and
                               x["active"] and x["revoked_epoch"] == 1
                               for x in ledger),
                "consumed": consumed["consumed"] if consumed else None,
            }


class ScopedIdpTransport:
    """One direct Keycloak admin endpoint; token is already FGAP target-limited."""

    def __init__(self, realm, token, *, observer=None, fault=None):
        self.realm = realm
        self.token = token   # server memory ONLY
        self.observer = observer
        self.fault = fault
        self.calls = 0
        self.responses = []
        self._lock = threading.Lock()

    def send_reset(self, target_idp_user, new_password):
        with self._lock:
            self.calls += 1
        if self.observer is not None:
            self.observer()  # independent second PG connection proves COMMIT
        if self.fault == "injected_timeout":
            raise ReadTimeout("sanitized injected timeout")
        if self.fault == "injected_disconnect":
            raise RemoteConnectionError("sanitized injected disconnect")
        result = request(
            "PUT", BASE + "/admin/realms/" + self.realm +
            "/users/" + target_idp_user + "/reset-password",
            headers={"Authorization": "Bearer " + self.token},
            json={"type": "password", "temporary": False,
                  "value": new_password},
        )
        self.responses.append(result.status_code)
        if self.fault == "discard_real_response":
            # IdP has already handled a REAL HTTP call; the caller cannot
            # distinguish a late/missing reply from an unsuccessful write.
            assert result.status_code == 204
            raise RemoteConnectionError("sanitized lost response")
        return result.status_code
