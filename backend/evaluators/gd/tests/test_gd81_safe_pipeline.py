from backend.evaluators.gd.gd79_reconciliation_guard import (
    reconcile_gd567,
)

def test_gd6_human_conflict_blocks():
    results = {
        c: {"status": "SCORED", "score": 3}
        for c in ("GD5", "GD6", "GD7")
    }
    coherence = {
        c: {"status": "CONSISTENT", "issues": []}
        for c in ("GD5", "GD6", "GD7")
    }

    result = reconcile_gd567(
        results,
        coherence,
        historical_gd6_disagreement=True,
    )

    assert result["GD6"]["status"] == "BLOCKED"

def test_gd5_applicability_disagreement_blocks():
    results = {
        c: {"status": "SCORED", "score": 3}
        for c in ("GD5", "GD6", "GD7")
    }
    coherence = {
        c: {"status": "CONSISTENT", "issues": []}
        for c in ("GD5", "GD6", "GD7")
    }
    coherence["GD5"] = {
        "status": "BLOCKED",
        "issues": ["UNRESOLVED_APPLICABILITY"],
    }

    result = reconcile_gd567(
        results,
        coherence,
    )

    assert result["GD5"]["status"] == "BLOCKED"

def test_gd7_ready_when_consistent():
    results = {
        c: {"status": "SCORED", "score": 1}
        for c in ("GD5", "GD6", "GD7")
    }
    coherence = {
        c: {"status": "CONSISTENT", "issues": []}
        for c in ("GD5", "GD6", "GD7")
    }

    result = reconcile_gd567(
        results,
        coherence,
    )

    assert result["GD7"]["status"] == "READY"
