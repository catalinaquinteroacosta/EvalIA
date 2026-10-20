import pytest

from backend.evaluators.semantic.em.extractor import (
    extraction_has_literal_evidence_errors,
    validate_extraction_evidence,
    validate_extraction_structure,
)
from backend.evaluators.semantic.em.schemas import (
    COMPONENT_DESCRIPTIONS,
)


def make_valid_result(code):
    components = {}

    for name in COMPONENT_DESCRIPTIONS[code]:
        components[name] = {
            "value": "unknown",
            "evidence": [],
            "counterevidence": [],
            "reason": "No concluyente.",
        }

    return {
        "indicator_code": code,
        "components": components,
    }


@pytest.mark.parametrize(
    "code",
    ["EM" + str(i) for i in range(1, 14)],
)
def test_valid_structure_for_all_indicators(code):
    result = make_valid_result(code)

    validate_extraction_structure(
        code,
        result,
    )


def test_rejects_wrong_indicator_code():
    result = make_valid_result("EM1")
    result["indicator_code"] = "EM2"

    with pytest.raises(ValueError):
        validate_extraction_structure(
            "EM1",
            result,
        )


def test_rejects_missing_component():
    result = make_valid_result("EM1")
    result["components"].pop(
        "emotion_recognized"
    )

    with pytest.raises(ValueError):
        validate_extraction_structure(
            "EM1",
            result,
        )


def test_rejects_extra_component():
    result = make_valid_result("EM1")

    result["components"]["invented_component"] = {
        "value": "true",
        "evidence": [],
        "counterevidence": [],
        "reason": "Inventado.",
    }

    with pytest.raises(ValueError):
        validate_extraction_structure(
            "EM1",
            result,
        )


def test_rejects_numeric_score_as_value():
    result = make_valid_result("EM1")

    result["components"][
        "emotion_recognized"
    ]["value"] = "3"

    with pytest.raises(ValueError):
        validate_extraction_structure(
            "EM1",
            result,
        )


def test_literal_evidence_valid_when_quote_exists():
    result = make_valid_result("EM1")

    result["components"][
        "emotion_recognized"
    ] = {
        "value": "true",
        "evidence": [
            "entiendo que te sientes agotada"
        ],
        "counterevidence": [],
        "reason": "Reconoce agotamiento.",
    }

    validations = validate_extraction_evidence(
        "EM1",
        result,
        user_message="Estoy agotada.",
        ai_response=(
            "entiendo que te sientes agotada"
        ),
    )

    assert (
        validations[
            "emotion_recognized"
        ]["evidence_valid"]
        is True
    )

    assert (
        extraction_has_literal_evidence_errors(
            validations
        )
        is False
    )


def test_literal_evidence_error_when_quote_is_invented():
    result = make_valid_result("EM1")

    result["components"][
        "emotion_recognized"
    ] = {
        "value": "true",
        "evidence": [
            "entiendo perfectamente tu tristeza"
        ],
        "counterevidence": [],
        "reason": "Prueba.",
    }

    validations = validate_extraction_evidence(
        "EM1",
        result,
        user_message="Estoy agotada.",
        ai_response="Te escucho.",
    )

    assert (
        validations[
            "emotion_recognized"
        ]["evidence_valid"]
        is False
    )

    assert (
        extraction_has_literal_evidence_errors(
            validations
        )
        is True
    )


def test_extractor_validation_does_not_score():
    result = make_valid_result("EM2")

    validate_extraction_structure(
        "EM2",
        result,
    )

    assert "score" not in result
    assert "applicable" not in result


def test_all_em_prompts_require_raw_exact_substrings():
    from backend.evaluators.semantic.em.prompts import (
        build_em_extraction_prompt,
    )

    for i in range(1, 14):
        code = "EM" + str(i)

        prompt = build_em_extraction_prompt(
            indicator_code=code,
            user_message="Estoy agotada.",
            ai_response="Entiendo que estas agotada.",
            previous_context="",
        )

        assert "substring literal exacto" in prompt
        assert "NO agregues comillas" in prompt
        assert "NO devuelvas:" in prompt
        assert "normalices ni parafrasees" in prompt
