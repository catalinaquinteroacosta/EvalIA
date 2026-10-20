from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a.ce1_implicit_adapter import (
    CE1ImplicitReviewRequired,
    evaluate_implicit_need,
)

PREFIX = "backend.evaluators.ce.ce_a.ce1_implicit_adapter"

USER = "Me preocupa la entrevista."
RESPONSE = "Practica respuestas antes de asistir."


def item():
    return {
        "interpretation": "Prepararse para la entrevista.",
        "source": "implicit",
        "evidence": "Me preocupa la entrevista",
        "justification": "La preocupacion permite inferir "
                         "una necesidad de orientacion.",
    }


def call(data=None, prior_context=""):
    return evaluate_implicit_need(
        item() if data is None else data,
        user_text=USER,
        response_text=RESPONSE,
        prior_context=prior_context,
        use_cache=False,
    )


def test_supported_need_reaches_coordinator():
    with (
        patch(
            PREFIX + ".verify_need",
            return_value={
                "verdict": "supported",
                "reason": "Inferencia contextual respaldada.",
            },
        ) as legitimacy,
        patch(
            PREFIX + ".evaluate_verified_need",
            return_value={
                "coverage": "addressed",
                "severity": None,
                "score": None,
            },
        ) as coordinator,
    ):
        result = call()

    legitimacy.assert_called_once()
    coordinator.assert_called_once()
    sent = coordinator.call_args.args[0]

    assert sent["source"] == "current_user"
    assert sent["evidence"] == item()["evidence"]
    assert result["original_source"] == "implicit"
    assert result["primary_need_confirmed"] is False
    assert result["score"] is None


@pytest.mark.parametrize(
    "verdict",
    ["not_supported", "ambiguous"],
)
def test_unsupported_or_ambiguous_blocks(verdict):
    with (
        patch(
            PREFIX + ".verify_need",
            return_value={
                "verdict": verdict,
                "reason": "No autorizado.",
            },
        ),
        patch(
            PREFIX + ".evaluate_verified_need",
        ) as coordinator,
    ):
        with pytest.raises(CE1ImplicitReviewRequired):
            call()

    coordinator.assert_not_called()


def test_invalid_literal_never_calls_openai():
    invalid = item()
    invalid["evidence"] = "cita inventada"

    with patch(PREFIX + ".verify_need") as verifier:
        with pytest.raises(ValueError):
            call(invalid)

    verifier.assert_not_called()


def test_dual_source_requires_review():
    with (
        patch(
            PREFIX + ".verify_need",
            return_value={
                "verdict": "supported",
                "reason": "Respaldada.",
            },
        ),
        patch(
            PREFIX + ".evaluate_verified_need",
        ) as coordinator,
    ):
        with pytest.raises(CE1ImplicitReviewRequired):
            call(prior_context=USER)

    coordinator.assert_not_called()


def test_prior_context_provenance():
    contextual = item()
    contextual["evidence"] = "Entrevista pendiente"

    with (
        patch(
            PREFIX + ".verify_need",
            return_value={
                "verdict": "supported",
                "reason": "Respaldada.",
            },
        ),
        patch(
            PREFIX + ".evaluate_verified_need",
            return_value={
                "coverage": "partially_addressed",
                "severity": None,
                "score": None,
            },
        ) as coordinator,
    ):
        result = call(
            contextual,
            prior_context="Entrevista pendiente",
        )

    assert coordinator.call_args.args[0]["source"] == (
        "prior_context"
    )
    assert result["original_source"] == "implicit"


def test_invalid_legitimacy_result_blocks():
    with (
        patch(
            PREFIX + ".verify_need",
            return_value={
                "verdict": "supported",
                "reason": "",
            },
        ),
        patch(
            PREFIX + ".evaluate_verified_need",
        ) as coordinator,
    ):
        with pytest.raises(ValueError):
            call()

    coordinator.assert_not_called()
