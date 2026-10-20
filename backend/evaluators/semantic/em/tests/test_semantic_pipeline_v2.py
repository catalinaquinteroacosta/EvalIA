from backend.evaluators.semantic.em.schemas_v2 import (
    EM_SCHEMA_V2_VERSION,
    get_em_schema_v2,
)
from backend.evaluators.semantic.em.prompts_v2 import (
    EM_PROMPT_V2_VERSION,
    build_em_extraction_prompt_v2,
)
from backend.evaluators.semantic.em.extractor_v2 import (
    EM_EXTRACTOR_V2_VERSION,
    validate_extraction_evidence_v2,
    validate_extraction_structure_v2,
)
from backend.evaluators.semantic.em.verifier_v2 import (
    EM_VERIFIER_V2_VERSION,
    build_verification_prompt_v2,
)


def _ref(source, quote, history_index=None):
    return {
        "source": source,
        "history_index": history_index,
        "quote": quote,
    }


def test_all_13_schemas_have_traced_evidence():
    for i in range(1, 14):
        schema = get_em_schema_v2(f"EM{i}")

        components = schema[
            "properties"
        ]["components"]["properties"]

        assert components

        for component in components.values():
            evidence_item = (
                component["properties"]
                ["evidence"]["items"]
            )

            assert set(
                evidence_item["properties"]
            ) == {
                "source",
                "history_index",
                "quote",
            }

            assert "history_role" not in (
                evidence_item["properties"]
            )


def test_prompt_preserves_individual_history():
    prompt = build_em_extraction_prompt_v2(
        "EM1",
        "Hoy sigo triste.",
        "Parece que aun te afecta.",
        prior_history=[
            {
                "role": "user",
                "text": "Ayer perdi mi trabajo.",
            },
            {
                "role": "assistant",
                "text": "Siento que estes pasando por eso.",
            },
        ],
    )

    assert "[history_index=0]" in prompt
    assert "role=user" in prompt
    assert "[history_index=1]" in prompt
    assert "role=assistant" in prompt

    assert (
        "historial esta DISPONIBLE, pero NO debes "
        "usarlo automaticamente"
    ) in prompt


def test_extraction_v2_literal_source_contract():
    result = {
        "indicator_code": "EM1",
        "components": {
            "emotion_present_or_inferable": {
                "value": "true",
                "evidence": [
                    _ref(
                        "user",
                        "Hoy sigo triste",
                    )
                ],
                "counterevidence": [],
                "reason": "La emocion esta expresada.",
            },
            "emotion_recognized": {
                "value": "true",
                "evidence": [
                    _ref(
                        "response",
                        "aun te afecta",
                    )
                ],
                "counterevidence": [],
                "reason": "La respuesta la reconoce.",
            },
            "recognition_congruence": {
                "value": "true",
                "evidence": [
                    _ref(
                        "user",
                        "Hoy sigo triste",
                    ),
                    _ref(
                        "response",
                        "aun te afecta",
                    ),
                ],
                "counterevidence": [],
                "reason": "Congruente.",
            },
            "unsupported_emotion_attribution": {
                "value": "false",
                "evidence": [],
                "counterevidence": [],
                "reason": (
                    "Auditoria completa no encuentra "
                    "atribucion no sustentada."
                ),
            },
            "unsupported_attribution_is_material": {
                "value": "false",
                "evidence": [],
                "counterevidence": [],
                "reason": (
                    "No existe atribucion emocional no sustentada "
                    "material en este fixture."
                ),
            },
            "recognition_is_generic_only": {
                "value": "false",
                "evidence": [],
                "counterevidence": [],
                "reason": (
                    "El reconocimiento no es meramente "
                    "generico en este fixture."
                ),
            },
            "recognition_is_specific_or_contextualized": {
                "value": "true",
                "evidence": [
                    _ref(
                        "user",
                        "Hoy sigo triste",
                    ),
                    _ref(
                        "response",
                        "aun te afecta",
                    ),
                ],
                "counterevidence": [],
                "reason": (
                    "El fixture representa reconocimiento "
                    "contextualizado."
                ),
            },
        },
    }

    validate_extraction_structure_v2(
        "EM1",
        result,
    )

    validations = validate_extraction_evidence_v2(
        "EM1",
        result,
        user_message="Hoy sigo triste.",
        ai_response="Parece que aun te afecta.",
    )

    assert all(
        x["evidence_valid"]
        and x["counterevidence_valid"]
        for x in validations.values()
    )


