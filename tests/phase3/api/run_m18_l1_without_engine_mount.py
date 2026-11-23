"""Run the complete current non-engine API suite in a real image; two original C018 filesystem-dependent
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
assert len(all_cases) >= 203, f"API suite shrank unexpectedly: {len(all_cases)}"
assert len(ids) == len(all_cases), "Duplicate API unittest IDs"
assert BLOCKED.issubset(ids), f"Missing original engine-bound IDs: {BLOCKED - ids}"
cases = [test for test in all_cases if test.id() not in BLOCKED]
assert len(cases) == len(all_cases) - len(BLOCKED)
result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(cases))
if not result.wasSuccessful() or result.testsRun != len(cases):
    sys.exit("F3_API_CONTAINER_NON_ENGINE_TESTS_FAIL")
print(f"F3_API_CONTAINER_{len(cases)}_PASS_{len(BLOCKED)}_ENGINE_MOUNT_TESTS_BLOCKED")
