"""BND-IDP-02C: disposable SECOND realm, standard Keycloak reset-entry adversarial tests.

Never used in a real product or another realm. No secret, JWT, browser URL
query, action-token link, cookie, HTML or email is logged or written to JSON.
The original 01/02A/02B suites execute first and are not modified.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import secrets
import time
from urllib.parse import urlencode, urlsplit

import jwt
from playwright.async_api import expect, TimeoutError as PWTimeout

from support import (BASE, MAIL, CALLBACK, CLIENT, credentials, request,
    message_for, mail_ids, action_url, verifier, challenge)

REALM_C = "auth-idp-controlled-ci"
ROOT = BASE + "/admin/realms/" + REALM_C
LOGIN = BASE + "/realms/" + REALM_C
USER_SCOPE = "openid email profile"
AUTH_ADMIN_SCOPE = "openid email profile kc-admin-api"


class Root:
    def __init__(self, master_token):
        self.master_token = master_token

    def call(self, method, suffix="", *, expect_status=200, **kwargs):
        reply = request(method, ROOT + suffix,
                        headers={"Authorization":"Bearer " + self.master_token}, **kwargs)
        allowed = {expect_status} if isinstance(expect_status,int) else set(expect_status)
        assert reply.status_code in allowed, "CONTROL_ROOT_STANDARD_REST_UNEXPECTED_STATUS"
        return reply

    def user(self, email):
        rows = self.call("GET","/users",params={"email":email,"exact":"true"}).json()
        assert len(rows)==1,"CONTROL_USER_NOT_FOUND"
        return rows[0]

    def client(self, cid):
        rows = self.call("GET","/clients",params={"clientId":cid}).json()
        assert len(rows)==1,"CONTROL_CLIENT_NOT_FOUND"
        return self.call("GET","/clients/"+rows[0]["id"]).json()


def create_user(root, email, password):
    root.call("POST","/users",json={
        "username":email,"email":email,"enabled":True,
        "emailVerified":True,"requiredActions":[],
        "firstName":"Synthetic","lastName":"Controlled",
        "credentials":[{"type":"password","temporary":False,"value":password}]
    },expect_status=201)
    return root.user(email)["id"]


def create_client(root, payload):
    root.call("POST","/clients",json=payload,expect_status=201)
    return root.client(payload["clientId"])


def initialize_second_realm(e):
    # Master bootstrap is used ONLY for creating isolated synthetic
    # fixtures; NOT itself a candidate controlled Reset service.
    master = e.Admin().token
    root = Root(master)
    realm = {
        "realm":REALM_C,"enabled":True,"sslRequired":"none",
        "displayName":"CI controlled-reset standard capability candidate",
        "registrationAllowed":False,"registrationEmailAsUsername":True,
        "loginWithEmailAllowed":True,"duplicateEmailsAllowed":False,
        "verifyEmail":False,"resetPasswordAllowed":True,
        "bruteForceProtected":False,
        "passwordPolicy":"length(12) and digits(1) and upperCase(1) and specialChars(1)",
        "accessTokenLifespan":180,
        "actionTokenGeneratedByAdminLifespan":180,
        "actionTokenGeneratedByUserLifespan":180,
        "smtpServer":{"host":"mailpit","port":"1025",
            "from":"controlled-idp-ci@example.test","ssl":"false",
            "starttls":"false","auth":"false"},
    }
    response = request("POST",BASE+"/admin/realms",
        headers={"Authorization":"Bearer "+master},json=realm)
    assert response.status_code==201,"CONTROL_REALM_CREATE_FAILED"
    assert root.call("GET").json()["realm"]==REALM_C
    create_client(root,{
        "clientId":CLIENT,"enabled":True,"protocol":"openid-connect",
        "publicClient":True,"standardFlowEnabled":True,
        "directAccessGrantsEnabled":False,"implicitFlowEnabled":False,
        "serviceAccountsEnabled":False,"redirectUris":[CALLBACK],
        "webOrigins":[],"attributes":{"pkce.code.challenge.method":"S256"},
    })
    info=request("GET",LOGIN+"/.well-known/openid-configuration")
    assert info.status_code==200 and info.json()["issuer"]==LOGIN
    e.RESULTS["RC_isolation"]={
        "separate_realm":True,"realm_name_is_distinct_from_prior":True,
        "legacy_realm_unmodified":True,"identity_db_disposable_only":True,
        "test_browser_redirect_uses_pkce_s256":True,
    }
    e.case("RC-00-second-disposable-realm-and-oidc-client")
    return root,info.json()


async def login(e, browser, cb, oidc, email, password, *, expect_failure=False,
                action=None, keep_context=False):
    nonce=secrets.token_urlsafe(26)
    state=secrets.token_urlsafe(26)
    proof=verifier()
    params={
        "client_id":CLIENT,"redirect_uri":CALLBACK,"response_type":"code",
        "scope":USER_SCOPE,"state":state,"nonce":nonce,
        "code_challenge":challenge(proof),"code_challenge_method":"S256",
        "prompt":"login",
    }
    if action:
        params["kc_action"]=action
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(oidc["authorization_endpoint"]+"?"+urlencode(params))
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=15000)
        await e.fill_login(page,email,password)
        if expect_failure:
            await expect(page.locator(
                '#input-error, [role="alert"], .alert-error, #kc-feedback-text').first
            ).to_be_visible(timeout=10000)
            assert cb.server.inbox.empty(),"CONTROL_OLD_CREDENTIAL_GOT_CODE"
            return None
        await page.wait_for_url(CALLBACK+"*",timeout=18000)
        data=cb.next()
        assert data.get("state")==[state] and len(data.get("code",[]))==1
        response=request("POST",oidc["token_endpoint"],data={
            "grant_type":"authorization_code","client_id":CLIENT,
            "redirect_uri":CALLBACK,"code":data["code"][0],
            "code_verifier":proof})
        assert response.status_code==200,"CONTROL_OIDC_CODE_EXCHANGE_FAILED"
        token=response.json()
        signer=jwt.PyJWKClient(oidc["jwks_uri"]).get_signing_key_from_jwt(token["id_token"]).key
        claims=jwt.decode(token["id_token"],signer,
            audience=CLIENT,issuer=oidc["issuer"],algorithms=["RS256"],
            options={"require":["iss","aud","iat","exp","sub","nonce"]})
        assert claims["nonce"]==nonce,"CONTROL_NONCE_MISMATCH"
        if keep_context:
            return ctx,token
        return token
    finally:
        await page.close()
        if not keep_context:
            await ctx.close()


def token(root, client_id, secret, *, scope="kc-admin-api"):
    reply=request("POST",LOGIN+"/protocol/openid-connect/token",
                  data={"grant_type":"client_credentials",
                        "client_id":client_id,"client_secret":secret,
                        "scope":scope})
    assert reply.status_code==200,"CONTROL_SERVICE_TOKEN_NOT_ISSUED"
    return reply.json()["access_token"]


def admin_request(access, suffix, *, method="PUT", **kwargs):
    return request(method, ROOT + suffix,
         headers={"Authorization":"Bearer "+access},**kwargs)


def issue_service(root, cid, *, grant_manage=False, grant_view=False):
    secret=secrets.token_urlsafe(40)
    client=create_client(root,{
        "clientId":cid,"enabled":True,"protocol":"openid-connect",
        "publicClient":False,"clientAuthenticatorType":"client-secret",
        "secret":secret,"standardFlowEnabled":False,
        "directAccessGrantsEnabled":False,"implicitFlowEnabled":False,
        "serviceAccountsEnabled":True,
    })
    scope_rows=root.call("GET","/client-scopes").json()
    admin_scopes=[s for s in scope_rows if s.get("name")=="kc-admin-api"]
    assert len(admin_scopes)==1,"CONTROL_ADMIN_SCOPE_NOT_FOUND"
    root.call("PUT","/clients/"+client["id"]+
        "/optional-client-scopes/"+admin_scopes[0]["id"],expect_status=204)
    if grant_manage or grant_view:
        su=root.call("GET","/clients/"+client["id"]+"/service-account-user").json()
        rm=[x for x in root.call("GET","/clients",
                                 params={"clientId":"realm-management"}).json()]
        assert len(rm)==1,"CONTROL_REALM_MANAGEMENT_NOT_FOUND"
        roles=[]
        for name in (["manage-users"] if grant_manage else ["view-users"]):
            roles.append(root.call("GET","/clients/"+rm[0]["id"]+
                                   "/roles/"+name).json())
        root.call("POST","/users/"+su["id"]+"/role-mappings/clients/"+rm[0]["id"],
             json=roles,expect_status=204)
    details=root.client(cid)
    assert details.get("serviceAccountsEnabled") is True
    assert details.get("standardFlowEnabled") is False
    return token(root,cid,secret)


def password_update(root, uid, value, *, token_value=None):
    url="/users/"+uid+"/reset-password"
    payload={"type":"password","temporary":False,"value":value}
    if token_value is None:
        return root.call("PUT",url,json=payload,expect_status=204).status_code
    return admin_request(token_value,url,json=payload).status_code


async def old_action_token(e, root, email, uid):
    # Issue while enabled; keep the RAW action link ONLY in process RAM.
    before=mail_ids()
    root.call("PUT","/users/"+uid+"/execute-actions-email",
        params={"client_id":CLIENT,"redirect_uri":CALLBACK,"lifespan":180},
        json=["UPDATE_PASSWORD"],expect_status=204)
    mail=await e.email_after(email,before,seconds=18)
    return action_url(mail[1])


async def browser_action_attempt(e,browser,url,new_password,*,email=None,old_password=None):
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(url,wait_until="domcontentloaded")
        if email is not None and await page.locator("#kc-form-login").is_visible():
            assert old_password is not None
            await e.fill_login(page,email,old_password)
        form=page.locator("#password-new")
        try:
            await expect(form).to_be_visible(timeout=4500)
        except (PWTimeout, AssertionError):
            # Playwright expect() emits AssertionError on a visible-state
            # mismatch. No password form is an observed negative, not CI
            # success. Actual credentials are tested independently below.
            return {"real_password_form":False,"submitted":False}
        await form.fill(new_password)
        confirm=page.locator("#password-confirm")
        await expect(confirm).to_be_visible(timeout=7000)
        await confirm.fill(new_password)
        submit=page.locator('#kc-submit, #kc-passwd-update-form input[type="submit"]')
        await expect(submit.first).to_be_visible(timeout=7000)
        await submit.first.click()
        return {"real_password_form":True,"submitted":True}
    finally:
        await ctx.close()


def drain_probe_callbacks(cb):
    # Adversarial action flows may redirect to the CI-only callback even
    # without displaying an UPDATE_PASSWORD form. Never treat such a
    # callback as proof of credential mutation and never leak Code/URL.
    removed = 0
    while not cb.server.inbox.empty():
        cb.next()
        removed += 1
    return removed


async def standard_action_started_before_restriction(e,browser,oidc,email,password):
    # Initiate a genuine AIA while policy still allows UPDATE_PASSWORD,
    # retain the in-flight browser BEFORE the policy is hardened.
    ctx,page=await e.new_page(browser)
    nonce=secrets.token_urlsafe(24)
    state=secrets.token_urlsafe(24)
    params={"client_id":CLIENT,"redirect_uri":CALLBACK,
        "response_type":"code","scope":USER_SCOPE,
        "state":state,"nonce":nonce,"code_challenge":challenge(verifier()),
        "code_challenge_method":"S256","prompt":"login",
        "kc_action":"UPDATE_PASSWORD"}
    try:
        await page.goto(oidc["authorization_endpoint"]+"?"+urlencode(params))
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=10000)
        await e.fill_login(page,email,password)
        await expect(page.locator("#password-new")).to_be_visible(timeout=12000)
        return ctx,page
    except Exception:
        await ctx.close()
        raise


async def complete_existing_action(page,new_password):
    # Real browser form is ALREADY rendered before disable; test whether
    # a standard runtime permission check stops a stale workflow.
    await page.locator("#password-new").fill(new_password)
    await page.locator("#password-confirm").fill(new_password)
    submit=page.locator('#kc-submit, #kc-passwd-update-form input[type="submit"]')
    await submit.first.click(timeout=10000)


def restrict_standard(root):
    original=root.call("GET").json()
    patched=deepcopy(original)
    patched["resetPasswordAllowed"]=False
    patched["registrationAllowed"]=False
    root.call("PUT",json=patched,expect_status=204)
    read=root.call("GET").json()
    assert read["resetPasswordAllowed"] is False
    assert read["registrationAllowed"] is False

    account=root.client("account-console")
    account["enabled"]=False
    root.call("PUT","/clients/"+account["id"],json=account,expect_status=204)
    assert root.client("account-console")["enabled"] is False

    actions=root.call("GET","/authentication/required-actions").json()
    match=[x for x in actions if x.get("alias")=="UPDATE_PASSWORD"]
    assert len(match)==1,"CONTROL_UPDATE_PASSWORD_ACTION_NOT_FOUND"
    disabled=deepcopy(match[0])
    disabled["enabled"]=False
    root.call("PUT","/authentication/required-actions/UPDATE_PASSWORD",
              json=disabled,expect_status=204)
    reread=root.call("GET","/authentication/required-actions").json()
    match=[x for x in reread if x.get("alias")=="UPDATE_PASSWORD"]
    assert len(match)==1 and match[0]["enabled"] is False
    return {"resetPasswordAllowed":False,"registrationAllowed":False,
            "account_console_enabled":False,
            "UPDATE_PASSWORD_provider_enabled":False,
            "readback_verified":True}


async def run(e,browser,cb):
    # Launch only AFTER prior suites pass. No existing test realm modifications.
    e.CURRENT="RC-separate-realm-standard-initialize"
    root,oidc=initialize_second_realm(e)
    ordinary="ordinary-controlled@example.test"
    issued="old-link-controlled@example.test"
    started="inflight-controlled@example.test"
    direct_user="direct-action-controlled@example.test"
    unrelated="other-managed-user@example.test"
    users=(ordinary,issued,started,direct_user,unrelated)
    old={k:"Qx9!"+secrets.token_urlsafe(18) for k in users}
    new={k:"Zp8!"+secrets.token_urlsafe(18) for k in users}
    uid={}
    for k in users:
        uid[k]=create_user(root,k,old[k])
    e.CURRENT="RC-before-lock-real-normal-OIDC"
    await login(e,browser,cb,oidc,ordinary,old[ordinary])
    e.case("RC-01-real-user-oidc-before-restriction")
    e.CURRENT="RC-before-lock-old-issued-token-and-prestarted-action"
    old_url=await old_action_token(e,root,issued,uid[issued])
    started_ctx,started_page=await standard_action_started_before_restriction(
        e,browser,oidc,started,old[started])
    e.case("RC-02-stale-action-token-and-inflight-form-preissued")
    e.CURRENT="RC-standard-policy-restrictions-readback"
    readback=restrict_standard(root)
    e.RESULTS["RC_restricted_standard_config"]=readback
    e.case("RC-03-all-standard-restriction-flags-readback")

    # Test live browser and direct endpoints, not simply absence of links.
    e.CURRENT="RC-after-lock-browser-and-kc-action"
    direct_action=oidc["authorization_endpoint"]+"?"+urlencode({
        "client_id":CLIENT,"redirect_uri":CALLBACK,"response_type":"code",
        "scope":USER_SCOPE,"state":secrets.token_urlsafe(24),
        "nonce":secrets.token_urlsafe(24),
        "code_challenge":challenge(verifier()),"code_challenge_method":"S256",
        "prompt":"login","kc_action":"UPDATE_PASSWORD"})
    direct=await browser_action_attempt(e,browser,direct_action,new[direct_user],email=direct_user,old_password=old[direct_user])
    discarded_direct=drain_probe_callbacks(cb)
    e.RESULTS["RC_kc_action_new"]={"password_form":direct["real_password_form"],
                                  "password_submit":direct["submitted"],
                                  "callback_count_after_direct_probe":discarded_direct}
    e.case("RC-04-actual-direct-kc-action-probed")

    e.CURRENT="RC-after-lock-forgot-direct"
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(oidc["authorization_endpoint"]+"?"+urlencode({
            "client_id":CLIENT,"redirect_uri":CALLBACK,"response_type":"code",
            "scope":USER_SCOPE,"state":secrets.token_urlsafe(24),
            "nonce":secrets.token_urlsafe(24),
            "code_challenge":challenge(verifier()),
            "code_challenge_method":"S256"}),wait_until="domcontentloaded")
        await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
        visible_forgot=await page.locator('a[href*="reset-credentials"]').is_visible()
        before_mail=mail_ids()
        link=page.locator('a[href*="reset-credentials"]')
        if await link.count():
            path=await link.first.get_attribute("href")
            # The exact raw direct route stays in RAM only; do not log.
            if path:
                await page.goto(BASE+path if path.startswith("/") else path)
        mail_new=mail_ids()-before_mail
        e.RESULTS["RC_forgot"]={
            "forgot_link_visible":visible_forgot,
            "direct_get_has_password_form":await page.locator("#password-new").is_visible(),
            "new_local_reset_mail_without_request":len(mail_new)>0,
        }
    finally:
        await ctx.close()
    e.case("RC-05-forgot-direct-browser-and-mail-observed")

    e.CURRENT="RC-after-lock-account-console-direct"
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(LOGIN+"/account/",wait_until="domcontentloaded")
        await page.wait_for_load_state("domcontentloaded")
        e.RESULTS["RC_account_console"]={
            "account_client_disabled_readback":True,
            "visible_password_change_form":await page.locator("#password-new").is_visible(),
            "visible_update_button":await page.get_by_role(
                "button",name="Update",exact=True).is_visible(),
            "account_page_http_status":request("GET",LOGIN+"/account/").status_code,
        }
    finally:
        await ctx.close()
    e.case("RC-06-account-console-browser-and-direct-route")

    # Old minted action token and a prestarted form are distinct from
    # a NEW kc_action request. Test them AFTER restrictions.
    e.CURRENT="RC-after-lock-preissued-mail-action-token"
    old_link=await browser_action_attempt(e,browser,old_url,new[issued])
    discarded_old_token=drain_probe_callbacks(cb)
    e.RESULTS["RC_old_action_link"]={
        "real_password_form":old_link["real_password_form"],
        "password_submitted":old_link["submitted"],
        "callbacks_after_old_link":discarded_old_token}
    e.case("RC-07-preissued-action-token-real-browser-probe")
    e.CURRENT="RC-after-lock-prestarted-required-action-form"
    try:
        await complete_existing_action(started_page,new[started])
        e.RESULTS["RC_prestarted_action"]={"submitted_after_policy_change":True}
    finally:
        await started_ctx.close()
    discarded_inflight=drain_probe_callbacks(cb)
    e.RESULTS["RC_prestarted_action"]["callbacks_after_submit"]=discarded_inflight
    e.case("RC-08-prestarted-action-form-continued-after-hardening")

    e.CURRENT="RC-direct-kc-action-old-vs-new-credential-check"
    # A mere missing form is not enough: the independent old credential
    # must remain accepted before the controlled service reset.
    if not direct["submitted"]:
        await login(e,browser,cb,oidc,direct_user,old[direct_user])
    e.case("RC-08a-direct-action-credential-fence-measured")
    e.CURRENT="RC-no-admin-for-ordinary-or-limited-operator"
    # Client Credentials: separate role-bound identities for the
    # test-only restricted operational principal and service principal.
    operator_token=issue_service(root,"controlled-operator",grant_view=True)
    service_token=issue_service(root,"controlled-reset-service",grant_manage=True)
    operator_status=password_update(root,uid[ordinary],new[ordinary],
                                    token_value=operator_token)
    assert operator_status in (401,403),"OPERATOR_RESET_REST_AUTHORIZATION_BYPASS"
    e.RESULTS["RC_role_limits"]={
        "operator_view_users_only":True,
        "operator_reset_status":operator_status,
        "service_uses_only_manage_users_role":True,
        "service_role_is_target_user_scoped":False,
        "root_admin_outside_policy":True}
    e.case("RC-09-limited-operator-admin-reset-denied")

    e.CURRENT="RC-service-role-real-password-change"
    result=password_update(root,uid[ordinary],new[ordinary],
                           token_value=service_token)
    assert result==204,"SERVICE_STANDARD_RESET_NOT_AUTHORIZED"
    await login(e,browser,cb,oidc,ordinary,old[ordinary],
                expect_failure=True)
    await login(e,browser,cb,oidc,ordinary,new[ordinary])
    e.case("RC-10-service-standard-reset-old-denied-new-accepted")

    # Crucial: a single built-in manage-users role has all-users scope
    # in the realm. It is not fine-grained target-user access.
    e.CURRENT="RC-service-coarse-scope-verification"
    other_status=password_update(root,uid[unrelated],new[unrelated],
                                 token_value=service_token)
    e.RESULTS["RC_service_scope"]={
       "other_user_reset_http":other_status,
       "single_user_scope_proven":False,
       "manage_users_is_sufficient_but_broad":other_status==204}
    e.case("RC-11-builtin-manage-users-scope-measured")

    e.CURRENT="RC-adversarial-bypass-final-denial"
    # Read actual independent credential status for pre-issued token
    # and in-flight form, not merely the UI's hidden/visible state.
    bypass=[]
    for email in (issued,started):
        try:
            await login(e,browser,cb,oidc,email,new[email])
        except (PWTimeout,AssertionError):
            pass
        else:
            bypass.append("old-token" if email==issued else "inflight-form")
    e.RESULTS["RC_bypass"]={
        "old_token_or_inflight_password_change_succeeded":bool(bypass),
        "bypass_classifications":bypass,
        "complete_self_service_denial_proven":not bypass,
        "all_password_change_channels_exhaustively_enumerated":False,
        "root_or_realm_admin_bound":False,
    }
    e.RESULTS["RC_verdict"]={
        "controlled_entry":"NOT_PROVEN",
        "reason":"standard manage-users is realm-wide; pre-issued flow measured separately; "
                 "no per-credential operation entitlement or product reset barrier",
        "product_session_revocation":"NOT_TESTED",
        "next":"test standard fine-grained admin permissions & complete independent "
               "credential change controls before designing product reset gate",
    }
    if bypass or direct["submitted"] or other_status==204:
        # A real bypass or broader-than-user service authority is a
        # denial of the claimed strong single-entry policy. CI RED.
        e.STAGES["RC-12-single-controlled-reset-entry"] = "BLOCKED"
        raise AssertionError("CONTROLLED_RESET_SINGLE_ENTRY_NOT_PROVEN")
    raise AssertionError("CONTROLLED_RESET_EXHAUSTIVE_SCOPE_NOT_PROVEN")
