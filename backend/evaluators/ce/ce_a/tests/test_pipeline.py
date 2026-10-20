from backend.evaluators.ce.ce_a import pipeline
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER,
    RESPONSE,
    example,
)


def configure(monkeypatch, omission_verdict):
    monkeypatch.setattr(
        pipeline,
        "audit_coverage",
        lambda **kwargs: {
            "verdict": "complete",
            "findings": [],
            "reason": "Cobertura simulada.",
        },
    )

    monkeypatch.setattr(
        pipeline,
        "verify_claims",
        lambda **kwargs: {
            "verdict": "supported",
            "reason": "Cita respaldada.",
        },
    )

    monkeypatch.setattr(
        pipeline,
        "verify_need",
        lambda *args, **kwargs: {
            "verdict": "supported",
            "reason": "Necesidad respaldada.",
        },
    )

    monkeypatch.setattr(
        pipeline,
        "verify_omission",
        lambda **kwargs: {
            "verdict": omission_verdict,
            "reason": "Resultado simulado.",
        },
    )


def with_omission():
    data = example()
    data["ce2_essential_omissions"] = [
        {
            "missing_information": "Orientaci?n esencial",
            "context_justification": "Solicitud contextual",
            "source": "current_user",
            "user_evidence": "?Qu? puedo hacer esta noche?",
        }
    ]
    return data


def test_supported_omission(monkeypatch):
    configure(monkeypatch, "supported")

    result = pipeline.evaluate_ce_a_evidence(
        USER,
        RESPONSE,
        extraction=with_omission(),
    )

    assert len(result["omission_checks"]) == 1
    assert result["pending"] == []
    assert result["ready_for_scoring"] is False


def test_rejected_omission(monkeypatch):
    configure(monkeypatch, "not_supported")

    result = pipeline.evaluate_ce_a_evidence(
        USER,
        RESPONSE,
        extraction=with_omission(),
    )

    assert result["pending"] == []
    assert result["status"] == "partial_validation_complete"
    assert result["omission_resolution"] is not None


def test_ambiguous_omission(monkeypatch):
    configure(monkeypatch, "ambiguous")

    result = pipeline.evaluate_ce_a_evidence(
        USER,
        RESPONSE,
        extraction=with_omission(),
    )

    assert result["pending"][0]["verdict"] == "ambiguous"
    assert result["ready_for_scoring"] is False


def test_no_omissions(monkeypatch):
    configure(monkeypatch, "supported")

    result = pipeline.evaluate_ce_a_evidence(
        USER,
        RESPONSE,
        extraction=example(),
    )

    assert result["omission_checks"] == []
    assert result["status"] == "partial_validation_complete"
