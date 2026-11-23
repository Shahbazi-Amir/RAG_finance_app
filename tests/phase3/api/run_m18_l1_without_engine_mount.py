"""Run all engine-independent API tests in real image; two original C018 filesystem-dependent
tests remain BLOCKED, not passed. No changes to original test suite.
"""
import sys
import unittest
import os
# Match unittest discover's import root even when invoked by direct script path.
sys.path.insert(0, os.getcwd())

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
assert len(all_cases) >= 198, f"Unexpected regression in test discovery: {len(all_cases)}"
assert len(ids) == len(all_cases), "Duplicate API test IDs"
assert BLOCKED.issubset(ids), f"Missing original engine-bound IDs: {BLOCKED - ids}"
cases = [test for test in all_cases if test.id() not in BLOCKED]
expected = len(all_cases) - len(BLOCKED)
assert len(cases) == expected
result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(cases))
if not result.wasSuccessful() or result.testsRun != expected:
    sys.exit("F3_API_CONTAINER_NON_ENGINE_TESTS_FAIL")
print(f"F3_API_CONTAINER_{expected}_PASS_2_ENGINE_MOUNT_TESTS_BLOCKED")
