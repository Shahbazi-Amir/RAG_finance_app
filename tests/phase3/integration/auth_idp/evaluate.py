"""Real OIDC / registration / SMTP / MFA Keycloak candidate tests, CI only.

No API/UI/BFF/product database. Exactly two synthetic users and one synthetic
realm manager; all passwords and tokens live only in process memory. Never
print exception messages (Playwright URLs often contain sensitive action tokens).
Artifacts contain IDs/statuses, static component versions and revocation facts.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import jwt
import pyotp
from playwright.async_api import async_playwright, expect

from support import (
    Admin, BASE, MAIL, CALLBACK, CLIENT, REALM, CallbackServer,
    action_url, authorization, credentials, discovery, exchange,
    mail_ids, message_for, refresh, request, require_ci, verifier,
    verify_id, expect_response,
)

STAGES: dict[str, str] = {}
CURRENT = "boot"
REPORT = None
RESULTS = {}
EMAILS = ("first@example.test", "second@example.test")
MANAGER = "realm-operator@example.test"
POLICY = "policy-probe@example.test"
PASSWORDS = {}
ADMIN = None
OIDC = None


def case(label: str, fact: str | None = None):
    STAGES[label] = "PASS"
    if fact:
        RESULTS[label] = fact
    print(label + ": PASS", flush=True)


async def email_after(address: str, seen: set[str], seconds: int = 20):
    async def wait():
        for _ in range(seconds * 5):
            item = await asyncio.to_thread(message_for, address, seen)
            if item:
                return item
            await asyncio.sleep(0.2)
        raise AssertionError("SMTP_MESSAGE_NOT_CAPTURED")
    return await asyncio.wait_for(wait(), timeout=seconds + 3)


async def local_only(route):
    address = route.request.url
    if address.startswith((BASE + "/", "http://127.0.0.1:8765/")) or address.startswith(
        ("data:", "blob:", "about:")
    ):
        await route.continue_()
    else:
        raise AssertionError("BROWSER_NON_LOOPBACK_REQUEST")


async def new_page(browser):
    context = await browser.new_context()
    await context.route("**/*", local_only)
    page = await context.new_page()
    page.set_default_timeout(10000)
    return context, page


def fresh_flow():
    return {"nonce": secrets.token_urlsafe(24), "state": secrets.token_urlsafe(24),
            "proof": verifier()}


async def begin(browser, *, admin_api=False):
    global CURRENT
    f = fresh_flow()
    ctx, page = await new_page(browser)
    CURRENT = "browser-authorization-document"
    await page.goto(authorization(OIDC, f["nonce"], f["state"], f["proof"],
                                  admin_api=admin_api))
    CURRENT = "browser-login-form-render"
    await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
    return f, ctx, page


async def fill_login(page, email: str, password: str):
    await page.locator("#username").fill(email)
    await page.locator("#password").fill(password)
    await page.locator("#kc-login").click()


def checked_callback_code(params: dict, flow: dict) -> str:
    # Must execute before exchange in both product-independent positive and
    # deliberately corrupted test callbacks.
    assert params.get("state") == [flow["state"]], "STATE_MISMATCH"
    assert "error" not in params, "CALLBACK_AUTH_ERROR"
    assert len(params.get("code", [])) == 1, "CALLBACK_CODE_COUNT"
    return params["code"][0]


async def checked_callback_exchange(params: dict, flow: dict):
    code = checked_callback_code(params, flow)
    tokens = await asyncio.to_thread(exchange, OIDC, code, flow["proof"])
    return tokens, code


async def authorized(page, cb, flow):
    await page.wait_for_url("http://127.0.0.1:8765/callback*", timeout=20000)
    tokens, code = await checked_callback_exchange(cb.next(), flow)
    claims = await asyncio.to_thread(verify_id, OIDC, tokens["id_token"], flow["nonce"])
    assert claims["email_verified"] is True, "UNVERIFIED_ACCOUNT_ISSUED_ID_TOKEN"
    return tokens, claims, code



async def real_unexchanged_callback(browser, cb, email: str, password: str):
    # A fresh browser-authenticated Code for each destructive scenario.
    flow, ctx, page = await begin(browser)
    await fill_login(page, email, password)
    await page.wait_for_url(CALLBACK + "*", timeout=20000)
    params = cb.next()
    assert checked_callback_code(params, flow), "REAL_CALLBACK_REQUIRED"
    return flow, params, ctx


async def reject_state_variant(browser, cb, email, password, *, absent: bool):
    global CURRENT
    flow, params, ctx = await real_unexchanged_callback(browser, cb, email, password)
    corrupted = dict(params)
    if absent:
        corrupted.pop("state", None)
    else:
        corrupted["state"] = [secrets.token_urlsafe(32)]
        assert corrupted["state"] != params.get("state")
    CURRENT = "negative-oidc-state-missing" if absent else "negative-oidc-state-wrong"
    try:
        # If validation were absent, this would consume the REAL Code.
        await checked_callback_exchange(corrupted, flow)
    except AssertionError as exc:
        assert str(exc) == "STATE_MISMATCH", "WRONG_CALLBACK_REJECTION_STAGE"
    else:
        raise AssertionError("CORRUPTED_STATE_WAS_ACCEPTED")
    # Only a code NOT exchanged by the corrupted callback can still succeed.
    tokens, _ = await checked_callback_exchange(params, flow)
    await asyncio.to_thread(verify_id, OIDC, tokens["id_token"], flow["nonce"])
    await ctx.close()
    case("IDP-A02-missing-state-rejected-before-exchange" if absent else
         "IDP-A01-wrong-state-rejected-before-exchange")


async def oidc_negative_matrix(browser, cb, good_id_token, good_nonce):
    global CURRENT
    await reject_state_variant(browser, cb, EMAILS[0], PASSWORDS[EMAILS[0]], absent=False)
    await reject_state_variant(browser, cb, EMAILS[0], PASSWORDS[EMAILS[0]], absent=True)
    for test_name, overrides, exception_type in (
        ("IDP-A03-wrong-expected-nonce", {"nonce": secrets.token_urlsafe(24)}, AssertionError),
        ("IDP-A04-wrong-expected-issuer",
         {"expected_issuer": OIDC["issuer"] + "/invalid"}, jwt.InvalidIssuerError),
        ("IDP-A05-wrong-expected-audience",
         {"expected_audience": "unregistered-client"}, jwt.InvalidAudienceError),
    ):
        CURRENT = "negative-oidc-claim-" + test_name
        args = dict(overrides)
        nonce = args.pop("nonce", good_nonce)
        try:
            await asyncio.to_thread(verify_id, OIDC, good_id_token, nonce, **args)
        except exception_type:
            pass
        else:
            raise AssertionError("WRONG_EXPECTED_ID_TOKEN_CLAIM_ACCEPTED")
        # Same real signed token MUST pass the genuine expectations.
        await asyncio.to_thread(verify_id, OIDC, good_id_token, good_nonce)
        case(test_name)
    CURRENT = "negative-oidc-wrong-pkce-fresh-code"
    flow, params, ctx = await real_unexchanged_callback(
        browser, cb, EMAILS[0], PASSWORDS[EMAILS[0]])
    code = checked_callback_code(params, flow)
    wrong_proof = verifier()
    assert wrong_proof != flow["proof"], "PKCE_NEGATIVE_NOT_DISTINCT"
    assert await asyncio.to_thread(exchange, OIDC, code, wrong_proof, 400) is None
    await ctx.close()
    case("IDP-A06-fresh-code-wrong-pkce-verifier-rejected")

async def signup(browser, cb, email, password):
    f, ctx, page = await begin(browser)
    before = mail_ids()
    global CURRENT
    CURRENT = "browser-registration-link"
    statuses: list[int] = []
    def capture_registration_response(response):
        if "/login-actions/registration" in urlsplit(response.url).path:
            statuses.append(response.status)  # HTTP status number only
    page.on("response", capture_registration_response)
    await page.locator('#kc-registration a[href*="registration"]').click()
    await page.wait_for_load_state("domcontentloaded")
    CURRENT = "browser-registration-form"
    body_text = (await page.locator("body").inner_text()).casefold()
    RESULTS["registration_response"] = {
        "http_status_codes": statuses[-3:],  # no headers, query or bodies
        "has_body": await page.locator("body").count() > 0,
        "is_error_wording": any(t in body_text for t in (
            "something went wrong", "invalid request", "page not found",
            "we are sorry", "an error has occurred", "unavailable", "error")),
        "is_registration_wording": any(t in body_text for t in (
            "register", "registration", "sign up", "create account")),
        "is_email_wording": "email" in body_text,
        "is_login_wording": any(t in body_text for t in ("sign in", "login")),
        "body_chars_bucket": min(len(body_text) // 100, 30),
    }
    # Keycloak theme changes may use different form IDs; collect only safe
    # category booleans, NEVER the URL/query/HTML/field values/action token.
    RESULTS["registration_screen_shape"] = {
        "on_registration_action_path": "/registration" in urlsplit(page.url).path,
        "kc_register_form_count": await page.locator("#kc-register-form").count(),
        "any_form_count": await page.locator("form").count(),
        "login_form_count": await page.locator("#kc-form-login").count(),
        "registration_form_action_count": await page.locator('form[action*="registration"]').count(),
        "page_error_box_count": await page.locator("#kc-error-message, .alert-error").count(),
    }
    RESULTS["registration_input_visibility"] = {
        "form_visible": await page.locator("#kc-register-form").is_visible(),
        "email_visible": await page.locator('input[name="email"]').first.is_visible(),
        "password_visible": await page.locator('input[name="password"]').first.is_visible(),
    }
    await expect(page.locator('input[name="email"]').first).to_be_visible()
    for field, value in (("firstName", "Synthetic"), ("lastName", "Person"),
                         ("email", email), ("password", password),
                         ("password-confirm", password)):
        item = page.locator('[name="' + field + '"]')
        if await item.count() == 0:
            if field in ("password", "password-confirm"):
                # Keycloak 26.8 defaults to setting credentials only after
                # email verification; do not enable deprecated early-password.
                RESULTS["password_deferred_until_verified_email"] = True
                continue
            if field in ("firstName", "lastName"):
                continue
            raise AssertionError("REQUIRED_REGISTRATION_EMAIL_MISSING")
        await item.fill(value)
    CURRENT = "browser-registration-submit"
    await page.locator('#kc-register-form input[type="submit"], #kc-submit').first.click()
    CURRENT = "smtp-registration-verification"
    await email_after(email, before)
    assert ADMIN.user(email).get("emailVerified") is False, "NEW_USER_PREVERIFIED"
    # Verification required action must block a normal OIDC callback.
    assert cb.server.inbox.empty(), "UNVERIFIED_ACCOUNT_CALLBACK"
    case("IDP-01-register-and-unverified-gate")
    mid, message = await email_after(email, before)
    link = action_url(message)
    CURRENT = "browser-email-verification-link"
    await page.goto(link, wait_until="domcontentloaded")
    CURRENT = "email-verification-db-effect"
    for _ in range(40):
        if ADMIN.user(email).get("emailVerified") is True:
            break
        await asyncio.sleep(0.2)
    assert ADMIN.user(email).get("emailVerified") is True, "EMAIL_VERIFICATION_NOT_COMMITTED"
    case("IDP-02-verify-email-via-local-SMTP")
    if RESULTS.get("password_deferred_until_verified_email"):
        CURRENT = "post-verification-set-password"
        pw_new = page.locator('#password-new, input[name="password-new"]').first
        if not await pw_new.is_visible():
            # An action-token page can end at an explicit confirmation screen.
            # Use Keycloak's documented UPDATE_PASSWORD e-mail action, not
            # privileged admin-set-password, and prove local-only delivery.
            CURRENT = "password-action-email-request"
            prior = mail_ids()
            await asyncio.to_thread(ADMIN.action_mail, ADMIN.user(email)["id"], "UPDATE_PASSWORD")
            CURRENT = "password-action-local-smtp-capture"
            _, action_message = await email_after(email, prior)
            CURRENT = "password-action-browser-link"
            await page.goto(action_url(action_message), wait_until="domcontentloaded")
            RESULTS["initial_password_method"] = "separate local UPDATE_PASSWORD action email"
        CURRENT = "password-action-form-visible"
        await expect(pw_new).to_be_visible(timeout=15000)
        CURRENT = "password-action-form-fill"
        await pw_new.fill(password)
        await page.locator('#password-confirm, input[name="password-confirm"]').first.fill(password)
        CURRENT = "password-action-submit"
        await page.locator(
            '#kc-submit, #kc-passwd-update-form button[type="submit"], '
            '#kc-passwd-update-form input[type="submit"]'
        ).first.click()
        case("IDP-02A-verified-user-sets-password-after-email")
    # Deliberately reuse the consumed action URL once: it must not reissue a
    # second independent verification/recovery privilege.
    ctx2, replay = await new_page(browser)
    await replay.goto(link, wait_until="domcontentloaded")
    assert "code=" not in urlsplit(replay.url).query, "ACTION_REPLAY_CREATED_OIDC_CODE"
    await ctx2.close()
    await ctx.close()
    # Verification may finish the original authorization session and send an
    # actual callback. Drain that flow's code without exchanging it; later
    # logins must be independently bound to their own state and nonce.
    while not cb.server.inbox.empty():
        cb.server.inbox.get_nowait()
    CURRENT = "email-verification-finished"


async def login(browser, cb, email, password, otp=None, expect_failure=False):
    flow, ctx, page = await begin(browser)
    await fill_login(page, email, password)
    if expect_failure:
        global CURRENT
        CURRENT = "invalid-password-form-visible"
        await expect(page.locator("#kc-form-login")).to_be_visible()
        CURRENT = "invalid-password-no-current-flow-callback"
        # The official v2 login theme can render the error outside the
        # legacy .alert-error selectors. The safety property is no callback
        # for THIS state and the login screen remains, not specific CSS text.
        await page.wait_for_load_state("networkidle", timeout=10000)
        assert "/callback" not in urlsplit(page.url).path, "BAD_PASSWORD_REDIRECTED_TO_CALLBACK"
        assert await page.locator("#kc-form-login").is_visible(), "BAD_PASSWORD_LEFT_LOGIN_FORM"
        RESULTS["bad_password_error_indicator_present"] = await page.locator(
            "#input-error, #kc-error-message, [role=alert], .alert-error, "
            "[class*=alert-danger], [class*=pf-v5-c-alert], [class*=pf-c-alert]"
        ).first.is_visible()
        # A previous successful reset or registration can finish its OWN
        # earlier browser authorization. Only a code for THIS invalid login
        # would prove a bypass. Never exchange any unexpected callback.
        while not cb.server.inbox.empty():
            callback = cb.server.inbox.get_nowait()
            assert callback.get("state") != [flow["state"]], "INVALID_PASSWORD_CALLBACK"
        await ctx.close()
        return None
    if otp is not None:
        selector = page.locator('#otp, input[name="otp"], #totp').first
        await expect(selector).to_be_visible(timeout=12000)
        await selector.fill(otp)
        await page.locator("#kc-login, #kc-login-otp, #kc-form-login input[type=submit]").first.click()
    tokens, claims, code = await authorized(page, cb, flow)
    return ctx, page, tokens, claims, code, flow


async def reset_password(browser, cb, email: str, old: str, new: str):
    global CURRENT
    flow, context, page = await begin(browser)
    old_messages = mail_ids()
    CURRENT = "reset-forgot-password-link"
    await page.locator('a[href*="reset-credentials"]').first.click()
    CURRENT = "reset-request-form"
    await expect(page.locator("#kc-reset-password-form")).to_be_visible(timeout=10000)
    await page.locator('#kc-reset-password-form input[name="username"]').fill(email)
    CURRENT = "reset-request-submit"
    await page.locator('#kc-reset-password-form #kc-form-buttons, #kc-reset-password-form button[type="submit"], #kc-reset-password-form input[type="submit"]').first.click()
    CURRENT = "reset-smtp-email"
    _, message = await email_after(email, old_messages)
    link = action_url(message)
    CURRENT = "reset-browser-action-link"
    await page.goto(link)
    CURRENT = "reset-password-form"
    pw = page.locator('#password-new, input[name="password-new"]').first
    await expect(pw).to_be_visible(timeout=15000)
    await pw.fill(new)
    await page.locator('#password-confirm, input[name="password-confirm"]').first.fill(new)
    CURRENT = "reset-password-submit"
    await page.locator('#kc-submit, #kc-passwd-update-form button[type="submit"], #kc-passwd-update-form input[type="submit"]').first.click()
    await page.wait_for_load_state("domcontentloaded")
    # The one-time reset URL cannot be used to perform the same operation again.
    CURRENT = "reset-consumed-link-denial"
    rctx, again = await new_page(browser)
    await again.goto(link, wait_until="domcontentloaded")
    assert not await again.locator("#password-new").count(), "CONSUMED_RESET_TOKEN_REUSED"
    await rctx.close()
    await context.close()
    case("IDP-06-forgot-reset-once")
    # Completing a valid password-reset action can finish its *original*
    # authorization request. Consume only that flow's callback; a later
    # bad-password login must be judged against its own fresh callback.
    CURRENT = "reset-drain-original-callback"
    while not cb.server.inbox.empty():
        original_callback = cb.server.inbox.get_nowait()
        assert original_callback.get("state") == [flow["state"]], "UNEXPECTED_RESET_CALLBACK_ORIGIN"
    CURRENT = "reset-old-password-negative"
    await login(browser, cb, email, old, expect_failure=True)
    case("IDP-07-old-password-denied-after-reset")
    logged = await login(browser, cb, email, new)
    assert logged is not None
    case("IDP-08-new-password-login")
    await logged[0].close()



async def old_browser_sso(ctx, cb) -> bool:
    flow = fresh_flow()
    page = await ctx.new_page()
    try:
        await page.goto(authorization(OIDC, flow["nonce"], flow["state"],
                                      flow["proof"], prompt_login=False),
                        wait_until="domcontentloaded")
        await page.wait_for_url(CALLBACK + "*", timeout=12000)
        params = cb.next()
        assert params.get("state") == [flow["state"]], "SSO_STATE_MISMATCH"
        if "error" in params:
            assert params["error"] in (["login_required"], ["interaction_required"]), "UNEXPECTED_SSO_ERROR"
            assert not params.get("code"), "SSO_ERROR_WITH_CODE"
            return False
        tokens, _ = await checked_callback_exchange(params, flow)
        claims = await asyncio.to_thread(verify_id, OIDC, tokens["id_token"], flow["nonce"])
        assert claims["email_verified"] is True, "SSO_UNVERIFIED_USER"
        return True
    finally:
        await page.close()


async def observe_after_reset(browser, cb, context, old_tokens):
    global CURRENT
    CURRENT = "reset-old-browser-sso"
    # Probe BEFORE refresh so a successful refresh cannot revive the
    # very browser SSO session we are measuring.
    sso = await old_browser_sso(context, cb)
    CURRENT = "reset-old-refresh"
    refresh_status = await asyncio.to_thread(refresh, OIDC, old_tokens["refresh_token"])
    assert refresh_status in (200, 400, 401), "UNEXPECTED_RESET_REFRESH_STATUS"
    CURRENT = "reset-old-userinfo"
    userinfo_status = (await asyncio.to_thread(request,
        "GET", OIDC["userinfo_endpoint"],
        headers={"Authorization": "Bearer " + old_tokens["access_token"]})).status_code
    assert userinfo_status in (200, 401, 403), "UNEXPECTED_RESET_USERINFO_STATUS"
    CURRENT = "reset-old-access-local-jwt"
    signed = False
    try:
        jwk = jwt.PyJWKClient(OIDC["jwks_uri"]).get_signing_key_from_jwt(old_tokens["access_token"]).key
        decoded = jwt.decode(old_tokens["access_token"], jwk, algorithms=["RS256"],
                             issuer=OIDC["issuer"],
                             options={"verify_aud": False, "require": ["exp", "iss"]})
        assert decoded["exp"] > datetime.now(timezone.utc).timestamp(), "OLD_TOKEN_EXPIRED_DURING_PROBE"
        signed = True
    except jwt.InvalidTokenError:
        signed = False
    assert isinstance(sso, bool) and isinstance(signed, bool), "INVALID_RESET_OBSERVATION"
    RESULTS["after_password_reset"] = {
        "old_browser_silent_oidc_login_without_new_password": sso,
        "old_refresh_http": refresh_status,
        "old_userinfo_http": userinfo_status,
        "old_access_jwt_signature_valid_before_expiry": signed,
        "policy": "observe-only: reset is not assumed to revoke independent JWT, refresh or browser session",
        "admin_forced_logout_used_for_reset_test": False,
        "product_bff_session_tested": False,
    }
    case("IDP-B01-reset-observed-old-browser-refresh-userinfo-and-jwt")

async def expired_action(browser, email):
    global CURRENT
    CURRENT = "expired-action-email-request"
    seen = mail_ids()
    uid = ADMIN.user(email)["id"]
    await asyncio.to_thread(ADMIN.action_mail, uid, "UPDATE_PASSWORD", 1)
    CURRENT = "expired-action-email-capture"
    _, msg = await email_after(email, seen)
    link = action_url(msg)
    await asyncio.sleep(2.2)  # expiry tested by real link rejection, not just time alone
    ctx, page = await new_page(browser)
    CURRENT = "expired-action-browser-denial"
    await page.goto(link, wait_until="domcontentloaded")
    assert not await page.locator("#password-new").count(), "EXPIRED_RESET_ALLOWED"
    await ctx.close()
    case("IDP-09-expired-reset-link-denied")



async def password_policy_and_lockout(browser, cb):
    global CURRENT
    CURRENT = "policy-create-ephemeral-account"
    uid = ADMIN.create_policy_probe(POLICY)
    previous = mail_ids()
    await asyncio.to_thread(ADMIN.action_mail, uid, "UPDATE_PASSWORD")
    CURRENT = "policy-local-update-password-email"
    _, msg = await email_after(POLICY, previous)
    ctx, page = await new_page(browser)
    await page.goto(action_url(msg), wait_until="domcontentloaded")
    fields = '#password-new, input[name="password-new"]'
    await expect(page.locator(fields).first).to_be_visible(timeout=15000)
    CURRENT = "policy-submit-weak-password"
    await page.locator(fields).first.fill("weak")
    await page.locator('#password-confirm, input[name="password-confirm"]').first.fill("weak")
    await page.locator('#kc-submit, #kc-passwd-update-form button[type="submit"], #kc-passwd-update-form input[type="submit"]').first.click()
    await expect(page.locator(fields).first).to_be_visible(timeout=12000)
    assert "/callback" not in urlsplit(page.url).path, "WEAK_PASSWORD_COMPLETED_ACTION"
    # A weak rejected submission leaves the SAME required update action
    # available to complete with a password satisfying all four policies.
    CURRENT = "policy-submit-compliant-password"
    await page.locator(fields).first.fill(PASSWORDS[POLICY])
    await page.locator('#password-confirm, input[name="password-confirm"]').first.fill(PASSWORDS[POLICY])
    await page.locator('#kc-submit, #kc-passwd-update-form button[type="submit"], #kc-passwd-update-form input[type="submit"]').first.click()
    await ctx.close()
    # Action-email completion can leave a callback from its own flow.
    # Consume only non-exchanged callbacks and never use them as login proof.
    while not cb.server.inbox.empty():
        prior = cb.server.inbox.get_nowait()
        assert not prior.get("code"), "UNEXPECTED_POLICY_CALLBACK_CODE"
    CURRENT = "policy-valid-password-independent-login"
    valid = await login(browser, cb, POLICY, PASSWORDS[POLICY])
    assert valid[3]["email_verified"] is True
    await valid[0].close()
    CURRENT = "policy-weak-password-independent-denial"
    await login(browser, cb, POLICY, "weak", expect_failure=True)
    case("IDP-C01-weak-password-rejected-and-strong-password-login")
    # Separate bounded failures, all against synthetic policy-probe only.
    CURRENT = "policy-brute-force-negative-logins"
    counts = []
    locked = False
    for attempt in range(7):
        await asyncio.sleep(1.2)  # keep successive attempts > quick-login threshold
        await login(browser, cb, POLICY, "definitely-not-the-correct-password",
                    expect_failure=True)
        state = ADMIN.brute_force_status(uid)
        counts.append(state["numFailures"])
        if state["disabled"] is True:
            locked = True
            break
    assert locked, "TEMPORARY_LOCKOUT_NOT_OBSERVED"
    assert len(counts) <= 7 and len(counts) >= 1, "FAILURE_ATTEMPT_BOUND_BROKEN"
    assert max(counts) >= 1, "BRUTE_FORCE_FAILURE_NOT_COUNTED"
    CURRENT = "policy-valid-password-while-locked"
    assert ADMIN.brute_force_status(uid)["disabled"] is True, "LOCK_EXPIRED_BEFORE_VALID_NEGATIVE"
    await login(browser, cb, POLICY, PASSWORDS[POLICY], expect_failure=True)
    assert ADMIN.brute_force_status(uid)["disabled"] is True, "LOCK_EXPIRED_BEFORE_DENIAL_CONFIRMED"
    case("IDP-C02-bounded-failed-logins-and-locked-good-password-denied")
    CURRENT = "policy-natural-unlock-no-admin-clear"
    unlocked = False
    for _ in range(100):
        state = ADMIN.brute_force_status(uid)
        if state["disabled"] is False:
            unlocked = True
            break
        await asyncio.sleep(0.25)
    assert unlocked, "LOCK_NOT_RELEASED_WITHIN_25_SECONDS"
    recovered = await login(browser, cb, POLICY, PASSWORDS[POLICY])
    assert recovered[3]["email_verified"] is True
    await recovered[0].close()
    RESULTS["brute_force_behavior"] = {
        "wrong_password_attempts": len(counts),
        "observed_max_failure_count": max(counts),
        "disabled_observed": locked,
        "correct_password_denied_while_disabled": True,
        "natural_recovery_without_admin_clear": unlocked,
        "successful_login_after_natural_unlock": True,
        "wait_increment_config_seconds": 12,
        "max_wait_config_seconds": 30,
        "failure_factor_config": 5,
    }
    case("IDP-C03-temporary-lockout-natural-release-and-login")

async def manager(browser, cb):
    global CURRENT
    CURRENT = "manager-provision-minimal-role"
    pw = PASSWORDS[MANAGER]
    uid = ADMIN.create_manager(MANAGER, pw)
    flow, ctx, page = await begin(browser)
    await fill_login(page, MANAGER, pw)
    # Required action CONFIGURE_TOTP must block the callback.
    CURRENT = "manager-mfa-required-action"
    await expect(page.locator("#kc-totp-settings-form")).to_be_visible(timeout=12000)
    assert cb.server.inbox.empty(), "MANAGER_MFA_NOT_REQUIRED"
    CURRENT = "manager-mfa-seed-setup"
    await page.locator("#mode-manual").click()
    seed = (await page.locator("#kc-totp-secret-key").inner_text()).replace(" ", "")
    enrollment_counter = int(time.time()) // 30
    code = pyotp.TOTP(seed).now()
    await page.locator("#totp").fill(code)
    name = page.locator("#userLabel")
    if await name.count():
        await name.fill("ci-only-manager")
    await page.locator("#saveTOTPBtn").click()
    CURRENT = "manager-mfa-enrollment-submit"
    tokens, claims, _ = await authorized(page, cb, flow)
    assert claims["email"] == MANAGER
    case("IDP-10-manager-mfa-enrollment-required")
    await ctx.close()
    # Password alone must never get an OIDC callback after enrollment.
    flow2, ctx2, page2 = await begin(browser)
    CURRENT = "manager-mfa-relogin"
    await fill_login(page2, MANAGER, pw)
    otp_input = page2.locator('#otp, input[name="otp"]').first
    await expect(otp_input).to_be_visible(timeout=12000)
    assert cb.server.inbox.empty(), "MANAGER_PASSWORD_ONLY_BYPASS"
    await otp_input.fill("000000" if pyotp.TOTP(seed).now() != "000000" else "999999")
    await page2.locator("#kc-login").click()
    await expect(page2.locator('#otp, input[name="otp"]').first).to_be_visible()
    assert cb.server.inbox.empty(), "MANAGER_BAD_OTP_ACCEPTED"
    # A rejected OTP can alter/terminate that authentication session. A
    # fresh Code+PKCE/state context must prove positive valid MFA independently.
    await ctx2.close()
    # Only this real manager OIDC login requests the optional Admin REST scope.
    flow3, ctx3, page3 = await begin(browser, admin_api=True)
    CURRENT = "manager-mfa-fresh-valid-login"
    await fill_login(page3, MANAGER, pw)
    valid_otp_field = page3.locator('#otp, input[name="otp"]').first
    await expect(valid_otp_field).to_be_visible(timeout=12000)
    # OATH HOTP/TOTP replay controls may reject the SAME time-step OTP
    # already consumed during enrollment. Wait for a NEW counter, bounded.
    CURRENT = "manager-mfa-wait-fresh-totp-counter"
    for _ in range(70):
        if int(time.time()) // 30 > enrollment_counter:
            break
        await asyncio.sleep(0.5)
    assert int(time.time()) // 30 > enrollment_counter, "OTP_COUNTER_DID_NOT_ADVANCE"
    valid_otp = pyotp.TOTP(seed).now()
    assert valid_otp != code, "OTP_ENROLLMENT_CODE_REUSED"
    RESULTS["manager_otp_new_counter"] = True
    await valid_otp_field.fill(valid_otp)
    await page3.locator("#kc-login").click()
    CURRENT = "manager-mfa-valid-otp-callback"
    manager_tokens, _, _ = await authorized(page3, cb, flow3)
    case("IDP-11-manager-mfa-no-password-only-bypass")
    await ctx3.close()
    # This intentionally uses a minimal realm-management role, not realm-admin.
    url = BASE + "/admin/realms/" + REALM + "/users"
    CURRENT = "manager-minimal-admin-rest"
    granted = request("GET", url, headers={"Authorization": "Bearer " + manager_tokens["access_token"]})
    safe_claims = jwt.decode(manager_tokens["access_token"], options={"verify_signature": False})
    RESULTS["manager_role_diagnostic"] = {
        "admin_get_status": granted.status_code,
        "has_view_users_client_role": "view-users" in
          safe_claims.get("resource_access", {}).get("realm-management", {}).get("roles", []),
        "has_query_users_client_role": "query-users" in
          safe_claims.get("resource_access", {}).get("realm-management", {}).get("roles", []),
        "audience_has_realm_management": "realm-management" in
          ([safe_claims.get("aud")] if isinstance(safe_claims.get("aud"), str) else safe_claims.get("aud", [])),
        "scope_has_kc_admin_api": "kc-admin-api" in safe_claims.get("scope", "").split(),
        "audience_has_admin_rest_url": (BASE + "/admin/realms/" + REALM) in
          ([safe_claims.get("aud")] if isinstance(safe_claims.get("aud"), str) else safe_claims.get("aud", [])),
    }
    assert RESULTS["manager_role_diagnostic"]["scope_has_kc_admin_api"], "ADMIN_API_SCOPE_MISSING_IN_TOKEN"
    assert RESULTS["manager_role_diagnostic"]["audience_has_admin_rest_url"], "ADMIN_REST_AUDIENCE_MISSING"
    assert granted.status_code == 200, "MANAGER_LIMITED_ROLE_DENIED"
    case("IDP-12-manager-minimal-role")
    return uid, manager_tokens


async def run(browser, cb):
    global ADMIN, OIDC
    ADMIN = Admin()
    ADMIN.create_realm()
    OIDC = discovery()
    case("IDP-00-realm-policy-and-OIDC-discovery")

    # Two users must self-register, complete real email actions, and log in via
    # the browser Authorization Code + PKCE flow. Never token-inject a user.
    for email in EMAILS:
        await signup(browser, cb, email, PASSWORDS[email])
    first = await login(browser, cb, EMAILS[0], PASSWORDS[EMAILS[0]])
    second = await login(browser, cb, EMAILS[1], PASSWORDS[EMAILS[1]])
    assert first[3]["sub"] != second[3]["sub"]
    assert first[3]["email"] == EMAILS[0] and second[3]["email"] == EMAILS[1]
    case("IDP-03-two-distinct-real-OIDC-logins")
    assert refresh(OIDC, first[2]["refresh_token"]) == 200
    case("IDP-04-real-refresh-valid-before-logout")
    # A second exchange of an already-used authorization code must be rejected.
    assert exchange(OIDC, first[4], first[5]["proof"], allowed=400) is None
    case("IDP-05-auth-code-replay-denied")
    # Signature/iss/aud/nonce validation is performed for every real id_token;
    # tampered signatures and mismatched audience/issuer/nonce must fail.
    tok = first[2]["id_token"]
    changed = tok[:-3] + ("AAA" if tok[-3:] != "AAA" else "BBB")
    for payload, expected_nonce in ((changed, first[5]["nonce"]),
                                    (tok, "wrong-nonce")):
        try:
            verify_id(OIDC, payload, expected_nonce)
        except (jwt.InvalidTokenError, AssertionError):
            pass
        else:
            raise AssertionError("TAMPERED_TOKEN_OR_NONCE_ACCEPTED")
    case("IDP-13-signature-issuer-audience-nonce-validation")
    # Real malicious callback variants and separate unspent PKCE Code.
    await oidc_negative_matrix(browser, cb, tok, first[5]["nonce"])
    # Server itself must reject an unregistered redirect URI.
    bad = request("GET", OIDC["authorization_endpoint"], params={
        "client_id": CLIENT, "response_type": "code", "scope": "openid",
        "redirect_uri": "http://127.0.0.1:8766/not-authorized",
        "state": secrets.token_urlsafe(24), "nonce": secrets.token_urlsafe(24),
        "code_challenge": "abc", "code_challenge_method": "S256",
    })
    assert bad.status_code in (400, 403), "OPEN_REDIRECT_NOT_REJECTED"
    case("IDP-14-redirect-allowlist")
    user_url = BASE + "/admin/realms/" + REALM + "/users"
    forbidden = request("GET", user_url, headers={"Authorization": "Bearer " + first[2]["access_token"]})
    # Keycloak Admin REST can reject a user token with 401 (not an admin
    # audience) or 403 (authenticated without realm-management role).
    # Both are denial; 2xx is NEVER accepted.
    assert forbidden.status_code in (401, 403), "ORDINARY_USER_ADMIN_PRIVILEGE"
    RESULTS["ordinary_user_admin_http"] = forbidden.status_code
    ordinary_claims = jwt.decode(first[2]["access_token"],
                                 options={"verify_signature": False})
    RESULTS["ordinary_user_requested_admin_api_scope"] = (
        "kc-admin-api" in ordinary_claims.get("scope", "").split())
    assert not RESULTS["ordinary_user_requested_admin_api_scope"], "ORDINARY_ADMIN_SCOPE_LEAK"
    case("IDP-15-ordinary-user-cannot-administer-realm")

    # Force IdP logout of the real first user session. A signed JWT is not a
    # revocable BFF session; introspection/userinfo/refresh differ.
    uid = ADMIN.user(EMAILS[0])["id"]
    access = first[2]["access_token"]
    claims = jwt.decode(access, options={"verify_signature": False})
    assert claims["exp"] > datetime.now(timezone.utc).timestamp()
    ADMIN.logout_user(uid)
    after_refresh = refresh(OIDC, first[2]["refresh_token"])
    after_userinfo = request("GET", OIDC["userinfo_endpoint"],
                             headers={"Authorization": "Bearer " + access}).status_code
    assert after_refresh in (400, 401), "REVOKED_REFRESH_ACCEPTED"
    assert after_userinfo in (401, 403), "LOGOUT_USERINFO_NOT_DENIED"
    jwt_local_signed = False
    try:
        key = jwt.PyJWKClient(OIDC["jwks_uri"]).get_signing_key_from_jwt(access).key
        jwt.decode(access, key, algorithms=["RS256"], issuer=OIDC["issuer"],
                   options={"verify_aud": False, "require": ["exp", "iss"]})
        jwt_local_signed = True
    except jwt.InvalidTokenError:
        pass
    RESULTS["revocation"] = {
        "type": "IdP admin-initiated session logout",
        "old_refresh_http": after_refresh,
        "old_userinfo_http": after_userinfo,
        "old_access_JWT_signature_valid_until_expiry": jwt_local_signed,
        "access_lifetime_configuration_seconds": 180,
        "product_BFF_session_tested": False,
        "token_introspection_tested": False,
    }
    case("IDP-16-logout-distinguishes-access-refresh-session")
    await first[0].close()
    await second[0].close()

    # B: a separate pre-reset REAL OIDC login stays in its original
    # Chromium context; its tokens and cookies are not overwritten by reset.
    CURRENT = "reset-independent-preexisting-login"
    pre_reset = await login(browser, cb, EMAILS[1], PASSWORDS[EMAILS[1]])
    assert await old_browser_sso(pre_reset[0], cb), "PRE_RESET_SSO_WAS_NOT_ESTABLISHED"
    case("IDP-B00-old-browser-sso-established-before-reset")
    await reset_password(browser, cb, EMAILS[1], PASSWORDS[EMAILS[1]], PASSWORDS["reset"])
    await observe_after_reset(browser, cb, pre_reset[0], pre_reset[2])
    await pre_reset[0].close()
    await expired_action(browser, EMAILS[1])
    await password_policy_and_lockout(browser, cb)
    uid, manager_tokens = await manager(browser, cb)
    case("IDP-17-admin-actor-is-not-unbounded-superuser",
         "realm-management view-users only; no admin panel or product scope")

    # Never confuse action-password reset with revocation of all access JWTs.
    RESULTS["reset_limit"] = "Reset effects on preexisting browser SSO, old refresh, UserInfo and locally signed JWT are separately measured under after_password_reset; product BFF revocation remains out of scope."
    RESULTS["compatibility"] = "Keycloak 26.8.2 + PostgreSQL 17.11 + Mailpit 1.32.0; test-only localhost HTTP; no production TLS/BFF/RLS"


def safe_report(success: bool):
    path = Path(os.environ.get("IDP_REPORT", "/nonexistent"))
    if os.environ.get("CI") != "true" or str(path) != "/evidence/report.json":
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "mission": "AGENT-API-AUTH-IDP-01",
        "candidate": "Keycloak 26.8.2",
        "identity_database": "PostgreSQL 17.11 (separate, disposable)",
        "smtp": "Mailpit v1.32.0 (Docker internal, only capture)",
        "browser": "Playwright 1.64.1 Chromium",
        "ci_only": True, "product_auth": False, "product_rls": False,
        "m05_gate_accepted": False,
        "overall": "PASS" if success else "FAIL",
        "current_stage": CURRENT,
        "cases": STAGES,
        "nonsecret_facts": RESULTS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


async def main():
    global CURRENT
    require_ci()
    # All test credentials are synthetic and ephemeral; never print or save.
    for email in (*EMAILS, MANAGER, POLICY):
        PASSWORDS[email] = "Qx9!" + secrets.token_urlsafe(18)
    PASSWORDS["reset"] = "Zp7!" + secrets.token_urlsafe(18)
    try:
        with CallbackServer() as cb:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    CURRENT = "real_idp_integration"
                    await run(browser, cb)
                finally:
                    await browser.close()
        CURRENT = "completed"
        safe_report(True)
        print("ISOLATED_IDP_EVALUATION_PASS", flush=True)
    except Exception as exc:
        # NEVER include Playwright errors, captured links, cookies, token strings,
        # HTTP response bodies or caller URLs in stdout / artifact.
        STAGES[CURRENT] = "FAIL"
        try:
            safe_report(False)
        except OSError:
            # A permissions failure should never dump paths/credential context
            # or a second exception traceback to public CI logs.
            print("SANITIZED_REPORT_WRITE_FAILED", flush=True)
        print("ISOLATED_IDP_EVALUATION_FAIL stage=" + CURRENT +
              " category=" + type(exc).__name__, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
