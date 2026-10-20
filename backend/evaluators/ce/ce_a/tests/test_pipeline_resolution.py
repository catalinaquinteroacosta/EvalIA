from copy import deepcopy

import pytest

from backend.evaluators.ce.ce_a import pipeline
from backend.evaluators.ce.ce_a.tests.test_pipeline import (
    configure,
    with_omission,
)
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER,
    RESPONSE,
)


def evaluate(data=None):
    return pipeline.evaluate_ce_a_evidence(
        USER,
        RESPONSE,
        extraction=data if data is not None else with_omission(),
    )


def test_rejected_omission_has_trace(monkeypatch):
    configure(monkeypatch, "not_supported")
    original = with_omission()
    snapshot = deepcopy(original)

    result = evaluate(original)

    assert original == snapshot
    assert result["pending"] == []
    assert result["status"] == "partial_validation_complete"
    assert result["omission_resolution"][
        "resolved_extraction"
    ]["ce2_essential_omissions"] == []
    assert result["omission_resolution"][
        "resolution_log"
    ][0]["action"] == "excluded_after_verification"
    assert result["ready_for_scoring"] is False


def test_supported_omission_is_retained(monkeypatch):
    configure(monkeypatch, "supported")
    original = with_omission()
    result = evaluate(original)

    assert result["omission_resolution"][
        "resolved_extraction"
    ]["ce2_essential_omissions"] == (
        original["ce2_essential_omissions"]
    )


@pytest.mark.parametrize(
    "verdict",
    ["ambiguous", "unexpected"],
)
def test_unresolved_omission_blocks(monkeypatch, verdict):
    configure(monkeypatch, verdict)
    result = evaluate()

    assert result["omission_resolution"] is None
    assert result["status"] == "review_required"
    assert result["ready_for_scoring"] is False


@pytest.mark.parametrize(
    "coverage_verdict",
    ["incomplete", "ambiguous"],
)
def test_failed_coverage_blocks(monkeypatch, coverage_verdict):
    configure(monkeypatch, "not_supported")

    monkeypatch.setattr(
        pipeline,
        "audit_coverage",
        lambda **kwargs: {
            "verdict": coverage_verdict,
            "findings": (
                [{
                    "field": "ce1_digressions",
                    "issue": "Missing relevant content.",
                    "evidence": RESPONSE,
                }]
                if coverage_verdict == "incomplete"
                else []
            ),
            "reason": "Coverage not complete.",
        },
    )

    result = evaluate()
    assert result["omission_resolution"] is None
    assert result["status"] == "review_required"


@pytest.mark.parametrize(
    "verifier,verdict",
    [
        ("verify_need", "not_supported"),
        ("verify_claims", "not_supported"),
    ],
)
def test_other_verification_blocks(
    monkeypatch, verifier, verdict
):
    configure(monkeypatch, "not_supported")

    monkeypatch.setattr(
        pipeline,
        verifier,
        lambda *args, **kwargs: {
            "verdict": verdict,
            "reason": "Verification failed.",
        },
    )

    result = evaluate()
    assert result["omission_resolution"] is None
    assert result["status"] == "review_required"
