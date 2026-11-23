"""Run 196 API tests in real image; two original C018 filesystem-dependent
tests remain BLOCKED, not passed. No changes to original test suite.
"""
import sys
import unittest

BLOCKED = {
    "test_staging_preflight.PinnedStagingPreflight.test_cli_requires_no_dispatch_and_reports_only_safe_bools",
    "test_staging_preflight.PinnedStagingPreflight.test_preflight_only_static_checks_never_imports_runner_or_secrets",
}

def flatten(suite):
    for x in suite:
        if isinstance(x, unittest.TestSuite):
            yield from flatten(x)
        else:
            yield x

all_cases = list(flatten(unittest.defaultTestLoader.discover("tests/phase3/api", pattern="test_*.py")))
ids = {test.id() for test in all_cases}
assert len(all_cases) == 198, f"Unexpected test count: {len(all_cases)}"
assert BLOCKED.issubset(ids), f"Missing original engine-bound IDs: {BLOCKED - ids}"
cases = [test for test in all_cases if test.id() not in BLOCKED]
assert len(cases) == 196
result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(cases))
if not result.wasSuccessful() or result.testsRun != 196:
    sys.exit("F3_API_CONTAINER_NON_ENGINE_TESTS_FAIL")
print("F3_API_CONTAINER_196_PASS_2_ENGINE_MOUNT_TESTS_BLOCKED")
