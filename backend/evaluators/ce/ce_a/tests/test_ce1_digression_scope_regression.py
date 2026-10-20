from backend.evaluators.ce.ce_a import (
    ce1_digression_verifier as verifier,
)


def test_verifier_evaluates_only_quoted_fragment(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        verifier,
        "describe_observable",
        lambda *args, **kwargs: {"description": "Recuerda llevar el inhalador", "reason": "Cita literal."},
    )
    monkeypatch.setattr(
        verifier,
        "verify_claims",
        lambda *args, **kwargs: {
            "verdict": "supported",
            "reason": "Cita respaldada.",
        },
    )
    monkeypatch.setattr(
        verifier,
        "get_semantic_identity",
        lambda **kwargs: {"model": "test-model"},
    )

    def fake_semantic(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return {
            "verdict": "relevant",
            "reason": "Atiende la solicitud previa.",
        }

    monkeypatch.setattr(
        verifier,
        "run_structured_semantic",
        fake_semantic,
    )

    result = verifier.verify_ce1_digression(
        interpretation="Indica llevar el inhalador.",
        evidence="Recuerda llevar tu inhalador",
        user_text="?Que mas debo tener en cuenta?",
        response_text=(
            "Prepara tus documentos. "
            "Recuerda llevar tu inhalador."
        ),
        prior_context=(
            "El usuario pidio que se le recordara "
            "llevar su inhalador."
        ),
    )

    prompt = captured["prompt"]
    assert "EXCLUSIVAMENTE" in prompt
    assert "no clasifiques otros fragmentos" in prompt
    assert "contexto previo" in prompt
    assert "Reserva useful_complement" in prompt
    assert result["contextual_verdict"]["verdict"] == "relevant"
    assert result["score"] is None


def test_unsupported_evidence_never_reaches_context(
    monkeypatch,
):
    monkeypatch.setattr(
        verifier,
        "describe_observable",
        lambda *args, **kwargs: {"description": "Recuerda llevar el inhalador", "reason": "Cita literal."},
    )
    monkeypatch.setattr(
        verifier,
        "verify_claims",
        lambda *args, **kwargs: {
            "verdict": "ambiguous",
            "reason": "Interpretacion incierta.",
        },
    )

    def forbidden(**kwargs):
        raise AssertionError(
            "No debe clasificarse evidencia incierta."
        )

    monkeypatch.setattr(
        verifier,
        "run_structured_semantic",
        forbidden,
    )

    result = verifier.verify_ce1_digression(
        interpretation="Indica llevar el inhalador.",
        evidence="Recuerda llevar tu inhalador",
        user_text="?Que mas debo tener en cuenta?",
        response_text="Recuerda llevar tu inhalador.",
    )

    assert result["status"] == "review_required"
    assert result["contextual_verdict"] is None
    assert result["severity"] is None
    assert result["score"] is None
