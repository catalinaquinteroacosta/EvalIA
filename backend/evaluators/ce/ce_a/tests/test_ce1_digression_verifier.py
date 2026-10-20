from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a.ce1_digression_verifier import (
    validate_digression_result,
    verify_ce1_digression,
)

PREFIX = "backend.evaluators.ce.ce_a.ce1_digression_verifier"


def inputs():
    return {
        "interpretation": "Recomienda comprar flores.",
        "evidence": "compra flores",
        "user_text": "Como preparo mi entrevista?",
        "response_text": "Practica respuestas. Por cierto, compra flores.",
    }


def supported():
    return {
        "verdict": "supported",
        "reason": "La cita respalda la interpretacion.",
    }


def contextual(verdict):
    return {
        "verdict": verdict,
        "reason": "Evaluacion contextual de prueba.",
    }


@pytest.mark.parametrize(
    "verdict",
    [
        "relevant",
        "useful_complement",
        "unnecessary_digression",
        "ambiguous",
    ],
)
def test_contextual_categories(verdict):
    with (
        patch(PREFIX + ".describe_observable", return_value={"description":"Se recomienda comprar flores.","reason":"Contenido literal."}),
        patch(
            PREFIX + ".verify_claims",
            return_value=supported(),
        ) as claims,
        patch(
            PREFIX + ".get_semantic_identity",
            return_value={"model": "test-model"},
        ),
        patch(
            PREFIX + ".run_structured_semantic",
            return_value=contextual(verdict),
        ) as semantic,
    ):
        result = verify_ce1_digression(**inputs())

    claims.assert_called_once()
    semantic.assert_called_once()
    assert result["contextual_verdict"]["verdict"] == verdict
    assert result["score"] is None
    assert result["severity"] is None
    assert result["status"] == (
        "review_required" if verdict == "ambiguous"
        else "classified"
    )


@pytest.mark.parametrize(
    "verdict",
    ["not_supported", "ambiguous"],
)
def test_unverified_evidence_blocks_contextual_check(verdict):
    with (
        patch(PREFIX + ".describe_observable", return_value={"description":"Se recomienda comprar flores.","reason":"Contenido literal."}),
        patch(
            PREFIX + ".verify_claims",
            return_value={
                "verdict": verdict,
                "reason": "Sin respaldo confirmado.",
            },
        ),
        patch(
            PREFIX + ".run_structured_semantic",
        ) as semantic,
    ):
        result = verify_ce1_digression(**inputs())

    semantic.assert_not_called()
    assert result["status"] == "review_required"
    assert result["contextual_verdict"] is None


def test_invented_quote_blocks_before_openai():
    data = inputs()
    data["evidence"] = "frase inventada"

    with patch(PREFIX + ".verify_claims") as claims:
        with pytest.raises(ValueError):
            verify_ce1_digression(**data)

    claims.assert_not_called()


def test_invalid_contextual_result():
    with pytest.raises(ValueError):
        validate_digression_result({
            "verdict": "major",
            "reason": "No autorizado.",
        })
