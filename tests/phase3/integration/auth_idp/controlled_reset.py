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
CLEAN_REALM = "auth-idp-clean-bootstrap-ci"
ROOT = BASE + "/admin/realms/" + REALM_C
LOGIN = BASE + "/realms/" + REALM_C
USER_SCOPE = "openid email profile"
AUTH_ADMIN_SCOPE = "openid email profile kc-admin-api"


class Root:
    def __init__(self, master_token, realm_name=REALM_C):
        self.master_token = master_token
        self.realm_name = realm_name

    def call(self, method, suffix="", *, expect_status=200, **kwargs):
        reply = request(method, BASE + "/admin/realms/" + self.realm_name + suffix,
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
            # Mirror the already-accepted IDP-01 negative OIDC proof:
            # the theme is free to put error text outside legacy alerts.
            # REAL denial means stable login form, no redirect, and
            # no callback with this challenge's signed random state.
            await expect(page.locator("#kc-form-login")).to_be_visible(
                timeout=10000)
            await page.wait_for_load_state("networkidle",timeout=10000)
            assert "/callback" not in urlsplit(page.url).path
            assert await page.locator("#kc-form-login").is_visible()
            while not cb.server.inbox.empty():
                payload=cb.next()
                assert payload.get("state") != [state],"CONTROL_OLD_CREDENTIAL_GOT_CODE"
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
    reply=request("POST",BASE+"/realms/"+root.realm_name+"/protocol/openid-connect/token",
                  data={"grant_type":"client_credentials",
                        "client_id":client_id,"client_secret":secret,
                        "scope":scope})
    assert reply.status_code==200,"CONTROL_SERVICE_TOKEN_NOT_ISSUED"
    return reply.json()["access_token"]


def admin_request(access, suffix, *, method="PUT", realm_name=REALM_C, **kwargs):
    return request(method, BASE + "/admin/realms/" + realm_name + suffix,
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
    return admin_request(token_value,url,realm_name=root.realm_name,
                         json=payload).status_code


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



def configure_scoped_fgap(e, root, target_user_id, service_client_id):
    """Supported FGAP v2, only in disposable realm; no broad admin role."""
    e.CURRENT="RC-fgap-v2-realm-initial"
    previous=root.call("GET").json()
    enabled=deepcopy(previous)
    enabled["adminPermissionsEnabled"]=True
    e.CURRENT="RC-fgap-v2-realm-activate-put"
    root.call("PUT",json=enabled,expect_status=204)
    e.CURRENT="RC-fgap-v2-realm-activate-readback"
    assert root.call("GET").json().get("adminPermissionsEnabled") is True, (
        "CONTROL_FGAP_V2_NOT_ENABLED")
    e.CURRENT="RC-fgap-v2-client-discovery"
    authz_client=root.client("admin-permissions")["id"]
    e.CURRENT="RC-fgap-v2-service-client"
    service_client=root.client(service_client_id)["id"]
    e.CURRENT="RC-fgap-v2-service-account"
    service_user=root.call("GET","/clients/"+service_client+
        "/service-account-user").json()["id"]
    e.CURRENT="RC-fgap-v2-realm-management-client"
    rm_id=root.client("realm-management")["id"]
    e.CURRENT="RC-fgap-v2-role-map-read"
    mappings=root.call("GET","/users/"+service_user+
        "/role-mappings/clients/"+rm_id).json()
    e.CURRENT="RC-fgap-v2-role-map-no-broad"
    assert not any(x.get("name") in (
        "manage-users","view-users","realm-admin","manage-realm") for x in mappings), (
        "CONTROL_FGAP_SERVICE_HAS_BROAD_BUILTIN_ROLE")
    prefix="/clients/"+authz_client+"/authz/resource-server"
    policy_name="controlled-reset-only-service-policy"
    perm_name="controlled-one-user-reset-operation"
    e.CURRENT="RC-fgap-v2-create-user-policy"
    root.call("POST",prefix+"/policy/user",json={
        "name":policy_name,"logic":"POSITIVE",
        "users":[service_user]},expect_status=201)
    e.CURRENT="RC-fgap-v2-create-one-user-scope-permission"
    root.call("POST",prefix+"/permission/scope",json={
        "name":perm_name,"resourceType":"Users",
        "scopes":["reset-password"],"resources":[target_user_id],
        "policies":[policy_name]},expect_status=201)
    e.CURRENT="RC-fgap-v2-list-permissions"
    entries=root.call("GET",prefix+"/permission/scope").json()
    e.CURRENT="RC-fgap-v2-exact-permission-readback"
    matching=[x for x in entries if x.get("name")==perm_name]
    assert len(matching)==1,"CONTROL_FGAP_PERMISSION_NOT_READABLE"
    assert matching[0].get("id"),"CONTROL_FGAP_PERMISSION_ID_MISSING"
    # List entries may be BRIEF representations: independently request
    # exact full server-side permission by its ID for scope/user readback.
    e.CURRENT="RC-fgap-v2-read-full-permission-by-id"
    actual=root.call("GET",prefix+"/permission/scope/"+
                     matching[0]["id"]).json()
    assert actual.get("name")==perm_name,"CONTROL_FGAP_PERMISSION_NAME_CHANGED"
    e.CURRENT="RC-fgap-v2-verify-persisted-resource-operation-and-policy"
    readback={
      "type":actual.get("resourceType")=="Users",
      "scope":"reset-password" in actual.get("scopes",[]),
      "one_resource":set(actual.get("resources",[]))=={target_user_id},
      "linked_policy":policy_name in actual.get("policies",[]),
    }
    e.RESULTS["RC_fgap_exact_readback_checks"]=readback
    # The provider may serialize stored associations as internal AuthZ IDs
    # rather than the names/UUIDs used in POST. Preserve this mismatch as
    # NOT_VERIFIED, and still run direct positive + adversarial REST tests.
    # The final CI security verdict MUST remain blocked if any readback
    # property or functional negative test is unproven.
    exact_readback=all(readback.values())
    return {"enabled_readback":True,"service_has_no_broad_admin_role":True,
            "one_user_scope_readback":readback["one_resource"],
            "only_reset_password_scope_readback":readback["scope"],
            "linked_policy_readback":readback["linked_policy"],
            "stored_permission_details_verified":exact_readback}


async def run(e,browser,cb):
    # Launch only AFTER prior suites pass. No existing test realm modifications.
    e.CURRENT="RC-separate-realm-standard-initialize"
    root,oidc=initialize_second_realm(e)
    ordinary="ordinary-controlled@example.test"
    issued="old-link-controlled@example.test"
    started="inflight-controlled@example.test"
    direct_user="direct-action-controlled@example.test"
    unrelated="other-managed-user@example.test"
    started_after_logout="inflight-logout-controlled@example.test"
    issued_after_logout="old-link-logout-controlled@example.test"
    users=(ordinary,issued,started,direct_user,unrelated,
           started_after_logout,issued_after_logout)
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
    old_url_after_logout=await old_action_token(
        e,root,issued_after_logout,uid[issued_after_logout])
    started_ctx,started_page=await standard_action_started_before_restriction(
        e,browser,oidc,started,old[started])
    logout_ctx,logout_page=await standard_action_started_before_restriction(
        e,browser,oidc,started_after_logout,old[started_after_logout])
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
    # Separate IN-FLIGHT form created before policy, not a reload or new
    # challenge. Try the documented standard user-session logout-all and
    # independently check the credential afterwards. The earlier baseline
    # in-flight bypass above remains unchanged.
    e.CURRENT="RC-standard-logout-all-versus-existing-authentication-form"
    logout_reply=root.call("POST","/logout-all",expect_status=(200,204))
    try:
        try:
            await complete_existing_action(logout_page,new[started_after_logout])
            after_logout_submitted=True
        except (PWTimeout,AssertionError):
            after_logout_submitted=False
    finally:
        await logout_ctx.close()
    logout_callbacks=drain_probe_callbacks(cb)
    old_link_post_logout=await browser_action_attempt(
        e,browser,old_url_after_logout,new[issued_after_logout])
    old_link_callbacks=drain_probe_callbacks(cb)
    e.RESULTS["RC_standard_user_session_logout_barrier"]={
        "admin_logout_all_http":logout_reply.status_code,
        "preexisting_form_used_without_reload":True,
        "inflight_form_submitted_after_logout":after_logout_submitted,
        "inflight_callbacks_after_logout":logout_callbacks,
        "preissued_token_form_after_logout":old_link_post_logout["real_password_form"],
        "preissued_token_submitted_after_logout":old_link_post_logout["submitted"],
        "preissued_token_callbacks_after_logout":old_link_callbacks,
        "logout_all_is_not_authentication_session_revocation_proof":True}
    # This is a real independent browser credential check, not a callback
    # inference. Do it BEFORE FGAP so a later permission/setup failure
    # cannot hide the answer about the SAME pre-policy in-flight form.
    e.CURRENT="RC-logout-all-real-credential-independence-check"
    try:
        await login(e,browser,cb,oidc,started_after_logout,
                    new[started_after_logout])
    except (PWTimeout,AssertionError):
        logout_form_changed_password=False
        await login(e,browser,cb,oidc,started_after_logout,
                    old[started_after_logout])
    else:
        logout_form_changed_password=True
        await login(e,browser,cb,oidc,started_after_logout,
                    old[started_after_logout],expect_failure=True)
    # An unsubmitted old email action link must not change the credential.
    await login(e,browser,cb,oidc,issued_after_logout,
                old[issued_after_logout])
    e.RESULTS["RC_standard_user_session_logout_barrier"].update({
        "same_inflight_form_new_password_independently_accepted":
            logout_form_changed_password,
        "same_inflight_form_old_password_independently_denied":
            logout_form_changed_password,
        "preissued_token_old_credential_still_accepted":True})
    e.case("RC-12-standard-logout-all-preexisting-form-and-token-probed")

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
    # Prove both unauthorized identities against the DIRECT Admin API:
    # ordinary user password OIDC bearer versus view-users-only operator.
    ordinary_login=await login(e,browser,cb,oidc,ordinary,old[ordinary])
    ordinary_status=password_update(root,uid[ordinary],new[ordinary],
                                    token_value=ordinary_login["access_token"])
    assert ordinary_status in (401,403),"ORDINARY_USER_ADMIN_RESET_AUTHORIZATION_BYPASS"
    operator_status=password_update(root,uid[ordinary],new[ordinary],
                                    token_value=operator_token)
    assert operator_status in (401,403),"OPERATOR_RESET_REST_AUTHORIZATION_BYPASS"
    # The unauthorized attempts did NOT change the credential.
    await login(e,browser,cb,oidc,ordinary,old[ordinary])
    e.RESULTS["RC_role_limits"]={
        "ordinary_real_user_admin_reset_http":ordinary_status,
        "ordinary_real_user_denied":True,
        "operator_view_users_only":True,
        "operator_reset_status":operator_status,
        "service_uses_only_manage_users_role":True,
        "service_role_is_target_user_scoped":False,
        "root_admin_outside_policy":True}
    e.case("RC-09-limited-operator-admin-reset-denied")

    e.CURRENT="RC-service-role-real-password-change"
    result=password_update(root,uid[ordinary],new[ordinary],
                           token_value=service_token)
    e.RESULTS["RC_service_controlled_reset_http"]=result
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
    # Supported FGAP v2 on the SAME disposable second realm. Do not give
    # this principal view-users/manage-users/realm-admin or 'manage' scope.
    e.CURRENT="RC-fgap-v2-exact-permission-config-readback"
    scoped_client="controlled-reset-scoped-service"
    scoped_token=issue_service(root,scoped_client)
    fgap_readback=configure_scoped_fgap(e,root,uid[ordinary],scoped_client)
    e.RESULTS["RC_fgap_configuration"]=fgap_readback
    e.case("RC-13-standard-fgap-v2-reset-password-only-readback-measured")

    e.CURRENT="RC-fgap-v2-real-target-and-unrelated-operation-tests"
    fgap_new="Sc7!"+secrets.token_urlsafe(18)
    fgap_other="No7!"+secrets.token_urlsafe(18)
    scoped_target_status=password_update(root,uid[ordinary],fgap_new,
                                         token_value=scoped_token)
    if scoped_target_status==204:
        await login(e,browser,cb,oidc,ordinary,new[ordinary],
                    expect_failure=True)
        await login(e,browser,cb,oidc,ordinary,fgap_new)
    scoped_other_status=password_update(root,uid[unrelated],fgap_other,
                                        token_value=scoped_token)
    unrelated_profile_status=admin_request(
        scoped_token,"/users/"+uid[ordinary],
        json={"firstName":"ForbiddenMutation"}).status_code
    target_profile_unchanged=(
        root.call("GET","/users/"+uid[ordinary]).json().get("firstName")
        =="Synthetic")
    # A refused reset must leave the OTHER user's actual credential
    # usable. No credential value, token or user identifier is exported.
    if scoped_other_status in (401,403):
        await login(e,browser,cb,oidc,unrelated,new[unrelated])
        unrelated_old_retained=True
    else:
        unrelated_old_retained=False
    e.RESULTS["RC_fgap_results"]={
        "target_reset_http":scoped_target_status,
        "target_new_credential_verified":scoped_target_status==204,
        "other_user_reset_http":scoped_other_status,
        "other_user_old_credential_retained":unrelated_old_retained,
        "unrelated_admin_profile_update_http":unrelated_profile_status,
        "target_profile_unchanged":target_profile_unchanged,
        "least_privilege_test_passed":(
            scoped_target_status==204 and scoped_other_status in (401,403)
            and unrelated_old_retained and unrelated_profile_status in (401,403)
            and target_profile_unchanged)}
    e.case("RC-14-fgap-v2-target-other-user-and-other-operation-measured")

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
    if e.RESULTS["RC_standard_user_session_logout_barrier"][
            "same_inflight_form_new_password_independently_accepted"]:
        bypass.append("inflight-form-after-logout-all")
    e.RESULTS["RC_bypass"]={
        "old_token_or_inflight_password_change_succeeded":bool(bypass),
        "bypass_classifications":bypass,
        "complete_self_service_denial_proven":not bypass,
        "all_password_change_channels_exhaustively_enumerated":False,
        "root_or_realm_admin_bound":False,
    }
    e.RESULTS["RC_verdict"]={
        "controlled_entry":"NOT_PROVEN",
        "reason":"original manage-users service remains realm-wide; pre-policy "
                 "in-flight form and post-logout form tested independently; "
                 "scoped FGAP service proof reported separately; no product reset barrier",
        "product_session_revocation":"NOT_TESTED",
        "next":"test standard fine-grained admin permissions & complete independent "
               "credential change controls before designing product reset gate",
    }
    if (bypass or direct["submitted"] or other_status==204
            or not e.RESULTS["RC_fgap_results"]["least_privilege_test_passed"]
            or not fgap_readback["stored_permission_details_verified"]):
        # A real bypass or broader-than-user service authority is a
        # denial of the claimed strong single-entry policy. CI RED.
        e.STAGES["RC-12-single-controlled-reset-entry"] = "BLOCKED"
        raise AssertionError("CONTROLLED_RESET_SINGLE_ENTRY_NOT_PROVEN")
    raise AssertionError("CONTROLLED_RESET_EXHAUSTIVE_SCOPE_NOT_PROVEN")


# CLEAN BOOTSTRAP is a distinct CI mode, not the historical RC migration test.
# Do not move, delete, bypass or relabel run() and its final fail-closed check.
def initialize_clean_realm(e):
    e.CURRENT="CB-00-create-fresh-realm-with-final-policy"
    master=e.Admin().token
    root=Root(master,CLEAN_REALM)
    initial={
      "realm":CLEAN_REALM,"enabled":True,"sslRequired":"none",
      "registrationAllowed":False,"registrationEmailAsUsername":True,
      "loginWithEmailAllowed":True,"duplicateEmailsAllowed":False,
      "verifyEmail":False,"resetPasswordAllowed":False,
      "adminPermissionsEnabled":True,"bruteForceProtected":False,
      "passwordPolicy":"length(12) and digits(1) and upperCase(1) and specialChars(1)",
      "accessTokenLifespan":180,
      "actionTokenGeneratedByAdminLifespan":180,
      "actionTokenGeneratedByUserLifespan":180,
      "smtpServer":{"host":"mailpit","port":"1025",
                    "from":"clean-bootstrap-ci@example.test",
                    "ssl":"false","starttls":"false","auth":"false"}
    }
    resp=request("POST",BASE+"/admin/realms",
       headers={"Authorization":"Bearer "+master},json=initial)
    assert resp.status_code==201,"CB_REALM_CREATE_FAILED"
    r=root.call("GET").json()
    assert r["realm"]==CLEAN_REALM
    assert r.get("adminPermissionsEnabled") is True
    assert r["resetPasswordAllowed"] is False
    # No synthetic users, browser login, action-token issue or action form
    # has occurred in this fresh realm; lock every alternative BEFORE those.
    readback=restrict_standard(root)
    assert root.call("GET").json().get("adminPermissionsEnabled") is True
    create_client(root,{
       "clientId":CLIENT,"enabled":True,"protocol":"openid-connect",
       "publicClient":True,"standardFlowEnabled":True,
       "directAccessGrantsEnabled":False,"implicitFlowEnabled":False,
       "serviceAccountsEnabled":False,"redirectUris":[CALLBACK],
       "webOrigins":[],"attributes":{"pkce.code.challenge.method":"S256"}
    })
    login_root=BASE+"/realms/"+CLEAN_REALM
    discovered=request("GET",login_root+"/.well-known/openid-configuration")
    assert discovered.status_code==200
    assert discovered.json()["issuer"]==login_root
    e.RESULTS["CB_initial_conditions"]={
      "separate_fresh_realm":True,
      "final_reset_and_registration_disabled_before_users":True,
      "account_console_and_required_action_disabled_before_users":True,
      "fgap_v2_enabled_before_users":True,
      "no_preexisting_browser_form_or_reset_link_in_this_realm":True,
      "transition_proof_not_claimed":True,
      "standard_restrictions_readback":readback
    }
    e.case("CB-00-clean-policy-before-users-or-flows")
    return root,discovered.json(),login_root


def clean_fgap_permission(e,root,target_uuid,service_cid):
    # Administrative readback uses the real 26.8 REST representation:
    # PolicyRepresentation.scopes/resources/policies may contain internal IDs,
    # while scopesData/resourcesData can contain structured objects.
    # Exact matches, not mere array length, are essential to mark PROVEN.
    e.CURRENT="CB-01-create-exact-scoped-permission"
    assert root.call("GET").json().get("adminPermissionsEnabled") is True
    service_uuid=root.client(service_cid)["id"]
    suid=root.call("GET","/clients/"+service_uuid+
         "/service-account-user").json()["id"]
    management_uuid=root.client("realm-management")["id"]
    roles=root.call("GET","/users/"+suid+
         "/role-mappings/clients/"+management_uuid).json()
    assert not any(x.get("name") in (
         "manage-users","view-users","realm-admin","manage-realm")
         for x in roles),"CB_BROAD_ROLE_NOT_ALLOWED"
    authz=root.client("admin-permissions")["id"]
    pref="/clients/"+authz+"/authz/resource-server"
    pname="clean-one-service-policy"
    name="clean-one-target-reset-only"
    root.call("POST",pref+"/policy/user",json={
         "name":pname,"logic":"POSITIVE","users":[suid]
    },expect_status=201)
    root.call("POST",pref+"/permission/scope",json={
         "name":name,"resourceType":"Users","scopes":["reset-password"],
         "resources":[target_uuid],"policies":[pname]
    },expect_status=201)
    all_permissions=root.call("GET",pref+"/permission/scope").json()
    exact=[x for x in all_permissions if x.get("name")==name]
    assert len(exact)==1 and exact[0].get("id")
    item=root.call("GET",pref+"/permission/scope/"+exact[0]["id"]).json()
    assert item.get("name")==name and item.get("resourceType")=="Users"
    policy_rows=root.call("GET",pref+"/policy/user").json()
    policies=[x for x in policy_rows if x.get("name")==pname]
    assert len(policies)==1 and policies[0].get("id")
    policy_id=policies[0]["id"]
    policy_detail=root.call("GET",pref+"/policy/user/"+policy_id).json()
    assert policy_detail.get("name")==pname

    # Resolve permission references against the same pinned server's
    # persisted AuthZ scope, resource and policy objects (no ID logging).
    scope_rows=root.call("GET",pref+"/scope").json()
    scope_by_id={x.get("id"):x.get("name") for x in scope_rows
                 if x.get("id") and x.get("name")}
    def extract_ids(items):
        return [x.get("id") if isinstance(x,dict) else x
                for x in (items or [])]
    scope_ref=extract_ids(item.get("scopes"))
    scope_obj=[x.get("name") for x in (item.get("scopesData") or [])
               if isinstance(x,dict)]
    resolved_scopes=[scope_by_id.get(v,v) for v in scope_ref]
    # The API may emit either IDs or scopesData, not necessarily both.
    scope_ok=(resolved_scopes==["reset-password"] or
              scope_obj==["reset-password"])
    if resolved_scopes and scope_obj:
        scope_ok=scope_ok and set(resolved_scopes)==set(scope_obj)

    resource_ref=extract_ids(item.get("resources"))
    resource_data=item.get("resourcesData") or []
    resource_ids=[x.get("id") for x in resource_data if isinstance(x,dict)]
    names=[x.get("name") for x in resource_data if isinstance(x,dict)]
    candidate_ids=resource_ref or resource_ids
    candidate_names=names
    # If the permission references AuthZ resource IDs, query the actual
    # resources and cross-check their entity UUID, not their display label.
    if candidate_ids and target_uuid not in candidate_ids:
        linked=[]
        for rid in candidate_ids:
            reply=root.call("GET",pref+"/resource/"+rid)
            linked.append(reply.json())
        candidate_ids=[x.get("id") for x in linked]
        candidate_names=[x.get("name") for x in linked]
    resource_ok=(len(candidate_ids)==1 and
                 (candidate_ids[0]==target_uuid or
                  (len(candidate_names)==1 and
                   candidate_names[0]==target_uuid)))
    # The AuthZ user resource UUID is an authoritative entity identifier.
    # A broad "Users" type-level resource must never satisfy this check.
    if candidate_names==["Users"] and target_uuid not in candidate_ids:
        resource_ok=False
    policy_refs=extract_ids(item.get("policies"))
    policy_ok=(len(policy_refs)==1 and policy_refs[0] in (policy_id,pname))
    if not policy_refs:
        # Server-side associated-policy relation is a distinct Admin REST
        # endpoint; never fabricate a match from the POST request itself.
        assoc=root.call("GET",pref+"/permission/scope/"+
                        exact[0]["id"]+"/associatedPolicies",
                        expect_status=(200,404))
        if assoc.status_code==200:
            ar=assoc.json()
            policy_ok=(len(ar)==1 and
                       ar[0].get("id")==policy_id and
                       ar[0].get("name")==pname)
    checks={
       "resource_type_users":item.get("resourceType")=="Users",
       "only_reset_password_scope_resolved":scope_ok,
       "exact_single_target_user_resource_resolved":resource_ok,
       "exact_single_service_policy_resolved":policy_ok,
       "no_broad_admin_role":True,
    }
    e.RESULTS["CB_permission_readback"]={
       "keycloak_permission_representation":"PolicyRepresentation",
       "scope_refs_count":len(scope_ref),
       "scope_objects_count":len(scope_obj),
       "resource_refs_count":len(resource_ref),
       "resource_objects_count":len(resource_data),
       "policy_refs_count":len(policy_refs),
       "checks":checks,
       "all_relations_verified":all(checks.values()),
    }
    e.case("CB-01-FGAP-references-readback-measured")
    return all(checks.values())


async def clean_unchanged_password(e,browser,cb,oidc,email,old,attempted,stage):
    # An omitted form alone never qualifies as a password boundary.
    e.CURRENT=stage+"-real-negative-new-password"
    await login(e,browser,cb,oidc,email,attempted,expect_failure=True)
    e.CURRENT=stage+"-real-positive-original-password"
    await login(e,browser,cb,oidc,email,old)
    e.RESULTS[stage]={"attempted_password_rejected":True,
                      "original_password_still_accepted":True}
    e.case(stage+"-credential-not-changed")


async def clean_browser_password_attempt(e,browser,url,new_password,cb,
                                         *,email=None,old_password=None):
    outcome=await browser_action_attempt(e,browser,url,new_password,
                    email=email,old_password=old_password)
    callbacks=drain_probe_callbacks(cb)
    return {"real_password_form":outcome["real_password_form"],
            "submitted":outcome["submitted"],
            "callback_count":callbacks}


async def run_clean(e,browser,cb):
    # Distinct CI job / disposable Keycloak instance; does not run old RC.
    # The historical failing RC transition remains in its own job.
    e.RESULTS["CLEAN_BOOTSTRAP_CONTROLLED_RESET"]={
       "verdict":"NOT_PROVEN",
       "mode":"fresh-realm-final-policy-before-all-users-and-flows",
       "product_session_revocation":"NOT_TESTED",
       "existing_transition_result":"NOT_PROVEN_UNCHANGED"}
    root,oidc,lr=initialize_clean_realm(e)
    actors=("target","other","forgot","action","account","direct","required")
    email={k:"clean-"+k+"@example.test" for k in actors}
    old={k:"Qx9!"+secrets.token_urlsafe(18) for k in actors}
    attempted={k:"Zp8!"+secrets.token_urlsafe(18) for k in actors}
    uid={k:create_user(root,email[k],old[k]) for k in actors}
    service_token=issue_service(root,"clean-reset-only-service")
    fgap_ok=clean_fgap_permission(e,root,uid["target"],
                                   "clean-reset-only-service")
    # This is the FIRST user authentication in this new realm.
    e.CURRENT="CB-02-real-ordinary-email-password-login"
    await login(e,browser,cb,oidc,email["target"],old["target"])
    await login(e,browser,cb,oidc,email["other"],old["other"])
    e.case("CB-02-normal-real-OIDC-login-after-final-policy")

    e.CURRENT="CB-03-browser-forgot-and-direct-reset-endpoint"
    ctx,page=await e.new_page(browser)
    before=mail_ids()
    reset_form_seen=False
    try:
        nonce=secrets.token_urlsafe(18)
        url=oidc["authorization_endpoint"]+"?"+urlencode({
          "client_id":CLIENT,"redirect_uri":CALLBACK,"response_type":"code",
          "scope":USER_SCOPE,"state":secrets.token_urlsafe(18),
          "nonce":nonce,"code_challenge":challenge(verifier()),
          "code_challenge_method":"S256"})
        await page.goto(url,wait_until="domcontentloaded")
        await expect(page.locator("#kc-form-login")).to_be_visible()
        link=page.locator('a[href*="reset-credentials"]')
        visible_forgot=await link.is_visible()
        if await link.count():
            href=await link.first.get_attribute("href")
            if href:
                await page.goto(BASE+href if href.startswith("/") else href)
                reset_form_seen=await page.locator("#kc-reset-password-form").is_visible()
        # Direct URL is exercised separately, regardless of link visibility.
        await page.goto(lr+"/login-actions/reset-credentials",
                        wait_until="domcontentloaded")
        direct_form=await page.locator("#kc-reset-password-form").is_visible()
        if direct_form:
            reset_form_seen=True
            await page.locator('#kc-reset-password-form input[name="username"]').fill(
                email["forgot"])
            await page.locator('#kc-reset-password-form button[type="submit"], #kc-reset-password-form input[type="submit"]').first.click()
    finally:
        await ctx.close()
    message=await asyncio.to_thread(message_for,email["forgot"],before)
    if message:
        attempt=await clean_browser_password_attempt(
               e,browser,action_url(message[1]),attempted["forgot"],cb)
    else:
        attempt={"real_password_form":False,"submitted":False,"callback_count":0}
    e.RESULTS["CB_forgot"]={
        "visible_link":visible_forgot,"form_seen":reset_form_seen,
        "local_mail_created":bool(message),"action_form_submitted":attempt["submitted"]}
    e.case("CB-03-forgot-direct-and-local-mail-attempted")
    await clean_unchanged_password(e,browser,cb,oidc,email["forgot"],
          old["forgot"],attempted["forgot"],"CB-03-forgot")

    e.CURRENT="CB-04-fresh-kc-action-actual-login-and-form"
    action_url_new=oidc["authorization_endpoint"]+"?"+urlencode({
       "client_id":CLIENT,"redirect_uri":CALLBACK,"response_type":"code",
       "scope":USER_SCOPE,"state":secrets.token_urlsafe(20),
       "nonce":secrets.token_urlsafe(20),
       "code_challenge":challenge(verifier()),
       "code_challenge_method":"S256","prompt":"login",
       "kc_action":"UPDATE_PASSWORD"})
    action_result=await clean_browser_password_attempt(e,browser,
         action_url_new,attempted["action"],cb,
         email=email["action"],old_password=old["action"])
    e.RESULTS["CB_kc_action"]=action_result
    e.case("CB-04-kc-action-real-browser-attempted")
    await clean_unchanged_password(e,browser,cb,oidc,email["action"],
         old["action"],attempted["action"],"CB-04-kc-action")

    e.CURRENT="CB-05-account-console-UI-and-direct-route"
    ctx,page=await e.new_page(browser)
    try:
        await page.goto(lr+"/account/#/security/signingin",
                        wait_until="domcontentloaded")
        status=request("GET",lr+"/account/").status_code
        update=page.get_by_role("button",name="Update",exact=True)
        update_button=await update.is_visible()
        if update_button:
            await update.click()
        password_form=await page.locator("#password-new").is_visible()
        did_submit=False
        if password_form:
            await page.locator("#password-new").fill(attempted["account"])
            await page.locator("#password-confirm").fill(attempted["account"])
            await page.locator(
                '#kc-submit, #kc-passwd-update-form input[type="submit"]'
            ).first.click()
            did_submit=True
        e.RESULTS["CB_account_console"]={
           "direct_http":status,"visible_update_button":update_button,
           "actual_password_form":password_form,"submitted":did_submit,
           "client_disabled_readback":root.client("account-console")["enabled"] is False}
    finally:
        await ctx.close()
    drain_probe_callbacks(cb)
    e.case("CB-05-account-console-direct-UI-attempted")
    await clean_unchanged_password(e,browser,cb,oidc,email["account"],
         old["account"],attempted["account"],"CB-05-account")

    e.CURRENT="CB-06-same-configuration-admin-issued-action-link"
    before=mail_ids()
    issuance=root.call("PUT","/users/"+uid["direct"]+"/execute-actions-email",
        params={"client_id":CLIENT,"redirect_uri":CALLBACK,"lifespan":180},
        json=["UPDATE_PASSWORD"],expect_status=(204,400,403))
    mail=await asyncio.to_thread(message_for,email["direct"],before)
    if issuance.status_code==204 and not mail:
        # The server accepted the issue request but there is no link to
        # exercise. Do not turn an untested link into a success.
        e.RESULTS["CB_action_issuance_missing_mail"]=True
    if mail:
        link_result=await clean_browser_password_attempt(
            e,browser,action_url(mail[1]),attempted["direct"],cb,
            email=email["direct"],old_password=old["direct"])
    else:
        link_result={"real_password_form":False,"submitted":False,
                     "callback_count":0}
    e.RESULTS["CB_action_link"]={
       "after_policy_issue_http":issuance.status_code,
       "issued_local_action_mail":bool(mail),
       "real_password_form":link_result["real_password_form"],
       "submitted":link_result["submitted"],
       "untested_accepted_issue":issuance.status_code==204 and not bool(mail)}
    e.case("CB-06-post-policy-action-token-tested-if-issued")
    await clean_unchanged_password(e,browser,cb,oidc,email["direct"],
         old["direct"],attempted["direct"],"CB-06-action-link")

    e.CURRENT="CB-07-same-configuration-admin-assigned-required-action"
    # This is an explicitly privileged bootstrap-issued action, NOT
    # evidence of a pre-existing user flow from before clean lockdown.
    u=root.call("GET","/users/"+uid["required"]).json()
    modified=deepcopy(u)
    modified["requiredActions"]=["UPDATE_PASSWORD"]
    root.call("PUT","/users/"+uid["required"],json=modified,expect_status=204)
    ctx,page=await e.new_page(browser)
    try:
        ra_url=oidc["authorization_endpoint"]+"?"+urlencode({
          "client_id":CLIENT,"redirect_uri":CALLBACK,"response_type":"code",
          "scope":USER_SCOPE,"state":secrets.token_urlsafe(22),
          "nonce":secrets.token_urlsafe(22),
          "code_challenge":challenge(verifier()),
          "code_challenge_method":"S256","prompt":"login"})
        await page.goto(ra_url,wait_until="domcontentloaded")
        await expect(page.locator("#kc-form-login")).to_be_visible()
        await e.fill_login(page,email["required"],old["required"])
        real_form=await page.locator("#password-new").is_visible()
        submitted=False
        if real_form:
            await page.locator("#password-new").fill(attempted["required"])
            await page.locator("#password-confirm").fill(attempted["required"])
            await page.locator(
                '#kc-submit, #kc-passwd-update-form input[type="submit"]'
            ).first.click()
            submitted=True
        e.RESULTS["CB_required_action"]={
           "admin_assigned_after_lock":True,
           "password_form_after_assignment":real_form,
           "submitted":submitted}
    finally:
        await ctx.close()
    drain_probe_callbacks(cb)
    # Clear the trusted-admin fixture requirement to enable an independent
    # fresh login; no normal user/limited service has this permission.
    changed=root.call("GET","/users/"+uid["required"]).json()
    changed["requiredActions"]=[]
    root.call("PUT","/users/"+uid["required"],json=changed,expect_status=204)
    e.case("CB-07-post-policy-assigned-required-action-attempted")
    await clean_unchanged_password(e,browser,cb,oidc,email["required"],
         old["required"],attempted["required"],"CB-07-required-action")

    e.CURRENT="CB-08-ordinary-OIDC-bearer-admin-reset-negative"
    ordinary=await login(e,browser,cb,oidc,email["other"],old["other"])
    unpriv=password_update(root,uid["target"],attempted["target"],
          token_value=ordinary["access_token"])
    assert unpriv in (401,403),"CB_ORDINARY_USER_ADMIN_RESET_ALLOWED"
    e.RESULTS["CB_ordinary_admin_reset_http"]=unpriv
    await login(e,browser,cb,oidc,email["target"],old["target"])
    e.case("CB-08-normal-user-admin-reset-denied")

    e.CURRENT="CB-09-scoped-service-actual-reset"
    status=password_update(root,uid["target"],attempted["target"],
          token_value=service_token)
    if status==204:
        await login(e,browser,cb,oidc,email["target"],old["target"],
                    expect_failure=True)
        await login(e,browser,cb,oidc,email["target"],attempted["target"])
    e.RESULTS["CB_target_reset"]={
       "http":status,"old_denied_new_accepted":status==204}
    e.case("CB-09-scoped-target-password-reset-measured")

    e.CURRENT="CB-10-service-out-of-domain-and-unrelated-operation"
    out_pw="Oz8!"+secrets.token_urlsafe(18)
    out_status=password_update(root,uid["other"],out_pw,
                               token_value=service_token)
    profile_status=admin_request(service_token,
         "/users/"+uid["target"],realm_name=root.realm_name,
         json={"firstName":"ForbiddenMutation"}).status_code
    unchanged=root.call("GET","/users/"+uid["target"]).json().get(
         "firstName")=="Synthetic"
    if out_status in (401,403):
        await login(e,browser,cb,oidc,email["other"],old["other"])
    e.RESULTS["CB_scope_negatives"]={
       "other_user_reset_http":out_status,
       "other_user_old_credential_retained":out_status in (401,403),
       "unrelated_profile_http":profile_status,
       "target_profile_unchanged":unchanged}
    e.case("CB-10-cross-user-and-profile-negative-measured")

    evidence=e.RESULTS
    mutation_routes=("CB-03-forgot","CB-04-kc-action","CB-05-account",
                     "CB-06-action-link","CB-07-required-action")
    forms_denied=all(evidence[k]["original_password_still_accepted"]
           and evidence[k]["attempted_password_rejected"] for k in mutation_routes)
    clean_pass=(fgap_ok and forms_denied
          and not evidence["CB_action_link"]["untested_accepted_issue"]
          and status==204 and out_status in (401,403)
          and profile_status in (401,403) and unchanged
          and unpriv in (401,403))
    evidence["CLEAN_BOOTSTRAP_CONTROLLED_RESET"].update({
       "verdict":"PROVEN" if clean_pass else "NOT_PROVEN",
       "permission_readback_complete":fgap_ok,
       "ordinary_route_password_unchanged":forms_denied,
       "allowed_target_reset_verified":status==204,
       "other_user_reset_denied":out_status in (401,403),
       "unrelated_admin_operation_denied":profile_status in (401,403),
       "root_or_realm_admin_outside_boundary":True,
       "transition_with_preexisting_flows":"NOT_PROVEN",
       "no_product_session_claim":True,
    })
    e.CURRENT="CB-11-clean-bootstrap-final-verdict"
    if not clean_pass:
        e.STAGES["CB-11-clean-bootstrap-final-verdict"]="BLOCKED"
        raise AssertionError("CLEAN_BOOTSTRAP_CONTROLLED_RESET_NOT_PROVEN")
    e.case("CB-11-clean-bootstrap-controlled-reset-PROVEN")
