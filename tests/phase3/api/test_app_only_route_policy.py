import unittest
from apps.api.app_only_route_policy import classify_route


def route(path, method="GET", query=b"", **overrides):
    return classify_route(dict(path=path, raw_path=path.encode("utf-8"),
                               method=method, query_string=query) | overrides)


class RoutePolicyTests(unittest.TestCase):
    def test_list(self):
        self.assertEqual(route("/v1/conversations"), "history")

    def test_detail(self):
        self.assertEqual(route("/v1/conversations/A_9-1/messages"), "history")

    def test_status(self):
        self.assertEqual(route("/v1/message-requests/status"), "history")

    def test_pagination(self):
        self.assertEqual(route("/v1/conversations", query=b"limit=1&cursor=abc"), "history")

    def test_send_disabled_even_with_query(self):
        for query in (b"", b"unexpected=1"):
            self.assertEqual(route("/v1/messages", "POST", query), "send_disabled")

    def test_revoke_only_post(self):
        path = "/internal/auth/session/v1/revoke-one"
        self.assertEqual(route(path, "POST"), "revoke")
        self.assertEqual(route(path), "deny")
        self.assertEqual(route(path, "POST", b"x=1"), "deny")

    def test_pg_ready_only_without_query(self):
        self.assertEqual(route("/internal/ready"), "pg_ready")
        self.assertEqual(route("/internal/ready", query=b"x=1"), "deny")

    def test_health(self):
        for path in ("/health/live", "/health/ready", "/v1/capabilities"):
            self.assertEqual(route(path), "health")
            self.assertEqual(route(path, query=b"x=1"), "deny")

    def test_no_mutating_history(self):
        for method in ("POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"):
            self.assertEqual(route("/v1/conversations", method), "deny")

    def test_no_engine_or_fixture(self):
        for path in ("/v1/message-requests/engine-status", "/v1/message-requests/retrieved-sources",
                     "/v1/message-requests/invited-live-result", "/v1/message-requests/claim-test-status",
                     "/v1/dispatch", "/docs", "/openapi.json"):
            self.assertEqual(route(path), "deny")

    def test_no_alternate_path_encoding(self):
        for path in ("/v1/conversations/", "/v1//conversations", "/v1/conversations/../messages",
                     "/v1/conversations/%41/messages", "/v1/conversations/نام/messages"):
            self.assertEqual(route(path), "deny")
        self.assertEqual(route("/v1/conversations", raw_path=b"/v1/%63onversations"), "deny")
        self.assertEqual(route("/v1/conversations", raw_path=b"/v1/messages"), "deny")

    def test_bad_id(self):
        for cid in ("_a", "-a", "a"*65, "a.b", "a/b"):
            self.assertEqual(route(f"/v1/conversations/{cid}/messages"), "deny")
        self.assertEqual(route(f"/v1/conversations/{'a'*64}/messages"), "history")

    def test_malformed_asgi_scope(self):
        for data in ({}, {"raw_path": None}, {"path": 1}, {"query_string": None}):
            self.assertEqual(classify_route(data), "deny")
        self.assertEqual(route("/v1/conversations", query_string="limit=1"), "deny")


if __name__ == "__main__":
    unittest.main()
