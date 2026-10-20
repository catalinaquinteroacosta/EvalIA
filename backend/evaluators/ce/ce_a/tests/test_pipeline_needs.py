import copy

from backend.evaluators.ce.ce_a import pipeline
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER,
    RESPONSE,
    example,
)


def configure(monkeypatch, need_verdict):
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
        "verify_need",
        lambda *args, **kwargs: {
            "verdict": need_verdict,
            "reason": "Resultado simulado.",
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
        "verify_omission",
        lambda **kwargs: {
            "verdict": "supported",
            "reason": "Omisi?n respaldada.",
        },
    )


def test_explicit_need_is_adapted(monkeypatch):
    captured = []

    def fake_need(need, **kwargs):
        captured.append(need)
        return {
            "verdict": "supported",
            "reason": "Correcto.",
        }

    configure(monkeypatch, "supported")
    monkeypatch.setattr(
        pipeline, "verify_need", fake_need
    )

    result = pipeline.evaluate_ce_a_evidence(
        USER, RESPONSE, extraction=example()
    )

    assert len(captured) == 1
    assert captured[0]["source"] == "current_user"
    assert captured[0]["evidence"] == (
        example()["explicit_needs"][0]["user_evidence"]
    )
    assert len(result["need_checks"]) == 1
    assert result["ready_for_scoring"] is False


def test_rejected_need_is_not_approved(monkeypatch):
    configure(monkeypatch, "not_supported")

    result = pipeline.evaluate_ce_a_evidence(
        USER, RESPONSE, extraction=example()
    )

    assert result["pending"][0]["field"] == "needs"
    assert result["status"] == "review_required"
    assert result["ready_for_scoring"] is False


def test_ambiguous_contextual_need(monkeypatch):
    configure(monkeypatch, "ambiguous")

    data = copy.deepcopy(example())
    prior = "Tengo una entrevista laboral importante."
    data["contextual_needs"] = [{
        "interpretation": "Necesita preparaci?n.",
        "source": "prior_context",
        "evidence": prior,
        "justification": "Expres? esa situaci?n antes.",
    }]

    result = pipeline.evaluate_ce_a_evidence(
        USER,
        RESPONSE,
        prior_context=prior,
        extraction=data,
    )

    assert len(result["need_checks"]) == 2
    assert all(
        item["verdict"] == "ambiguous"
        for item in result["need_checks"]
    )
    assert result["ready_for_scoring"] is False
