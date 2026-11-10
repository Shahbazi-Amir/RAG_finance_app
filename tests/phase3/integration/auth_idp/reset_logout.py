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
import threading
import time
from urllib.parse import urlencode, urlsplit

import jwt
import requests
from playwright.async_api import expect

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


async def update_account_console(e, browser, cb, email, old_pw, new_pw, context):
    """Real Playwright Account Console UI, never direct credential Admin REST."""
    e.CURRENT = "RB-account-console-navigate"
    page = await context.new_page()
    try:
        await page.goto(BASE + "/realms/" + REALM +
                        "/account/#/account-security/signing-in",
                        wait_until="domcontentloaded")
        # Initial UI may redirect to SSO authorization and back.
        await expect(page.get_by_role("button", name="Update").first).to_be_visible(timeout=20000)
        e.CURRENT = "RB-account-console-click-update"
        await page.get_by_role("button", name="Update").first.click()
        e.CURRENT = "RB-account-console-password-change-form"
        await expect(page.locator("#password-new")).to_be_visible(timeout=18000)
        await page.locator("#password-new").fill(new_pw)
        await page.locator("#password-confirm").fill(new_pw)
        if await page.locator("#password").count() and await page.locator("#password").is_visible():
            await page.locator("#password").fill(old_pw)
        e.CURRENT = "RB-account-console-submit"
        await page.locator('#kc-submit, #kc-passwd-update-form button[type="submit"], #kc-passwd-update-form input[type="submit"]').first.click()
        await page.wait_for_load_state("domcontentloaded")
        # Real credentials, separately verified by independent OIDC logins.
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
        for kind in ("forgot","account","required","admin"):
            e.CURRENT = "RB-route-" + kind
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
    finally:
        receiver.stop()
