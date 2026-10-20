import pytest

from backend.evaluators.ce.ce_a.ce1_unaddressed_auditor import (
    aggregate_review,
    validate_audit,
)


def audit(verdict, assessment):
    return {
        "verdict": verdict,
        "independent_assessment": assessment,
        "reason": "Revision independiente.",
    }


def original(verdict):
    return {
        "verdict": verdict,
        "reason": "Verificacion inicial.",
    }


@pytest.mark.parametrize(
    "verdict",
    ["addressed", "partially_addressed", "unaddressed"],
)
def test_confirmed(verdict):
    result = aggregate_review(
        original(verdict),
        audit("confirmed", verdict),
    )
    assert result["verified"] is True
    assert result["verdict"] == verdict


def test_rejection_blocks():
    result = aggregate_review(
        original("unaddressed"),
        audit("rejected", "addressed"),
    )
    assert result["review_required"] is True
    assert result["verdict"] is None


def test_ambiguity_blocks():
    result = aggregate_review(
        original("unaddressed"),
        audit("ambiguous", "ambiguous"),
    )
    assert result["verified"] is False


@pytest.mark.parametrize(
    "verdict,assessment",
    [
        ("confirmed", "addressed"),
        ("rejected", "unaddressed"),
        ("ambiguous", "addressed"),
    ],
)
def test_contradictions_rejected(verdict, assessment):
    with pytest.raises(ValueError):
        validate_audit(
            audit(verdict, assessment),
            "unaddressed",
        )


def test_original_ambiguity_never_authorized():
    result = aggregate_review(
        original("ambiguous"),
        audit("ambiguous", "ambiguous"),
    )
    assert result["review_required"] is True