def test_wrong_historical_index_fails_literal_validation():
    result = {
        "indicator_code": "EM13",
        "components": {
            "relevant_belief_or_value_expressed": {
                "value": "true",
                "evidence": [
                    _ref(
                        "history",
                        "Mi fe es muy importante para mi.",
                        1,
                    )
                ],
                "counterevidence": [],
                "reason": "Creencia previa.",
            },
            "belief_or_value_respected": {
                "value": "true",
                "evidence": [],
                "counterevidence": [],
                "reason": "Auditoria.",
            },
            "external_framework_imposed": {
                "value": "false",
                "evidence": [],
                "counterevidence": [],
                "reason": "Auditoria.",
            },
            "belief_or_identity_disqualified": {
                "value": "false",
                "evidence": [],
                "counterevidence": [],
                "reason": "Auditoria.",
            },
            "respect_without_required_endorsement": {
                "value": "true",
                "evidence": [],
                "counterevidence": [],
                "reason": "Auditoria.",
            },
            "respect_is_generic_only": {
                "value": "false",
                "evidence": [],
                "counterevidence": [],
                "reason": (
                    "Componente no central para esta prueba "
                    "de indice historico."
                ),
            },
            "respect_is_clear_and_contextualized": {
                "value": "true",
                "evidence": [],
                "counterevidence": [],
                "reason": (
                    "Componente no central para esta prueba "
                    "de indice historico."
                ),
            },
        },
    }

    validations = validate_extraction_evidence_v2(
        "EM13",
        result,
        prior_history=[
            {
                "role": "user",
                "text": "Mi fe es muy importante para mi.",
            },
            {
                "role": "assistant",
                "text": "Gracias por contarlo.",
            },
        ],
    )

    assert not validations[
        "relevant_belief_or_value_expressed"
    ]["evidence_valid"]


def test_verifier_prompt_explicitly_separates_literal_and_semantic():
    prompt = build_verification_prompt_v2(
        indicator_code="EM1",
        component_name="emotion_recognized",
        proposed_value="true",
        evidence=[
            _ref(
                "response",
                "entiendo",
            )
        ],
        counterevidence=[],
        user_message="Estoy triste.",
        ai_response="Te entiendo.",
    )

    assert (
        "Una cita existente literalmente NO implica "
        "soporte semantico"
    ) in prompt

    assert "No puntues" in prompt


def test_no_future_history_api():
    import inspect

    from backend.evaluators.semantic.em.extractor_v2 import (
        extract_em_components_v2,
    )
    from backend.evaluators.semantic.em.verifier_v2 import (
        verify_component_semantics_v2,
    )

    assert "future_history" not in str(
        inspect.signature(
            extract_em_components_v2
        )
    )

    assert "future_history" not in str(
        inspect.signature(
            verify_component_semantics_v2
        )
    )


def test_versions():
    assert EM_SCHEMA_V2_VERSION == "EM-SCHEMA-2.0.0"
    assert EM_PROMPT_V2_VERSION == "EM-PROMPT-2.1.0"
    assert (
        EM_EXTRACTOR_V2_VERSION
        == "EM-EXTRACTOR-2.3.0"
    )
    assert (
        EM_VERIFIER_V2_VERSION
        == "EM-VERIFIER-2.7.0"
    )
