from backend.evaluators.ce.ce_a import pipeline
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER, RESPONSE, example,
)


def configure(monkeypatch, coverage_verdict):
    monkeypatch.setattr(
        pipeline, "verify_need",
        lambda *args, **kwargs: {
            "verdict": "supported",
            "reason": "Necesidad v?lida.",
        },
    )
    monkeypatch.setattr(
        pipeline, "verify_claims",
        lambda **kwargs: {
            "verdict": "supported",
            "reason": "Evidencia v?lida.",
        },
    )
    monkeypatch.setattr(
        pipeline, "verify_omission",
        lambda **kwargs: {
            "verdict": "supported",
            "reason": "Omisi?n v?lida.",
        },
    )
    monkeypatch.setattr(
        pipeline, "audit_coverage",
        lambda **kwargs: {
            "verdict": coverage_verdict,
            "findings": (
                [{
                    "field": "ce1_digressions",
                    "issue": "Posible contenido no identificado.",
                    "evidence": RESPONSE,
                }]
                if coverage_verdict == "incomplete"
                else []
            ),
            "reason": "Auditor?a simulada.",
        },
    )


def test_complete_coverage_is_recorded(monkeypatch):
    configure(monkeypatch, "complete")
    result = pipeline.evaluate_ce_a_evidence(
        USER, RESPONSE, extraction=example()
    )
    assert result["coverage"]["verdict"] == "complete"
    assert result["pending"] == []
    assert result["ready_for_scoring"] is False


def test_incomplete_coverage_blocks_scoring(monkeypatch):
    configure(monkeypatch, "incomplete")
    result = pipeline.evaluate_ce_a_evidence(
        USER, RESPONSE, extraction=example()
    )
    assert any(
        item["field"] == "coverage"
        for item in result["pending"]
    )
    assert result["status"] == "review_required"
    assert result["ready_for_scoring"] is False


def test_ambiguous_coverage_blocks_scoring(monkeypatch):
    configure(monkeypatch, "ambiguous")
    result = pipeline.evaluate_ce_a_evidence(
        USER, RESPONSE, extraction=example()
    )
    assert result["coverage"]["verdict"] == "ambiguous"
    assert result["status"] == "review_required"
    assert result["ready_for_scoring"] is False
