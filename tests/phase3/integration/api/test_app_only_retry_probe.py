import unittest
from app_only_retry_probe import assert_disabled_retries


class RetryProbeTests(unittest.TestCase):
    def test_all_retries_denied(self):
        calls = []
        def send(index):
            calls.append(index)
            return 503, "ENGINE_NOT_CONFIGURED"
        self.assertEqual(assert_disabled_retries(send, lambda: (5, 3, 0, 0)), 6)
        self.assertEqual(sorted(calls), list(range(6)))

    def test_success_response_is_failure(self):
        with self.assertRaisesRegex(AssertionError, "RESPONSE_MISMATCH"):
            assert_disabled_retries(lambda i: (200, "OK"), lambda: (0,))

    def test_wrong_error_code_is_failure(self):
        with self.assertRaisesRegex(AssertionError, "RESPONSE_MISMATCH"):
            assert_disabled_retries(lambda i: (503, "OTHER"), lambda: (0,))

    def test_sql_mutation_is_failure(self):
        snapshots = iter([(0, 0), (0, 1)])
        with self.assertRaisesRegex(AssertionError, "SQL_CHANGED"):
            assert_disabled_retries(lambda i: (503, "ENGINE_NOT_CONFIGURED"), lambda: next(snapshots))

    def test_network_failure_propagates(self):
        def send(i):
            raise ConnectionError("synthetic")
        with self.assertRaises(ConnectionError):
            assert_disabled_retries(send, lambda: (0,))

    def test_count_bounds(self):
        for n in (0, 1, 9, True, "6"):
            with self.assertRaises(ValueError):
                assert_disabled_retries(None, None, attempts=n)

    def test_snapshot_failure_propagates(self):
        def snapshot():
            raise RuntimeError("synthetic SQL failure")
        with self.assertRaises(RuntimeError):
            assert_disabled_retries(lambda i: (503, "ENGINE_NOT_CONFIGURED"), snapshot)


if __name__ == "__main__":
    unittest.main()
