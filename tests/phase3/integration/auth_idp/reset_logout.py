"""BND-IDP-02B: isolated Keycloak 26.8.2 standard logout and password routes.

Only imported by the existing evaluation in the ephemeral Docker runner.
No product endpoint, SPI, external network service or database side effect.
Never print / persist a JWT, Cookie, email address, action link or session id.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import re
import threading
import time
from urllib.parse import urlencode, urlsplit

import jwt
import requests
from playwright.async_api import expect, TimeoutError as PlaywrightTimeoutError

from support import BASE, CLIENT, REALM, refresh, request, verify_id

LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"
RECEIVER_PORT = 8788
RECEIVER_HOST = "idp-logout-receiver"
RECEIVER_URL = "http://" + RECEIVER_HOST + ":" + str(RECEIVER_PORT) + "/logout"


def logout_claim_policy(claims: dict, *, now: int) -> None:
    """Post-signature policy. May also be tested on mutated *copies* of claims."""
    if not isinstance(claims, dict):
        raise ValueError("INVALID_LOGOUT_CLAIMS")
    if claims.get("events") != {LOGOUT_EVENT: {}} or "nonce" in claims:
        raise ValueError("INVALID_LOGOUT_EVENTS_OR_NONCE")
    if not any(isinstance(claims.get(k), str) and claims[k]
               for k in ("sid", "sub")):
        raise ValueError("LOGOUT_IDENTITY_REQUIRED")
    if (not isinstance(claims.get("jti"), str)
            or len(claims["jti"]) < 8):
        raise ValueError("LOGOUT_JTI_REQUIRED")
    iat, exp = claims.get("iat"), claims.get("exp")
    if (type(iat) is not int or type(exp) is not int
            or iat > now + 5 or iat < now - 300
            or exp <= now or exp <= iat or exp - iat > 180):
        raise ValueError("LOGOUT_TIME_INVALID")


class IsolatedLogoutReceiver:
    """A test-only client-side recipient; no product or persistent state."""

    def __init__(self, oidc: dict):
        self.oidc = oidc
        self.lock = threading.Lock()
        self.seen = set()
        self.received: list[tuple[str, dict]] = []  # RAM only: token never logged
        self.rejections = 0
        self.server = None
        self.worker = None
        self.alive = False

    def verify(self, compact: str, *, expected_issuer=None, expected_audience=None):
        header = jwt.get_unverified_header(compact)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise ValueError("LOGOUT_ALGORITHM_DENIED")
        key = jwt.PyJWKClient(self.oidc["jwks_uri"]).get_signing_key_from_jwt(compact).key
        claims = jwt.decode(compact, key, algorithms=["RS256"],
            audience=CLIENT if expected_audience is None else expected_audience,
            issuer=self.oidc["issuer"] if expected_issuer is None else expected_issuer,
            leeway=0, options={"require": ["iss","aud","iat","exp","jti"]})
        logout_claim_policy(claims, now=int(time.time()))
        return claims

    def handle(self, body: bytes, content_type: str):
        if (not content_type.startswith("application/x-www-form-urlencoded")
                or len(body) > 16384 or not body):
            with self.lock:
                self.rejections += 1
            return 400
        from urllib.parse import parse_qs
        params = parse_qs(body.decode("ascii", errors="replace"),
                          keep_blank_values=True, max_num_fields=5)
        value = params.get("logout_token")
        if set(params) != {"logout_token"} or not value or len(value) != 1:
            with self.lock:
                self.rejections += 1
            return 400
        compact = value[0]
        try:
            claims = self.verify(compact)
        except (jwt.PyJWTError, ValueError, KeyError, TypeError, OSError):
            with self.lock:
                self.rejections += 1
            return 400
        with self.lock:
            if claims["jti"] in self.seen:
                self.rejections += 1
                return 409
            self.seen.add(claims["jti"])
            self.received.append((compact, claims))
        return 204

    def start(self):
        if self.server is not None:
            raise AssertionError("RECEIVER_ALREADY_RUNNING")
        obj = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/logout":
                    self.send_response(404)
                    self.end_headers()
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                    if length < 1 or length > 16384:
                        status = 400
                    else:
                        status = obj.handle(self.rfile.read(length),
                                            self.headers.get("Content-Type", ""))
                except (ValueError, TypeError, OSError):
                    status = 400
                self.send_response(status)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", "0")
                self.end_headers()
            def log_message(self, *_):
                pass  # NEVER log raw POST, headers or Logout Token
        self.server = ThreadingHTTPServer(("0.0.0.0", RECEIVER_PORT), Handler)
        self.server.daemon_threads = True
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.alive = True

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.worker.join(timeout=4)
            self.server = None
            self.worker = None
        self.alive = False

    def snapshot(self):
        with self.lock:
            return len(self.received)

    async def wait_increase(self, before, seconds=6):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.snapshot() > before:
                return True
            await asyncio.sleep(0.1)
        return self.snapshot() > before

    def latest(self):
        with self.lock:
            if not self.received:
                raise AssertionError("NO_STANDARD_BACKCHANNEL_TOKEN_RECEIVED")
            return self.received[-1]


def configure_backchannel(admin):
    clients = admin.call("GET", "/clients", params={"clientId":CLIENT}).json()
    assert len(clients) == 1, "CI_OIDC_CLIENT_MISSING"
    cid = clients[0]["id"]
    original = admin.call("GET", "/clients/" + cid).json()
    updated = deepcopy(original)
    updated["frontchannelLogout"] = False
    attrs = dict(updated.get("attributes") or {})
    attrs.update({"backchannel.logout.url": RECEIVER_URL,
                  "backchannel.logout.session.required": "true"})
    updated["attributes"] = attrs
    admin.call("PUT", "/clients/" + cid, json=updated, expected=204)
    readback = admin.call("GET", "/clients/" + cid).json()
    assert readback.get("frontchannelLogout") is False
    assert readback.get("attributes", {}).get("backchannel.logout.url") == RECEIVER_URL
    assert readback.get("attributes", {}).get("backchannel.logout.session.required") == "true"
    # Keycloak built-in DB event storage: observation only, NOT an outbox.
    admin.call("PUT", "", json={"eventsEnabled": True,
                                "adminEventsEnabled": True,
                                "adminEventsDetailsEnabled": False}, expected=204)
    current = admin.call("GET", "").json()
    assert current.get("eventsEnabled") is True
    return cid


def user_events(admin, uid):
    """Observe only safe event type enums. Event Store != delivery guarantee."""
    events = admin.call("GET", "/events", params={"max":200}).json()
    return sorted(str(x.get("type")) for x in events if x.get("userId") == uid)


async def snapshot_old(e, cb, old, label):
    """Never refresh before measuring original browser SSO."""
    sso = await e.old_browser_sso(old[0], cb)
    old_refresh = await asyncio.to_thread(refresh, e.OIDC, old[2]["refresh_token"])
    old_userinfo = (await asyncio.to_thread(request, "GET",
        e.OIDC["userinfo_endpoint"], headers={
            "Authorization": "Bearer " + old[2]["access_token"]
        })).status_code
    assert old_refresh in (200,400,401)
    assert old_userinfo in (200,401,403)
    return {"old_sso_prompt_none_code": sso,
            "old_refresh_http": old_refresh, "old_userinfo_http": old_userinfo,
            "product_session_tested": False, "automatic_product_revoke": "NOT_PROVEN"}


async def changed_password_verified(e, browser, cb, email, old, new):
    await e.login(browser, cb, email, old, expect_failure=True)
    latest = await e.login(browser, cb, email, new)
    assert latest is not None
    await latest[0].close()


async def _visible_matches(locator):
    """Inspect ALL matching elements; never assume .first is visible."""
    count = await locator.count()
    visible = []
    for i in range(count):
        item = locator.nth(i)
        if await item.is_visible() and await item.is_enabled():
            visible.append(i)
    return {"total": count, "visible_enabled": len(visible)}, visible


def _account_resource_category(url: str) -> str:
    """Static route categories only: never return URL, query or token."""
    path = urlsplit(url).path
    if "/realms/" in path and "/account/" in path:
        if path.endswith((".js", ".mjs", ".css")):
            return "account_asset"
        if "/account/resources/" in path:
            return "account_api"
        return "account_document_or_api"
    if "/resources/" in path:
        return "theme_or_spa_asset"
    if "/protocol/openid-connect/" in path:
        return "oidc"
    if "/login-actions/" in path:
        return "login_action"
    return "other_internal"


async def _account_ui_state(page, responses, script_errors, request_failures):
    selectors = {
        "update_buttons": page.get_by_role("button", name="Update", exact=True),
        "update_links": page.get_by_role("link", name="Update", exact=True),
        "signing_links": page.locator('a[href*="signing-in"]'),
        "security_links": page.locator('a[href*="account-security"]'),
        "menu_buttons": page.get_by_role(
            "button", name=re.compile(r"menu|navigation|sidebar|toggle", re.I)),
        "expanded_buttons": page.locator('button[aria-expanded="false"]'),
        "password_new": page.locator('#password-new, input[name="password-new"]'),
        "login_form": page.locator("#kc-form-login"),
    }
    matches = {}
    usable = {}
    for name, locator in selectors.items():
        matches[name], usable[name] = await _visible_matches(locator)
    status_summary = {}
    for bucket, status in responses:
        key = bucket + "_" + str(status)
        status_summary[key] = status_summary.get(key, 0) + 1
    safe = {
        "viewport_width": page.viewport_size["width"],
        "viewport_height": page.viewport_size["height"],
        "on_account_path": "/account" in urlsplit(page.url).path,
        "on_oidc_redirect": "/protocol/openid-connect/" in urlsplit(page.url).path,
        "on_login_action": "/login-actions/" in urlsplit(page.url).path,
        "on_signin_hash": "signing-in" in urlsplit(page.url).fragment,
        "dom_ready": await page.locator("body").count() > 0,
        "matches": matches, "responses": status_summary,
        "script_error_categories": dict(script_errors),
        "request_failure_categories": dict(request_failures),
    }
    return safe, usable


async def update_account_console(e, browser, cb, email, old_pw, new_pw, context):
    """Real Account Console user interaction, no programmatic UI bypass.

    Diagnose the root cause through safe route/status/error classes and real
    per-element visibility. Do not claim readiness because hidden DOM exists.
    """
    global_base = BASE + "/realms/" + REALM + "/account/"
    e.CURRENT = "RB-account-console-readonly-client-configuration"
    account_clients = e.ADMIN.call(
        "GET", "/clients", params={"clientId": "account-console"}).json()
    assert len(account_clients) == 1, "STANDARD_ACCOUNT_CONSOLE_CLIENT_MISSING"
    account_client = e.ADMIN.call(
        "GET", "/clients/" + account_clients[0]["id"]).json()
    builtin_account = e.ADMIN.call(
        "GET", "/clients", params={"clientId": "account"}).json()
    e.RESULTS["RB_account_client_readback"] = {
        "account_console_present": True,
        "account_console_enabled": account_client.get("enabled") is True,
        "standard_flow_enabled": account_client.get("standardFlowEnabled") is True,
        "public_client": account_client.get("publicClient") is True,
        "account_client_exists": len(builtin_account) == 1,
        "realm_account_theme": bool(e.ADMIN.call("GET", "").json().get("accountTheme")),
        "no_client_privilege_changed": True,
    }
    assert account_client.get("enabled") is True, "ACCOUNT_CONSOLE_CLIENT_DISABLED"

    e.CURRENT = "RB-account-console-set-explicit-viewport"
    page = await context.new_page()
    await page.set_viewport_size({"width": 1440, "height": 900})
    responses = []
    script_errors = {}
    request_failures = {}

    def track_response(response):
        # Safe categories only. No paths, URL queries, response body, token.
        bucket = _account_resource_category(response.url)
        status = response.status
        if status in (200,201,204,301,302,303,304,307,308,400,401,403,404,429) or status >= 500:
            responses.append((bucket, status))
        if len(responses) > 240:
            del responses[:40]

    def track_pageerror(error):
        # Never persist exception text: it may contain user input or URL.
        candidate = str(error).split(":", 1)[0].lower()
        category = next((key for key in (
            "typeerror", "referenceerror", "syntaxerror", "rangeerror",
            "networkerror", "chunkloaderror") if candidate == key),
            "other_javascript_exception")
        script_errors[category] = script_errors.get(category, 0) + 1

    def track_failure(req):
        # No failure text; a failed resource's route bucket is enough.
        key = _account_resource_category(req.url)
        request_failures[key] = request_failures.get(key, 0) + 1

    page.on("response", track_response)
    page.on("pageerror", track_pageerror)
    page.on("requestfailed", track_failure)
    try:
        e.CURRENT = "RB-account-console-root-document-navigation"
        await page.goto(global_base, wait_until="domcontentloaded")
        e.CURRENT = "RB-account-console-conditionally-await-UI"
        # SPA readiness is a meaningful, rendered & enabled control, not a
        # fixed delay or an arbitrary hidden DOM anchor. Conditional bounded
        # polling is only for the real UI states.
        deadline = time.monotonic() + 18
        navigated = False
        ready = False
        while time.monotonic() < deadline:
            safe, usable = await _account_ui_state(
                page, responses, script_errors, request_failures)
            if usable["login_form"]:
                e.CURRENT = "RB-account-console-real-user-password-login"
                await e.fill_login(page, email, old_pw)
                navigated = False
                continue
            if (usable["update_buttons"] or usable["update_links"]) and (
                    "signing-in" in urlsplit(page.url).fragment):
                ready = True
                break
            if usable["signing_links"]:
                e.CURRENT = "RB-account-console-visible-signing-in-link"
                await page.locator('a[href*="signing-in"]').nth(
                    usable["signing_links"][0]).click()
                navigated = True
            elif usable["security_links"]:
                e.CURRENT = "RB-account-console-visible-security-link"
                await page.locator('a[href*="account-security"]').nth(
                    usable["security_links"][0]).click()
                navigated = True
            elif usable["menu_buttons"] and not navigated:
                e.CURRENT = "RB-account-console-open-real-menu"
                await page.get_by_role(
                    "button", name=re.compile(r"menu|navigation|sidebar|toggle", re.I)
                ).nth(usable["menu_buttons"][0]).click()
                navigated = True
            elif usable["expanded_buttons"] and not navigated:
                # Only click real visible controls. No force/hidden click.
                e.CURRENT = "RB-account-console-expand-visible-menu"
                await page.locator('button[aria-expanded="false"]').nth(
                    usable["expanded_buttons"][0]).click()
                navigated = True
            await asyncio.sleep(0.2)  # conditional predicate, not fixed readiness
        safe, usable = await _account_ui_state(
            page, responses, script_errors, request_failures)
        e.RESULTS["RB_account_console_diagnostics"] = safe
        print("RB_ACCOUNT_DIAGNOSTIC=" + repr(safe), flush=True)
        if not ready:
            e.CURRENT = "RB-account-console-ui-not-ready"
            raise AssertionError("ACCOUNT_CONSOLE_UI_NOT_READY")
        if usable["update_buttons"]:
            button = page.get_by_role("button", name="Update", exact=True).nth(
                usable["update_buttons"][0])
        elif usable["update_links"]:
            button = page.get_by_role("link", name="Update", exact=True).nth(
                usable["update_links"][0])
        else:
            raise AssertionError("ACCOUNT_CONSOLE_UPDATE_NOT_VISIBLE")
        e.CURRENT = "RB-account-console-real-update-click"
        await button.click(timeout=12000)

        # The standard UI may initiate built-in UPDATE_PASSWORD as a login
        # required action, or open an in-app password panel. Never simulate
        # that action through Admin REST or arbitrary JS.
        e.CURRENT = "RB-account-console-password-form"
        form_new = page.locator(
            '#password-new, input[name="password-new"], '
            'input[autocomplete="new-password"]')
        await expect(form_new.first).to_be_visible(timeout=16000)
        visible_new = [i for i in range(await form_new.count())
                       if await form_new.nth(i).is_visible()]
        assert visible_new, "ACCOUNT_CONSOLE_NEW_PASSWORD_NOT_VISIBLE"
        await form_new.nth(visible_new[0]).fill(new_pw)
        confirm = page.locator(
            '#password-confirm, input[name="password-confirm"], '
            'input[autocomplete="new-password"]')
        confirm_visible = [i for i in range(await confirm.count())
                           if await confirm.nth(i).is_visible()]
        assert len(confirm_visible) >= 1
        # Use distinct confirm input, never refill first new password.
        confirmed = False
        for i in confirm_visible:
            item = confirm.nth(i)
            if await item.input_value() != new_pw:
                await item.fill(new_pw)
                confirmed = True
                break
        assert confirmed, "ACCOUNT_CONSOLE_CONFIRM_FIELD_NOT_FOUND"
        current_pw = page.locator(
            '#password, input[name="password"], '
            'input[autocomplete="current-password"]')
        for i in range(await current_pw.count()):
            if await current_pw.nth(i).is_visible():
                await current_pw.nth(i).fill(old_pw)
                break
        e.CURRENT = "RB-account-console-submit-password-from-UI"
        submit = page.locator(
            '#kc-submit, #kc-passwd-update-form button[type="submit"], '
            '#kc-passwd-update-form input[type="submit"], '
            'button[type="submit"]')
        visible_submit = [i for i in range(await submit.count())
                          if await submit.nth(i).is_visible()
                          and await submit.nth(i).is_enabled()]
        assert visible_submit, "ACCOUNT_CONSOLE_UI_SUBMIT_NOT_VISIBLE"
        await submit.nth(visible_submit[0]).click(timeout=12000)
        e.RESULTS["RB_account_console_actual_browser_submit"] = True
    finally:
        await page.close()


async def required_action_change(e, browser, cb, uid, email, new_pw):
    e.ADMIN.call("PUT", "/users/" + uid,
                 json={"requiredActions":["UPDATE_PASSWORD"]}, expected=204)
    flow, ctx, page = await e.begin(browser)
    try:
        e.CURRENT = "RB-required-action-original-password"
        await e.fill_login(page, email, e.PASSWORDS[email])
        e.CURRENT = "RB-required-action-update-form"
        await expect(page.locator("#password-new")).to_be_visible(timeout=17000)
        assert cb.server.inbox.empty(), "REQUIRED_ACTION_BYPASSED"
        await page.locator("#password-new").fill(new_pw)
        await page.locator("#password-confirm").fill(new_pw)
        await page.locator('#kc-submit, #kc-passwd-update-form input[type="submit"]').first.click()
        await page.wait_for_url(e.CALLBACK + "*", timeout=20000)
        tokens, _ = await e.checked_callback_exchange(cb.next(), flow)
        claims = await asyncio.to_thread(verify_id, e.OIDC, tokens["id_token"], flow["nonce"])
        assert claims["email"] == email
    finally:
        await ctx.close()


async def route_probe(e, browser, cb, receiver, kind):
    e.CURRENT = "RB-route-init-" + kind
    email = kind + "-b@example.test"
    old = "Qz9!" + secrets.token_urlsafe(18)
    new = "Jr8!" + secrets.token_urlsafe(18)
    e.PASSWORDS[email] = old
    uid = e.ADMIN.create_policy_probe(email, old)
    pre = await e.login(browser, cb, email, old)
    assert pre is not None and await e.old_browser_sso(pre[0], cb)
    msg_before = receiver.snapshot()
    events_before = user_events(e.ADMIN, uid)
    try:
        if kind == "forgot":
            await e.reset_password(browser, cb, email, old, new)
        elif kind == "account":
            await update_account_console(e, browser, cb, email, old, new, pre[0])
        elif kind == "required":
            await required_action_change(e, browser, cb, uid, email, new)
        elif kind == "admin":
            e.ADMIN.call("PUT", "/users/" + uid + "/reset-password",
                         json={"type":"password","temporary":False,"value":new},
                         expected=204)
        else:
            raise AssertionError("UNKNOWN_RESET_ROUTE")
        e.CURRENT = "RB-route-prior-session-observation-" + kind
        # First measure unchanged retained original browser / old access and
        # refresh credentials. This is separate from credential acceptance.
        evidence = await snapshot_old(e, cb, pre, kind)
        events_after = user_events(e.ADMIN, uid)
        evidence["keycloak_user_event_types_new"] = sorted(
            set(events_after) - set(events_before))
        evidence["backchannel_tokens_received_during_change"] = (
            receiver.snapshot() - msg_before)
        evidence["automatic_logout_claimed"] = False
        e.RESULTS["RB_route_" + kind] = evidence
        e.CURRENT = "RB-route-credential-verification-" + kind
        await changed_password_verified(e, browser, cb, email, old, new)
        e.case("RB-route-" + kind + "-actual-password-and-session-matrix")
        return evidence
    finally:
        await pre[0].close()


async def token_negative_matrix(e, receiver):
    """Validate a REAL signed logout token, then independent adversarial inputs."""
    compact, genuine = receiver.latest()
    checked = receiver.verify(compact)
    assert checked == genuine
    assert "sid" in checked or "sub" in checked
    # Claims after cryptographic verify can be checked against adversarial
    # input expectations without fabricating an IdP-issued signed JWT.
    for bad in (
        {**genuine, "events":{}},
        {**genuine, "nonce":"synthetic-should-be-denied"},
        {**genuine, "sid":None, "sub":None},
        {**genuine, "iat":int(time.time())+500},
        {**genuine, "exp":int(time.time())-1},
    ):
        try:
            logout_claim_policy(bad, now=int(time.time()))
        except ValueError:
            pass
        else:
            raise AssertionError("INVALID_LOGOUT_CLAIM_POLICY_ACCEPTED")
    for key, expect_value, err in (
        ("iss", e.OIDC["issuer"] + "/wrong", jwt.InvalidIssuerError),
        ("aud", "not-the-client", jwt.InvalidAudienceError),
    ):
        try:
            receiver.verify(compact, **({"expected_issuer":expect_value}
                                       if key == "iss" else
                                       {"expected_audience":expect_value}))
        except err:
            pass
        else:
            raise AssertionError("WRONG_LOGOUT_ISSUER_OR_AUDIENCE_ACCEPTED")
    # HTTP receiver MUST reject the same once-consumed signed token, an
    # access/ID Token and a broken signature. All probes stay inside runner.
    endpoint = "http://127.0.0.1:" + str(RECEIVER_PORT) + "/logout"
    original = requests.post(endpoint, data={"logout_token":compact}, timeout=5)
    assert original.status_code == 409, "REPLAYED_LOGOUT_TOKEN_ACCEPTED"
    broken = compact[:-5] + ("AAAAA" if compact[-5:] != "AAAAA" else "BBBBB")
    assert requests.post(endpoint, data={"logout_token":broken}, timeout=5).status_code == 400
    assert requests.post(endpoint, data={"logout_token":"a.b.c"}, timeout=5).status_code == 400
    assert requests.post(endpoint, json={"logout_token":"untrusted"}, timeout=5).status_code == 400
    e.RESULTS["RB_logout_validation"] = {
        "real_signed_token_received":True, "signature_issuer_audience_time_valid":True,
        "event_claim_checked":True, "subject_or_sid_checked":True,
        "replay_denied":True, "invalid_signature_denied":True,
        "wrong_expected_issuer_audience_denied":True,
        "invalid_events_time_identity_policy_denied":True,
        "receiver_isolated_no_product_session":True,
        "durable_replay_store":False,
    }
    e.case("RB-logout-token-real-signature-claims-and-replay-negatives")


async def standard_logout(e, browser, cb, receiver):
    """One real RP-initiated OIDC Logout and one standard Admin-initiated."""
    e.CURRENT = "RB-standard-logout-provision"
    email = "logout-b@example.test"
    password = "Pk8!" + secrets.token_urlsafe(18)
    e.PASSWORDS[email] = password
    uid = e.ADMIN.create_policy_probe(email, password)
    active = await e.login(browser, cb, email, password)
    assert await e.old_browser_sso(active[0], cb)
    old_tokens = active[2]
    before = receiver.snapshot()
    page = await active[0].new_page()
    try:
        e.CURRENT = "RB-standard-oidc-end-session"
        uri = e.OIDC["end_session_endpoint"] + "?" + urlencode(
            {"id_token_hint": old_tokens["id_token"], "client_id": CLIENT})
        await page.goto(uri, wait_until="domcontentloaded")
        # Some Keycloak setups present an explicit confirmation screen.
        submit = page.locator("#kc-logout, form[action*='logout'] input[type='submit']")
        if await submit.count() and await submit.first.is_visible():
            await submit.first.click()
        await page.wait_for_load_state("domcontentloaded")
    finally:
        await page.close()
    refresh_code = await asyncio.to_thread(refresh, e.OIDC, old_tokens["refresh_token"])
    userinfo_code = (await asyncio.to_thread(request, "GET", e.OIDC["userinfo_endpoint"],
        headers={"Authorization":"Bearer " + old_tokens["access_token"]})).status_code
    delivered = await receiver.wait_increase(before, seconds=8)
    e.RESULTS["RB_standard_oidc_logout"] = {
        "refresh_http":refresh_code,"userinfo_http":userinfo_code,
        "backchannel_received":delivered, "token_delivery_guaranteed":False}
    assert refresh_code in (400,401), "OIDC_LOGOUT_OLD_REFRESH_STILL_VALID"
    e.case("RB-standard-oidc-logout-measured")
    await active[0].close()

    # Fresh distinct session, same synthetic account, standard Admin user logout.
    active = await e.login(browser, cb, email, password)
    before = receiver.snapshot()
    e.CURRENT = "RB-standard-admin-logout"
    e.ADMIN.logout_user(uid)
    delivered_admin = await receiver.wait_increase(before, seconds=8)
    status = await asyncio.to_thread(refresh, e.OIDC, active[2]["refresh_token"])
    assert status in (400,401), "ADMIN_LOGOUT_OLD_REFRESH_STILL_VALID"
    e.RESULTS["RB_standard_admin_logout"] = {
        "refresh_http":status, "backchannel_received":delivered_admin,
        "delivery_guarantee":"NOT_PROVEN", "product_revocation":"NOT_TESTED"}
    assert delivered_admin, "STANDARD_BACKCHANNEL_NOT_OBSERVED"
    e.case("RB-standard-admin-logout-backchannel-delivered")
    await active[0].close()
    await token_negative_matrix(e,receiver)


async def offline_recovery(e, browser, cb, receiver):
    """Observe Keycloak behavior with the receiver offline, then restarted."""
    e.CURRENT = "RB-receiver-outage-user-provision"
    email = "outage-b@example.test"
    password = "Pj9!" + secrets.token_urlsafe(18)
    uid = e.ADMIN.create_policy_probe(email, password)
    active = await e.login(browser, cb, email, password)
    before = receiver.snapshot()
    try:
        receiver.stop()  # actual stopped TCP listener, not HTTP 500 only
        e.CURRENT = "RB-receiver-offline-logout"
        e.ADMIN.logout_user(uid)
        status = await asyncio.to_thread(refresh, e.OIDC, active[2]["refresh_token"])
        assert status in (400,401)
        with receiver.lock:
            during = len(receiver.received)
        assert during == before, "RECEIVED_WHILE_RECEIVER_STOPPED"
    finally:
        receiver.start()
        await active[0].close()
    e.CURRENT = "RB-receiver-restart-observation"
    await asyncio.sleep(4)
    new_after_restart = receiver.snapshot() - before
    e.RESULTS["RB_receiver_outage"] = {
        "receiver_stopped_before_logout":True,
        "idp_old_refresh_http":status,
        "received_while_offline":0,
        "received_after_receiver_restart_in_4s":new_after_restart,
        "retry_guarantee":"NOT_PROVEN",
        "persistence_guarantee":"NOT_PROVEN",
        "recovery_guarantee":"NOT_PROVEN",
        "product_session_reconciled":False,
    }
    e.case("RB-receiver-outage-and-restart-observed")


async def run(browser, cb, e):
    """Only entered AFTER all existing IDP-01 and BND-IDP-02A cases PASS."""
    e.CURRENT = "RB-rebootstrap-admin"
    e.ADMIN = e.Admin()  # previous short-lived admin token may expire
    receiver = IsolatedLogoutReceiver(e.OIDC)
    receiver.start()
    try:
        e.CURRENT = "RB-backchannel-client-config"
        configure_backchannel(e.ADMIN)
        e.case("RB-backchannel-standard-client-config-readback")
        account_blocked = False
        for kind in ("forgot","account","required","admin"):
            e.CURRENT = "RB-route-" + kind
            if kind == "account":
                try:
                    await route_probe(e, browser, cb, receiver, kind)
                except (AssertionError, PlaywrightTimeoutError) as exc:
                    # Not a PASS or fallback: carry this blocker forward so
                    # standard Logout, required/Admin route and outage probes
                    # still execute before the final CI fails closed.
                    e.RESULTS["RB_account_console_blocker"] = {
                        "stage":e.CURRENT, "category":type(exc).__name__,
                        "actual_account_password_changed":False}
                    e.STAGES["RB-route-account-console"] = "BLOCKED"
                    print("RB-route-account-console: BLOCKED stage=" +
                          e.CURRENT + " category=" + type(exc).__name__,
                          flush=True)
                    account_blocked = True
            else:
                await route_probe(e, browser, cb, receiver, kind)
        await standard_logout(e,browser,cb,receiver)
        await offline_recovery(e,browser,cb,receiver)
        e.RESULTS["RB_verdict"] = {
            "candidate":"standard_accepted_only_where_empirically_tested",
            "complete_reset_revocation":"BLOCKED",
            "client_product_session":"NOT_CONNECTED",
            "keycloak_internal_event_store_is_outbox":False,
            "next_package":"bounded reset surfaces + product-owned revocation barrier; "
                           "event delivery needs separate reliable mechanism/acceptance",
        }
        e.case("RB-result-standard-capabilities-bounded-external-reset-blocked")
        if account_blocked:
            e.RESULTS["RB_verdict"]["account_console"]="BLOCKED_NOT_PROVEN"
            e.CURRENT = "RB-account-console-not-proven-final"
            raise AssertionError("ACCOUNT_CONSOLE_NOT_PROVEN")
    finally:
        receiver.stop()
