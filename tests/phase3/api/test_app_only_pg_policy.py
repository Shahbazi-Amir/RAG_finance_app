import unittest
from apps.api.app_only_pg_policy import pg_tls_options_allowed


class PGTLSOptionsTests(unittest.TestCase):
    def setUp(self):
        self.valid = {"host": "postgres.internal", "port": "5432", "sslmode": "verify-full",
                      "sslrootcert": "/run/secrets/pg-ca.pem"}

    def test_named_host(self):
        self.assertTrue(pg_tls_options_allowed(self.valid))

    def test_loopback_requires_tls_too(self):
        self.assertTrue(pg_tls_options_allowed(self.valid | {"host": "127.0.0.1"}))
        self.assertFalse(pg_tls_options_allowed(self.valid | {"host": "127.0.0.1", "sslmode": "prefer"}))

    def test_ssl_downgrades(self):
        for mode in (None, "disable", "allow", "prefer", "require", "verify-ca"):
            self.assertFalse(pg_tls_options_allowed(self.valid | {"sslmode": mode}))

    def test_local_socket_and_multiple_hosts(self):
        for host in ("", "/tmp", "@local", "a,b", "a b", None):
            self.assertFalse(pg_tls_options_allowed(self.valid | {"host": host}))

    def test_ca_path(self):
        for root in (None, "ca.pem", "/run/../ca.pem", "/"):
            self.assertFalse(pg_tls_options_allowed(self.valid | {"sslrootcert": root}))

    def test_port(self):
        for port in (None, "", "0", "65536", "5432,5433", 5432, "١٢٣"):
            self.assertFalse(pg_tls_options_allowed(self.valid | {"port": port}))

    def test_no_service_or_hostaddr_override(self):
        for key in ("service", "hostaddr"):
            self.assertFalse(pg_tls_options_allowed(self.valid | {key: "other"}))

    def test_no_gss_preference(self):
        self.assertTrue(pg_tls_options_allowed(self.valid | {"gssencmode": "disable"}))
        for mode in ("prefer", "require"):
            self.assertFalse(pg_tls_options_allowed(self.valid | {"gssencmode": mode}))

    def test_malformed_options(self):
        for value in (None, [], {}, "dsn"):
            self.assertFalse(pg_tls_options_allowed(value))


if __name__ == "__main__":
    unittest.main()
