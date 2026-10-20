import pytest

from backend.evaluators.ce.ce_a import (
    ce1_verified_digression_pipeline as pipeline,
)


ARGS = {
    "interpretation": "Menciona los volcanes.",
    "evidence": "Los volcanes son fascinantes",
    "user_text": "?C?mo preparo mi entrevista?",
    "response_text": "Los volcanes son fascinantes.",
}


def original(
    verdict="unnecessary_digression",
    support="supported",
    status="classified",
):
    return {
        "status": status,
        "evidence_support": {
            "verdict": support,
            "reason": "Resultado de evidencia.",
        },
        "contextual_verdict": (
            {
                "verdict": verdict,
                "reason": "Primera clasificacion.",
            }
            if status == "classified"
            else None
        ),
        "severity": None,
        "score": None,
    }


def test_agreement_verifies_without_scoring(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "verify_ce1_digression",
        lambda **kwargs: original(),
    )
    monkeypatch.setattr(
        pipeline,
        "audit_ce1_digression",
        lambda **kwargs: {
            "assessment": "unnecessary_digression",
            "reason": "Auditoria independiente.",
        },
    )

    result = pipeline.evaluate_verified_digression(**ARGS)

    assert result["status"] == "verified"
    assert result["decision"]["verified"] is True
    assert result["severity"] is None
    assert result["score"] is None
    assert result["evidence"] == ARGS["evidence"]


def test_disagreement_requires_review(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "verify_ce1_digression",
        lambda **kwargs: original(),
    )
    monkeypatch.setattr(
        pipeline,
        "audit_ce1_digression",
        lambda **kwargs: {
            "assessment": "relevant",
            "reason": "Discrepancia.",
        },
    )

    result = pipeline.evaluate_verified_digression(**ARGS)

    assert result["status"] == "review_required"
    assert result["decision"]["verdict"] is None
    assert result["score"] is None


@pytest.mark.parametrize(
    "support,status",
    [
        ("ambiguous", "review_required"),
        ("not_supported", "review_required"),
        ("supported", "review_required"),
    ],
)
def test_unverified_first_control_blocks_audit(
    monkeypatch, support, status
):
    monkeypatch.setattr(
        pipeline,
        "verify_ce1_digression",
        lambda **kwargs: original(
            support=support,
            status=status,
        ),
    )

    def forbidden_audit(**kwargs):
        raise AssertionError(
            "El auditor no debe ejecutarse."
        )

    monkeypatch.setattr(
        pipeline,
        "audit_ce1_digression",
        forbidden_audit,
    )

    result = pipeline.evaluate_verified_digression(**ARGS)

    assert result["status"] == "review_required"
    assert result["audit"] is None
    assert result["score"] is None


def test_ambiguous_audit_blocks(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "verify_ce1_digression",
        lambda **kwargs: original(),
    )
    monkeypatch.setattr(
        pipeline,
        "audit_ce1_digression",
        lambda **kwargs: {
            "assessment": "ambiguous",
            "reason": "No concluyente.",
        },
    )

    result = pipeline.evaluate_verified_digression(**ARGS)

    assert result["status"] == "review_required"
    assert result["decision"]["verified"] is False
    assert result["score"] is None
