import pytest

from backend.evaluators.ir.core.integrity import (
    validate_reconciliation_rows,
    assess_integrity,
)


def decision(identifier, verdict="supported"):
    return {
        "id": identifier,
        "verdict": verdict,
        "reason": "Justificación de prueba",
    }


def test_complete_decisions():
    assert validate_reconciliation_rows(
        [decision("a"), decision("b")],
        ["a", "b"],
    )


def test_missing_decision_rejected():
    with pytest.raises(ValueError):
        validate_reconciliation_rows(
            [decision("a")],
            ["a", "b"],
        )


def test_duplicate_decision_rejected():
    with pytest.raises(ValueError):
        validate_reconciliation_rows(
            [decision("a"), decision("a")],
            ["a"],
        )


def test_unknown_decision_rejected():
    with pytest.raises(ValueError):
        validate_reconciliation_rows(
            [decision("x")],
            ["a"],
        )


def test_ambiguous_remains_blocked():
    result = assess_integrity(
        {
            "status": "REVIEWED",
            "reconciliation": [
                decision("a", "ambiguous")
            ],
        },
        ["a"],
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_previous_blocked_not_cleared():
    result = assess_integrity(
        {
            "status": "BLOCKED",
            "reconciliation": [
                decision("a")
            ],
        },
        ["a"],
    )

    assert result["status"] == "BLOCKED"


def test_valid_structure_does_not_assign_score():
    result = assess_integrity(
        {
            "status": "REVIEWED",
            "reconciliation": [
                decision("a", "unsupported")
            ],
        },
        ["a"],
    )

    assert result["status"] == "INTEGRITY_CHECKED"
    assert result["score"] is None


def test_missing_expected_id_blocks():
    result = assess_integrity(
        {
            "status": "REVIEWED",
            "reconciliation": [],
        },
        ["a"],
    )

    assert result["status"] == "BLOCKED"