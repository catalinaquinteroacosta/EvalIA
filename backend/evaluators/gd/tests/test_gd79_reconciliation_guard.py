from backend.evaluators.gd.gd79_reconciliation_guard import (
    reconcile_gd567,
)

def test_disagreement_blocks():
    results = {
        code: {"status": "SCORED", "score": 0}
        for code in ("GD5", "GD6", "GD7")
    }
    coherence = {
        code: {"status": "CONSISTENT", "issues": []}
        for code in ("GD5", "GD6", "GD7")
    }

    output = reconcile_gd567(results, coherence)

    assert output["GD6"]["status"] == "BLOCKED"
    assert output["GD5"]["status"] == "READY"
    assert output["GD7"]["status"] == "READY"

def test_semantic_inconsistency_blocks():
    results = {
        code: {"status": "SCORED", "score": 3}
        for code in ("GD5", "GD6", "GD7")
    }
    coherence = {
        code: {"status": "CONSISTENT", "issues": []}
        for code in ("GD5", "GD6", "GD7")
    }
    coherence["GD7"]["status"] = "BLOCKED"

    output = reconcile_gd567(results, coherence)

    assert output["GD7"]["status"] == "BLOCKED"

def test_missing_score_blocks():
    results = {
        code: {"status": "SCORED", "score": 3}
        for code in ("GD5", "GD6", "GD7")
    }
    results["GD5"] = {
        "status": "BLOCKED",
        "score": None,
    }

    coherence = {
        code: {"status": "CONSISTENT", "issues": []}
        for code in ("GD5", "GD6", "GD7")
    }

    output = reconcile_gd567(results, coherence)

    assert output["GD5"]["status"] == "BLOCKED"
