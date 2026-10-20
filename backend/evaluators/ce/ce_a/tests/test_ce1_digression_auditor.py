import pytest

from backend.evaluators.ce.ce_a.ce1_digression_auditor import (
    aggregate_digression,
    validate_digression_audit,
)


@pytest.mark.parametrize(
    "verdict",
    [
        "relevant",
        "useful_complement",
        "unnecessary_digression",
    ],
)
def test_matching_assessments_accepted(verdict):
    result = aggregate_digression(
        {"verdict": verdict, "reason": "Original."},
        {"assessment": verdict, "reason": "Auditoria."},
    )

    assert result["verified"] is True
    assert result["verdict"] == verdict
    assert result["score"] is None
    assert result["severity"] is None


def test_disagreement_requires_review():
    result = aggregate_digression(
        {
            "verdict": "unnecessary_digression",
            "reason": "Original.",
        },
        {
            "assessment": "useful_complement",
            "reason": "Auditoria.",
        },
    )

    assert result["verified"] is False
    assert result["verdict"] is None
    assert result["review_required"] is True


@pytest.mark.parametrize(
    "original,audit",
    [
        ("ambiguous", "relevant"),
        ("relevant", "ambiguous"),
        ("ambiguous", "ambiguous"),
    ],
)
def test_ambiguity_requires_review(original, audit):
    result = aggregate_digression(
        {"verdict": original, "reason": "Original."},
        {"assessment": audit, "reason": "Auditoria."},
    )

    assert result["verified"] is False
    assert result["verdict"] is None


def test_invalid_audit_blocks():
    with pytest.raises(ValueError):
        validate_digression_audit({
            "assessment": "major",
            "reason": "Invalido.",
        })


def test_missing_reason_blocks():
    with pytest.raises(ValueError):
        validate_digression_audit({
            "assessment": "relevant",
            "reason": "",
        })
