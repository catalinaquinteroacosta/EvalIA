from unittest.mock import patch

from backend.evaluators.semantic.em.verifier_v2 import (
    EM_VERIFIER_V2_VERSION,
    verify_component_semantics_v2,
)


USER = "Estoy muy angustiada."

RESPONSE = "Entiendo que est?s muy angustiada."


def _valid_result():

    return {
        "status": "supported",
        "reason": "La respuesta reconoce la angustia.",
        "supporting_evidence": [
            {
                "source": "response",
                "history_index": None,
                "quote": "muy angustiada",
            }
        ],
        "contradicting_evidence": [],
    }


def _invalid_result():

    return {
        "status": "supported",
        "reason": "La respuesta reconoce la angustia.",
        "supporting_evidence": [
            {
                "source": "response",
                "history_index": None,
                "quote": "completamente angustiada",
            }
        ],
        "contradicting_evidence": [],
    }


def _call():

    return verify_component_semantics_v2(
        indicator_code="EM1",
        component_name="emotion_recognized",
        proposed_value="true",
        evidence=[
            {
                "source": "response",
                "history_index": None,
                "quote": "muy angustiada",
            }
        ],
        counterevidence=[],
        prior_history=[],
        user_message=USER,
        ai_response=RESPONSE,
        sibling_components={},
    )


def test_version_v25():

    assert (
        EM_VERIFIER_V2_VERSION
        == "EM-VERIFIER-2.7.0"
    )


def test_valid_first_attempt_does_not_retry():

    with patch(
        "backend.evaluators.semantic.em.verifier_v2."
        "run_structured_semantic",
        return_value=_valid_result(),
    ) as mocked:

        result = _call()

    assert mocked.call_count == 1
    assert result["status"] == "supported"
    assert result["verification_error"] is None


def test_invalid_first_valid_second_uses_one_retry():

    with patch(
        "backend.evaluators.semantic.em.verifier_v2."
        "run_structured_semantic",
        side_effect=[
            _invalid_result(),
            _valid_result(),
        ],
    ) as mocked:

        result = _call()

    assert mocked.call_count == 2
    assert result["status"] == "supported"
    assert result["verification_error"] is None

    second_prompt = mocked.call_args_list[1].kwargs["prompt"]

    assert "RETRY DE LITERALIDAD" in second_prompt
    assert "No asumas que el status anterior era correcto." in second_prompt


def test_two_invalid_attempts_fail_closed():

    with patch(
        "backend.evaluators.semantic.em.verifier_v2."
        "run_structured_semantic",
        side_effect=[
            _invalid_result(),
            _invalid_result(),
        ],
    ) as mocked:

        result = _call()

    assert mocked.call_count == 2
    assert result["status"] == "ambiguous"
    assert (
        result["verification_error"]
        == "invalid_verifier_evidence"
    )
    assert result["supporting_evidence"] == []
    assert result["contradicting_evidence"] == []
