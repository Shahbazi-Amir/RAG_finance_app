"""CR-API-03A real isolated CI: two PostgreSQL 17.11 stores + Keycloak 26.8.2.

Runs only in ephemeral egress-denied Docker network. This is an executable
*synthetic authority* proof, NOT recovery, C2, Product API or persistent IdP
outcome. Only case labels/HTTP statuses/booleans go to the sanitized artifact.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import sys
import threading

import jwt
import psycopg
from playwright.async_api import async_playwright

from reset_c1_fixture import (ProductFixture, ScopedIdpTransport,
                              setup_clean_idp, provision_exact_user_service)
from src.phase3.auth.reset_c1_dispatch import (
    BoundSyntheticReset, C1Rejected, dispatch_after_committed_c1,
)
from src.phase3.storage.postgres import auth_session
from controlled_reset import login
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
    "durable_idp_attempt_outcome": "NOT_IMPLEMENTED",
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


def observer(product, owner, cap, revoked_count=1):
    def check():
        # A SEPARATE committed read connection runs INSIDE the transport,
        # precisely before any Keycloak PUT can occur.
        expect_pending(product, owner, cap, revoked_count=revoked_count)
    return check


def transport(idp, *, token=None, **kw):
    return ScopedIdpTransport(
        idp.root.realm_name, token if token is not None else idp.scoped_token, **kw)


def once(product, bound, value, remote, **kw):
    # Authz/target hint comes from caller. The verified target only comes
    # from a separate trusted Product identity resolver, NOT the executor.
    return dispatch_after_committed_c1(
        lambda: product.connect("auth_reset_executor"),
        bound, value, remote,
        resolve_identity=product.resolve_identity,
        trusted_issuer=product.trusted_issuer, **kw,
    )


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
         issuer_executor_roles_separated=True)

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
                assert product.resolve_identity(owner) == (
                    idp.oidc["issuer"], idp.target_id)
                case("CR-A02A-real-oidc-subject-to-immutable-product-owner",
                     actual_signed_subject=True,
                     db_owner_mapping_exact=True, executor_has_no_mapping_read=True)

                # Critical adversarial test: service B has a genuinely
                # persisted target-B reset permission (tested separately),
                # but a synthetic authorization of owner A cannot choose
                # B as its IdP destination. This is NOT an FGAP denial.
                CURRENT = "CR-A02B-owner-a-target-b-mismatch-before-c1"
                ses1, ses2 = product.session(owner), product.session(owner)
                bound = product.authorization(owner,idp.target_id)
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
                next_password = "As8!" + secrets.token_urlsafe(19)
                remote = transport(idp, observer=observer(
                    product, owner, bound, revoked_count=2))

                def pause_before_commit():
                    entered.set()
                    assert release.wait(12), "CI_COMMIT_HOLD_NOT_RELEASED"

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(once, product, bound, next_password,
                                         remote,
                                         before_commit_hook=pause_before_commit)
                    try:
                        assert entered.wait(12), "C1_DID_NOT_REACH_PRE_COMMIT"
                        assert remote.calls == 0, "IDP_CALLED_BEFORE_C1_COMMIT"
                        assert_precommit(product, owner, bound,
                                         active_sessions=2)
                    finally:
                        release.set()
                    observed = future.result(timeout=22)
                assert observed.observed_result == "OBSERVED_REMOTE_SUCCESS"
                assert observed.remote_http_status == 204
                assert observed.persisted_remote_outcome is False
                assert remote.calls == 1 and remote.responses == [204]
                expect_pending(product, owner, bound, revoked_count=2)
                case("CR-A03-no-idp-before-real-c1-commit",
                     precommit_remote_attempts=0,
                     independent_observer_found_postcommit_state=True)
                case("CR-A04-c1-commit-then-one-real-idp-http-204",
                     product_epoch=1, revoked_sessions=2,
                     idp_http=204, transport_attempts=1,
                     persisted_remote_result=False)

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
                    product, race_owner, race))
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
                assert denied_remote.calls == 1 and denied_remote.responses == [403]
                expect_pending(product, foreign_owner, foreign)
                await login(idp.e, browser, cb, idp.oidc,
                            idp.other_email, foreign_pw, expect_failure=True)
                await login(idp.e, browser, cb, idp.oidc,
                            idp.other_email, idp.other_old)
                case("CR-A10-target-scoped-service-denies-unrelated-user",
                     idp_http=403, unrelated_old_password_accepted=True,
                     product_gate_closed=True)

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
                    assert fault.calls == 1
                    expect_pending(product, fail_owner, fail_cap)
                    case(label, injected_transport_failure=True,
                         one_attempt=True, durable_outcome=False,
                         product_gate_closed=True, no_auto_retry=True)

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
                assert lost_transport.calls == 1 and lost_transport.responses == [204]
                expect_pending(product, loss_owner, loss_cap)
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
                     zero_retries=True, durable_idp_result=False)

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
                    assert counts == gates
                    assert counts >= 6
                    columns = conn.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='auth_l1' AND "
                        "table_name IN ('reset_c1_authorizations',"
                        "'reset_c1_operations')",
                    ).fetchall()
                    names = {x["column_name"] for x in columns}
                    assert not names.intersection({
                        "password", "new_password", "raw_token", "recovery_link",
                        "email_url", "idp_response_body",
                    })
                case("CR-A16-only-c1-ledger-every-gate-closed",
                     persisted_active_ops=counts, pending_gates=gates,
                     persisted_idp_outcomes=0,
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

            finally:
                await browser.close()


def safe_report(ok):
    path = Path(os.environ.get("RESET_REPORT", "/nonexistent"))
    if os.environ.get("CI") != "true" or str(path) != "/evidence/reset_dispatch.json":
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "mission": "CR-API-03A",
        "source": "accepted Migration 006 + clean Keycloak FGAP V2",
        "overall": "PASS" if ok else "FAIL",
        "stage": CURRENT,
        "cases": STAGES,
        "facts": FACTS,
        "result_note": "observed IdP responses are NOT persistent outcomes",
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
