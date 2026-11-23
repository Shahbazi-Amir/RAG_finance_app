#!/usr/bin/env python3
"""Strict real-browser two-owner E2E. Never mocks the UI, IdP, BFF or API.

Run only AFTER Foundation/API/DB start one actual integrated app-only stack
with real disposable Keycloak/OIDC, trusted BFF, HTTPS/mTLS and PG in a SINGLE
CI job and DB independently emits a sanitized fresh seed manifest.

Playwright never routes/fulfills/aborts, edits cookies, injects owner headers,
uses storage_state or injects an Auth context. Accounts log in by actual IdP UI.
A green source-only/browser-503 smoke is NOT this five-stage witness.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright, expect

BASE = "https://127.0.0.1:3443"
IDP_PATH_SUFFIX = "/protocol/openid-connect/auth"
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROOT = Path(__file__).resolve().parents[4]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def configured():
    if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("E2E_MUST_RUN_ON_DISPOSABLE_AUTHORIZED_CI_RUNNER")
    if os.environ.get("PHASE3_APP_MODE") != "APP_ONLY":
        raise RuntimeError("NO_ENGINE_MODE_NOT_CONFIRMED")
    if os.environ.get("UI_REAL_BROWSER_ORIGIN", BASE) != BASE:
        raise RuntimeError("ONLY_TEMPORARY_HTTPS_LOCAL_LAB_IS_AUTHORIZED")
    if os.environ.get("UI_REAL_BROWSER_APPROVED") != "true":
        raise RuntimeError("INTEGRATED_LAB_EXECUTION_NOT_APPROVED")
    idp = os.environ.get("UI_REAL_IDP_ORIGIN", "")
    split = urlsplit(idp)
    if (split.scheme != "http" or split.hostname != "127.0.0.1"
            or split.port is None or not split.path in ("", "/")
            or split.query or split.fragment or split.username or split.password):
        raise RuntimeError("DISPOSABLE_IDP_ORIGIN_NOT_PINNED")
    path = os.environ.get("UI_REAL_PG_SEED_RECEIPT", "")
    if not path or not Path(path).is_file() or Path(path).is_symlink():
        raise RuntimeError("PG_OWNER_SEED_RECEIPT_REQUIRED")
    receipt = json.loads(Path(path).read_text(encoding="utf-8"))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                     text=True).strip()
    if (not HEX40.fullmatch(commit) or
            receipt.get("kind") != "ui_f3_actual_pg_two_owner_seed" or
            receipt.get("contract_version") != "ui.pg_two_owner_seed.v1" or
            receipt.get("integrated_sha") != commit or
            not HEX64.fullmatch(str(receipt.get("pg_cluster_id_sha256", "")))):
        raise RuntimeError("SOURCE_OR_PG_SEED_PROVENANCE_MISMATCH")
    users = receipt.get("users")
    if not isinstance(users, dict) or set(users) != {"A", "B"}:
        raise RuntimeError("PG_SEED_MUST_PROVIDE_TWO_ACTUAL_OWNERS")
    for alias, row in users.items():
        if (not isinstance(row, dict)
                or not isinstance(row.get("owner_id"), str)
                or not SAFE_ID.fullmatch(row["owner_id"])
                or not isinstance(row.get("conversation_ids"), list)
                or not all(isinstance(x, str) and SAFE_ID.fullmatch(x)
                           for x in row["conversation_ids"])
                or len(set(row["conversation_ids"])) != len(row["conversation_ids"])
                or not isinstance(row.get("message_ids"), dict)):
            raise RuntimeError("PG_SEED_OWNER_RECORD_INVALID")
        if not row["conversation_ids"]:
            raise RuntimeError("PG_SEED_MISSING_HISTORY_" + alias)
        for cid, ids in row["message_ids"].items():
            if (cid not in row["conversation_ids"]
                    or not isinstance(ids, list)
                    or not all(isinstance(mid, str) and SAFE_ID.fullmatch(mid) for mid in ids)
                    or len(ids) != len(set(ids))):
                raise RuntimeError("PG_SEED_MESSAGE_CROSS_REFERENCE_INVALID")
    if (users["A"]["owner_id"] == users["B"]["owner_id"]
            or set(users["A"]["conversation_ids"]) & set(users["B"]["conversation_ids"])):
        raise RuntimeError("PG_SEED_OWNER_COLLISION")
    # A must own enough rows to exercise an ACTUAL next-page operation,
    # rather than a visible button with no server cursor.
    if len(users["A"]["conversation_ids"]) < 3:
        raise RuntimeError("PG_SEED_REQUIRES_A_CONVERSATION_PAGINATION")
    first_a = users["A"]["conversation_ids"][0]
    if len(users["A"]["message_ids"].get(first_a, [])) <= 30:
        raise RuntimeError("PG_SEED_REQUIRES_FIRST_A_THREAD_OVER_30_MESSAGES")
    credentials = {}
    for alias in ("A", "B"):
        name = os.environ.get("UI_REAL_" + alias + "_USERNAME", "")
        password = os.environ.get("UI_REAL_" + alias + "_PASSWORD", "")
        if not name or not password:
            raise RuntimeError("DISPOSABLE_IDP_LOGIN_NOT_PROVISIONED")
        credentials[alias] = (name, password)
    return receipt, idp, credentials, commit


def id_for_test(tag: str) -> str:
    return tag + hashlib.sha256(os.urandom(32)).hexdigest()[:24]


async def login(browser, alias, idp, creds, owner, width):
    # Separate fresh browser contexts; no cookie injection or auth shortcuts.
    ctx = await browser.new_context(
        viewport={"width": width, "height": 844 if width <= 390 else 800},
        is_mobile=width <= 390, ignore_https_errors=True)
    page = await ctx.new_page()
    try:
        login_resp = await page.goto(BASE + "/login", wait_until="domcontentloaded")
        assert login_resp is not None and login_resp.status == 200, (
            "BFF_REAL_LOGIN_NOT_READY", alias, login_resp.status if login_resp else None)
        await expect(page.get_by_test_id("login-submit")).to_be_visible()
        async with page.expect_response(
            lambda response: response.url.endswith("/api/auth/login")
            and response.request.method == "POST", timeout=30000
        ) as posting:
            await page.get_by_test_id("login-submit").click(no_wait_after=True)
        assert (await posting.value).status == 303, "BFF_OIDC_START_NOT_REDIRECTED"
        await page.locator('input[name="username"]').wait_for(
            state="visible", timeout=30000)
        # Verify actual redirect to the expected IdP; do not accept a fake form.
        observed = urlsplit(page.url)
        if observed.scheme + "://" + observed.netloc != idp or not observed.path.endswith(
                IDP_PATH_SUFFIX):
            raise AssertionError("BROWSER_DID_NOT_ENTER_ACTUAL_CONFIGURED_IDP")
        await page.locator('input[name="username"]').fill(creds[0])
        await page.locator('input[name="password"]').fill(creds[1])
        async with page.expect_response(
            lambda response: response.request.method == "GET"
            and "/api/history/conversations?limit=2" in response.url,
            timeout=45000
        ) as after_login:
            await page.locator("#kc-login").click()
        first_page = await after_login.value
        assert first_page.status == 200, (
            "SIGNED_BFF_API_PG_HISTORY_FIRST_FAILING_BOUNDARY",
            alias, first_page.status)
        payload = await first_page.json()
        assert payload["kind"] == "conversation_page", "HISTORY_NOT_PRODUCT_V1"
        assert payload["scope_user_id"] == owner["owner_id"], "BFF_ACCOUNT_OWNER_MISMATCH"
        assert all(v["owner_user_id"] == owner["owner_id"] for v in payload["items"])
        await expect(page.get_by_test_id("history-state")).not_to_contain_text(
            "در دسترس نیست", timeout=12000)
        capabilities = await page.evaluate("""async () => {
          const r=await fetch('/api/product-capabilities',{cache:'no-store'});
          return {status:r.status, payload:await r.json()};
        }""")
        assert capabilities["status"] == 200
        assert capabilities["payload"]["send_mode"] == "DISABLED"
        assert capabilities["payload"]["engine_available"] is False
        await expect(page.get_by_test_id("history-send")).to_be_disabled()
        await expect(page.get_by_test_id("history-question")).to_be_disabled()
        await expect(page.get_by_test_id("create-conversation")).to_be_disabled()
        cookies = [x for x in await ctx.cookies(BASE)
                   if x["name"] == "__Host-rag-session"]
        assert len(cookies) == 1
        assert cookies[0]["secure"] and cookies[0]["httpOnly"]
        assert cookies[0]["sameSite"] == "Lax"
        print("UI_REAL_OIDC_"+alias+"_SIGNED_HISTORY_HTTP_200_PASS",flush=True)
        return ctx, page
    except BaseException:
        await ctx.close()
        raise


async def open_mobile_drawer(page, width):
    if width <= 390:
        trigger = page.get_by_role("button", name="بازکردن فهرست گفت‌وگوها")
        if await trigger.get_attribute("aria-expanded") != "true":
            await trigger.click()


async def verify_list_and_thread(page, owner, width):
    await open_mobile_drawer(page, width)
    expected = owner["conversation_ids"]
    for _ in range(len(expected) + 3):
        visible = await page.locator('[data-testid^="conversation-"]').evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('data-testid').slice(13))")
        assert len(visible) == len(set(visible)), "DUPLICATE_HISTORY_DOM_IDS"
        assert set(visible).issubset(set(expected)), "CROSS_OWNER_HISTORY_IN_DOM"
        if set(visible) == set(expected):
            break
        more = page.get_by_test_id("more-conversations")
        await expect(more).to_be_visible(timeout=12000)
        await expect(more).to_be_enabled()
        previous = len(visible)
        async with page.expect_response(
            lambda r: r.request.method == "GET"
            and "/api/history/conversations?limit=2&cursor=" in r.url,
            timeout=15000
        ) as cursor_response:
            await more.click()
        assert (await cursor_response.value).status == 200, "PG_LIST_CURSOR_HTTP_ERROR"
        await page.wait_for_function(
            "before => document.querySelectorAll('[data-testid^=conversation-]').length > before",
            arg=previous, timeout=12000)
    else:
        raise AssertionError("PAGINATION_NEVER_COMPLETED")
    # Preserve exact DB row order, not merely cardinality or owner.
    visible = await page.locator('[data-testid^="conversation-"]').evaluate_all(
        "(nodes) => nodes.map(n => n.getAttribute('data-testid').slice(13))")
    assert visible == expected, ("PG_LIST_ORDER_MISMATCH",len(visible),len(expected))
    target = expected[0]
    # The SQL producer must put the long thread on the first visible owner A
    # record, making reload and cursor assertions deterministic.
    async with page.expect_response(
        lambda r: r.request.method == "GET"
        and "/api/history/conversations/" + target + "/messages?limit=30" in r.url,
        timeout=18000
    ) as message_response:
        # React thread is loaded on selection; listening must start BEFORE
        # a distinct click in the invoking caller. This fallback is just a
        # real user-operated refresh via navigation when request was too fast.
        await page.goto(BASE + "/history")
        await open_mobile_drawer(page, width)
        await page.get_by_test_id("conversation-" + target).click()
    reply = await message_response.value
    assert reply.status == 200, "PG_THREAD_FIRST_PAGE_NOT_200"
    data = await reply.json()
    assert data["owner_user_id"] == owner["owner_id"]
    assert data["conversation_id"] == target
    wanted = owner["message_ids"][target]
    for _ in range(len(wanted)//30 + 3):
        seen = await page.locator('[data-testid^="history-message-"]').evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('data-testid').slice(16))")
        assert len(seen) == len(set(seen)), "DUPLICATE_MESSAGE_IDS_IN_DOM"
        assert set(seen).issubset(set(wanted)), "MESSAGE_ID_OUTSIDE_PG_SEED"
        if len(seen) == len(wanted):
            break
        more = page.get_by_test_id("more-messages")
        await expect(more).to_be_visible(timeout=12000)
        previous = len(seen)
        async with page.expect_response(
            lambda r: r.request.method == "GET"
            and "/api/history/conversations/" + target +
                "/messages?limit=30&cursor=" in r.url,
            timeout=15000
        ) as next_response:
            await more.click()
        assert (await next_response.value).status == 200
        await page.wait_for_function(
            "before => document.querySelectorAll('[data-testid^=history-message-]').length>before",
            arg=previous, timeout=15000)
    else:
        raise AssertionError("MESSAGE_PAGINATION_DID_NOT_COMPLETE")
    ids = await page.locator('[data-testid^="history-message-"]').evaluate_all(
        "(nodes) => nodes.map(n => n.getAttribute('data-testid').slice(16))")
    assert ids == wanted, "MESSAGE_PG_ORDER_OR_REFRESH_DIFF"
    await page.reload(wait_until="domcontentloaded")
    await open_mobile_drawer(page, width)
    await expect(page.get_by_test_id("conversation-" + target)).to_be_visible(
        timeout=20000)
    await page.get_by_test_id("conversation-" + target).click()
    await expect(page.get_by_test_id("history-message-" + wanted[0])).to_be_visible(
        timeout=15000)
    print("UI_REAL_OWNER_PG_CONVERSATION_MESSAGE_CURSOR_REFRESH_PASS",flush=True)
    return target


async def browser_fetch(page, url, method="GET", body=None):
    # Only real in-browser same-origin fetch, never Playwright route interception
    # nor request_context with artificially forged cookie/actor headers.
    return await page.evaluate("""async ({url, method, body}) => {
      const response = await fetch(url, {
        method, credentials:'same-origin', cache:'no-store',
        ...(body===null?{}:{headers:{'Content-Type':'application/json'},
                             body:JSON.stringify(body)})
      });
      return {status:response.status, text:await response.text()};
    }""",{"url":url,"method":method,"body":body})


async def journey(browser, receipt, idp, credentials, width):
    a=b=None
    try:
        a, pa = await login(browser, "A", idp, credentials["A"],
                            receipt["users"]["A"], width)
        b, pb = await login(browser, "B", idp, credentials["B"],
                            receipt["users"]["B"], width)
        ca = await verify_list_and_thread(pa, receipt["users"]["A"], width)
        await open_mobile_drawer(pb,width)
        visible_b = await pb.locator('[data-testid^="conversation-"]').evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('data-testid').slice(13))")
        assert not set(visible_b) & set(receipt["users"]["A"]["conversation_ids"])
        # Direct foreign URL from B's real context; the BFF signs B's identity.
        foreign = await browser_fetch(pb,
            "/api/history/conversations/" + ca + "/messages?limit=30")
        assert foreign["status"] == 404, (
            "B_CROSS_OWNER_DIRECT_RECORD_MUST_BE_404", foreign["status"])
        assert ca not in foreign["text"], "FOREIGN_ID_LEAK_IN_B_ERROR"
        print("UI_REAL_B_DIRECT_A_URL_SIGNED_HTTP_404_PASS",flush=True)
        # Explicit browser POST (not a disabled React button) MUST NOT commit
        # a Send in app-only; the DB owner separately checks zero rows.
        valid = {
            "kind":"send_message_request","contract_version":"product.v1",
            "requested_conversation_id":ca,
            "client_message_id":id_for_test("uih_"),
            "idempotency_key":id_for_test("key_"),
            "question":"آزمون عدم ثبت ارسال در حالت بدون موتور"
        }
        denied = await browser_fetch(pa,"/api/history/messages","POST",valid)
        assert denied["status"] == 503
        assert json.loads(denied["text"]) == {"error":"ENGINE_NOT_AVAILABLE"}
        print("UI_REAL_BROWSER_DIRECT_SEND_503_NO_EXECUTE_PASS",flush=True)
        logout = await a.new_page()
        await logout.goto(BASE + "/login")
        await expect(logout.get_by_test_id("logout-submit")).to_be_visible(
            timeout=12000)
        async with logout.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/auth/logout"), timeout=30000
        ) as result:
            await logout.get_by_test_id("logout-submit").click()
        assert (await result.value).status == 303, "REVOCATION_NOT_COMMITTED"
        await expect(logout.get_by_test_id("logout-success")).to_be_visible()
        # Old tab retains old UI state until a real server GET detects revoke.
        await open_mobile_drawer(pa,width)
        async with pa.expect_response(
            lambda response: response.request.method == "GET"
            and "/api/history/conversations?limit=2" in response.url,
            timeout=20000
        ) as old_session:
            await pa.get_by_test_id("refresh-history").click()
        assert (await old_session.value).status == 401, "REVOKED_SESSION_NOT_401"
        await expect(pa.get_by_test_id("history-login-required")).to_be_visible()
        assert await pa.locator('[data-testid^="conversation-"]').count() == 0
        assert await pa.locator('[data-testid^="history-message-"]').count() == 0
        still_b = await browser_fetch(pb, "/api/history/conversations?limit=2")
        assert still_b["status"] == 200
        assert json.loads(still_b["text"])["scope_user_id"] == receipt["users"]["B"]["owner_id"]
        print("UI_REAL_REVOKE_A_401_PURGE_B_200_PASS",flush=True)
        return {
            "viewport":width,
            "oidc_auth_two_users":True,
            "owner_scoped_pg_history":True,
            "pagination_and_refresh":True,
            "cross_owner_404":True,
            "revoke_401_b_still_200":True,
            "app_only_send_503":True,
            "conversation_id_sha256":digest(ca),
        }
    finally:
        if b is not None:
            await b.close()
        if a is not None:
            await a.close()


async def main():
    receipt, idp, credentials, sha = configured()
    result = {"kind":"ui_f3_real_signed_two_owner_journey",
              "contract_version":"ui.real_history_browser.v1",
              "source_sha":sha, "environment":"EPHEMERAL_CI_REAL_IDP_MTLS_PG",
              "pg_cluster_id_sha256":receipt["pg_cluster_id_sha256"],
              "steps":[],"target_accepted":False}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            for width in (1280,390):
                result["steps"].append(await journey(
                    browser,receipt,idp,credentials,width))
        finally:
            await browser.close()
    out = os.environ.get("UI_REAL_BROWSER_RECEIPT_DIR", "")
    if out:
        d = Path(out)
        if not d.is_absolute() or not d.is_dir():
            raise RuntimeError("RECEIPT_DIRECTORY_NOT_PREPARED")
        (d/"ui_real_signed_history_sanitized.json").write_text(
            json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    # Green lab != Mac/Ops owner signoff, never auto-accept target.
    print("UI_F3_EPHEMERAL_REAL_OIDC_A_B_HISTORY_404_REFRESH_REVOKE_401_PASS_NOT_MAC_L2",
          flush=True)


if __name__ == "__main__":
    asyncio.run(main())
