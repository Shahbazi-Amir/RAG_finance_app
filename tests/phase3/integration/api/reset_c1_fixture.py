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
from src.phase3.storage.postgres import auth_session, reset_c1, reset_identity_lookup, reset_idp_attempt
from controlled_reset import (initialize_clean_realm, create_user, issue_service,
                              clean_fgap_permission, _cb_paged_authz)
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
    other_scoped_token: str
    e: IdpHarnessContext

    def __repr__(self):
        return "SyntheticIdp(<redacted>)"

    def create_account(self, label: str):
        # Real user in the already-restricted Keycloak realm, not merely a
        # random UUID invented by Product PostgreSQL.
        assert label.isalnum()
        email = "c1-" + label + "-" + secrets.token_hex(4) + "@example.test"
        old_password = "Qz9!" + secrets.token_urlsafe(18)
        subject = create_user(self.root, email, old_password)
        record = self.root.call("GET", "/users/" + subject).json()
        assert record.get("id") == subject and record.get("email") == email
        return subject, email, old_password


def provision_exact_user_service(root, uid: str, cid: str, excluded: list[str]) -> str:
    """CI bootstrap only: per-user FGAP permission, no broad admin role.

    Read the persisted per-user permission via Keycloak 26.8.2's paginated
    search and reverse resource/scope/policy endpoints. No UUIDs in reports.
    """
    assert cid.replace("-", "").isalnum()
    token = issue_service(root, cid)
    cid_uuid = root.client(cid)["id"]
    suid = root.call("GET","/clients/"+cid_uuid+"/service-account-user").json()["id"]
    rm_id = root.client("realm-management")["id"]
    direct = root.call("GET","/users/"+suid+
                      "/role-mappings/clients/"+rm_id).json()
    composite = root.call("GET","/users/"+suid+
                         "/role-mappings/clients/"+rm_id+"/composite").json()
    broad={"manage-users","view-users","realm-admin","manage-realm"}
    assert not any(x.get("name") in broad for x in direct+composite)
    authz = root.client("admin-permissions")["id"]
    pref = "/clients/"+authz+"/authz/resource-server"
    policy_name = cid+"-one-user-policy"
    permission_name = cid+"-one-user-reset"
    root.call("POST",pref+"/policy/user",json={
        "name":policy_name,"logic":"POSITIVE","users":[suid]
    },expect_status=201)
    root.call("POST",pref+"/permission/scope",json={
        "name":permission_name,"resourceType":"Users",
        "scopes":["reset-password"],"resources":[uid],
        "policies":[policy_name]
    },expect_status=201)
    permissions,pm = _cb_paged_authz(root,pref,"/permission/scope")
    candidates=[x for x in permissions if x.get("name")==permission_name]
    assert pm["complete"] and len(candidates)==1
    perm_id=candidates[0]["id"]
    detail=root.call("GET",pref+"/permission/scope/"+perm_id).json()
    assert detail["resourceType"]=="Users"
    scopes,sm=_cb_paged_authz(root,pref,"/scope")
    target_scope=[x for x in scopes if x.get("name")=="reset-password"]
    assert sm["complete"] and len(target_scope)==1
    for scope in scopes:
        links=root.call("GET",pref+"/scope/"+scope["id"]+"/permissions").json()
        assert any(x.get("id")==perm_id for x in links)==(
            scope["id"]==target_scope[0]["id"])
    policy_rows,polm=_cb_paged_authz(root,pref,"/policy/user")
    policies=[x for x in policy_rows if x.get("name")==policy_name]
    assert polm["complete"] and len(policies)==1
    linked=root.call("GET",pref+"/permission/scope/"+perm_id+
                     "/associatedPolicies").json()
    assert len(linked)==1 and linked[0].get("id")==policies[0]["id"]
    resources,rm=_cb_paged_authz(root,pref,"/resource")
    assert rm["complete"]
    candidates=[]
    for resource in resources:
        attrs=resource.get("attributes") or {}
        if resource.get("name")==uid or any(
            uid in (value if isinstance(value,list) else [value])
            for value in attrs.values()
        ):
            candidates.append(resource)
    assert len(candidates)==1
    internal_id=candidates[0].get("_id") or candidates[0].get("id")
    fetched=root.call("GET",pref+"/resource/"+internal_id).json()
    assert (fetched.get("_id") or fetched.get("id"))==internal_id
    reverse=root.call("GET",pref+"/resource/"+internal_id+"/permissions").json()
    assert any(x.get("id")==perm_id for x in reverse)
    selector,selm=_cb_paged_authz(root,pref,"/permission",{
        "resourceType":"Users","resource":uid,"scope":"reset-password"})
    assert selm["complete"] and any(x.get("id")==perm_id for x in selector)
    for other in excluded:
        excluded_rows,em=_cb_paged_authz(root,pref,"/permission",{
            "resourceType":"Users","resource":other,"scope":"reset-password"})
        assert em["complete"] and not any(
            x.get("id")==perm_id for x in excluded_rows)
    return token


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
    # Independent service with *real* target-B capability for adversarial
    # owner-A/target-B mismatch: this is NOT a fake 403-only FGAP case.
    b_token=provision_exact_user_service(root,other,"c1-b-only",[target])
    return SyntheticIdp(root, oidc, target, other, target_email, other_email,
                        old, other_old, scoped_token, b_token, e)


