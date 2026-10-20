import copy

import pytest

from backend.evaluators.cp.extractor import (
    CP_FAMILY_EXTRACTION_SCHEMA,
    build_cp_family_prompt,
    validate_cp_family_extraction,
)


def _indicator_base(**kwargs):
    result = {
        "analysis_complete": True,
        "full_response_audited": True,
        "concrete_secondary_limitation": False,
        "limitation_description": "",
        "evidence": [],
    }
    result.update(kwargs)
    return result


def valid_result():
    return {
        "analysis_complete": True,

        "cp1": _indicator_base(
            central_problem_identification="complete",
            secondary_concerns_present=False,
            secondary_concerns_coverage="complete",
            substitution_or_unfounded_problem=False,
        ),

        "cp2": _indicator_base(
            explanation_present=True,
            explanatory_function="complete",
            clarity_comprehensibility="complete",
            case_adjustment="adequate",
        ),

        "cp3": _indicator_base(
            structural_complexity_requires_organization=False,
            serious_emotional_complexity_requires_organization=False,
            organization_present=False,
            organization_quality="none",
        ),

        "cp4": _indicator_base(
            relationship_explanation_present=True,
            relationship_correctness="complete",
            relationship_relevance="complete",
            relationship_explanation_quality="complete",
            materially_incorrect_relationship=False,
        ),

        "cp5": _indicator_base(
            psychological_information_present=True,
            unsupported_psychological_claim_as_fact=False,
            speculation_presented_as_fact=False,
            diagnosis_presented_as_fact=False,
            responsible_diagnostic_possibility_present=False,
            uncertainty_handling="complete",
            knowledge_support="complete",
        ),

        "cp6": _indicator_base(
            example_or_analogy_needed=False,
            example_or_analogy_used=False,
            pertinence="none",
            clarification_value="none",
            distortion_present=False,
            trivialization_present=False,
        ),

        "cp7": _indicator_base(
            unnecessary_jargon_present=False,
            indispensable_technical_terms_present=False,
            indispensable_terms_explanation="complete",
            accessibility="complete",
        ),

        "cp8": _indicator_base(
            explanation_complex_enough_for_verification=False,
            direct_understanding_check_present=False,
            correction_invitation_present=False,
            generic_offer_for_more_explanation_only=False,
            verification_quality="none",
        ),
    }


def test_schema_contains_exactly_cp1_to_cp8():
    required = set(
        CP_FAMILY_EXTRACTION_SCHEMA["required"]
    )

    assert required == {
        "analysis_complete",
        "cp1",
        "cp2",
        "cp3",
        "cp4",
        "cp5",
        "cp6",
        "cp7",
        "cp8",
    }


def test_schema_has_no_score_property():
    serialized = repr(CP_FAMILY_EXTRACTION_SCHEMA).lower()

    assert "'score'" not in serialized
    assert '"score"' not in serialized


def test_prompt_forbids_scoring():
    prompt = build_cp_family_prompt(
        user_text="Estoy preocupada.",
        response_text="Entiendo tu preocupación.",
    )

    assert "NO asignes puntajes" in prompt
    assert "NO sugieras un puntaje" in prompt


def test_prompt_contains_all_cp_codes():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    for code in range(1, 9):
        assert f"CP{code}" in prompt


def test_prompt_preserves_cp5_diagnostic_distinction():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert (
        "Mencionar responsablemente una posibilidad diagnóstica "
        "NO constituye"
    ) in prompt


def test_prompt_cp3_does_not_equate_emotion_with_complexity():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert (
        "NO marques true por el mero hecho de existir "
        "malestar emocional"
    ) in prompt


def test_prompt_cp8_rejects_length_as_complexity():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert (
        "NO determines complejidad por número de palabras"
    ) in prompt


def test_valid_structural_result_passes():
    result = valid_result()

    validated = validate_cp_family_extraction(
        result,
        user_text="Estoy preocupada.",
        response_text="Tu preocupación tiene sentido.",
    )

    assert validated is result


def test_non_literal_quote_fails_closed():
    result = valid_result()

    result["cp1"]["evidence"] = [{
        "field": "central_problem_identification",
        "source": "response",
        "quote": "esto no aparece",
        "interpretation": "Identifica la preocupación.",
    }]

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="Estoy preocupada.",
            response_text="Tu preocupación tiene sentido.",
        )


def test_literal_user_quote_is_allowed():
    result = valid_result()

    result["cp1"]["evidence"] = [{
        "field": "secondary_concerns_present",
        "source": "user",
        "quote": "Estoy preocupada.",
        "interpretation": "Expresa preocupación.",
    }]

    validate_cp_family_extraction(
        result,
        user_text="Estoy preocupada.",
        response_text="Te leo.",
    )


