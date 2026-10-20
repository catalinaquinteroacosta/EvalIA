import pytest

from backend.evaluators.semantic.em.verifier import (
    CONTROLLED_INFERENCE_RULES,
    VERIFIER_SCHEMA,
    build_verification_prompt,
)
from backend.evaluators.semantic.em.specs import EM_SPECS


def test_all_13_indicators_have_controlled_inference_rule():
    expected = {"EM" + str(i) for i in range(1, 14)}

    assert set(CONTROLLED_INFERENCE_RULES) == expected
    assert set(EM_SPECS) == expected


@pytest.mark.parametrize(
    "code,component",
    [
        ("EM1", "emotion_present_or_inferable"),
        ("EM2", "emotion_situation_relation"),
        ("EM3", "external_perspective_imposed"),
        ("EM4", "understanding_communicated"),
        ("EM5", "own_experience_reference"),
        ("EM6", "emotion_presented_as_understandable"),
        ("EM7", "tone_congruence"),
        ("EM8", "need_explicit_or_inferable"),
        ("EM9", "important_information_missing"),
        ("EM10", "proportionality"),
        ("EM11", "response_particularized"),
        ("EM12", "observable_user_language_level"),
        ("EM13", "relevant_belief_or_value_expressed"),
    ],
)
def test_each_indicator_builds_isolated_verifier_prompt(
    code,
    component,
):
    prompt = build_verification_prompt(
        indicator_code=code,
        component_name=component,
        proposed_value="true",
        evidence=["Texto literal"],
        counterevidence=[],
        user_message="Texto literal",
        ai_response="Respuesta.",
    )

    assert code in prompt
    assert component in prompt
    assert "VERIFICACION SEMANTICA INDEPENDIENTE" in prompt
    assert "No asignes puntuaciones 0, 1, 2, 3 ni N/A" in prompt


def test_em1_explicitly_allows_reasonable_inference():
    prompt = build_verification_prompt(
        indicator_code="EM1",
        component_name="emotion_present_or_inferable",
        proposed_value="true",
        evidence=["Desde que murio mi perro no quiero salir de la cama."],
        counterevidence=[],
        user_message="Desde que murio mi perro no quiero salir de la cama.",
        ai_response="Te leo.",
    )

    assert "razonablemente inferible" in prompt
    assert "No inventes una emocion especifica" in prompt


def test_em8_allows_supported_need_inference():
    prompt = build_verification_prompt(
        indicator_code="EM8",
        component_name="need_explicit_or_inferable",
        proposed_value="true",
        evidence=["No se que hacer ahora."],
        counterevidence=[],
        user_message="No se que hacer ahora.",
        ai_response="Entiendo.",
    )

    assert "razonablemente inferible" in prompt
    assert "no puede fabricar una necesidad" in prompt


def test_em12_blocks_unobservable_capacity_inference():
    prompt = build_verification_prompt(
        indicator_code="EM12",
        component_name="observable_user_language_level",
        proposed_value="true",
        evidence=["Explicamelo de forma sencilla."],
        counterevidence=[],
        user_message="Explicamelo de forma sencilla.",
        ai_response="Claro.",
    )

    assert "No infieras inteligencia" in prompt
    assert "educacion" in prompt
    assert "capacidad cognitiva" in prompt


def test_em13_does_not_require_endorsement():
    prompt = build_verification_prompt(
        indicator_code="EM13",
        component_name="respect_without_required_endorsement",
        proposed_value="true",
        evidence=["Para mi la oracion es muy importante."],
        counterevidence=[],
        user_message="Para mi la oracion es muy importante.",
        ai_response="Podemos respetar ese valor.",
    )

    assert "no exige afirmar una creencia como verdad" in prompt


def test_invalid_component_is_rejected():
    with pytest.raises(ValueError):
        build_verification_prompt(
            indicator_code="EM1",
            component_name="componente_inventado",
            proposed_value="true",
            evidence=[],
            counterevidence=[],
            user_message="x",
            ai_response="y",
        )


def test_invalid_semantic_value_is_rejected():
    with pytest.raises(ValueError):
        build_verification_prompt(
            indicator_code="EM1",
            component_name="emotion_recognized",
            proposed_value="3",
            evidence=[],
            counterevidence=[],
            user_message="x",
            ai_response="y",
        )


def test_verifier_schema_has_only_three_states():
    assert set(
        VERIFIER_SCHEMA["properties"]["status"]["enum"]
    ) == {
        "supported",
        "not_supported",
        "ambiguous",
    }


