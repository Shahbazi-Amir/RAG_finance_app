"""Dependency-free source contract guards for the existing API53 offline job.

Full behavioral test with FastAPI/PyJWT/cryptography/psycopg is separately
tests/phase3/integration/api/test_staging_bootstrap_asgi.py and MUST be run by
Foundation with its complete dependencies; these guards do not prove mTLS.
"""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src/phase3/auth/bootstrap_oidc.py"
SERVER = ROOT / "apps/api/private_staging_bootstrap_asgi.py"
TLS = ROOT / "src/phase3/auth/staging_transport_mtls.py"
INTEGRATION = ROOT / "tests/phase3/integration/api/test_staging_bootstrap_asgi.py"
NETWORK = ROOT / "tests/phase3/integration/api/test_staging_bootstrap_network.py"


class BootstrapSourceGuards(unittest.TestCase):
    def test_01_core_server_tls_integration_all_compile(self):
        for file in (CORE, SERVER, TLS, INTEGRATION, NETWORK):
            with self.subTest(path=file.name):
                compile(file.read_text(encoding="utf-8"), str(file), "exec")

    def test_02_private_staging_exact_public_callback(self):
        content = CORE.read_text()
        self.assertIn("https://ragfinance.ir/api/auth/callback", content)
        self.assertIn('runtime_profile == "private_staging"', content)
        self.assertIn('runtime_profile == "loopback_fixture"', content)
        self.assertIn('issuer_url.scheme == "https"', content)
        self.assertIn("ipaddress.ip_address(host).is_loopback", content)
        self.assertIn('realm_match.group(1) not in {".", ".."}', content)
        self.assertIn("/protocol/openid-connect/token", content)
        self.assertIn("/protocol/openid-connect/certs", content)
        self.assertIn("follow_redirects=False", content)
        self.assertIn("_StagingNoRedirectJWKClient", content)
        self.assertIn("verify=self._trusted_tls", content)

    def test_03_private_bootstrap_five_POST_only(self):
        source = SERVER.read_text()
        self.assertIn('for name in sorted(OPS)', source)
        self.assertIn('methods=["POST"]', source)
        self.assertIn('create_bootstrap_app', source)
        tree = ast.parse((ROOT/"src/phase3/auth/bootstrap_oidc.py").read_text())
        ops = next(node.value for node in tree.body
                   if isinstance(node,ast.Assign)
                   and any(isinstance(x,ast.Name) and x.id=="OPS"
                           for x in node.targets))
        self.assertEqual({x.value for x in ops.elts},
                         {"start","complete","status","ack","abort"})

    def test_04_transport_requires_real_openssl_der_and_object(self):
        source = TLS.read_text()
        self.assertIn('ssl_object.getpeercert(binary_form=True)', source)
        self.assertIn('ssl.CERT_REQUIRED', source)
        self.assertIn('self.__capability', source)
        self.assertIn('peer_der_from_scope', source)

    def test_05_no_ci_demo_or_public_bind(self):
        source = SERVER.read_text()
        self.assertIn('"127.0.0.1"', source)
        self.assertIn('or os.getenv("GITHUB_ACTIONS") == "true"', source)
        self.assertIn('proxy_headers=False', source)
        self.assertIn('ssl_cert_reqs=ssl.CERT_REQUIRED', source)
        self.assertIn('workers=1', source)

    def test_06_actual_signed_bootstrap_suite_stays_separate(self):
        code = INTEGRATION.read_text()
        self.assertIn("test_03_all_five_signed_https_asgi_endpoints_fenced", code)
        self.assertIn("test_06_foreign_certificate_or_forged_scope_not_accepted", code)
        self.assertNotIn("ARVAN_GATEWAY_API_KEY", code)
        self.assertIn("BOOTSTRAP_STAGING_REAL_LOCAL_HTTPS_MTLS_RS256_FIVE_ROUTES_PASS", NETWORK.read_text())


if __name__ == "__main__":
    unittest.main()
