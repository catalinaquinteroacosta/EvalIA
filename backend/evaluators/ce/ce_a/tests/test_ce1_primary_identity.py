from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a import (
    ce1_primary_identity as mod,
)


USER = "Necesito prepararme para mi entrevista."


def test_valid_paraphrase_confirmation():
    result = {
        "verdict": "confirmed",
        "source": "current_user",
        "evidence": "prepararme para mi entrevista",
        "reason": "Las expresiones son equivalentes.",
    }
    assert mod.validate_result(
        result,
        user_text=USER,
        prior_context="",
    ) == result


@pytest.mark.parametrize("evidence", [
    "",
    "cita inventada",
])
def test_false_evidence_blocked(evidence):
    with pytest.raises(ValueError):
        mod.validate_result(
            {
                "verdict": "confirmed",
                "source": "current_user",
                "evidence": evidence,
                "reason": "Supuestamente respaldado.",
            },
            user_text=USER,
            prior_context="",
        )


def test_prior_context_provenance():
    result = {
        "verdict": "confirmed",
        "source": "prior_context",
        "evidence": "entrevista laboral",
        "reason": "El contexto confirma la solicitud.",
    }
    assert mod.validate_result(
        result,
        user_text=USER,
        prior_context="Ma?ana tengo una entrevista laboral.",
    ) == result


def test_ambiguous_cannot_confirm():
    with pytest.raises(ValueError):
        mod.validate_result(
            {
                "verdict": "ambiguous",
                "source": "current_user",
                "evidence": "prepararme",
                "reason": "No concluyente.",
            },
            user_text=USER,
            prior_context="",
        )


def test_invalid_candidate_blocks_api():
    with patch.object(
        mod, "get_semantic_identity"
    ) as identity:
        with pytest.raises(ValueError):
            mod.verify_primary_identity(
                primary_need="Preparar entrevista",
                candidate_need="Comprar un coche",
                candidate_source="current_user",
                candidate_evidence="comprar coche",
                user_text=USER,
                use_cache=False,
            )
    identity.assert_not_called()


def test_openai_verifies_without_scoring():
    with (
        patch.object(
            mod,
            "get_semantic_identity",
            return_value={"model": "test-model"},
        ),
        patch.object(
            mod,
            "run_structured_semantic",
            return_value={
                "verdict": "confirmed",
                "source": "current_user",
                "evidence": "prepararme para mi entrevista",
                "reason": "Equivalencia confirmada.",
            },
        ) as semantic,
    ):
        result = mod.verify_primary_identity(
            primary_need="Preparar entrevista",
            candidate_need="Alistarse para entrevista",
            candidate_source="current_user",
            candidate_evidence="prepararme para mi entrevista",
            user_text=USER,
            use_cache=False,
        )

    assert result["verdict"] == "confirmed"
    assert "score" not in result
    semantic.assert_called_once()