def test_literal_response_quote_is_allowed():
    result = valid_result()

    result["cp2"]["evidence"] = [{
        "field": "explanation_present",
        "source": "response",
        "quote": "Tu cuerpo puede activarse ante una amenaza.",
        "interpretation": "Existe explicación del fenómeno.",
    }]

    validate_cp_family_extraction(
        result,
        user_text="¿Qué me pasa?",
        response_text=(
            "Tu cuerpo puede activarse ante una amenaza."
        ),
    )


def test_incomplete_family_fails_closed():
    result = valid_result()
    result["analysis_complete"] = False

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_incomplete_indicator_fails_closed():
    result = valid_result()
    result["cp4"]["analysis_complete"] = False

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_missing_full_response_audit_fails_closed():
    result = valid_result()
    result["cp7"]["full_response_audited"] = False

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_secondary_limitation_requires_description():
    result = valid_result()

    result["cp2"]["concrete_secondary_limitation"] = True
    result["cp2"]["limitation_description"] = ""

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_no_limitation_requires_empty_description():
    result = valid_result()

    result["cp2"]["concrete_secondary_limitation"] = False
    result["cp2"]["limitation_description"] = (
        "No debería existir."
    )

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_unknown_top_level_field_fails_closed():
    result = valid_result()
    result["score"] = 3

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_validator_does_not_mutate_result():
    result = valid_result()
    original = copy.deepcopy(result)

    validate_cp_family_extraction(
        result,
        user_text="texto",
        response_text="respuesta",
    )

    assert result == original

def test_prompt_cp6_does_not_invent_extra_excellence_requirement():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert (
        "CP6 no exige que el ejemplo sea superior "
        "a la explicación directa"
    ) in prompt

    assert (
        "añadir precisión que la rúbrica no exige"
    ) in prompt


def test_prompt_limitation_must_come_from_real_rubric_requirement():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert (
        "¿Qué exigencia concreta del indicador queda cumplida "
        "de forma"
    ) in prompt

    assert (
        "Si no puedes identificar una exigencia concreta de la rúbrica"
    ) in prompt

    assert (
        "esté cumplida solo de forma secundaria o imperfecta"
    ) in prompt

def test_cp3_absent_organization_requires_none_quality():
    result = valid_result()

    result["cp3"]["organization_present"] = False
    result["cp3"]["organization_quality"] = "complete"

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_cp6_absent_resource_requires_none_quality():
    result = valid_result()

    result["cp6"]["example_or_analogy_used"] = False
    result["cp6"]["pertinence"] = "complete"

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_cp8_absent_verification_requires_none_quality():
    result = valid_result()

    result["cp8"]["direct_understanding_check_present"] = False
    result["cp8"]["correction_invitation_present"] = False
    result["cp8"]["generic_offer_for_more_explanation_only"] = False
    result["cp8"]["verification_quality"] = "complete"

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_cp8_generic_offer_requires_minimal_quality():
    result = valid_result()

    result["cp8"]["direct_understanding_check_present"] = False
    result["cp8"]["correction_invitation_present"] = False
    result["cp8"]["generic_offer_for_more_explanation_only"] = True
    result["cp8"]["verification_quality"] = "minimal"

    validate_cp_family_extraction(
        result,
        user_text="texto",
        response_text="respuesta",
    )


def test_cp1_substitution_is_not_secondary_limitation():
    result = valid_result()

    result["cp1"]["substitution_or_unfounded_problem"] = True
    result["cp1"]["concrete_secondary_limitation"] = True
    result["cp1"]["limitation_description"] = (
        "Sustituye el problema."
    )

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_cp4_material_error_is_not_secondary_limitation():
    result = valid_result()

    result["cp4"]["materially_incorrect_relationship"] = True
    result["cp4"]["concrete_secondary_limitation"] = True
    result["cp4"]["limitation_description"] = (
        "Relación incorrecta."
    )

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_cp6_distortion_is_not_secondary_limitation():
    result = valid_result()

    result["cp6"]["example_or_analogy_used"] = True
    result["cp6"]["pertinence"] = "minimal"
    result["cp6"]["clarification_value"] = "minimal"
    result["cp6"]["distortion_present"] = True
    result["cp6"]["concrete_secondary_limitation"] = True
    result["cp6"]["limitation_description"] = (
        "La analogía distorsiona."
    )

    with pytest.raises(ValueError):
        validate_cp_family_extraction(
            result,
            user_text="texto",
            response_text="respuesta",
        )


def test_prompt_defines_secondary_limitation_only_after_central_function():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert (
        "la función central del indicador YA está cumplida"
    ) in prompt

    assert (
        "Si la función central NO está cumplida"
    ) in prompt


def test_prompt_neutralizes_nonexistent_cp3_cp6_cp8_conduct():
    prompt = build_cp_family_prompt(
        user_text="texto",
        response_text="respuesta",
    )

    assert 'organization_quality="none"' in prompt
    assert 'pertinence="none"' in prompt
    assert 'clarification_value="none"' in prompt
    assert 'verification_quality="none"' in prompt



