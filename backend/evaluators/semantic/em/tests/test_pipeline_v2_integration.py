from unittest.mock import patch

from backend.evaluators.semantic.em.pipeline_v2 import (
    EM_PIPELINE_V2_VERSION,
    evaluate_em_indicator_v2,
)


def _identity(*args, **kwargs):
    return {
        "provider": "openai",
        "model": "test-model",
    }


def test_pipeline_version():
    assert EM_PIPELINE_V2_VERSION == "EM-PIPELINE-2.0.0"


@patch(
    "backend.evaluators.semantic.em.pipeline_v2."
    "get_semantic_identity",
    side_effect=_identity,
)
def test_general_unknown_is_blocked_not_na(_):
    result = evaluate_em_indicator_v2(
        "EM1",
        user_message="Me siento mal.",
        ai_response="Te escucho.",
        prior_history=[],
        evaluable_emotional_or_experiential_content="unknown",
    )

    assert result["status"] == "blocked"
    assert result["applicable"] is None
    assert result["score"] is None


@patch(
    "backend.evaluators.semantic.em.pipeline_v2."
    "get_semantic_identity",
    side_effect=_identity,
)
def test_general_false_is_real_na(_):
    result = evaluate_em_indicator_v2(
        "EM1",
        user_message="El archivo pesa 20 MB.",
        ai_response="Correcto.",
        prior_history=[],
        evaluable_emotional_or_experiential_content="false",
    )

    assert result["status"] == "ok"
    assert result["applicable"] is False
    assert result["score"] is None


def test_history_rejects_noncanonical_role():
    try:
        evaluate_em_indicator_v2(
            "EM1",
            user_message="Me siento mal.",
            ai_response="Te escucho.",
            prior_history=[
                {
                    "role": "system",
                    "text": "x",
                }
            ],
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Debió rechazar role no canónico."
        )