def test_verifier_defines_false_as_absence_not_failure():
    prompt = build_verification_prompt(
        indicator_code="EM5",
        component_name="experience_appropriation",
        proposed_value="false",
        evidence=[],
        counterevidence=[],
        user_message="Me siento sola.",
        ai_response="Entiendo que esto esta siendo dificil para ti.",
    )

    assert "proposed_value=false" in prompt
    assert "ESTA AUSENTE" in prompt
    assert (
        'entonces false esta sustentado'
        in prompt
    )


def test_verifier_unknown_requires_real_unresolved_state():
    prompt = build_verification_prompt(
        indicator_code="EM3",
        component_name="perspective_timing",
        proposed_value="unknown",
        evidence=[],
        counterevidence=[],
        user_message="Quiero intentarlo.",
        ai_response="Entiendo. Podemos explorar opciones.",
    )

    assert "proposed_value=unknown" in prompt
    assert "proposed_value=unknown" in prompt
    assert "devuelve OBLIGATORIAMENTE" in prompt
    assert "REGLA DE CONSISTENCIA" in prompt
    assert (
        "Solo devuelve \"supported\" para proposed_value=unknown"
        in prompt
    )
    assert (
        "true Y false siguen siendo interpretaciones"
        in prompt
    )


def test_verifier_quotes_must_be_raw_exact_substrings():
    prompt = build_verification_prompt(
        indicator_code="EM9",
        component_name="clarification_sought",
        proposed_value="true",
        evidence=["que esta ocurriendo"],
        counterevidence=[],
        user_message="No se que hacer.",
        ai_response="que esta ocurriendo",
    )

    assert "substrings literales exactos" in prompt
    assert "NO agregues comillas" in prompt
    assert "signos de interrogacion" in prompt
    assert (
        "la cita debe ser literal"
        in prompt
    )


def test_verifier_preserves_semantic_paraphrase():
    prompt = build_verification_prompt(
        indicator_code="EM1",
        component_name="emotion_recognized",
        proposed_value="true",
        evidence=["todo se me hace pesado"],
        counterevidence=[],
        user_message="todo se me hace pesado",
        ai_response="Parece que estas muy triste.",
    )

    assert (
        "Puedes interpretar semanticamente y puedes reconocer una parafrasis"
        in prompt
    )


def test_em3_perspective_timing_conditional_inactive():
    from backend.evaluators.semantic.em.verifier import (
        build_verification_prompt,
    )

    prompt = build_verification_prompt(
        indicator_code="EM3",
        component_name="perspective_timing",
        proposed_value="unknown",
        evidence=[],
        counterevidence=[],
        previous_context="",
        user_message="No quiero terminar la relacion.",
        ai_response=(
            "Entiendo que para ti la relacion todavia tiene posibilidades."
        ),
        sibling_components={
            "external_perspective_present": "false",
        },
    )

    assert "external_perspective_present: false" in prompt
    assert "componente condicionado no activado" in prompt
    assert "NO lo reinterpretas como true ni como false" in prompt


def test_em3_perspective_timing_active_when_external_present():
    from backend.evaluators.semantic.em.verifier import (
        build_verification_prompt,
    )

    prompt = build_verification_prompt(
        indicator_code="EM3",
        component_name="perspective_timing",
        proposed_value="true",
        evidence=[],
        counterevidence=[],
        previous_context="",
        user_message="Creo que la relacion puede mejorar.",
        ai_response=(
            "Entiendo que para ti puede mejorar. "
            "Tambien podria ser util considerar otra posibilidad."
        ),
        sibling_components={
            "external_perspective_present": "true",
        },
    )

    assert "external_perspective_present: true" in prompt
    assert "verifica normalmente" in prompt


def test_other_components_do_not_get_em3_conditional_rule():
    from backend.evaluators.semantic.em.verifier import (
        build_verification_prompt,
    )

    prompt = build_verification_prompt(
        indicator_code="EM2",
        component_name="emotion_situation_relation",
        proposed_value="true",
        evidence=[],
        counterevidence=[],
        previous_context="",
        user_message="Estoy triste desde que murio mi perro.",
        ai_response="Tiene sentido que estes triste por su muerte.",
        sibling_components={
            "external_perspective_present": "false",
        },
    )

    assert "REGLA CONDICIONAL ESPECIFICA EM3.perspective_timing" not in prompt