class ProductFixture:
    """Creates separate CI principals and untouched 003–008 Product schema."""

    def __init__(self):
        if os.environ.get("CI") != "true" or os.environ.get(
            "COMPOSE_PROJECT_NAME"
        ) != "authidpci":
            raise RuntimeError("RESET_FIXTURE_REQUIRES_ISOLATED_CI")
        self.root_password = credentials()["RESET_DB_PASSWORD"]
        self.roles = {}
        self.dbname = "product_ci"
        self.host = "product-db"
        self.trusted_issuer = None

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
                 "auth_reset_issuer", "auth_reset_executor", "auth_reset_lookup",
                 "auth_reset_idp_recorder")
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
                "007_scoped_reset_identity_lookup.up.sql",
                "008_durable_idp_attempt_outcome.up.sql",
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
                    'EXECUTE') AS issuer_executor,
                  has_function_privilege(
                    'auth_reset_lookup',
                    'auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)',
                    'EXECUTE') AS lookup_allowed,
                  has_function_privilege(
                    'auth_reset_lookup',
                    'auth_l1.execute_reset_c1(text,text,text,text,bigint,uuid)',
                    'EXECUTE') AS lookup_c1,
                  has_function_privilege(
                    'auth_reset_executor',
                    'auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)',
                    'EXECUTE') AS executor_lookup,
                  has_function_privilege(
                    'auth_reset_lookup',
                    'auth_l1.issue_reset_c1_authorization(text,text,text,text,bigint,bigint,text,integer)',
                    'EXECUTE') AS lookup_issuer,
                  has_table_privilege(
                    'auth_reset_lookup','auth_l1.identity_links','SELECT'
                  ) AS lookup_direct_identity,
                  has_function_privilege(
                    'auth_reset_idp_recorder',
                    'auth_l1.record_reset_idp_attempt(text,text,text,text,bigint,uuid,uuid)',
                    'EXECUTE') AS recorder_attempt,
                  has_function_privilege(
                    'auth_reset_idp_recorder',
                    'auth_l1.record_reset_idp_outcome(text,text,text,text,bigint,uuid,uuid,text,text)',
                    'EXECUTE') AS recorder_outcome,
                  has_function_privilege(
                    'auth_reset_idp_recorder',
                    'auth_l1.execute_reset_c1(text,text,text,text,bigint,uuid)',
                    'EXECUTE') AS recorder_c1,
                  has_function_privilege(
                    'auth_reset_idp_recorder',
                    'auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)',
                    'EXECUTE') AS recorder_lookup,
                  has_function_privilege(
                    'auth_reset_executor',
                    'auth_l1.record_reset_idp_attempt(text,text,text,text,bigint,uuid,uuid)',
                    'EXECUTE') AS executor_recorder,
                  has_function_privilege(
                    'auth_reset_lookup',
                    'auth_l1.record_reset_idp_attempt(text,text,text,text,bigint,uuid,uuid)',
                    'EXECUTE') AS lookup_recorder,
                  has_table_privilege(
                    'auth_reset_idp_recorder','auth_l1.reset_idp_attempts','SELECT'
                  ) AS recorder_direct_select,
                  has_table_privilege(
                    'auth_reset_idp_recorder','auth_l1.identity_links','SELECT'
                  ) AS recorder_identity_select
            """).fetchone()
            assert privileges == {
                "executor_yes": True,
                "executor_issuer": False,
                "issuer_executor": False,
                "lookup_allowed": True,
                "lookup_c1": False,
                "executor_lookup": False,
                "lookup_issuer": False,
                "lookup_direct_identity": False,
                "recorder_attempt": True,
                "recorder_outcome": True,
                "recorder_c1": False,
                "recorder_lookup": False,
                "executor_recorder": False,
                "lookup_recorder": False,
                "recorder_direct_select": False,
                "recorder_identity_select": False,
            }, "RESET_DB_ROLE_SPLIT_UNPROVEN"

    def owner(self, issuer: str, subject: str):
        # Identity is already present in the *actual* synthetic IdP realm.
        # Never invent an arbitrary subject to pair with a Keycloak user.
        assert issuer == self.trusted_issuer and isinstance(subject,str)
        with self.connect("auth_mapper") as conn:
            with conn.transaction():
                rec = auth_session.map_identity(conn, issuer, subject)
        # Only fixture preparation verifies this via privileged observation.
        # The adapter itself MUST use 007 with auth_reset_lookup, never admin.
        assert self.inspect_identity_fixture_only(rec["owner_id"]) == (issuer, subject)
        return rec["owner_id"]

    def inspect_identity_fixture_only(self, owner_id: str):
        # Privileged ONLY as fixture preparation/independent observation.
        # There is no use of this function in the Adapter's Resolve path.
        with self.admin() as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                rows=conn.execute(
                    "SELECT issuer,subject FROM auth_l1.identity_links "
                    "WHERE owner_id=%s",(owner_id,)).fetchall()
        assert len(rows)==1
        return rows[0]["issuer"],rows[0]["subject"]

    def lookup_scoped_for_test(self, bound, *, expected_issuer=None):
        # Independent test observation uses the real non-BYPASSRLS 007 role,
        # NOT the privileged ProductFixture.admin() connector.
        auth=bound.authorization
        with self.connect("auth_reset_lookup") as conn:
            return reset_identity_lookup.resolve(
                conn,auth.opaque,trusted_owner_id=auth.owner_id,
                kind=auth.kind,expected_epoch=auth.expected_epoch,
                expected_issuer=(self.trusted_issuer if expected_issuer is None
                                 else expected_issuer))

    def expire_authorization_fixture_only(self, bound):
        # Test-only fault injection, never an Adapter lookup fallback.
        with self.admin() as conn:
            with conn.transaction():
                conn.execute(
                    "UPDATE auth_l1.reset_c1_authorizations "
                    "SET expires_at=clock_timestamp()-interval '1 second' "
                    "WHERE authorization_sha256=%s",
                    (reset_c1.digest_authorization(
                        bound.authorization.opaque),))
        # This privileged mutation is forbidden in Product runtime.

    def attempt_rows(self, owner):
        # CI-only privileged observation; runtime Recorder itself lacks
        # direct table SELECT. Never print UUIDs, digests or raw JSON.
        with self.admin() as conn:
            return conn.execute(
                "SELECT attempt_id,operation_id,owner_id,revoked_epoch,"
                "outcome,outcome_code,recorded_at,finalized_at "
                "FROM auth_l1.reset_idp_attempts WHERE owner_id=%s",
                (owner,)).fetchall()

    def assert_no_network_role_transactions(self):
        # Called by transport observer AFTER committed Attempt, directly
        # before the Keycloak PUT. Neither Lookup, Executor nor Recorder
        # may hold open *any* primary PostgreSQL transaction at that point.
        with self.admin() as conn:
            n=conn.execute(
                "SELECT count(*) AS n FROM pg_stat_activity WHERE "
                "usename=ANY(%s) AND xact_start IS NOT NULL",
                (["auth_reset_lookup","auth_reset_executor",
                  "auth_reset_idp_recorder"],)).fetchone()["n"]
            assert n==0, "REMOTE_STARTED_WITH_OPEN_PRODUCT_DB_TX"

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
        if self.fault == "injected_5xx":
            self.responses.append(503)
            return 503
        if self.fault == "injected_401":
            self.responses.append(401)
            return 401
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
