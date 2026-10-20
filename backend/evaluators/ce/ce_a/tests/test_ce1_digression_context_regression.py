import pytest

from backend.evaluators.ce.ce_a import (
    ce1_digression_auditor as auditor,
)


@pytest.fixture
def captured_auditor(monkeypatch):
    captured = {}

    def fake_identity(**kwargs):
        captured["identity"] = kwargs
        return {"model": "test-model"}

    def fake_semantic(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return {
            "assessment": "relevant",
            "reason": (
                "El fragmento responde a una "
                "solicitud del contexto previo."
            ),
        }

    monkeypatch.setattr(
        auditor,
        "get_semantic_identity",
        fake_identity,
    )
    monkeypatch.setattr(
        auditor,
        "run_structured_semantic",
        fake_semantic,
    )

    return captured


def test_auditor_limits_analysis_to_quoted_fragment(
    captured_auditor,
):
    result = auditor.audit_ce1_digression(
        interpretation=(
            "Indica que se debe llevar el inhalador."
        ),
        evidence="Recuerda llevar tu inhalador",
        user_text="?Qu? m?s deber?a tener en cuenta?",
        response_text=(
            "Prepara tus documentos. "
            "Recuerda llevar tu inhalador."
        ),
        prior_context=(
            "El usuario pidio que se le recordara "
            "llevar su inhalador."
        ),
    )

    prompt = captured_auditor["prompt"]

    assert "EXCLUSIVAMENTE" in prompt
    assert "evidence" in prompt
    assert "no clasifiques otros" in prompt
    assert result["assessment"] == "relevant"


def test_auditor_considers_prior_requests(
    captured_auditor,
):
    auditor.audit_ce1_digression(
        interpretation=(
            "Indica que se debe llevar el inhalador."
        ),
        evidence="Recuerda llevar tu inhalador",
        user_text="?Qu? m?s deber?a tener en cuenta?",
        response_text="Recuerda llevar tu inhalador.",
        prior_context=(
            "El usuario pidio que se le recordara "
            "llevar su inhalador."
        ),
    )

    prompt = captured_auditor["prompt"]

    assert "contexto previo" in prompt
    assert "relevant" in prompt
    assert "useful_complement" in prompt
    assert "llevar su inhalador" in prompt


def test_contextual_disagreement_blocks_scoring():
    result = auditor.aggregate_digression(
        {
            "verdict": "relevant",
            "reason": (
                "Atiende una solicitud previa."
            ),
        },
        {
            "assessment": "useful_complement",
            "reason": (
                "El auditor discrepa."
            ),
        },
    )

    assert result["verified"] is False
    assert result["review_required"] is True
    assert result["verdict"] is None
    assert result["severity"] is None
    assert result["score"] is None


def test_contextual_agreement_does_not_score():
    result = auditor.aggregate_digression(
        {
            "verdict": "relevant",
            "reason": (
                "Atiende una solicitud previa."
            ),
        },
        {
            "assessment": "relevant",
            "reason": (
                "Atiende la misma solicitud."
            ),
        },
    )

    assert result["verified"] is True
    assert result["verdict"] == "relevant"
    assert result["severity"] is None
    assert result["score"] is None
