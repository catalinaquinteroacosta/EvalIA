import pytest

from backend.evaluators.ce.ce_a.ce1_unaddressed_verifier import (
    validate_result,
    verify_unaddressed_need,
)

USER = "Como puedo prepararme esta noche?"
RESPONSE = "Prepara los documentos de la entrevista."

ITEM = {
    "need": "Prepararse esta noche.",
    "source": "current_user",
    "evidence": "prepararme esta noche",
    "explanation": "Supuestamente no se atiende.",
}


@pytest.mark.parametrize(
    "verdict",
    [
        "unaddressed",
        "partially_addressed",
        "addressed",
        "ambiguous",
    ],
)
def test_valid_verdicts(verdict):
    data = {"verdict": verdict, "reason": "Evaluacion."}
    assert validate_result(data) == data


@pytest.mark.parametrize(
    "data",
    [
        {"verdict": "supported", "reason": "No corresponde."},
        {"verdict": "addressed", "reason": ""},
        {"verdict": "addressed"},
        {"verdict": "addressed", "reason": "OK", "score": 3},
        [],
    ],
)
def test_invalid_results(data):
    with pytest.raises(ValueError):
        validate_result(data)


def test_semantic_call_without_real_api(monkeypatch):
    from backend.evaluators.ce.ce_a import ce1_unaddressed_verifier as mod

    calls = []

    monkeypatch.setattr(
        mod,
        "get_semantic_identity",
        lambda **kwargs: {"model": "mock-model"},
    )

    def fake_semantic(**kwargs):
        calls.append(kwargs)
        return {
            "verdict": "addressed",
            "reason": "La respuesta ofrece una preparacion pertinente.",
        }

    monkeypatch.setattr(
        mod,
        "run_structured_semantic",
        fake_semantic,
    )

    result = verify_unaddressed_need(
        ITEM,
        user_text=USER,
        response_text=RESPONSE,
        use_cache=False,
    )

    assert result["verdict"] == "addressed"
    assert len(calls) == 1
    assert calls[0]["schema"] == mod.SCHEMA
    assert "No asignes gravedad" in calls[0]["prompt"]


def test_invalid_evidence_blocks_api(monkeypatch):
    from backend.evaluators.ce.ce_a import ce1_unaddressed_verifier as mod

    def forbidden(**kwargs):
        raise AssertionError("No debe llamarse la API.")

    monkeypatch.setattr(
        mod,
        "get_semantic_identity",
        forbidden,
    )

    invalid = dict(ITEM, evidence="texto inexistente")

    with pytest.raises(ValueError):
        verify_unaddressed_need(
            invalid,
            user_text=USER,
            response_text=RESPONSE,
            use_cache=False,
        )
