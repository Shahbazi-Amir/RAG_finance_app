"""Test-only app-only client retry matrix; no persistence or dispatch authority."""
from concurrent.futures import ThreadPoolExecutor


def assert_disabled_retries(send, snapshot, *, attempts=6):
    """Run one simultaneous retry wave and verify unchanged scoped SQL state.

    send(index) must return the actual HTTP status and parsed error code.
    snapshot() must read independently measured state for both owners.
    A network error, unexpected response or SQL change is a test failure.
    """
    if type(attempts) is not int or not 2 <= attempts <= 8:
        raise ValueError("INVALID_RETRY_COUNT")
    before = snapshot()
    with ThreadPoolExecutor(max_workers=attempts) as pool:
        results = tuple(pool.map(send, range(attempts)))
    if results != ((503, "ENGINE_NOT_CONFIGURED"),) * attempts:
        raise AssertionError("APP_ONLY_RETRY_RESPONSE_MISMATCH")
    if snapshot() != before:
        raise AssertionError("APP_ONLY_RETRY_SQL_CHANGED")
    return len(results)
