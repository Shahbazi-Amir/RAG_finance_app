import unittest
from apps.api.app_only_db_pair import same_tls_database


class DatabasePairTests(unittest.TestCase):
    def setUp(self):
        self.history = dict(host="pg", port="5432", dbname="isolated",
                            sslmode="verify-full", sslrootcert="/run/pg-ca.pem",
                            user="history_app", password="synthetic-a")
        self.revoke = dict(self.history, user="auth_revoker", password="synthetic-b")

    def test_distinct_roles_and_passwords_same_endpoint(self):
        self.assertTrue(same_tls_database(self.history, self.revoke))

    def test_mismatched_destination(self):
        for field, value in (("host", "other-pg"), ("port", "5433"),
                             ("dbname", "another_db"), ("sslrootcert", "/other/ca.pem")):
            with self.subTest(field=field):
                self.assertFalse(same_tls_database(self.history, dict(self.revoke, **{field: value})))

    def test_missing_explicit_destination(self):
        for field in ("host", "port", "dbname", "sslrootcert", "sslmode"):
            with self.subTest(field=field):
                self.assertFalse(same_tls_database(self.history, {k:v for k,v in self.revoke.items() if k != field}))

    def test_wrong_roles(self):
        self.assertFalse(same_tls_database(self.history, dict(self.revoke, user="history_app")))
        self.assertFalse(same_tls_database(self.revoke, self.history))

    def test_no_tls_downgrade(self):
        for mode in ("disable", "prefer", "require", "verify-ca"):
            self.assertFalse(same_tls_database(self.history, dict(self.revoke, sslmode=mode)))

    def test_no_indirect_destination(self):
        for field in ("service", "servicefile", "hostaddr"):
            self.assertFalse(same_tls_database(self.history, dict(self.revoke, **{field:"override"})))

    def test_no_implicit_gss_override(self):
        self.assertFalse(same_tls_database(self.history, dict(self.revoke, gssencmode="require")))
        self.assertTrue(same_tls_database(self.history, dict(self.revoke, gssencmode="disable")))

    def test_invalid_port(self):
        for port in ("0", "65536", "5432,5433", "５４３２", "9"*1000, 5432):
            self.assertFalse(same_tls_database(dict(self.history, port=port), dict(self.revoke, port=port)))

    def test_invalid_host(self):
        for host in ("", "/run/postgresql", "pg,other", None):
            self.assertFalse(same_tls_database(dict(self.history, host=host), dict(self.revoke, host=host)))

    def test_invalid_ca(self):
        for ca in ("relative.pem", "/run/../ca.pem", None):
            self.assertFalse(same_tls_database(dict(self.history, sslrootcert=ca), dict(self.revoke, sslrootcert=ca)))

    def test_nonmapping_denied(self):
        self.assertFalse(same_tls_database(None, self.revoke))
        self.assertFalse(same_tls_database(self.history, "dsn"))


if __name__ == "__main__":
    unittest.main()
