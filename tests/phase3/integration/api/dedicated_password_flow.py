"""CR-IDP-02B: standard Keycloak dedicated password-only client/flow.

CI-only privileged bootstrap/readback; no product migration, auth path, SPI,
extension, password-capturing proxy, C2, Gate reopening or new Session.
Sensitive identifiers, credentials, state, codes, JWTs and URLs stay in RAM.
Keycloak 26.8.2 Admin REST endpoints: /authentication/flows, /executions
and per-client authenticationFlowBindingOverrides.browser.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlencode, urlsplit
import secrets

import jwt
from playwright.async_api import expect

from support import BASE, CALLBACK, CLIENT, challenge, verifier, request
from fresh_reset_proof import Denied, Challenge

CLIENT_PROOF = "isolated-password-reauth-only"
FLOW_PROOF = "isolated-required-password-only"
PROVIDER = "auth-username-password-form"
PKCE = "S256"

def _flow(root):
    rows=root.call("GET","/authentication/flows").json()
    matches=[f for f in rows if f.get("alias")==FLOW_PROOF]
    if len(matches)!=1:
        raise Denied("MISSING_REQUIRED_PASSWORD_FLOW")
    return matches[0]

def _executions(root):
    rows=root.call("GET",f"/authentication/flows/{FLOW_PROOF}/executions").json()
    if not isinstance(rows,list):
        raise Denied("BAD_AUTHENTICATION_FLOW_READBACK")
    return rows

def setup_dedicated(root, regular_client_id):
    """Bootstrap entirely inside disposable clean realm, not existing client."""
    normal_before=root.client(regular_client_id)
    normal_binding=(normal_before.get("authenticationFlowBindingOverrides") or {}).copy()
    root.call("POST","/authentication/flows",json={
        "alias":FLOW_PROOF, "description":"CI-only password factor required",
        "providerId":"basic-flow","topLevel":True,"builtIn":False,
    },expect_status=201)
    root.call("POST",f"/authentication/flows/{FLOW_PROOF}/executions/execution",
              json={"provider":PROVIDER},expect_status=201)
    ex=_executions(root)
    if len(ex)!=1 or ex[0].get("providerId")!=PROVIDER:
        raise Denied("UNRECOGNIZED_KEYCLOAK_EXECUTION")
    root.call("PUT",f"/authentication/flows/{FLOW_PROOF}/executions",
              json={"id":ex[0]["id"],"requirement":"REQUIRED"},
              expect_status=204)
    f=_flow(root)
    if f.get("builtIn") is not False or f.get("topLevel") is not True:
        raise Denied("WRONG_FLOW_TYPE")
    root.call("POST","/clients",json={
        "clientId":CLIENT_PROOF,"enabled":True,"protocol":"openid-connect",
        "publicClient":True,"standardFlowEnabled":True,
        "directAccessGrantsEnabled":False,"implicitFlowEnabled":False,
        "serviceAccountsEnabled":False,"redirectUris":[CALLBACK],
        "webOrigins":[],"attributes":{"pkce.code.challenge.method":PKCE},
        "authenticationFlowBindingOverrides":{"browser":f["id"]},
    },expect_status=201)
    # Re-read *persisted* ClientRepresentation, not just POST payload.
    got=root.client(CLIENT_PROOF)
    if (got.get("authenticationFlowBindingOverrides") or {}).get("browser")!=f["id"]:
        root.call("PUT","/clients/"+got["id"],
                  json={"authenticationFlowBindingOverrides":{"browser":f["id"]}},
                  expect_status=204)
    verify_dedicated(root,normal_before)
    return normal_before

def verify_dedicated(root, normal_before):
    """CI-only privileged observer: fail closed on any ambiguous/drifted flow.

    Runtime wiring of a least-privileged config attestation is NOT supplied
    by this CI helper; this check is NOT a Product permission grant.
    """
    now=root.client(CLIENT_PROOF)
    flow=_flow(root)
    ex=_executions(root)
    normal_after=root.client(normal_before["clientId"])
    if normal_after!=normal_before:
        raise Denied("ORDINARY_OIDC_CLIENT_MUTATED")
    if len(ex)!=1:
        raise Denied("UNEXPECTED_ALTERNATE_AUTHENTICATION_EXECUTION")
    e=ex[0]
    if (e.get("providerId")!=PROVIDER or e.get("requirement")!="REQUIRED"
        or e.get("authenticationFlow") is True):
        raise Denied("PASSWORD_NOT_UNCONDITIONALLY_REQUIRED")
    if (flow.get("builtIn") is not False or flow.get("topLevel") is not True
        or flow.get("providerId")!="basic-flow"):
        raise Denied("UNAPPROVED_FLOW_REPRESENTATION")
    if (now.get("authenticationFlowBindingOverrides") or {}).get("browser")!=flow["id"]:
        raise Denied("CLIENT_FLOW_BINDING_DRIFT")
    if (now.get("publicClient") is not True or now.get("enabled") is not True
        or now.get("standardFlowEnabled") is not True
        or now.get("directAccessGrantsEnabled") is not False
        or now.get("implicitFlowEnabled") is not False
        or now.get("serviceAccountsEnabled") is not False
        or now.get("redirectUris")!=[CALLBACK]
        or (now.get("attributes") or {}).get("pkce.code.challenge.method")!=PKCE):
        raise Denied("DEDICATED_CLIENT_POLICY_DRIFT")
    return True


class DedicatedBoundVerifier:
    """RAM-only server-owned challenge, tied to real committed 008 rows."""

    def __init__(self, root, normal_before, bound_server):
        self.root=root
        self.normal_before=normal_before
        self.bound=bound_server
        self.issued={}

    def start(self):
        if not self.bound.eligible():
            raise Denied("008_OUTCOME_OR_EPOCH_NO_LONGER_ELIGIBLE")
        verify_dedicated(self.root,self.normal_before)
        f=Challenge(self.bound.owner,self.bound.issuer,self.bound.subject,
                    self.bound.operation,self.bound.attempt,self.bound.epoch,
                    "dedicated",secrets.token_urlsafe(28),
                    secrets.token_urlsafe(28),verifier())
        self.issued[f.state]=f
        return f

    def url(self, f, *, client=CLIENT_PROOF, prompt=None, max_age=None):
        assert self.issued.get(f.state) is f
        params={"client_id":client,"redirect_uri":CALLBACK,
                "response_type":"code","scope":"openid email profile",
                "state":f.state,"nonce":f.nonce,
                "code_challenge":challenge(f.pkce),
                "code_challenge_method":"S256"}
        if prompt is not None:
            params["prompt"]=prompt
        if max_age is not None:
            params["max_age"]=str(max_age)
        return self.bound.oidc["authorization_endpoint"]+"?"+urlencode(params)

    def check(self,f,callback,id_token):
        if self.issued.get(f.state) is not f or f.used:
            raise Denied("CHALLENGE_REPLAY_OR_WRONG_SERVER")
        if any(k in callback for k in (
            "owner","owner_id","operation","operation_id",
            "attempt","attempt_id","epoch","revoked_epoch")):
            raise Denied("BROWSER_SELECTED_SECURITY_SCOPE")
        if callback.get("state")!=[f.state] or len(callback.get("code",[]))!=1:
            raise Denied("INVALID_OR_OLD_CALLBACK")
        if not self.bound.eligible(owner=f.owner,operation=f.operation,
                                   attempt=f.attempt,epoch=f.epoch):
            raise Denied("STALE_RESET_OPERATION")
        # Keycloak's *actual live flow readback*, not a claim of the browser.
        verify_dedicated(self.root,self.normal_before)
        try:
            key=jwt.PyJWKClient(self.bound.oidc["jwks_uri"]).get_signing_key_from_jwt(id_token).key
            claims=jwt.decode(id_token,key,algorithms=["RS256"],
                audience=CLIENT_PROOF,issuer=f.issuer,
                options={"require":["iss","sub","aud","exp","iat","nonce"]})
        except (jwt.PyJWTError,ValueError):
            raise Denied("DEDICATED_CLIENT_SIGNATURE_AUDIENCE_DENIED") from None
        if claims.get("nonce")!=f.nonce or claims.get("sub")!=f.subject:
            raise Denied("DEDICATED_NONCE_OR_SUBJECT")
        if claims.get("email_verified") is not True:
            raise Denied("UNVERIFIED_IDENTITY")
        # This is a bounded CI-only assertion about dedicated-client execution.
        # No C2 or Product session is issued.
        f.used=True
        return claims

async def _navigate(ctx,url):
    page=await ctx.new_page()
    await page.goto(url,wait_until="domcontentloaded",timeout=15000)
    return page

async def _interactive(e,ctx,cb,server,flow,email,password,*,rejected=False):
    page=await _navigate(ctx,server.url(flow))
    try:
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=15000)
        await e.fill_login(page,email,password)
        if rejected:
            await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
            await page.wait_for_load_state("networkidle",timeout=12000)
            assert "/callback" not in urlsplit(page.url).path
            assert cb.server.inbox.empty(), "OLD_PASSWORD_GOT_DEDICATED_CODE"
            return None
        await page.wait_for_url(CALLBACK+"*",timeout=20000)
        return cb.next()
    finally:
        await page.close()

def _tokens(oidc,params,flow,client=CLIENT_PROOF,*,verifier_override=None):
    assert params.get("state")==[flow.state] and len(params.get("code",[]))==1
    resp=request("POST",oidc["token_endpoint"],data={
        "grant_type":"authorization_code","client_id":client,
        "redirect_uri":CALLBACK,"code":params["code"][0],
        "code_verifier":flow.pkce if verifier_override is None else verifier_override})
    return resp

async def _no_code_with_old_sso(old_ctx,cb,server,f,*,prompt=None,max_age=None):
    page=await _navigate(old_ctx,server.url(f,prompt=prompt,max_age=max_age))
    try:
        if "/callback" in urlsplit(page.url).path:
            result=cb.next()
            assert result.get("state")==[f.state]
            assert "code" not in result, "SSO_BYPASS_DEDICATED_PASSWORD_FLOW"
            assert result.get("error") in (["login_required"],["interaction_required"])
            return "oidc_denied"
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=10000)
        assert cb.server.inbox.empty()
        return "password_required"
    finally:
        await page.close()

async def exercise_transient_drift(idp,product,cb,old_ctx,server,case):
    """Real transient rebind AFTER challenge starts, restore BEFORE verification.

    Crucially all auth requests use the SAME dedicated client, state, nonce,
    S256 PKCE and original pre-reset SSO browser. No password is entered.
    The client configuration is restored regardless of test outcome.
    """
    root=idp.root
    # This check is the verifier's actual trusted CI readback at issuance.
    verify_dedicated(root,server.normal_before)
    f=server.start()
    original=root.client(CLIENT_PROOF)
    dedicated_id=_flow(root)["id"]
    assert original["authenticationFlowBindingOverrides"]["browser"]==dedicated_id
    default=[v for v in root.call("GET","/authentication/flows").json()
             if v.get("alias")=="browser"]
    assert len(default)==1 and default[0]["id"]!=dedicated_id
    # Inspect the actual server-side SSO alternative, not a guessed alias.
    browser_ex=root.call("GET","/authentication/flows/browser/executions").json()
    has_cookie=any(x.get("providerId")=="auth-cookie"
                   and x.get("requirement")=="ALTERNATIVE"
                   for x in browser_ex)
    assert has_cookie, "DEFAULT_BROWSER_SSO_COOKIE_NOT_VERIFIED"
    # The injected drift differs ONLY in the binding UUID. We do not alter
    # ordinary client, flow executions, realm policy or Product metadata.
    changed=dict(original)
    changed["authenticationFlowBindingOverrides"]={"browser":default[0]["id"]}
    request_callback=None
    signed_token=None
    exchanged=False
    no_password_entry=True
    mutated_readback=False
    unsafe_rejected_by_guard=False
    root.call("PUT","/clients/"+original["id"],json=changed,expect_status=204)
    try:
        during=root.client(CLIENT_PROOF)
        mutated_readback=(
            (during.get("authenticationFlowBindingOverrides") or {}).get("browser")
            ==default[0]["id"]
        )
        assert mutated_readback,"TRANSIENT_BINDING_NOT_PERSISTED"
        try:
            verify_dedicated(root,server.normal_before)
        except Denied:
            unsafe_rejected_by_guard=True
        assert unsafe_rejected_by_guard, "UNSAFE_BINDING_NOT_DETECTED_DURING_DRIFT"
        # There is NO second challenge. Use exactly the f issued while the
        # REQUIRED password-only flow was configured and read back.
        page=await _navigate(old_ctx,server.url(f,prompt="none"))
        try:
            await page.wait_for_url(CALLBACK+"*",timeout=15000)
            request_callback=cb.next()
            assert request_callback.get("state")==[f.state]
            if request_callback.get("code"):
                real=_tokens(idp.oidc,request_callback,f,client=CLIENT_PROOF)
                assert real.status_code==200,"TRANSIENT_REAL_CODE_EXCHANGE_DENIED"
                signed_token=real.json()["id_token"]  # RAM only, never logs
                exchanged=True
            else:
                assert request_callback.get("error") in (
                    ["login_required"],["interaction_required"])
        finally:
            await page.close()
    finally:
        # Restore and re-read BEFORE invoking any callback verifier.
        root.call("PUT","/clients/"+original["id"],json=original,
                  expect_status=204)
    assert verify_dedicated(root,server.normal_before)
    assert root.client(CLIENT_PROOF)==original,"RESTORED_CLIENT_DRIFT_REMAINS"
    assert not f.used and no_password_entry
    case("CR-T00-transient-client-flow-drift-bracketed-by-correct-readbacks",
         initial_readback_password_only=True,
         actual_intermediate_binding_cookie_flow=mutated_readback,
         default_browser_cookie_alternative_verified=has_cookie,
         unsafe_flow_detected_during_window=unsafe_rejected_by_guard,
         final_readback_restored=True,
         same_dedicated_client_and_challenge=True,
         no_browser_password_entry=True)

    if not exchanged:
        case("CR-T01-no-auth-code-during-transient-sso-flow",
             issued_dedicated_code=False,exchanged_real_code=False,
             transient_bypass_reproduced=False,
             verdict="NOT_REPRODUCED_IN_THIS_RUN")
        return {"issued":False,"accepted":False,
                "verdict":"NOT_REPRODUCED_IN_THIS_RUN"}

    # A signed token from the REAL target Keycloak is presented to the
    # UNCHANGED original verifier. Readbacks are currently both correct.
    accepted=False
    rejection="NONE"
    try:
        claims=server.check(f,request_callback,signed_token)
        assert claims["sub"]==idp.target_id
        accepted=True
    except Denied:
        rejection="ORIGINAL_VERIFIER_REJECTED"
    if accepted:
        # Preserve the existing single-use rule even under this exploit.
        try:
            server.check(f,request_callback,signed_token)
            raise AssertionError("TRANSIENT_CHALLENGE_REPLAY_ALLOWED")
        except Denied:
            pass
    case("CR-T01-real-dedicated-code-after-temporary-sso-flow",
         dedicated_code_issued=True,real_keycloak_exchange_http_200=True,
         token_not_fabricated=True,client_id_unchanged=True,
         same_state_nonce_pkce=True,no_password_entry=True,
         policy_restored_before_callback_verification=True)
    case("CR-T02-original-verifier-tested-after-restored-readback",
         original_verifier_accepted=accepted,
         original_verifier_rejected=not accepted,
         rejection_classification=rejection,
         transient_bypass_reproduced=accepted,
         finding="SECURITY_BYPASS_TRANSIENT_FLOW" if accepted else
                 "TRANSIENT_TOKEN_DENIED_BY_VERIFIER",
         no_c2=True,product_gate_still_closed=(
             product.state(server.bound.owner,server.bound.auth)["gate"]
             =="pending_reauth"))
    assert product.state(server.bound.owner,server.bound.auth)[
        "gate"]=="pending_reauth"
    assert product.state(server.bound.owner,server.bound.auth)[
        "sessions"].get("active",0)==0
    return {"issued":True,"accepted":accepted,
            "verdict":"SECURITY_BYPASS_REPRODUCED" if accepted else
                      "ORIGINAL_VERIFIER_DENIED"}


async def exercise(e,browser,cb,idp,product,bound_server,old_ctx,
                   normal_id_token,old_password,new_password,case):
    """Run after real 007→C1→008→Keycloak and prior 02A tests (unchanged)."""
    normal_before=setup_dedicated(idp.root,CLIENT)
    server=DedicatedBoundVerifier(idp.root,normal_before,bound_server)
    assert server.bound.eligible()
    case("CR-D00-real-keycloak-client-flow-execution-readback",
         dedicated_client=True, single_password_required=True,
         no_cookie_or_alternative=True, ordinary_client_unchanged=True,
         admin_only_used_by_ci_observer=True)
    # Browser ALREADY has an old SSO cookie from before the C1 reset.
    results={}
    for label,opts in (
        ("CR-D01-omitted-prompt",{}),
        ("CR-D02-prompt-none",{"prompt":"none"}),
        ("CR-D03-downgraded-max-age",{"max_age":100000}),
        ("CR-D04-prompt-none-and-max-age",{"prompt":"none","max_age":100000}),
    ):
        f=server.start()
        results[label]=await _no_code_with_old_sso(old_ctx,cb,server,f,**opts)
        assert not f.used
        case(label, old_sso_context=True,
             dedicated_code_from_sso=False,
             password_requirement_persisted=True)
    # Swapping to the regular client may issue a genuine SSO code, but
    # it cannot satisfy the server-issued DEDICATED challenge.
    swapped=server.start()
    page=await _navigate(old_ctx,server.url(swapped,client=CLIENT,prompt="none"))
    try:
        await page.wait_for_url(CALLBACK+"*",timeout=15000)
        p=cb.next()
        assert p.get("state")==[swapped.state] and p.get("code")
        ordinary=_tokens(idp.oidc,p,swapped,client=CLIENT)
        assert ordinary.status_code==200
        jwt_token=ordinary.json()["id_token"]
        try:
            server.check(swapped,p,jwt_token)
            raise AssertionError("SWAPPED_NORMAL_CLIENT_TOKEN_ACCEPTED")
        except Denied:
            pass
    finally:
        await page.close()
    case("CR-D05-client-swap-to-ordinary-sso-denied",
         regular_sso_code_observed=True,dedicated_audience_required=True,
         server_challenge_not_consumed=True)
    # A regular token minted at the old flow must never satisfy a dedicated
    # challenge even with an unmodified nonce and Keycloak RSA signature.
    nochange=server.start()
    forged={"state":[nochange.state],"code":["browser-selected-code"]}
    try:
        server.check(nochange,forged,normal_id_token)
        raise AssertionError("NORMAL_ID_TOKEN_ACCEPTED")
    except Denied:
        pass
    case("CR-D06-old-normal-client-token-denied",
         signed_normal_token_not_dedicated=True,scope_cannot_be_selected=True)

    # Crucially run this BEFORE the positive new-password login in this old
    # browser, so its SSO Cookie is truly from BEFORE Product C1/IdP reset.
    drift=await exercise_transient_drift(idp,product,cb,old_ctx,server,case)

    # Dedicated password: old credential must be rejected, new accepted,
    # even in the SAME OLD SSO browser. Separate challenge per attempt.
    bad=server.start()
    await _interactive(e,old_ctx,cb,server,bad,idp.target_email,old_password,rejected=True)
    assert not bad.used
    case("CR-D07-old-password-denied-with-old-sso",
         old_sso_not_bypassing_required_password=True,
         no_success_code_from_invalid_credential=True)

    good=server.start()
    callback=await _interactive(e,old_ctx,cb,server,good,idp.target_email,new_password)
    token_response=_tokens(idp.oidc,callback,good)
    assert token_response.status_code==200,"DEDICATED_CODE_EXCHANGE_DENIED"
    id_token=token_response.json()["id_token"]
    claims=server.check(good,callback,id_token)
    assert claims["sub"]==idp.target_id
    try:
        server.check(good,callback,id_token)
        raise AssertionError("DEDICATED_CHALLENGE_REPLAY")
    except Denied:
        pass
    code_replay=_tokens(idp.oidc,callback,good)
    assert code_replay.status_code==400
    case("CR-D08-new-password-signed-dedicated-code-bound",
         old_sso_browser=True,required_password_execution=True,
         dedicated_client_audience_verified=True,
         real_new_password_login=True,
         exact_owner_operation_attempt_epoch=True,
         nonce_state_pkce_signature=True,
         code_and_challenge_replay_denied=True)
    case("CR-D09-replay-callback-and-code-denied",
         once_only_server_state=True,oidc_code_replay_http_400=True)

    # Persisted config drift is detected again at callback, not just setup.
    f=server.start()
    altered=idp.root.client(CLIENT_PROOF)
    default_browser=[f for f in idp.root.call(
        "GET","/authentication/flows").json() if f.get("alias")=="browser"]
    assert len(default_browser)==1
    altered["authenticationFlowBindingOverrides"]={"browser":default_browser[0]["id"]}
    idp.root.call("PUT","/clients/"+altered["id"],json=altered,expect_status=204)
    try:
        try:
            verify_dedicated(idp.root,normal_before)
            raise AssertionError("CLIENT_DRIFT_NOT_DENIED")
        except Denied:
            pass
        try:
            server.check(f,{"state":[f.state],"code":["invalid"]},id_token)
            raise AssertionError("DRIFTED_CLIENT_ALLOWED")
        except Denied:
            pass
    finally:
        altered["authenticationFlowBindingOverrides"]={"browser":_flow(idp.root)["id"]}
        idp.root.call("PUT","/clients/"+altered["id"],json=altered,expect_status=204)
    assert verify_dedicated(idp.root,normal_before)
    case("CR-D10-real-client-binding-drift-fail-closed",
         real_admin_rest_config_drift=True,readback_rejected=True,
         restored_after_test=True,no_product_gate_change=True)

    # A new challenge is forbidden if 008 becomes stale or ambiguous.
    assert not server.bound.eligible(epoch=server.bound.epoch+1)
    assert product.state(bound_server.owner,bound_server.auth)["gate"]=="pending_reauth"
    case("CR-D11-no-c2-current-epoch-and-gate-still-closed",
         freshness_evidence="CONFIGURATION_PLUS_DEDICATED_AUDIENCE_BOUNDED_CI",
         keycloak_method_signed_per_operation=False,
         no_product_session_issued=True,no_c2=True,gate_closed=True)
    results["transient"] = drift
    return results
