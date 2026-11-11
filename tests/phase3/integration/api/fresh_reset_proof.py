"""CR-IDP-02A — operation-bound OIDC *candidate* after real 008 outcome.

CI-only; never issues a product session or calls C2. Crucial limitation:
Keycloak's ordinary signed ID token does NOT attest that a particular
password was typed in a specific flow. Playwright input is independent
observer evidence, NOT server-verifiable factor evidence. Accordingly this
harness must always report FRESH_PASSWORD_SERVER_PROOF=NOT_PROVEN.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import secrets
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

import jwt
import psycopg
from playwright.async_api import expect

from support import (CALLBACK, CLIENT, authorization, challenge, exchange,
                     verifier, verify_id)
from src.phase3.storage.postgres import auth_session

class Denied(ValueError):
    pass


@dataclass(repr=False)
class Challenge:
    owner: str
    issuer: str
    subject: str
    operation: object
    attempt: object
    epoch: int
    mode: str
    state: str
    nonce: str
    pkce: str
    used: bool = False

    def __repr__(self):
        return "Challenge(<redacted>)"


class BoundServer:
    """Synthetic server-owned in-memory challenge store, NOT a product API."""

    def __init__(self, product, oidc, owner, auth, subject, operation, attempt, epoch):
        self.product = product
        self.oidc = oidc
        self.owner = owner
        self.auth = auth
        self.subject = subject
        self.operation = operation
        self.attempt = attempt
        self.epoch = epoch
        self.issuer = oidc["issuer"]
        self.issued = {}

    def eligible(self, *, owner=None, operation=None, attempt=None, epoch=None):
        o = self.owner if owner is None else owner
        op = self.operation if operation is None else operation
        at = self.attempt if attempt is None else attempt
        ep = self.epoch if epoch is None else epoch
        if o != self.owner or op != self.operation or at != self.attempt or ep != self.epoch:
            return False
        # Privileged READ here is explicitly an isolated test OBSERVER; no
        # privileged identity resolver is called in the Runtime Adapter.
        rows = self.product.attempt_rows(o)
        if len(rows) != 1:
            return False
        row = rows[0]
        if (row["operation_id"] != op or row["attempt_id"] != at
            or row["revoked_epoch"] != ep
            or row["outcome"] != "OBSERVED_REMOTE_SUCCESS"
            or row["outcome_code"] != "REMOTE_2XX_OBSERVED"
            or row["finalized_at"] is None):
            return False
        product = self.product.state(o, self.auth)
        if product["epoch"] != ep or product["gate"] != "pending_reauth":
            return False
        return self.product.inspect_identity_fixture_only(o) == (
            self.issuer, self.subject)

    def start(self, mode):
        if not self.eligible() or mode not in ("interactive", "silent"):
            raise Denied("INELIGIBLE_REAL_008_SCOPE")
        flow = Challenge(self.owner,self.issuer,self.subject,self.operation,
                         self.attempt,self.epoch,mode,
                         secrets.token_urlsafe(27),secrets.token_urlsafe(27),
                         verifier())
        self.issued[flow.state] = flow
        return flow

    def url(self, flow, *, downgrade_prompt=False):
        assert self.issued.get(flow.state) is flow
        prompt = flow.mode == "interactive" and not downgrade_prompt
        url = authorization(self.oidc,flow.nonce,flow.state,flow.pkce,
                            prompt_login=prompt)
        # Keycloak supports max_age=0 but it is NOT server evidence of a
        # fresh password. Old SSO can satisfy normal valid OIDC validation.
        if prompt:
            url += "&max_age=0"
        return url

    def examine(self, flow, callback, token):
        # All binding values come from this server-owned record, NEVER from
        # callback URL, browser supplied owner/op/attempt or ID-token extras.
        if self.issued.get(flow.state) is not flow or flow.used:
            raise Denied("CHALLENGE_REPLAY")
        if any(k in callback for k in (
            "owner", "owner_id", "operation", "operation_id", "attempt",
            "attempt_id", "epoch", "revoked_epoch"
        )):
            raise Denied("BROWSER_CANNOT_SELECT_OPERATION")
        if callback.get("state") != [flow.state] or "error" in callback:
            raise Denied("STATE_OR_ERROR")
        if len(callback.get("code",[])) != 1:
            raise Denied("NO_SINGLE_CODE")
        if flow.mode != "interactive":
            raise Denied("SILENT_SSO_NOT_FRESH_PASSWORD")
        if not self.eligible(owner=flow.owner,operation=flow.operation,
                             attempt=flow.attempt,epoch=flow.epoch):
            raise Denied("EPOCH_OR_ATTEMPT_MISMATCH")
        try:
            claims=verify_id(self.oidc,token,flow.nonce)
        except (AssertionError,jwt.PyJWTError,ValueError):
            raise Denied("SIGNED_OIDC_VALIDATION_DENIED") from None
        if claims.get("sub") != flow.subject or claims.get("iss") != flow.issuer:
            raise Denied("SIGNED_SUBJECT_MISMATCH")
        if not claims.get("email_verified"):
            raise Denied("UNVERIFIED_SUBJECT")
        # One-time candidate consumption is a server-side in-process CAS.
        # It does not consume a DB credential, C2 proof, or product Session.
        flow.used=True
        return "BOUND_OIDC_CANDIDATE_ONLY_NOT_FRESH_PASSWORD_PROOF"


async def _drive(ctx,cb,server,flow,email=None,password=None,*,old_bad=None,
                 downgrade_prompt=False):
    page=await ctx.new_page()
    try:
        await page.goto(server.url(flow,downgrade_prompt=downgrade_prompt),
                        wait_until="domcontentloaded",timeout=15000)
        if email is not None:
            await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
            await page.locator("#username").fill(email)
            await page.locator("#password").fill(password)
            await page.locator("#kc-login").click()
            if old_bad is True:
                await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
                await page.wait_for_load_state("networkidle")
                assert "/callback" not in urlsplit(page.url).path
                assert cb.server.inbox.empty(), "REJECTED_OLD_PASSWORD_GOT_CALLBACK"
                return None
        await page.wait_for_url(CALLBACK+"*",timeout=20000)
        return cb.next()
    finally:
        await page.close()


async def _get_tokens(server,params,flow):
    assert params.get("state")==[flow.state]
    assert len(params.get("code",[]))==1 and "error" not in params
    tokens=await asyncio.to_thread(exchange,server.oidc,
                                   params["code"][0],flow.pkce)
    return tokens


async def establish_pre_reset_sso(e, browser,cb,idp):
    """Old SSO browser is really authenticated BEFORE any C1/008 reset."""
    from controlled_reset import login
    ctx,tokens=await login(e,browser,cb,idp.oidc,idp.target_email,
                           idp.target_old,keep_context=True)
    # Real prompt=none code proves this browser has a usable old SSO.
    flow=Challenge("","","",None,None,0,"silent",
                   secrets.token_urlsafe(27),secrets.token_urlsafe(27),verifier())
    url=authorization(idp.oidc,flow.nonce,flow.state,flow.pkce,
                      prompt_login=False)
    page=await ctx.new_page()
    try:
        await page.goto(url)
        await page.wait_for_url(CALLBACK+"*",timeout=15000)
        params=cb.next()
        assert params.get("state")==[flow.state] and params.get("code")
        tokens=await asyncio.to_thread(exchange,idp.oidc,
                                       params["code"][0],flow.pkce)
        assert verify_id(idp.oidc,tokens["id_token"],flow.nonce)["sub"]==idp.target_id
    finally:
        await page.close()
    # Save a real pre-C1 callback, not an invented stale state.
    stale=Challenge("","","",None,None,0,"silent",
                    secrets.token_urlsafe(27),secrets.token_urlsafe(27),verifier())
    page=await ctx.new_page()
    try:
        await page.goto(authorization(idp.oidc,stale.nonce,stale.state,stale.pkce,
                                      prompt_login=False))
        await page.wait_for_url(CALLBACK+"*",timeout=15000)
        params=cb.next()
        assert params.get("state")==[stale.state] and params.get("code")
    finally:
        await page.close()
    return ctx,params


async def run_bound_case(e,browser,cb,idp,product,owner,bound,observed,
                         old_password,new_password,old_ctx,stale_callback,case):
    assert observed.persisted_remote_outcome and observed.committed_attempt
    server=BoundServer(product,idp.oidc,owner,bound,idp.target_id,
                       observed.operation_id,observed.attempt_id,
                       observed.revoked_epoch)
    assert server.eligible()
    assert not server.eligible(operation=uuid4())
    assert not server.eligible(attempt=uuid4())
    assert not server.eligible(owner="other-synthetic-owner")
    assert not server.eligible(epoch=observed.revoked_epoch+1)
    case("CR-F00-real-008-observed-success-licenses-only-challenge-start",
         exact_committed_008_outcome=True, scope_server_fixed=True,
         browser_supplied_identifiers_not_authority=True)

    # Old pre-C1 callback's state never selects today's operation.
    fresh=server.start("interactive")
    try:
        server.examine(fresh,stale_callback,"not-a-token")
        raise AssertionError("PRE_C1_CALLBACK_ACCEPTED")
    except Denied:
        pass
    assert not fresh.used
    case("CR-F01-old-pre-c1-callback-rejected-before-exchange",
         genuine_pre_reset_callback=True, no_state_reuse=True)

    # Real prompt=none SSO in the OLD browser, including a downgrade of a
    # *server-issued interactive* request, must not count as password factor.
    silent=server.start("silent")
    page=await old_ctx.new_page()
    try:
        await page.goto(server.url(silent))
        await page.wait_for_url(CALLBACK+"*",timeout=15000)
        p=cb.next()
        assert p.get("state")==[silent.state]
        if p.get("code"):
            t=await _get_tokens(server,p,silent)
            assert verify_id(idp.oidc,t["id_token"],silent.nonce)["sub"]==idp.target_id
            try:
                server.examine(silent,p,t["id_token"])
                raise AssertionError("OLD_SSO_ACCEPTED_AS_PASSWORD")
            except Denied:
                pass
        else:
            assert p.get("error") in (["login_required"],["interaction_required"])
    finally:
        await page.close()
    case("CR-F02-old-browser-sso-not-valid-password-evidence",
         old_sso_real_before_reset=True, silent_code_not_fresh_proof=True,
         signed_jwt_alone_is_not_password_proof=True)

    # An attacker can edit the *prompt* in the OIDC authorize URI without
    # changing state/nonce/PKCE. If old SSO survives, a signed Code may
    # arrive under a server-assumed 'interactive' challenge. This is the
    # exact gap preventing a server-side fresh PASSWORD assurance verdict.
    downgrade=server.start("interactive")
    page=await old_ctx.new_page()
    downgrade_signed=False
    try:
        await page.goto(server.url(downgrade,downgrade_prompt=True))
        await page.wait_for_url(CALLBACK+"*",timeout=15000)
        p=cb.next()
        if p.get("code"):
            t=await _get_tokens(server,p,downgrade)
            downgrade_signed=verify_id(idp.oidc,t["id_token"],downgrade.nonce)[
                "sub"]==idp.target_id
        else:
            assert p.get("error") in (["login_required"],["interaction_required"])
    finally:
        await page.close()
    # Deliberately NEVER endorse this as an interactive password proof.
    case("CR-F03-prompt-url-downgrade-assurance-gap-measured",
         prompt_parameter_not_cryptographically_bound=True,
         downgrade_yielded_signed_code=downgrade_signed,
         server_cannot_infer_password_factor=True)

    # The old context above tests the adversarial pre-C1 SSO. Use a
    # *separate clean browser context* for actual password entry, so an old
    # IdP authentication-session redirect cannot be mistaken for the fresh
    # password form. Both carry the SAME server-bound operation snapshot.
    fresh_ctx,unused_page=await e.new_page(browser)
    await unused_page.close()
    print("CR-F04-bound-old-password-start: STAGE",flush=True)
    bad=server.start("interactive")
    await _drive(fresh_ctx,cb,server,bad,idp.target_email,old_password,old_bad=True)
    assert not bad.used
    case("CR-F04-bound-old-password-denied-no-callback",
         actual_old_password_rejected=True, no_bound_callback=True)

    print("CR-F05-bound-new-password-start: STAGE",flush=True)
    good=server.start("interactive")
    params=await _drive(fresh_ctx,cb,server,good,idp.target_email,new_password)
    token=await _get_tokens(server,params,good)
    id_token=token["id_token"]
    # These negative tests run before one-time Candidate consumption.
    for bad_params in (
        {**params,"state":[secrets.token_urlsafe(24)]},
        {k:v for k,v in params.items() if k!="state"},
        {**params,"operation_id":[str(uuid4())]},
        {**params,"attempt_id":[str(uuid4())]},
        {**params,"owner_id":["forged-owner"]},
        {**params,"epoch":["999"]},
    ):
        try:
            server.examine(good,bad_params,id_token)
            raise AssertionError("INVALID_CALLBACK_ACCEPTED")
        except Denied:
            pass
    assert not good.used
    for fake_token,nonce,kwargs in (
        (id_token, secrets.token_urlsafe(24),{}),
        (id_token,good.nonce,{"expected_issuer":idp.oidc["issuer"]+"/wrong"}),
        (id_token,good.nonce,{"expected_audience":"wrong-client"}),
        (id_token[:-4]+"AAAA",good.nonce,{}),
    ):
        try:
            verify_id(idp.oidc,fake_token,nonce,**kwargs)
        except (AssertionError,jwt.InvalidTokenError):
            pass
        else:
            raise AssertionError("SIGNED_CLAIM_NEGATIVE_ACCEPTED")
    claims=verify_id(idp.oidc,id_token,good.nonce)
    # auth_time/ACR/AMR only attest IdP metadata, not a server-verifiable
    # event saying which password was typed by which browser for this op.
    assert claims["sub"]==idp.target_id
    candidate=server.examine(good,params,id_token)
    assert candidate=="BOUND_OIDC_CANDIDATE_ONLY_NOT_FRESH_PASSWORD_PROOF"
    assert good.used
    try:
        server.examine(good,params,id_token)
        raise AssertionError("ONE_TIME_CHALLENGE_REPLAY")
    except Denied:
        pass
    assert (await asyncio.to_thread(exchange,idp.oidc,
                                    params["code"][0],good.pkce,400)) is None
    case("CR-F05-signed-state-nonce-issuer-audience-sub-candidate-bound",
         signed_oidc_verified=True, nonce_and_state_checked=True,
         exact_server_owner_operation_attempt_epoch=True,
         browser_metadata_rejected=True, one_time_candidate_consumed=True,
         old_sso_not_accepted_as_fresh_factor=True)
    case("CR-F06-auth-code-replay-denied-after-bound-exchange",
         oidc_code_one_time=True, server_challenge_one_time=True)

    # Distinct real user, real signed OIDC token: must NOT satisfy the
    # operation's original target subject, despite valid signature.
    wrong_user=server.start("interactive")
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(server.url(wrong_user))
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
        await e.fill_login(page,idp.other_email,idp.other_old)
        await page.wait_for_url(CALLBACK+"*",timeout=20000)
        wrong_callback=cb.next()
        wrong_tok=await _get_tokens(server,wrong_callback,wrong_user)
        assert verify_id(idp.oidc,wrong_tok["id_token"],wrong_user.nonce)[
            "sub"]==idp.other_id
        try:
            server.examine(wrong_user,wrong_callback,wrong_tok["id_token"])
            raise AssertionError("OTHER_USER_ACCEPTED_AS_RESET_OWNER")
        except Denied:
            pass
        assert not wrong_user.used
    finally:
        await ctx.close()
    case("CR-F07-other-valid-signed-account-rejected",
         different_real_keycloak_subject=True, owner_still_bound=True)

    # Test Keycloak's real PKCE enforcement on a separate valid Code: an
    # incorrect code_verifier is rejected by token endpoint, not by a stub.
    pkce_flow=server.start("interactive")
    print("CR-F08-real-pkce-negative-start: STAGE",flush=True)
    pkce_cb=await _drive(fresh_ctx,cb,server,pkce_flow,idp.target_email,new_password)
    bad_verifier=secrets.token_urlsafe(45)
    assert bad_verifier!=pkce_flow.pkce
    assert (await asyncio.to_thread(exchange,idp.oidc,
           pkce_cb["code"][0],bad_verifier,400)) is None
    case("CR-F08-actual-keycloak-pkce-wrong-verifier-rejected",
         real_code_wrong_verifier_http_400=True)
    await fresh_ctx.close()

    # Here OIDC binding is server-checkable but password factor is only
    # observed by Playwright. Deliberately no token is promoted to a C2 proof.
    assert product.state(owner,bound)["gate"]=="pending_reauth"
    case("CR-F09-no-c2-no-product-session-and-assurance-not_proven",
         local_bound_oidc_candidate=True, independent_browser_password_entry=True,
         verified_password_factor_from_server=False,
         fresh_password_assurance="NOT_PROVEN",gate_still_pending=True)
    return server


def reject_unqualified(server,product,owner,bound,operation,attempt,epoch):
    candidate=BoundServer(product,server.oidc,owner,bound,server.subject,
                          operation,attempt,epoch)
    assert candidate.eligible() is False
    try:
        candidate.start("interactive")
        raise AssertionError("NON_SUCCESS_008_START_ALLOWED")
    except Denied:
        pass
    return True


async def reject_stale_epoch_with_real_callback(e,browser,cb,idp,server,
                                                product,case,current_password):
    flow=server.start("interactive")
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(server.url(flow))
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
        await e.fill_login(page,idp.target_email,current_password)
        await page.wait_for_url(CALLBACK+"*",timeout=20000)
        params=cb.next()
        t=await _get_tokens(server,params,flow)
        assert verify_id(idp.oidc,t["id_token"],flow.nonce)["sub"]==server.subject
    finally:
        await ctx.close()
    with product.connect("auth_revoker") as conn:
        with conn.transaction():
            next_epoch=auth_session.revoke_all(conn,server.owner,server.epoch)
    assert next_epoch==server.epoch+1
    assert server.eligible() is False
    try:
        server.examine(flow,params,t["id_token"])
        raise AssertionError("EPOCH_DRIFT_ACCEPTED")
    except Denied:
        pass
    assert product.state(server.owner,server.auth)["gate"]=="pending_reauth"
    case("CR-F10-epoch-changed-after-real-callback-rejected",
         real_signed_callback_before_epoch_change=True,
         real_revoker_cas=True,current_epoch_mismatch_denied=True,
         no_gate_open=True)


def assert_no_c2_or_session(product,owner,auth):
    row=product.state(owner,auth)
    assert row["gate"]=="pending_reauth"
    assert row["sessions"].get("active",0)==0
    return True
