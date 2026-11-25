"""Strict public TLS for the existing real signed browser journey.

Only disposable GitHub-hosted Linux CI may install its ephemeral lab CA.
No route interception, certificate-error bypass, session/cookie injection or
changes to the frozen login/restore harness. Keycloak's isolated HTTP origin
is not claimed to be a verified HTTPS IdP.
"""
from __future__ import annotations
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
from playwright.async_api import Error as PlaywrightError


class StrictBrowser:
    """Adapt the frozen harness's legacy context option, never its traffic."""
    def __init__(self, browser):
        self.browser = browser
        self.contexts_created = 0

    async def new_context(self, **options):
        # Override the legacy True flag at the sole browser-context factory.
        # This is real Playwright with normal TLS and independent contexts.
        options["ignore_https_errors"] = False
        context = await self.browser.new_context(**options)
        self.contexts_created += 1
        return context


async def reject_untrusted_login(browser, origin):
    """Before installing the lab CA, the real Next HTTPS login must fail."""
    context = await browser.new_context(ignore_https_errors=False)
    try:
        page = await context.new_page()
        try:
            await page.goto(origin + "/login", wait_until="domcontentloaded", timeout=15000)
        except PlaywrightError as exc:
            # Network or timeout failure is NOT certificate rejection.
            if not re.search(r"certificat|cert_|unknown.issuer|ssl|tls|sec_error", str(exc), re.I):
                raise AssertionError("BROWSER_UNTRUSTED_CA_NOT_A_CERTIFICATE_ERROR") from None
        else:
            raise AssertionError("BROWSER_UNTRUSTED_CA_ACCEPTED")
    finally:
        await context.close()
    print("F3_BROWSER_UNTRUSTED_LAB_CA_DENIED_PASS", flush=True)


@contextmanager
def trust_job_ca(demo, engine):
    if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
            or os.getenv("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.getenv("RUNNER_OS") != "Linux"):
        raise RuntimeError("BROWSER_CA_DISPOSABLE_HOSTED_LINUX_ONLY")
    ca = Path(demo.ca)
    assert ca.is_file() and not ca.is_symlink() and ca.parent == demo.root
    run_id = os.environ["GITHUB_RUN_ID"]
    assert re.fullmatch(r"[0-9]{1,24}", run_id)
    assert engine in ("chromium", "firefox", "webkit")
    name = "f3-ui-strict-" + run_id + "-" + engine
    target = "/usr/local/share/ca-certificates/" + name + ".crt"
    nss = Path.home() / ".pki" / "nssdb"
    nss.mkdir(parents=True, exist_ok=True)
    spec = "sql:" + str(nss)
    if not (nss / "cert9.db").exists():
        subprocess.run(["certutil", "-N", "--empty-password", "-d", spec], check=True)
    old_env = {key: os.environ.get(key) for key in
               ("NODE_EXTRA_CA_CERTS", "PLAYWRIGHT_FIREFOX_POLICIES_JSON")}
    installed_system = installed_nss = False
    try:
        subprocess.run(["sudo", "install", "-m", "0644", str(ca), target], check=True)
        installed_system = True
        subprocess.run(["sudo", "update-ca-certificates"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["certutil", "-A", "-d", spec, "-n", name, "-t", "C,,", "-i", str(ca)], check=True)
        installed_nss = True
        # Node APIRequestContext is distinct from browser TLS; keep verification.
        os.environ["NODE_EXTRA_CA_CERTS"] = str(ca)
        if engine == "firefox":
            # Playwright's documented Firefox enterprise policy import.
            policy = demo.root / "firefox-ci-policies.json"
            policy.write_text(json.dumps({"policies": {"Certificates": {"Install": [str(ca)]}}}))
            os.environ["PLAYWRIGHT_FIREFOX_POLICIES_JSON"] = str(policy)
        with socket.create_connection(("127.0.0.1", 3443), timeout=8) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname="127.0.0.1") as verified:
                assert verified.version() in ("TLSv1.2", "TLSv1.3")
        try:
            with socket.create_connection(("127.0.0.1", 3443), timeout=8) as sock:
                with ssl.create_default_context().wrap_socket(sock, server_hostname="wrong-san.invalid"):
                    pass
        except ssl.SSLCertVerificationError:
            pass
        else:
            raise AssertionError("PUBLIC_TLS_WRONG_SAN_ACCEPTED")
        print("F3_BROWSER_PUBLIC_CA_OPENSSL_WRONG_SAN_DENIED_PASS", flush=True)
        yield
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if installed_nss:
            subprocess.run(["certutil", "-D", "-d", spec, "-n", name], check=True)
        if installed_system:
            subprocess.run(["sudo", "rm", "-f", target], check=True)
            subprocess.run(["sudo", "update-ca-certificates", "--fresh"], check=True, stdout=subprocess.DEVNULL)


async def verify_trusted_login(browser, origin):
    context = await browser.new_context(ignore_https_errors=False)
    try:
        page = await context.new_page()
        response = await page.goto(origin + "/login", wait_until="domcontentloaded", timeout=15000)
        assert response is not None and response.status == 200
        assert await page.evaluate("() => window.isSecureContext") is True
        response = await context.request.get(origin + "/login")
        assert response.status == 200
    finally:
        await context.close()
    print("F3_BROWSER_STRICT_TRUST_LOGIN_AND_NODE_REQUEST_PASS", flush=True)
