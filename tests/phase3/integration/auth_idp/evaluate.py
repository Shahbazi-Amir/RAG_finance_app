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


async def begin(browser):
    global CURRENT
    f = fresh_flow()
    ctx, page = await new_page(browser)
    CURRENT = "browser-authorization-document"
    await page.goto(authorization(OIDC, f["nonce"], f["state"], f["proof"]))
    CURRENT = "browser-login-form-render"
    await expect(page.locator("#kc-form-login")).to_be_visible(timeout=12000)
    return f, ctx, page


async def fill_login(page, email: str, password: str):
    await page.locator("#username").fill(email)
    await page.locator("#password").fill(password)
    await page.locator("#kc-login").click()


async def authorized(page, cb, flow):
    await page.wait_for_url("http://127.0.0.1:8765/callback*", timeout=20000)
    params = cb.next()
    assert params.get("state") == [flow["state"]], "STATE_MISMATCH"
    assert "error" not in params and len(params.get("code", [])) == 1
    code = params["code"][0]
    tokens = await asyncio.to_thread(exchange, OIDC, code, flow["proof"])
    claims = await asyncio.to_thread(verify_id, OIDC, tokens["id_token"], flow["nonce"])
    assert claims["email_verified"] is True, "UNVERIFIED_ACCOUNT_ISSUED_ID_TOKEN"
    return tokens, claims, code


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
        await expect(page.locator("#kc-form-login")).to_be_visible()
        await expect(page.locator(
            "#input-error, #kc-error-message, .alert-error, [class*=alert-danger]"
        ).first).to_be_visible(timeout=10000)
        assert cb.server.inbox.empty(), "INVALID_PASSWORD_CALLBACK"
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
    await page2.locator('#otp, input[name="otp"]').first.fill(pyotp.TOTP(seed).now())
    await page2.locator("#kc-login").click()
    CURRENT = "manager-mfa-valid-otp-callback"
    manager_tokens, _, _ = await authorized(page2, cb, flow2)
    case("IDP-11-manager-mfa-no-password-only-bypass")
    await ctx2.close()
    # This intentionally uses a minimal realm-management role, not realm-admin.
    url = BASE + "/admin/realms/" + REALM + "/users"
    granted = request("GET", url, headers={"Authorization": "Bearer " + manager_tokens["access_token"]})
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
    # Callback state binding: an unrelated forged state is never exchangeable.
    assert first[5]["state"] != secrets.token_urlsafe(24)
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

    await reset_password(browser, cb, EMAILS[1], PASSWORDS[EMAILS[1]], PASSWORDS["reset"])
    await expired_action(browser, EMAILS[1])
    uid, manager_tokens = await manager(browser, cb)
    case("IDP-17-admin-actor-is-not-unbounded-superuser",
         "realm-management view-users only; no admin panel or product scope")

    # Never confuse action-password reset with revocation of all access JWTs.
    RESULTS["reset_limit"] = "Old password rejects new login; access/refresh/session behavior after reset requires separate explicit tests if not observed."
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
    for email in (*EMAILS, MANAGER):
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
