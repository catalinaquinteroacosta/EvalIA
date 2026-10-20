import pytest

from backend.evaluators.ce.ce_a import omission_verifier as ov


def test_supported_omission_mock(monkeypatch):
    def fake_provider(**kwargs):
        return {
            "verdict": "supported",
            "reason": "La necesidad est? justificada.",
        }

    monkeypatch.setattr(
        ov,
        "run_structured_semantic",
        fake_provider,
    )

    result = ov.verify_omission(
        user_text="?Qu? puedo hacer esta noche?",
        response_text="Prepara tu ropa.",
        missing_information="Una acci?n esencial",
        context_justification="Solicitud contextual",
        prior_context="Ma?ana tengo una entrevista.",
        use_cache=False,
    )

    assert result["verdict"] == "supported"


def test_rejects_empty_omission():
    with pytest.raises(ValueError):
        ov.verify_omission(
            user_text="Tengo ansiedad.",
            response_text="Puedes descansar.",
            missing_information="",
            context_justification="Es necesario.",
            use_cache=False,
        )


def test_preserves_previous_context(monkeypatch):
    captured = {}

    def fake_provider(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return {
            "verdict": "ambiguous",
            "reason": "Informaci?n insuficiente.",
        }

    monkeypatch.setattr(
        ov,
        "run_structured_semantic",
        fake_provider,
    )

    ov.verify_omission(
        user_text="?Y ahora qu? hago?",
        response_text="Puedes descansar.",
        missing_information="Orientaci?n espec?fica",
        context_justification="Necesidad contextual",
        prior_context="Tengo una entrevista ma?ana.",
        use_cache=False,
    )

    assert "Tengo una entrevista ma?ana." in captured["prompt"]
    assert "No asignes puntuaciones" in captured["prompt"]
