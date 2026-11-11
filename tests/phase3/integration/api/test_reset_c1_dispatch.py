"""CR-API-03A real isolated CI: two PostgreSQL 17.11 stores + Keycloak 26.8.2.

Runs only in ephemeral egress-denied Docker network. This is an executable
*synthetic authority* proof, NOT recovery, C2, Product API or persistent IdP
outcome. Only case labels/HTTP statuses/booleans go to the sanitized artifact.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import sys
import threading
from uuid import uuid4

import jwt
import psycopg
from playwright.async_api import async_playwright

from reset_c1_fixture import (ProductFixture, ScopedIdpTransport,
                              setup_clean_idp, provision_exact_user_service)
from src.phase3.auth.reset_c1_dispatch import (
    BoundSyntheticReset, C1Rejected, dispatch_after_committed_c1,
)
from src.phase3.storage.postgres import auth_session, reset_idp_attempt
from controlled_reset import login
from fresh_reset_proof import (establish_pre_reset_sso, run_bound_case,
                               reject_unqualified, reject_stale_epoch_with_real_callback,
                               assert_no_c2_or_session)
from support import BASE, CLIENT, CallbackServer, request

STAGES = {}
FACTS = {
    "product_pg": "PostgreSQL 17.11 (disposable, separate from IdP)",
    "identity_pg": "PostgreSQL 17.11 (Keycloak only)",
    "keycloak": "26.8.2",
    "browser": "Playwright 1.64.1 Chromium",
    "authorization": "SYNTHETIC_INDEPENDENT_ISSUER_ROLE_ONLY",
    "c2": "NOT_IMPLEMENTED",
    "recovery": "NOT_IMPLEMENTED",
    "product_auth": "NOT_IMPLEMENTED",
    "durable_idp_attempt_outcome": "SYNTHETIC_008_LOCAL_OBSERVATION_ONLY",
    "fresh_auth_operation_bound_oidc_candidate": "PROVEN_BOUNDED_CI_ONLY",
    "fresh_password_server_verifiable_assurance": "NOT_PROVEN",
    "fresh_auth_c2_and_product_session": "NOT_IMPLEMENTED",
    "accepted": "NONE",
}
CURRENT = "bootstrap"


def case(name, **facts):
    STAGES[name] = "PASS"
    FACTS[name] = facts
    print(name + ": PASS", flush=True)


def expect_pending(product, owner, cap, *, revoked_count=1):
    s = product.state(owner, cap)
    assert s["epoch"] == 1 and s["gate"] == "pending_reauth"
    assert s["operations"] == 1 and s["pending"] and s["consumed"] is True
    assert s["sessions"].get("revoked", 0) == revoked_count
    assert s["sessions"].get("active", 0) == 0
    return s


def assert_precommit(product, owner, cap, active_sessions=1):
    s = product.state(owner, cap)
    assert s["epoch"] == 0 and s["gate"] == "open"
    assert s["operations"] == 0 and s["consumed"] is False
    assert s["sessions"].get("active", 0) == active_sessions


def observer(product, owner, cap, revoked_count=1, *, strict_no_transaction=True):
    def check():
        # A SEPARATE committed read connection runs INSIDE the transport,
        # precisely before any Keycloak PUT can occur.
        expect_pending(product, owner, cap, revoked_count=revoked_count)
        if strict_no_transaction:
            product.assert_no_network_role_transactions()
        # At transport entry the committed 008 intent is visible to a
        # *different* Product PG connection and is not finalized yet.
        rows=product.attempt_rows(owner)
        assert len(rows)==1 and rows[0]["outcome"] is None
    return check


def transport(idp, *, token=None, **kw):
    return ScopedIdpTransport(
        idp.root.realm_name, token if token is not None else idp.scoped_token, **kw)


def once(product, bound, value, remote, *,
         executor_connection_override=None, lookup_connection_override=None,
         recorder_connection_override=None,
         trusted_issuer_override=None, **kw):
    # The normal path uses only the non-BYPASSRLS 007 lookup principal.
    # Overrides are CI-only adversarial probes, never Product inputs.
    return dispatch_after_committed_c1(
        executor_connection_override or
        (lambda: product.connect("auth_reset_executor")),
        bound, value, remote,
        lookup_connection=(lookup_connection_override or
                           (lambda: product.connect("auth_reset_lookup"))),
        recorder_connection=(recorder_connection_override or
                             (lambda: product.connect("auth_reset_idp_recorder"))),
        trusted_issuer=(product.trusted_issuer if trusted_issuer_override is None
                        else trusted_issuer_override), **kw,
    )


def reject_without_executor(product,bound,remote,**kw):
    entered=[]
    def executor_forbidden():
        entered.append(True)
        raise AssertionError("EXECUTOR_REACHED_AFTER_INVALID_LOOKUP")
    try:
        once(product,bound,"Nt8!"+secrets.token_urlsafe(19),remote,
             executor_connection_override=executor_forbidden,**kw)
        raise AssertionError("INVALID_LOOKUP_WAS_ACCEPTED")
    except C1Rejected:
        pass
    assert not entered and remote.calls==0
    return True


def fresh_mapped_identity(product, idp, label):
    subject,email,old=idp.create_account(label)
    owner=product.owner(idp.oidc["issuer"], subject)
    return owner,subject,email,old


async def run():
    global CURRENT
    assert os.environ.get("CI") == "true"
    assert os.environ.get("COMPOSE_PROJECT_NAME") == "authidpci"
    assert os.environ.get("RESET_DISPATCH_MODE") == "isolated"
    product = ProductFixture()
    CURRENT = "CR-A00-product-database-versioned-migrations"
    product.bootstrap()
    case("CR-A00-two-separate-real-postgres-and-accepted-006-roles",
         separate_network_databases=True, migrations_unchanged=True,
         issuer_executor_roles_separated=True, migration008_unchanged=True,
         dedicated_recorder_privileges_checked=True)
    with product.connect("auth_reset_idp_recorder") as rc:
        assert rc.execute("SELECT current_user AS role").fetchone()[
            "role"]=="auth_reset_idp_recorder"
        try:
            rc.execute("SELECT 1 FROM auth_l1.reset_idp_attempts")
            raise AssertionError("RECORDER_DIRECT_READ_SHOULD_BE_DENIED")
        except psycopg.errors.InsufficientPrivilege:
            pass
    case("CR-C00-recorder-role-only-attempt-and-outcome",
         recorder_role_is_dedicated=True, direct_table_read_denied=True,
         no_lookup_or_executor_grants=True, no_privileged_fallback=True)

    CURRENT = "CR-A01-fresh-keycloak-and-target-scoped-fgap"
    idp = setup_clean_idp()
    # Source: actual HTTPS-equivalent *isolated* Keycloak OIDC discovery,
    # not user-supplied issuer or a synthetic product issuer.
    product.trusted_issuer = idp.oidc["issuer"]
    case("CR-A01-clean-realm-fgap-exact-readback",
         clean_bootstrap_before_users=True,
         no_manage_users_on_reset_service=True,
         scoped_readback=True)

    with CallbackServer() as cb:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                CURRENT = "CR-A02-normal-login-before-reset"
                signed_login = await login(idp.e, browser, cb, idp.oidc,
                                           idp.target_email, idp.target_old)
                await login(idp.e, browser, cb, idp.oidc,
                            idp.other_email, idp.other_old)
                case("CR-A02-genuine-oidc-password-login-before-c1",
                     old_target_accepted=True, unrelated_accepted=True)
                signer=jwt.PyJWKClient(idp.oidc["jwks_uri"]).get_signing_key_from_jwt(
                    signed_login["id_token"]).key
                verified_claims=jwt.decode(
                    signed_login["id_token"],signer,algorithms=["RS256"],
                    audience=CLIENT,issuer=idp.oidc["issuer"])
                assert verified_claims["sub"] == idp.target_id
                owner = product.owner(idp.oidc["issuer"], verified_claims["sub"])
                assert product.inspect_identity_fixture_only(owner) == (
                    idp.oidc["issuer"], idp.target_id)
                case("CR-A02A-real-oidc-subject-to-immutable-product-owner",
                     actual_signed_subject=True,
                     db_owner_mapping_exact=True, executor_has_no_mapping_read=True)
                CURRENT="CR-F-pre-reset-existing-sso-and-actual-stale-callback"
                old_sso_ctx,pre_reset_cb=await establish_pre_reset_sso(
                    idp.e,browser,cb,idp)
                case("CR-F-pre-reset-sso-and-stale-callback-captured",
                     genuine_keycloak_sso_before_reset=True,
                     callback_existed_before_c1=True, no_product_session_issued=True)

                # Critical adversarial test: service B has a genuinely
                # persisted target-B reset permission (tested separately),
                # but a synthetic authorization of owner A cannot choose
                # B as its IdP destination. This is NOT an FGAP denial.
                CURRENT = "CR-A02B-owner-a-target-b-mismatch-before-c1"
                ses1, ses2 = product.session(owner), product.session(owner)
                bound = product.authorization(owner,idp.target_id)
                CURRENT = "CR-B00-real-scoped-007-lookup-and-separated-roles"
                with product.connect("auth_reset_lookup") as lookup:
                    assert lookup.execute("SELECT current_user AS role").fetchone()[
                        "role"] == "auth_reset_lookup"
                    try:
                        lookup.execute("SELECT 1 FROM auth_l1.identity_links")
                        raise AssertionError("LOOKUP_DIRECT_SELECT_UNEXPECTED")
                    except psycopg.errors.InsufficientPrivilege:
                        pass
                assert product.lookup_scoped_for_test(bound)=={
                    "issuer":idp.oidc["issuer"],"subject":idp.target_id}
                assert_precommit(product,owner,bound,active_sessions=2)
                case("CR-B00-scoped-role-007-pair-without-state-mutation",
                     lookup_role_is_scoped=True, direct_table_read_denied=True,
                     executor_lookup_grant=False, lookup_c1_grant=False,
                     accepted_007_package_import=True,
                     no_privileged_connection_in_adapter=True)

                CURRENT = "CR-B01-invalid-proof-and-wrong-issuer-lookup-denials"
                invalid=BoundSyntheticReset(
                    replace(bound.authorization,opaque=secrets.token_urlsafe(32)),
                    idp.target_id)
                invalid_remote=transport(idp)
                reject_without_executor(product,invalid,invalid_remote)
                wrong_issuer_remote=transport(idp)
                reject_without_executor(
                    product,bound,wrong_issuer_remote,
                    trusted_issuer_override="https://wrong-issuer.invalid/realm")
                wrong_kind_remote=transport(idp)
                wrong_kind=BoundSyntheticReset(
                    replace(bound.authorization,kind="AUTHENTICATED_PASSWORD_CHANGE"),
                    idp.target_id)
                reject_without_executor(product,wrong_kind,wrong_kind_remote)
                assert invalid_remote.calls==wrong_issuer_remote.calls==wrong_kind_remote.calls==0
                assert_precommit(product,owner,bound,active_sessions=2)
                case("CR-B01-invalid-proof-kind-and-issuer-deny-before-c1",
                     invalid_proof_no_c1=True, wrong_kind_no_c1=True,
                     mismatched_server_issuer_no_c1=True,
                     all_network_calls_zero=True, no_admin_fallback=True)

                CURRENT = "CR-A02B-owner-a-target-b-mismatch-before-c1"
                mismatched = BoundSyntheticReset(
                    bound.authorization,idp.other_id)
                mismatch_remote = transport(
                    idp,token=idp.other_scoped_token)  # NO observer
                fake_password = "Mm8!" + secrets.token_urlsafe(19)
                try:
                    once(product,mismatched,fake_password,mismatch_remote)
                    raise AssertionError("OWNER_A_TARGET_B_DISPATCHED")
                except C1Rejected:
                    pass
                assert mismatch_remote.calls == 0
                assert_precommit(product, owner, bound, active_sessions=2)
                await login(idp.e,browser,cb,idp.oidc,
                            idp.other_email,fake_password,expect_failure=True)
                await login(idp.e,browser,cb,idp.oidc,
                            idp.other_email,idp.other_old)
                case("CR-A02B-owner-a-target-b-rejected-before-c1",
                     issuer_subject_owner_mismatch=True,
                     b_service_has_exact_fgAP_permission=True,
                     product_a_epoch_unchanged=True, remote_calls=0,
                     password_b_unchanged=True)

                # A real running C1 is held AFTER its SQL writes but BEFORE
                # COMMIT. A distinct connection still sees epoch 0, and no
                # HTTP Reset attempt has started. Then release and COMMIT.
                CURRENT = "CR-A03-before-commit-and-successful-idp-reset"
                entered, release = threading.Event(), threading.Event()
                attempt_entered, attempt_release = threading.Event(), threading.Event()
                next_password = "As8!" + secrets.token_urlsafe(19)
                remote = transport(idp, observer=observer(
                    product, owner, bound, revoked_count=2))

                def pause_before_commit():
                    entered.set()
                    assert release.wait(12), "CI_COMMIT_HOLD_NOT_RELEASED"

                def pause_before_attempt_commit():
                    attempt_entered.set()
                    assert attempt_release.wait(12), "CI_ATTEMPT_COMMIT_HOLD_NOT_RELEASED"

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(once, product, bound, next_password,
                                         remote,
                                         before_commit_hook=pause_before_commit,
                                         before_attempt_commit_hook=pause_before_attempt_commit)
                    try:
                        assert entered.wait(12), "C1_DID_NOT_REACH_PRE_COMMIT"
                        assert remote.calls == 0, "IDP_CALLED_BEFORE_C1_COMMIT"
                        assert_precommit(product, owner, bound,
                                         active_sessions=2)
                    finally:
                        release.set()
                    try:
                        assert attempt_entered.wait(12), "NO_RECORDER_PRECOMMIT"
                        assert remote.calls == 0, "IDP_CALLED_BEFORE_ATTEMPT_COMMIT"
                        expect_pending(product,owner,bound,revoked_count=2)
                        assert product.attempt_rows(owner)==[]
                    finally:
                        attempt_release.set()
                    observed = future.result(timeout=22)
                assert observed.observed_result == "OBSERVED_REMOTE_SUCCESS"
                assert observed.remote_http_status == 204
                assert observed.persisted_remote_outcome is True
                assert observed.committed_attempt is True
                assert observed.attempt_id is not None
                saved=product.attempt_rows(owner)
                assert len(saved)==1
                assert saved[0]["attempt_id"]==observed.attempt_id
                assert saved[0]["operation_id"]==observed.operation_id
                assert saved[0]["outcome"]==reset_idp_attempt.OBSERVED_REMOTE_SUCCESS
                assert saved[0]["outcome_code"]=="REMOTE_2XX_OBSERVED"
                assert remote.calls == 1 and remote.responses == [204]
                expect_pending(product, owner, bound, revoked_count=2)
                case("CR-A03-no-idp-before-real-c1-commit",
                     precommit_remote_attempts=0,
                     independent_observer_found_postcommit_state=True)
                case("CR-A04-c1-commit-then-one-real-idp-http-204",
                     product_epoch=1, revoked_sessions=2,
                     idp_http=204, transport_attempts=1,
                     persisted_remote_result=True, durable_intent=True)

                case("CR-C01-no-idp-before-separate-real-attempt-commit",
                     zero_remote_calls_while_uncommitted=True,
                     committed_c1_visible_before_attempt_commit=True,
                     inserted_attempt_invisible_precommit=True,
                     exactly_one_real_http_after_commits=True)

                CURRENT = "CR-A05-fenced-old-product-sessions"
                with product.connect("auth_sessions") as conn:
                    for sess in (ses1, ses2):
                        with conn.transaction():
                            assert auth_session.admit_session_fenced(
                                conn, sess.opaque, owner, 0, 0) is False
                        with conn.transaction():
                            assert auth_session.admit_session_fenced(
                                conn, sess.opaque, owner, 1, 0) is False
                case("CR-A05-both-old-product-session-admissions-rejected",
                     old_epoch_rejected=True, new_epoch_rejected=True,
                     reset_gate_closed=True)

                CURRENT = "CR-A06-credential-proof-of-actual-success"
                await login(idp.e, browser, cb, idp.oidc,
                            idp.target_email, idp.target_old,
                            expect_failure=True)
                await login(idp.e, browser, cb, idp.oidc,
                            idp.target_email, next_password)
                current_password = next_password
                case("CR-A06-old-credential-denied-new-accepted-real-oidc",
                     old_denied=True, new_accepted=True,
                     gate_still_pending=True)
                CURRENT="CR-F-operation-bound-post-008-oidc-candidate"
                fresh_server=await run_bound_case(
                    idp.e,browser,cb,idp,product,owner,bound,observed,
                    idp.target_old,next_password,old_sso_ctx,pre_reset_cb,case)
                assert assert_no_c2_or_session(product,owner,bound)

                # Simulated rollback aborts DB before commit; accepted C1
                # wrapper rolls back authority consumption and session bump.
                CURRENT = "CR-A07-injected-c1-rollback"
                rollback_owner,rb_uid,rb_email,rb_old = fresh_mapped_identity(
                    product,idp,"rollback")
                product.session(rollback_owner)
                rb = product.authorization(rollback_owner, rb_uid)
                bad_password = "Rb8!" + secrets.token_urlsafe(19)
                rb_remote = transport(idp)
                def abort_before_commit():
                    raise RuntimeError("CI_INJECTED_BEFORE_COMMIT_ABORT")
                try:
                    once(product, rb, bad_password, rb_remote,
                         before_commit_hook=abort_before_commit)
                    raise AssertionError("ROLLBACK_TEST_INCORRECTLY_COMMITTED")
                except C1Rejected:
                    pass
                assert rb_remote.calls == 0
                assert_precommit(product, rollback_owner, rb)
                await login(idp.e, browser, cb, idp.oidc,
                            rb_email, bad_password, expect_failure=True)
                await login(idp.e, browser, cb, idp.oidc,
                            rb_email, rb_old)
                case("CR-A07-real-pg-rollback-zero-idp-and-old-credential",
                     c1_rolled_back=True, remote_attempts=0,
                     original_credential_unchanged=True)

                # psycopg.Rollback is a BaseException intentionally SWALLOWED
                # by Transaction.__exit__; the Adapter itself must intercept
                # it INSIDE the transaction and deny network dispatch.
                CURRENT = "CR-A07B-real-psycopg-rollback-before-commit"
                soft_owner,soft_uid,soft_email,soft_old=fresh_mapped_identity(
                    product,idp,"softrollback")
                soft_session=product.session(soft_owner)
                soft_cap=product.authorization(soft_owner,soft_uid)
                soft_attempted="So8!"+secrets.token_urlsafe(19)
                soft_remote=transport(idp)  # no observer, no blocking fixture
                def absorbed_rollback():
                    raise psycopg.Rollback()
                try:
                    once(product,soft_cap,soft_attempted,soft_remote,
                         before_commit_hook=absorbed_rollback)
                    raise AssertionError("SWALLOWED_PG_ROLLBACK_DISPATCHED")
                except C1Rejected:
                    pass
                assert soft_remote.calls==0
                assert_precommit(product,soft_owner,soft_cap)
                with product.connect("auth_sessions") as admission:
                    with admission.transaction():
                        assert auth_session.admit_session_fenced(
                            admission,soft_session.opaque,soft_owner,0,0) is True
                await login(idp.e,browser,cb,idp.oidc,
                            soft_email,soft_attempted,expect_failure=True)
                await login(idp.e,browser,cb,idp.oidc,soft_email,soft_old)
                case("CR-A07B-real-psycopg-rollback-no-dispatch",
                     real_postgresql_rollback=True, transport_has_no_observer=True,
                     idp_attempts=0, c1_authorization_not_consumed=True,
                     epoch_unchanged=True, operations_zero=True,
                     original_session_still_accepted=True,
                     password_unchanged=True)

                CURRENT = "CR-A08-same-consumed-proof-no-repeat-dispatch"
                replay_remote = transport(idp)
                try:
                    once(product, bound, "No8!" + secrets.token_urlsafe(19),
                         replay_remote, operation_id=observed.operation_id)
                    raise AssertionError("CONSUMED_PROOF_REDISPATCHED")
                except C1Rejected:
                    pass
                assert replay_remote.calls == 0
                case("CR-A08-operation-id-and-consumed-proof-deny-redispatch",
                     redispatch_attempts=0, original_epoch_preserved=True)

                CURRENT = "CR-B02-consumed-authority-is-denied-at-lookup"
                consumed_remote=transport(idp)
                assert reject_without_executor(product,bound,consumed_remote)
                expect_pending(product,owner,bound,revoked_count=2)
                case("CR-B02-consumed-proof-lookup-denied-before-any-c1",
                     scoped_lookup_failed=True, executor_connections=0,
                     idp_calls=0, original_epoch_preserved=True)

                # Two actual executor connections race the SAME authority.
                CURRENT = "CR-A09-two-concurrent-executors"
                race_owner,race_uid,race_email,race_old=fresh_mapped_identity(
                    product,idp,"race")
                race_token=provision_exact_user_service(
                    idp.root,race_uid,"c1-race-svc",
                    [idp.target_id,idp.other_id])
                product.session(race_owner)
                race = product.authorization(race_owner, race_uid)
                race_password = "Cc8!" + secrets.token_urlsafe(19)
                race_remote = transport(idp,token=race_token,observer=observer(
                    product, race_owner, race,strict_no_transaction=False))
                def competing():
                    try:
                        return once(product, race, race_password, race_remote)
                    except C1Rejected:
                        return "C1_DENIED"
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(competing) for _ in range(2)]
                    results = [x.result(timeout=30) for x in futures]
                assert sum(getattr(x, "observed_result", "") ==
                           "OBSERVED_REMOTE_SUCCESS" for x in results) == 1
                assert results.count("C1_DENIED") == 1
                assert race_remote.calls == 1
                expect_pending(product, race_owner, race)
                await login(idp.e, browser, cb, idp.oidc,
                            race_email, race_old, expect_failure=True)
                await login(idp.e, browser, cb, idp.oidc,
                            race_email, race_password)
                case("CR-A09-real-concurrent-c1-only-one-dispatch",
                     successful_commit=1, denied_c1=1, remote_attempts=1)

                CURRENT = "CR-A10-fgap-denied-cross-account"
                # Direct IdP REST attempts are real, using ONLY the same
                # scoped runtime principal; never root/manage-users.
                foreign_owner = product.owner(
                    idp.oidc["issuer"],idp.other_id)
                product.session(foreign_owner)
                foreign = product.authorization(foreign_owner,idp.other_id)
                foreign_pw = "Df8!" + secrets.token_urlsafe(19)
                denied_remote = transport(idp, observer=observer(
                    product, foreign_owner, foreign))
                failed = once(product, foreign, foreign_pw, denied_remote)
                assert failed.observed_result == "REMOTE_REJECTED"
                assert failed.remote_http_status == 403
                assert failed.persisted_remote_outcome is True
                rejected_rows=product.attempt_rows(foreign_owner)
                assert len(rejected_rows)==1
                assert rejected_rows[0]["outcome"]==reset_idp_attempt.DEFINITIVE_REJECTION
                assert rejected_rows[0]["outcome_code"]=="POLICY_REJECTED"
                assert denied_remote.calls == 1 and denied_remote.responses == [403]
                expect_pending(product, foreign_owner, foreign)
                await login(idp.e, browser, cb, idp.oidc,
                            idp.other_email, foreign_pw, expect_failure=True)
                await login(idp.e, browser, cb, idp.oidc,
                            idp.other_email, idp.other_old)
                case("CR-A10-target-scoped-service-denies-unrelated-user",
                     idp_http=403, unrelated_old_password_accepted=True,
                     product_gate_closed=True, immutable_policy_rejection=True)

                CURRENT = "CR-A11-fgap-denied-profile-update"
                from controlled_reset import admin_request
                update = admin_request(
                    idp.scoped_token, "/users/" + idp.target_id,
                    realm_name=idp.root.realm_name,
                    json={"firstName": "ForbiddenMutation"},
                )
                assert update.status_code == 403
                assert idp.root.call(
                    "GET", "/users/" + idp.target_id
                ).json()["firstName"] == "Synthetic"
                case("CR-A11-fgap-unrelated-profile-rejected",
                     profile_http=403, profile_unchanged=True)

                # Inject timeout and disconnect at transport boundary;
                # no real Keycloak write is made in these two cases.
                for label, kind in (
                    ("CR-A12-timeout", "injected_timeout"),
                    ("CR-A13-disconnect", "injected_disconnect"),
                ):
                    CURRENT = label
                    fail_owner,fail_uid,_,_=fresh_mapped_identity(
                        product,idp,"timeout" if kind=="injected_timeout" else "disconnect")
                    product.session(fail_owner)
                    fail_cap = product.authorization(fail_owner,fail_uid)
                    fault = transport(idp, observer=observer(
                        product, fail_owner, fail_cap), fault=kind)
                    result = once(product, fail_cap,
                                  "Ut8!" + secrets.token_urlsafe(19), fault)
                    assert result.observed_result == "REMOTE_UNKNOWN"
                    assert result.remote_http_status is None
                    assert result.persisted_remote_outcome is True
                    row=product.attempt_rows(fail_owner)
                    assert len(row)==1 and row[0]["outcome"]==reset_idp_attempt.UNKNOWN
                    assert row[0]["outcome_code"]==(
                        "TIMEOUT" if kind=="injected_timeout" else "DISCONNECT")
                    assert fault.calls == 1
                    expect_pending(product, fail_owner, fail_cap)
                    case(label, injected_transport_failure=True,
                         one_attempt=True, durable_outcome=True,
                         recorded_outcome_unknown=True,
                         product_gate_closed=True, no_auto_retry=True)

                # The 007 lookup is a snapshot, not a lock: mutate Product
                # epoch AFTER successful lookup, before the 006 C1 call.
                CURRENT = "CR-B03-epoch-changes-between-lookup-and-c1"
                drift_owner,drift_uid,drift_email,drift_old=fresh_mapped_identity(
                    product,idp,"epochdrift")
                drift_session=product.session(drift_owner)
                drift_cap=product.authorization(drift_owner,drift_uid)
                assert product.lookup_scoped_for_test(drift_cap)["subject"]==drift_uid
                drift_remote=transport(idp)  # NO Observer hides the bug
                drift_hooks=[]
                def bump_epoch_after_lookup():
                    drift_hooks.append("lookup_completed")
                    with product.connect("auth_revoker") as c:
                        assert auth_session.revoke_all(c,drift_owner,0)==1
                try:
                    once(product,drift_cap,"Ew8!"+secrets.token_urlsafe(19),
                         drift_remote,after_lookup_hook=bump_epoch_after_lookup)
                    raise AssertionError("STALE_EPOCH_AFTER_LOOKUP_DISPATCHED")
                except C1Rejected:
                    pass
                assert drift_hooks==["lookup_completed"]
                assert drift_remote.calls==0
                drift_state=product.state(drift_owner,drift_cap)
                assert drift_state["epoch"]==1 and drift_state["gate"]=="pending_reauth"
                assert drift_state["operations"]==0 and not drift_state["consumed"]
                assert drift_state["sessions"]=={"revoked":1}
                case("CR-B03-epoch-drift-after-lookup-rejected-by-c1",
                     lookup_succeeded_before_mutation=True,
                     independent_revoke_changed_epoch=True,
                     c1_operation_absent=True, capability_not_consumed=True,
                     idp_calls=0, product_gate_pending=True)

                CURRENT = "CR-B04-expiry-between-lookup-and-c1"
                exp_owner,exp_uid,exp_email,exp_old=fresh_mapped_identity(
                    product,idp,"expdrift")
                product.session(exp_owner)
                exp_cap=product.authorization(exp_owner,exp_uid)
                assert product.lookup_scoped_for_test(exp_cap)["subject"]==exp_uid
                exp_remote=transport(idp)
                exp_hooks=[]
                def expire_after_lookup():
                    exp_hooks.append("lookup_completed")
                    product.expire_authorization_fixture_only(exp_cap)
                try:
                    once(product,exp_cap,"Ex8!"+secrets.token_urlsafe(19),
                         exp_remote,after_lookup_hook=expire_after_lookup)
                    raise AssertionError("EXPIRED_PROOF_AFTER_LOOKUP_DISPATCHED")
                except C1Rejected:
                    pass
                assert exp_hooks==["lookup_completed"] and exp_remote.calls==0
                assert_precommit(product,exp_owner,exp_cap)
                case("CR-B04-expired-after-lookup-rejected-by-independent-c1",
                     lookup_succeeded_before_expiry=True,
                     fixture_forced_expiry=True,
                     c1_operations_zero=True,
                     product_epoch_unchanged=True,
                     idp_calls=0)

                CURRENT = "CR-B05-wrong-db-role-must-not-fallback"
                wrongrole_owner,wrongrole_uid,_,_=fresh_mapped_identity(
                    product,idp,"wrongrole")
                product.session(wrongrole_owner)
                wrongrole_cap=product.authorization(wrongrole_owner,wrongrole_uid)
                wrongrole_remote=transport(idp)
                reject_without_executor(
                    product,wrongrole_cap,wrongrole_remote,
                    lookup_connection_override=lambda:product.connect(
                        "auth_reset_executor"))
                assert_precommit(product,wrongrole_owner,wrongrole_cap)
                case("CR-B05-executor-role-is-not-a-lookup-fallback",
                     attempted_wrong_role_denied=True,
                     executor_connections_after_lookup=0,
                     idp_calls=0, privileged_fallback_absent=True)

                # Actual commit followed by simulated process death BEFORE
                # calling IdP; next invocation cannot re-use C1 capability.
                CURRENT = "CR-A14-stop-after-commit-before-dispatch"
                stop_owner,stop_uid,_,_=fresh_mapped_identity(
                    product,idp,"aftercommit")
                product.session(stop_owner)
                stop_cap = product.authorization(stop_owner,stop_uid)
                stop_transport = transport(idp)
                def stop_process():
                    raise RuntimeError("CI_INJECTED_AFTER_COMMIT_STOP")
                try:
                    once(product, stop_cap, "St8!" + secrets.token_urlsafe(19),
                         stop_transport, after_commit_hook=stop_process)
                    raise AssertionError("POSTCOMMIT_STOP_NOT_TRIGGERED")
                except RuntimeError as exc:
                    assert str(exc) == "CI_INJECTED_AFTER_COMMIT_STOP"
                assert stop_transport.calls == 0
                expect_pending(product, stop_owner, stop_cap)
                try:
                    once(product, stop_cap, "No8!" + secrets.token_urlsafe(19),
                         stop_transport)
                    raise AssertionError("POSTCOMMIT_REPLAY_DISPATCHED")
                except C1Rejected:
                    pass
                assert stop_transport.calls == 0
                case("CR-A14-postcommit-crash-no-dispatch-no-replay",
                     commit_persisted=True, product_gate_closed=True,
                     dispatch_attempts=0, recovery_not_implemented=True)

                # Keycloak actually processes password change; the response
                # is deliberately discarded. Client MUST return UNKNOWN and
                # never infer rollback or issue another network attempt.
                CURRENT = "CR-A15-real-change-but-lost-response"
                loss_owner,loss_uid,loss_email,loss_old=fresh_mapped_identity(
                    product,idp,"lostreply")
                loss_token=provision_exact_user_service(
                    idp.root,loss_uid,"c1-loss-svc",
                    [idp.target_id,idp.other_id,race_uid])
                product.session(loss_owner)
                loss_cap = product.authorization(loss_owner,loss_uid)
                lost_pw = "Ls8!" + secrets.token_urlsafe(19)
                lost_transport = transport(idp,token=loss_token,observer=observer(
                    product, loss_owner, loss_cap),fault="discard_real_response")
                lost = once(product, loss_cap, lost_pw, lost_transport)
                assert lost.observed_result == "REMOTE_UNKNOWN"
                assert lost.remote_http_status is None
                assert lost.persisted_remote_outcome is True
                assert lost.committed_attempt is True
                assert lost_transport.calls == 1 and lost_transport.responses == [204]
                expect_pending(product, loss_owner, loss_cap)
                lost_rows=product.attempt_rows(loss_owner)
                assert len(lost_rows)==1
                assert lost_rows[0]["outcome"]==reset_idp_attempt.UNKNOWN
                assert lost_rows[0]["outcome_code"]=="DISCONNECT"
                await login(idp.e, browser, cb, idp.oidc,
                            loss_email, loss_old,
                            expect_failure=True)
                await login(idp.e, browser, cb, idp.oidc,
                            loss_email, lost_pw)
                replay_after_loss = transport(idp)
                try:
                    once(product, loss_cap,
                         "No8!" + secrets.token_urlsafe(19),
                         replay_after_loss, operation_id=lost.operation_id)
                    raise AssertionError("LOST_REPLY_REPLAY_DISPATCHED")
                except C1Rejected:
                    pass
                assert replay_after_loss.calls == 0
                case("CR-A15-actual-idp-changed-with-lost-response-still-unknown",
                     actual_remote_http=204,
                     adapter_outcome="REMOTE_UNKNOWN",
                     real_new_credential_accepted=True,
                     real_prior_credential_denied=True,
                     product_gate_closed=True,
                     zero_retries=True, durable_local_unknown=True,
                     durable_idp_password_proof=False)
                CURRENT="CR-F12-real-password-change-unknown-not-eligible"
                assert reject_unqualified(
                    fresh_server,product,loss_owner,loss_cap,
                    lost.operation_id,lost.attempt_id,lost.revoked_epoch)
                case("CR-F12-unknown-outcome-not-upgraded-by-correct-password",
                     actual_new_password_login_successful=True,
                     durable_record_unknown=True,
                     no_fresh_challenge_allowed=True,
                     no_gate_open=True)

                CURRENT = "CR-C02-real-rollback-of-attempt-sql-and-psycopg"
                for label,kind in (
                    ("CR-C02A-normal-attempt-rollback","ordinary"),
                    ("CR-C02B-swallowed-psycopg-rollback","swallowed"),
                ):
                    rb_owner,rb_uid,rb_email,rb_old=fresh_mapped_identity(
                        product,idp,"attemptnormal" if kind=="ordinary" else "attemptsoft")
                    product.session(rb_owner)
                    rb_cap=product.authorization(rb_owner,rb_uid)
                    rb_remote=transport(idp)  # NO observer or blocker
                    def roll_back_attempt():
                        if kind=="ordinary":
                            raise RuntimeError("CI_ATTEMPT_ROLLBACK_INJECTED")
                        raise psycopg.Rollback()
                    try:
                        once(product,rb_cap,"Ar8!"+secrets.token_urlsafe(18),
                             rb_remote,before_attempt_commit_hook=roll_back_attempt)
                        raise AssertionError("UNCOMMITTED_ATTEMPT_DISPATCHED")
                    except C1Rejected:
                        pass
                    assert rb_remote.calls==0
                    expect_pending(product,rb_owner,rb_cap)
                    assert product.attempt_rows(rb_owner)==[]
                    assert product.state(rb_owner,rb_cap)["consumed"] is True
                    case(label,one_c1_committed=True,real_attempt_rollback=True,
                         no_attempt_row=True,gate_closed=True,remote_calls=0,
                         no_second_attempt_authorized=True)

                CURRENT = "CR-C03-stop-after-attempt-commit-before-network"
                stop2_owner,stop2_uid,_,_=fresh_mapped_identity(
                    product,idp,"attemptstop")
                product.session(stop2_owner)
                stop2=product.authorization(stop2_owner,stop2_uid)
                stop2_remote=transport(idp)
                def stop_after_attempt():
                    raise RuntimeError("CI_STOP_AFTER_ATTEMPT_COMMIT")
                try:
                    once(product,stop2,"Aa8!"+secrets.token_urlsafe(19),
                         stop2_remote,after_attempt_commit_hook=stop_after_attempt)
                    raise AssertionError("POST_ATTEMPT_STOP_DISPATCHED")
                except C1Rejected:
                    pass
                assert stop2_remote.calls==0
                expect_pending(product,stop2_owner,stop2)
                stopped=product.attempt_rows(stop2_owner)
                assert len(stopped)==1
                assert stopped[0]["outcome"] is None and stopped[0]["finalized_at"] is None
                assert reject_without_executor(product,stop2,transport(idp))
                case("CR-C03-post-attempt-stop-keeps-no-outcome-no-retry",
                     attempt_committed=True, no_outcome_recorded=True,
                     zero_network_calls=True, same_authority_rejected=True)
                CURRENT="CR-F11-unfinalized-008-not-eligible"
                assert reject_unqualified(
                    fresh_server,product,stop2_owner,stop2,
                    stopped[0]["operation_id"],stopped[0]["attempt_id"],
                    stopped[0]["revoked_epoch"])
                case("CR-F11-unfinalized-attempt-never-eligible",
                     real_committed_attempt=True, outcome_absent=True,
                     zero_new_challenges=True, no_c2=True)

                CURRENT = "CR-C04-ambiguous-attempt-commit-ack"
                unclear_owner,unclear_uid,_,_=fresh_mapped_identity(
                    product,idp,"attemptunclear")
                product.session(unclear_owner)
                unclear=product.authorization(unclear_owner,unclear_uid)
                unclear_remote=transport(idp)
                def ambiguous_attempt_ack():
                    raise TimeoutError("CI_LOST_ATTEMPT_COMMIT_ACK")
                try:
                    once(product,unclear,"Au8!"+secrets.token_urlsafe(19),
                         unclear_remote,after_attempt_commit_hook=ambiguous_attempt_ack)
                    raise AssertionError("UNKNOWN_ATTEMPT_ACK_DISPATCHED")
                except C1Rejected:
                    pass
                assert unclear_remote.calls==0
                expect_pending(product,unclear_owner,unclear)
                unknown_ack=product.attempt_rows(unclear_owner)
                assert len(unknown_ack)==1 and unknown_ack[0]["outcome"] is None
                case("CR-C04-ambiguous-attempt-commit-no-dispatch",
                     simulated_ack_loss_after_real_commit=True,
                     durable_attempt_may_exist=True, idp_calls=0,
                     gate_closed=True, no_auto_retry=True)

                CURRENT = "CR-C05-actual-connection-close-before-attempt-commit"
                cut_owner,cut_uid,_,_=fresh_mapped_identity(
                    product,idp,"attemptcut")
                product.session(cut_owner)
                cut=product.authorization(cut_owner,cut_uid)
                cut_remote=transport(idp)
                recorder_conn=product.connect("auth_reset_idp_recorder")
                def sever_attempt_conn():
                    recorder_conn.close()   # actual PG session aborts TX
                try:
                    once(product,cut,"Ac8!"+secrets.token_urlsafe(19),
                         cut_remote,
                         recorder_connection_override=lambda:recorder_conn,
                         before_attempt_commit_hook=sever_attempt_conn)
                    raise AssertionError("CLOSED_CONNECTION_DISPATCHED")
                except C1Rejected:
                    pass
                assert cut_remote.calls==0 and product.attempt_rows(cut_owner)==[]
                expect_pending(product,cut_owner,cut)
                case("CR-C05-real-recorder-connection-failure-before-commit",
                     session_closed_mid_transaction=True,
                     attempt_not_committed=True, idp_calls=0,
                     c1_and_gate_still_committed=True)

                CURRENT = "CR-C06-outcome-commit-failure-after-real-idp-204"
                out_owner,out_uid,out_email,out_old=fresh_mapped_identity(
                    product,idp,"outcomefail")
                out_token=provision_exact_user_service(
                    idp.root,out_uid,"c1-outcome-fail-svc",
                    [idp.target_id,idp.other_id,race_uid])
                product.session(out_owner)
                out_cap=product.authorization(out_owner,out_uid)
                out_remote=transport(idp,token=out_token,
                                      observer=observer(product,out_owner,out_cap))
                out_new="Oc8!"+secrets.token_urlsafe(18)
                def fail_outcome_commit():
                    raise RuntimeError("CI_ROLLBACK_OUTCOME_AFTER_HTTP")
                observed_out=once(product,out_cap,out_new,out_remote,
                                  before_outcome_commit_hook=fail_outcome_commit)
                assert observed_out.observed_result=="OBSERVED_REMOTE_SUCCESS"
                assert observed_out.persisted_remote_outcome is False
                assert out_remote.calls==1
                saved_out=product.attempt_rows(out_owner)
                assert len(saved_out)==1 and saved_out[0]["outcome"] is None
                expect_pending(product,out_owner,out_cap)
                await login(idp.e,browser,cb,idp.oidc,
                            out_email,out_old,expect_failure=True)
                await login(idp.e,browser,cb,idp.oidc,out_email,out_new)
                assert reject_without_executor(product,out_cap,transport(idp))
                case("CR-C06-real-idp-write-outcome-rollback-not-durable",
                     real_remote_reset_http=204, observed_success=True,
                     local_outcome_not_committed=True,
                     old_password_denied=True,new_password_accepted=True,
                     no_redispatch=True,gate_closed=True)

                CURRENT = "CR-C07-lost-outcome-commit-ack"
                ack_owner,ack_uid,_,_=fresh_mapped_identity(
                    product,idp,"outcomeack")
                product.session(ack_owner)
                ack_cap=product.authorization(ack_owner,ack_uid)
                ack_remote=transport(idp,fault="injected_5xx")
                def lose_outcome_ack():
                    raise TimeoutError("CI_OUTCOME_ACK_NOT_OBSERVED")
                ack=once(product,ack_cap,"At8!"+secrets.token_urlsafe(19),
                         ack_remote,after_outcome_commit_hook=lose_outcome_ack)
                assert ack.observed_result=="REMOTE_UNKNOWN"
                assert ack.persisted_remote_outcome is False
                assert ack_remote.calls==1
                ack_rows=product.attempt_rows(ack_owner)
                assert len(ack_rows)==1 and ack_rows[0]["outcome"]==reset_idp_attempt.UNKNOWN
                assert ack_rows[0]["outcome_code"]=="REMOTE_5XX"
                expect_pending(product,ack_owner,ack_cap)
                case("CR-C07-lost-outcome-commit-ack-never-claims-persistence",
                     injected_503=True, simulated_ack_loss=True,
                     durable_flag_false_despite_row=True,
                     idp_calls=1, no_second_call=True,gate_closed=True)

                CURRENT = "CR-C08-outcome-psycopg-rollback-after-http"
                rbo_owner,rbo_uid,_,_=fresh_mapped_identity(
                    product,idp,"outcomerollback")
                product.session(rbo_owner)
                rbo_cap=product.authorization(rbo_owner,rbo_uid)
                rbo_remote=transport(idp,fault="injected_401")
                def rolled_back_outcome():
                    raise psycopg.Rollback()
                rbo=once(product,rbo_cap,"Ot8!"+secrets.token_urlsafe(19),
                         rbo_remote,before_outcome_commit_hook=rolled_back_outcome)
                assert rbo.observed_result=="REMOTE_UNKNOWN"
                assert rbo.persisted_remote_outcome is False
                rbo_rows=product.attempt_rows(rbo_owner)
                assert len(rbo_rows)==1 and rbo_rows[0]["outcome"] is None
                expect_pending(product,rbo_owner,rbo_cap)
                case("CR-C08-psycopg-outcome-rollback-no-durable-result",
                     unexpected_401_classified_unknown=True,
                     local_outcome_rollback=True, idp_calls=1,
                     no_retry=True,gate_closed=True)

                CURRENT = "CR-C09-recorder-role-mismatch-after-c1"
                role_owner,role_uid,_,_=fresh_mapped_identity(
                    product,idp,"recorderrole")
                product.session(role_owner)
                role_cap=product.authorization(role_owner,role_uid)
                role_remote=transport(idp)
                try:
                    once(product,role_cap,"Rr8!"+secrets.token_urlsafe(19),
                         role_remote,recorder_connection_override=lambda:
                         product.connect("auth_reset_executor"))
                    raise AssertionError("WRONG_RECORDER_ROLE_DISPATCHED")
                except C1Rejected:
                    pass
                assert role_remote.calls==0 and product.attempt_rows(role_owner)==[]
                expect_pending(product,role_owner,role_cap)
                case("CR-C09-no-executor-or-admin-recorder-fallback",
                     c1_committed=True, wrong_recorder_role_denied=True,
                     idp_calls=0, gate_closed=True)

                CURRENT = "CR-C10-duplicate-operation-attempt-denied"
                with product.connect("auth_reset_idp_recorder") as recorder:
                    try:
                        with recorder.transaction():
                            reset_idp_attempt.record_attempt(
                                recorder,bound.authorization.opaque,
                                owner_id=owner,kind=bound.authorization.kind,
                                revoked_epoch=observed.revoked_epoch,
                                operation_id=observed.operation_id,
                                attempt_id=uuid4())
                        raise AssertionError("SECOND_ATTEMPT_ACCEPTED")
                    except psycopg.errors.UniqueViolation:
                        pass
                assert len(product.attempt_rows(owner))==1
                assert remote.calls==1 and observed.committed_attempt is True
                case("CR-C10-immutable-one-attempt-unique-operation",
                     unique_operation_constraint_enforced=True,
                     attempt_rows=1, idp_calls=1,
                     existing_outcome_unchanged=True)

                CURRENT = "CR-A16-nonsecret-ledger-and-no-gate-opening"
                # The DB stores a one-way capability digest, operation UUID,
                # epoch/status; no password or action link. Raw secrets never
                # enter this query or any persistent evidence.
                with product.admin() as conn:
                    counts = conn.execute(
                        "SELECT count(*) AS n FROM auth_l1.reset_c1_operations "
                        "WHERE status='REVOKED_PENDING_IDP' AND active",
                    ).fetchone()["n"]
                    gates = conn.execute(
                        "SELECT count(*) AS n FROM auth_l1.owners "
                        "WHERE reset_gate='pending_reauth'",
                    ).fetchone()["n"]
                    # B03 intentionally exercised the *independent*
                    # accepted 003 auth_revoker (no 006 operation). Account
                    # for that real committed Gate without mislabeling it
                    # as a C1 operation or weakening the original invariant.
                    revoked_without_c1=conn.execute(
                        "SELECT count(*) AS n FROM auth_l1.owners o "
                        "WHERE o.reset_gate='pending_reauth' AND NOT EXISTS ("
                        "SELECT 1 FROM auth_l1.reset_c1_operations op "
                        "WHERE op.owner_id=o.owner_id AND op.active)"
                    ).fetchone()["n"]
                    assert revoked_without_c1==1
                    assert counts + revoked_without_c1 == gates
                    assert counts >= 6
                    assert product.state(drift_owner,drift_cap)[
                        "gate"]=="pending_reauth"
                    columns = conn.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='auth_l1' AND "
                        "table_name IN ('reset_c1_authorizations',"
                        "'reset_c1_operations','reset_idp_attempts')",
                    ).fetchall()
                    names = {x["column_name"] for x in columns}
                    assert not names.intersection({
                        "password", "new_password", "raw_token", "recovery_link",
                        "email_url", "idp_response_body",
                    })
                    totals=conn.execute(
                        "SELECT count(*) AS all_attempts,"
                        "count(*) FILTER (WHERE outcome IS NULL) AS unfinalized,"
                        "count(*) FILTER (WHERE outcome='UNKNOWN') AS unknowns,"
                        "count(*) FILTER (WHERE outcome='OBSERVED_REMOTE_SUCCESS') "
                        "AS observed_success,"
                        "count(*) FILTER (WHERE outcome='DEFINITIVE_REJECTION') "
                        "AS definitive "
                        "FROM auth_l1.reset_idp_attempts"
                    ).fetchone()
                    assert totals["all_attempts"] < counts
                    assert totals["unfinalized"] >= 4
                    assert totals["unknowns"] >= 3
                    assert totals["observed_success"] >= 2
                    assert totals["definitive"] >= 1
                    assert totals["all_attempts"] == (
                        totals["unfinalized"] + totals["unknowns"]
                        + totals["observed_success"] + totals["definitive"])
                case("CR-A16-only-c1-ledger-every-gate-closed",
                     persisted_active_ops=counts, pending_gates=gates,
                     independent_revoker_only_gates=revoked_without_c1,
                     all_pending_gates_accounted_for=True,
                     persisted_idp_outcomes_locally_recorded=True,
                     unfinished_attempts=totals["unfinalized"],
                     unknown_outcomes=totals["unknowns"],
                     observed_success_outcomes=totals["observed_success"],
                     definitive_rejections=totals["definitive"],
                     no_credential_payload_columns=True)

                # Positive capability control on B's SEPARATE scoped token,
                # after all C1 adapter barriers: this service really can
                # reset B. The owner-A→B mismatch refusal was therefore
                # independent of FGAP's target-access decision.
                CURRENT = "CR-A17-genuine-fgap-b-allowed-control"
                control_password="Bp8!"+secrets.token_urlsafe(19)
                b_transport=transport(idp,token=idp.other_scoped_token)
                assert b_transport.send_reset(
                    idp.other_id,control_password)==204
                assert b_transport.calls==1
                await login(idp.e,browser,cb,idp.oidc,
                            idp.other_email,idp.other_old,expect_failure=True)
                await login(idp.e,browser,cb,idp.oidc,
                            idp.other_email,control_password)
                case("CR-A17-fgap-b-service-actually-can-reset-b",
                     independent_b_scoped_http=204,
                     b_old_password_denied=True,
                     b_new_password_accepted=True,
                     b_service_has_no_broad_role=True,
                     negative_owner_mismatch_was_pre_c1=True)
                CURRENT="CR-F10-real-epoch-change-after-bound-oidc"
                try:
                    await reject_stale_epoch_with_real_callback(
                        idp.e,browser,cb,idp,fresh_server,product,case,
                        next_password)
                finally:
                    await old_sso_ctx.close()
                assert assert_no_c2_or_session(product,owner,bound)

            finally:
                await browser.close()


def safe_report(ok):
    path = Path(os.environ.get("RESET_REPORT", "/nonexistent"))
    if os.environ.get("CI") != "true" or str(path) != "/evidence/reset_dispatch.json":
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "mission": "CR-IDP-02A",
        "source": "accepted real 007-006-008-IdP sequence then server-bound OIDC challenge; prior reset regressions preserved",
        "overall": "PASS" if ok else "FAIL",
        "stage": CURRENT,
        "cases": STAGES,
        "facts": FACTS,
        "result_note": "Bound server OIDC candidate only; fresh password assurance NOT_PROVEN without IdP-signed password-factor evidence. No C2 or Product Session.",
        "fresh_auth_verdict": "NOT_PROVEN",
        "operation_bound_oidc_candidate": "PROVEN_BOUNDED_CI_ONLY",
    }, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        STAGES[CURRENT] = "FAIL"
        safe_report(False)
        # Suppress exception text and traceback: requests and Playwright may
        # contain sensitive callback URLs, client secrets or raw credentials.
        print("RESET_C1_DISPATCH_NOT_PROVEN stage=" + CURRENT +
              " category=" + type(e).__name__, flush=True)
        sys.exit(1)
    safe_report(True)
    print("C1_BEFORE_IDP_DISPATCH_PROVEN_BOUNDED_CI_ONLY", flush=True)
