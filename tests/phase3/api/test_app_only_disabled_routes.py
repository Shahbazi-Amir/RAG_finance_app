import asyncio
import unittest
from starlette.responses import JSONResponse
from apps.api.app_only_disabled_routes import deny_disabled_route


class DisabledRouteTests(unittest.TestCase):
    def invoke(self, path, method="GET", raw_path=None):
        async def run():
            events = []
            async def receive():
                raise AssertionError("REQUEST_BODY_MUST_NOT_BE_READ")
            async def send(event):
                events.append(event)
            def error(status, code, category, message):
                return JSONResponse({"error": {"code": code, "category": category,
                                               "message": message}}, status_code=status)
            scope = {"type": "http", "path": path, "method": method,
                     "raw_path": raw_path or path.encode(), "headers": []}
            denied = await deny_disabled_route(scope, receive, send, error)
            if not denied:
                self.assertEqual(events, [])
                return None
            self.assertEqual(events[0]["status"], 503)
            import json
            return json.loads(events[1]["body"])["error"]["code"]
        return asyncio.run(run())

    def test_send_is_denied_before_body(self):
        self.assertEqual(self.invoke("/v1/messages", "POST"), "ENGINE_NOT_CONFIGURED")

    def test_encoded_send_is_denied(self):
        self.assertEqual(self.invoke("/v1/messages", "POST", b"/v1/%6dessages"),
                         "ENGINE_NOT_CONFIGURED")

    def test_engine_status_is_denied(self):
        self.assertEqual(self.invoke("/v1/message-requests/engine-status"),
                         "ENGINE_STATUS_UNAVAILABLE")

    def test_retrieved_sources_are_denied(self):
        self.assertEqual(self.invoke("/v1/message-requests/retrieved-sources"),
                         "ENGINE_STATUS_UNAVAILABLE")

    def test_fixture_routes_denied(self):
        for suffix in ("claim-test-status", "invited-live-result"):
            self.assertEqual(self.invoke("/v1/message-requests/" + suffix),
                             "TEMPORARILY_UNAVAILABLE")

    def test_encoded_engine_status_is_denied(self):
        self.assertEqual(self.invoke("/v1/message-requests/engine-status", raw_path=
                                    b"/v1/message-requests/%65ngine-status"),
                         "ENGINE_STATUS_UNAVAILABLE")

    def test_history_list_detail_and_status_unchanged(self):
        for path in ("/v1/conversations", "/v1/conversations/a-1/messages",
                     "/v1/message-requests/status"):
            self.assertIsNone(self.invoke(path))

    def test_readiness_and_revoke_unchanged(self):
        self.assertIsNone(self.invoke("/health/ready"))
        self.assertIsNone(self.invoke("/internal/ready"))
        self.assertIsNone(self.invoke("/internal/auth/session/v1/revoke-one", "POST"))

    def test_unrelated_path_not_reclassified(self):
        self.assertIsNone(self.invoke("/v1/message-requests/engine-status-other"))


if __name__ == "__main__":
    unittest.main()
