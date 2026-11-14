"""Fixture-only answer producer for the isolated Product API."""
import json

from apps.api import history_api as history

_FIXTURE_CASES = history.ROOT / "packages/contracts/fixtures/product.v1.cases.json"


def answer_from_fixture(question: str) -> dict:
    """Leave retrieval and generation to the future versioned engine."""
    if not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    cases = json.loads(_FIXTURE_CASES.read_text(encoding="utf-8"))["cases"]
    return next(case["document"] for case in cases
                if case["case_id"] == "valid_answer_unresolved_source")
