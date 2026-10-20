from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a.ce1_verified_need_pipeline import (
    evaluate_verified_need,
)

PREFIX = "backend.evaluators.ce.ce_a.ce1_verified_need_pipeline"

USER = "Necesito preparar mi entrevista."
RESPONSE = "Investiga la empresa."


def need():
    return {
        "need": "Preparar la entrevista.",
        "source": "current_user",
        "evidence": "preparar mi entrevista",
        "explanation": "Solicitud del usuario.",
    }


def test_same_inputs_for_both_verifiers():
    original = {
        "verdict": "addressed",
        "reason": "Recomendacion pertinente.",
    }
    audit = {
        "verdict": "confirmed",
        "independent_assessment": "addressed",
        "reason": "La respuesta aborda la necesidad.",
    }

    with (
        patch(
            PREFIX + ".verify_unaddressed_need",
            return_value=original,
        ) as verifier,
        patch(
            PREFIX + ".audit_unaddressed_need",
            return_value=audit,
        ) as auditor,
    ):
        result = evaluate_verified_need(
            need(),
            user_text=USER,
            response_text=RESPONSE,
            prior_context="Contexto anterior.",
            model="modelo-de-prueba",
            use_cache=False,
        )

    assert result["coverage"] == "addressed"
    assert result["score"] is None
    assert result["severity"] is None

    verifier.assert_called_once_with(
        need(),
        user_text=USER,
        response_text=RESPONSE,
        prior_context="Contexto anterior.",
        model="modelo-de-prueba",
        use_cache=False,
    )

    auditor.assert_called_once_with(
        need(),
        original,
        user_text=USER,
        response_text=RESPONSE,
        prior_context="Contexto anterior.",
        model="modelo-de-prueba",
        use_cache=False,
    )


def test_disagreement_blocks():
    original = {
        "verdict": "unaddressed",
        "reason": "No atiende la solicitud.",
    }
    audit = {
        "verdict": "rejected",
        "independent_assessment": "addressed",
        "reason": "Si ofrece orientacion.",
    }

    with (
        patch(
            PREFIX + ".verify_unaddressed_need",
            return_value=original,
        ),
        patch(
            PREFIX + ".audit_unaddressed_need",
            return_value=audit,
        ),
    ):
        with pytest.raises(ValueError):
            evaluate_verified_need(
                need(),
                user_text=USER,
                response_text=RESPONSE,
            )


def test_invalid_need_never_calls_openai():
    invalid = need()
    invalid["evidence"] = "cita inexistente"

    with patch(
        PREFIX + ".verify_unaddressed_need"
    ) as verifier:
        with pytest.raises(ValueError):
            evaluate_verified_need(
                invalid,
                user_text=USER,
                response_text=RESPONSE,
            )

    verifier.assert_not_called()


def test_empty_response_never_calls_openai():
    with patch(
        PREFIX + ".verify_unaddressed_need"
    ) as verifier:
        with pytest.raises(ValueError):
            evaluate_verified_need(
                need(),
                user_text=USER,
                response_text="",
            )

    verifier.assert_not_called()
