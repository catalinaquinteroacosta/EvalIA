
from backend.evaluators.pa.verified_integration_pa10 import (
    evaluate_existing,
)


def test_eight_indicators():
    result = evaluate_existing()
    assert set(result) == {f"PA{i}" for i in range(1, 9)}


def test_disputed_indicators_remain_blocked():
    result = evaluate_existing()
    assert result["PA4"]["status"] == "BLOCKED"
    assert result["PA7"]["status"] == "BLOCKED"


def test_no_unverified_scores():
    result = evaluate_existing()
    assert all(item["score"] is None for item in result.values())


def test_six_ready_for_semantic_mapping():
    result = evaluate_existing()
    ready = [
        code for code, item in result.items()
        if item["status"] == "READY_FOR_SEMANTIC_MAPPING"
    ]
    assert len(ready) == 6
