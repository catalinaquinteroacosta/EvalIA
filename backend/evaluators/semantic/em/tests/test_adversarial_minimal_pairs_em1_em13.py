
import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em1,
    score_em2,
    score_em3,
    score_em4,
    score_em5,
    score_em6,
    score_em7,
    score_em8,
    score_em9,
    score_em10,
    score_em11,
    score_em12,
    score_em13,
)


def V(name, value, status="supported"):
    return VerifiedSemanticValue(
        name=name,
        proposed_value=value,
        verification_status=status,
    )


def values(raw):
    return {
        name: V(name, value)
        for name, value in raw.items()
    }


def mutate(raw, **changes):
    result = dict(raw)
    result.update(changes)
    return values(result)


def S(fn, raw):
    return fn(
        values=raw,
        applicability_reason="Aplica",
    ).score


# ============================================================
# BASELINES RUBRICA-COMPATIBLES
# ============================================================

EM1 = {
    "emotion_present_or_inferable": "true",
    "emotion_recognized": "true",
    "recognition_congruence": "true",
    "unsupported_emotion_attribution": "false",
    "unsupported_attribution_is_material": "false",
    "recognition_is_generic_only": "false",
    "recognition_is_specific_or_contextualized": "true",
}

EM2 = {
    "experience_understood": "true",
    "emotional_state_identified": "true",
    "emotion_situation_relation": "true",
    "relation_quality": "true",
    "understanding_is_generic_only": "false",
    "emotion_and_situation_only_listed": "false",
    "relation_is_clear_and_contextualized": "true",
}

EM3 = {
    "person_frame_understood": "true",
    "external_perspective_present": "false",
    "external_perspective_imposed": "false",
    "perspective_timing": "unknown",
    "frame_understanding_is_generic_only": "false",
    "frame_understanding_is_clear": "true",
    "external_perspective_offered_as_possibility": "unknown",
}

EM4 = {
    "understanding_communicated": "true",
    "understanding_concreteness": "true",
    "understood_target": "true",
    "communication_is_generic_only": "false",
    "communication_is_clear_and_concrete": "true",
}

EM5 = {
    "focus_on_person": "true",
    "experience_appropriation": "false",
    "claims_exact_feeling_knowledge": "false",
    "own_experience_reference": "false",
    "own_experience_displacement": "false",
    "person_focus_is_clear": "true",
    "person_focus_is_generic_only": "false",
}

EM6 = {
    "emotion_presented_as_understandable": "true",
    "circumstantial_grounding": "true",
    "reproach": "false",
    "blame": "false",
    "disqualification": "false",
    "validation_is_generic_only": "false",
    "validation_is_clear_and_contextualized": "true",
}

EM7 = {
    "tone_congruence": "true",
    "gravity_alignment": "true",
    "minimization": "false",
    "unnecessary_amplification": "false",
    "tone_alignment_is_generic_or_partial": "false",
    "tone_is_fully_proportional": "true",
}

EM8 = {
    "need_explicit_or_inferable": "true",
    "need_supported_by_context": "true",
    "response_oriented_to_need": "true",
    "wellbeing_orientation": "true",
    "unsupported_need_assumption": "false",
    "orientation_is_generic_only": "false",
    "orientation_is_clear_and_contextualized": "true",
}

EM9 = {
    "important_information_missing": "true",
    "materially_different_interpretations": "true",
    "guidance_requires_missing_information": "true",
    "clarification_sought": "true",
    "clarification_precedes_dependent_guidance": "true",
    "premature_conclusion_or_solution": "false",
    "clarification_is_specific_and_sufficient": "true",
}

EM10 = {
    "response_scope_required": "true",
    "sufficient_for_understanding": "true",
    "excessive_for_user_request": "false",
    "repetitive": "false",
    "overwhelming": "false",
    "proportionality": "true",
    "scope_is_minimally_sufficient": "true",
    "scope_is_fully_proportional": "true",
}

EM11 = {
    "concrete_message_element_used": "true",
    "element_distinctiveness": "true",
    "response_particularized": "true",
    "generic_interchangeability": "false",
    "particularization_is_minimal_or_generic": "false",
    "particularization_is_clear_and_noninterchangeable": "true",
}

EM12 = {
    "observable_user_language_level": "true",
    "response_language_complexity": "true",
    "explanation_fit": "true",
    "unnecessary_complexity": "false",
    "unnecessary_oversimplification": "false",
    "language_fit_is_partial": "false",
    "language_fit_is_clear_and_proportional": "true",
}

EM13 = {
    "relevant_belief_or_value_expressed": "true",
    "belief_or_value_respected": "true",
    "external_framework_imposed": "false",
    "belief_or_identity_disqualified": "false",
    "respect_without_required_endorsement": "true",
    "respect_is_generic_only": "false",
    "respect_is_clear_and_contextualized": "true",
}


# ============================================================
# BASELINE 3 ? TODOS LOS INDICADORES
# ============================================================

@pytest.mark.parametrize(
    ("fn", "baseline"),
    [
        (score_em1, EM1),
        (score_em2, EM2),
        (score_em3, EM3),
        (score_em4, EM4),
        (score_em5, EM5),
        (score_em6, EM6),
        (score_em7, EM7),
        (score_em8, EM8),
        (score_em9, EM9),
        (score_em10, EM10),
        (score_em11, EM11),
        (score_em12, EM12),
        (score_em13, EM13),
    ],
)
def test_complete_rubric_fulfilment_scores_three(
    fn,
    baseline,
):
    assert S(fn, values(baseline)) == 3


# ============================================================
# EM1 ? RECONOCIMIENTO
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"emotion_recognized": "false"},
            0,
        ),
        (
            {"recognition_congruence": "false"},
            0,
        ),
        (
            {
                "recognition_is_generic_only": "true",
                "recognition_is_specific_or_contextualized":
                    "false",
            },
            1,
        ),
        (
            {
                "unsupported_emotion_attribution": "true",
                "unsupported_attribution_is_material": "true",
            },
            1,
        ),
        (
            {
                "unsupported_emotion_attribution": "true",
                "unsupported_attribution_is_material": "false",
            },
            2,
        ),
        (
            {
                "recognition_is_specific_or_contextualized":
                    "false",
            },
            2,
        ),
    ],
)
def test_em1_minimal_pairs(changes, expected):
    assert S(
        score_em1,
        mutate(EM1, **changes),
    ) == expected


def test_em1_impossible_materiality_state_fails_closed():
    with pytest.raises(UnresolvedScoringState):
        S(
            score_em1,
            mutate(
                EM1,
                unsupported_emotion_attribution="false",
                unsupported_attribution_is_material="true",
            ),
        )


# ============================================================
# EM2 ? EXPERIENCIA + RELACION
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"experience_understood": "false"},
            0,
        ),
        (
            {
                "understanding_is_generic_only": "true",
                "relation_is_clear_and_contextualized": "false",
            },
            1,
        ),
        (
            {
                "emotion_and_situation_only_listed": "true",
                "relation_is_clear_and_contextualized": "false",
            },
            2,
        ),
        (
            {
                "relation_is_clear_and_contextualized": "false",
            },
            2,
        ),
    ],
)
def test_em2_minimal_pairs(changes, expected):
    assert S(
        score_em2,
        mutate(EM2, **changes),
    ) == expected


# ============================================================
# EM3 ? MARCO PERSONAL / PERSPECTIVA
# ============================================================

def test_em3_no_external_perspective_does_not_require_timing():
    assert S(
        score_em3,
        values(EM3),
    ) == 3


def test_em3_external_after_understanding_as_possibility_is_three():
    assert S(
        score_em3,
        mutate(
            EM3,
            external_perspective_present="true",
            perspective_timing="true",
            external_perspective_offered_as_possibility="true",
        ),
    ) == 3


@pytest.mark.parametrize(
    "changes",
    [
        {
            "external_perspective_present": "true",
            "perspective_timing": "false",
            "external_perspective_offered_as_possibility": "true",
        },
        {
            "external_perspective_present": "true",
            "external_perspective_imposed": "true",
            "perspective_timing": "true",
            "external_perspective_offered_as_possibility": "false",
        },
    ],
)
def test_em3_external_perspective_defects_block_three(
    changes,
):
    assert S(
        score_em3,
        mutate(EM3, **changes),
    ) == 2


# ============================================================
# EM4 ? COMUNICACION CONCRETA
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"understanding_communicated": "false"},
            0,
        ),
        (
            {
                "communication_is_generic_only": "true",
                "communication_is_clear_and_concrete": "false",
            },
            1,
        ),
        (
            {
                "communication_is_clear_and_concrete": "false",
            },
            2,
        ),
    ],
)
def test_em4_minimal_pairs(changes, expected):
    assert S(
        score_em4,
        mutate(EM4, **changes),
    ) == expected


# ============================================================
# EM5 ? FOCO EN LA PERSONA
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"focus_on_person": "false", "person_focus_is_clear": "false"},
            0,
        ),
        (
            {
                "person_focus_is_generic_only": "true",
                "person_focus_is_clear": "false",
            },
            1,
        ),
        (
            {"own_experience_reference": "true"},
            3,
        ),
        (
            {"claims_exact_feeling_knowledge": "true"},
            2,
        ),
    ],
)
def test_em5_minimal_pairs(changes, expected):
    assert S(
        score_em5,
        mutate(EM5, **changes),
    ) == expected


def test_em5_appropriation_with_lost_person_focus_is_zero():
    assert S(
        score_em5,
        mutate(
            EM5,
            focus_on_person="false",
            experience_appropriation="true",
            person_focus_is_clear="false",
        ),
    ) == 0


# ============================================================
# EM6 ? EMOCION COMPRENSIBLE
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {
                "emotion_presented_as_understandable": "false",
                "circumstantial_grounding": "false",
            },
            0,
        ),
        (
            {
                "validation_is_generic_only": "true",
                "validation_is_clear_and_contextualized": "false",
            },
            1,
        ),
        (
            {
                "circumstantial_grounding": "false",
                "validation_is_clear_and_contextualized": "false",
            },
            2,
        ),
    ],
)
def test_em6_minimal_pairs(changes, expected):
    assert S(
        score_em6,
        mutate(EM6, **changes),
    ) == expected


# ============================================================
# EM7 ? TONO Y GRAVEDAD
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"tone_congruence": "false"},
            0,
        ),
        (
            {
                "tone_alignment_is_generic_or_partial": "true",
                "tone_is_fully_proportional": "false",
            },
            1,
        ),
        (
            {
                "tone_is_fully_proportional": "false",
            },
            2,
        ),
        (
            {
                "minimization": "true",
                "gravity_alignment": "false",
                "tone_is_fully_proportional": "false",
            },
            1,
        ),
        (
            {
                "unnecessary_amplification": "true",
                "gravity_alignment": "true",
                "tone_is_fully_proportional": "false",
            },
            2,
        ),
    ],
)
def test_em7_minimal_pairs(changes, expected):
    assert S(
        score_em7,
        mutate(EM7, **changes),
    ) == expected


# ============================================================
# EM8 ? NECESIDAD / BIENESTAR
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {
                "response_oriented_to_need": "false",
                "wellbeing_orientation": "false",
            },
            0,
        ),
        (
            {
                "orientation_is_generic_only": "true",
                "orientation_is_clear_and_contextualized": "false",
            },
            1,
        ),
        (
            {
                "unsupported_need_assumption": "true",
                "orientation_is_clear_and_contextualized": "false",
            },
            1,
        ),
        (
            {
                "orientation_is_clear_and_contextualized": "false",
            },
            2,
        ),
    ],
)
def test_em8_minimal_pairs(changes, expected):
    assert S(
        score_em8,
        mutate(EM8, **changes),
    ) == expected


# ============================================================
# EM9 ? CLARIFICACION
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"clarification_sought": "false"},
            0,
        ),
        (
            {
                "premature_conclusion_or_solution": "true",
                "clarification_is_specific_and_sufficient": "false",
            },
            1,
        ),
        (
            {
                "clarification_precedes_dependent_guidance":
                    "false",
                "clarification_is_specific_and_sufficient":
                    "false",
            },
            1,
        ),
        (
            {
                "clarification_is_specific_and_sufficient":
                    "false",
            },
            2,
        ),
    ],
)
def test_em9_minimal_pairs(changes, expected):
    assert S(
        score_em9,
        mutate(EM9, **changes),
    ) == expected


# ============================================================
# EM10 ? EXTENSION / PROPORCIONALIDAD
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {
                "sufficient_for_understanding": "false",
                "scope_is_minimally_sufficient": "false",
            },
            0,
        ),
        (
            {
                "scope_is_minimally_sufficient": "false",
                "scope_is_fully_proportional": "false",
            },
            1,
        ),
        (
            {
                "scope_is_fully_proportional": "false",
            },
            2,
        ),
        (
            {
                "repetitive": "true",
                "scope_is_fully_proportional": "false",
            },
            2,
        ),
    ],
)
def test_em10_minimal_pairs(changes, expected):
    assert S(
        score_em10,
        mutate(EM10, **changes),
    ) == expected


# ============================================================
# EM11 ? PARTICULARIZACION
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {
                "concrete_message_element_used": "false",
                "response_particularized": "false",
            },
            0,
        ),
        (
            {
                "particularization_is_minimal_or_generic": "true",
                "particularization_is_clear_and_noninterchangeable":
                    "false",
            },
            1,
        ),
        (
            {
                "particularization_is_clear_and_noninterchangeable":
                    "false",
            },
            2,
        ),
    ],
)
def test_em11_minimal_pairs(changes, expected):
    assert S(
        score_em11,
        mutate(EM11, **changes),
    ) == expected


# ============================================================
# EM12 ? AJUSTE DE LENGUAJE
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {
                "explanation_fit": "false",
                "unnecessary_complexity": "true",
                "language_fit_is_clear_and_proportional": "false",
            },
            0,
        ),
        (
            {
                "explanation_fit": "false",
                "language_fit_is_clear_and_proportional": "false",
            },
            1,
        ),
        (
            {
                "language_fit_is_partial": "true",
                "language_fit_is_clear_and_proportional": "false",
            },
            2,
        ),
    ],
)
def test_em12_minimal_pairs(changes, expected):
    assert S(
        score_em12,
        mutate(EM12, **changes),
    ) == expected


# ============================================================
# EM13 ? CREENCIAS / VALORES
# ============================================================

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"belief_or_value_respected": "false"},
            0,
        ),
        (
            {"belief_or_identity_disqualified": "true"},
            0,
        ),
        (
            {
                "respect_is_generic_only": "true",
                "respect_is_clear_and_contextualized": "false",
            },
            1,
        ),
        (
            {
                "external_framework_imposed": "true",
                "respect_is_clear_and_contextualized": "false",
            },
            2,
        ),
        (
            {
                "respect_is_clear_and_contextualized": "false",
            },
            2,
        ),
    ],
)
def test_em13_minimal_pairs(changes, expected):
    if changes.get("external_framework_imposed") == "true":
        expected = 0

    assert S(
        score_em13,
        mutate(EM13, **changes),
    ) == expected


# ============================================================
# ADVERSARIAL ? VERIFICACION AMBIGUA NO SE CONVIERTE EN SCORE
# ============================================================

AMBIGUITY_CASES = [
    (
        score_em1,
        EM1,
        "recognition_congruence",
    ),
    (
        score_em2,
        EM2,
        "experience_understood",
    ),
    (
        score_em3,
        EM3,
        "person_frame_understood",
    ),
    (
        score_em4,
        EM4,
        "understanding_communicated",
    ),
    (
        score_em5,
        EM5,
        "focus_on_person",
    ),
    (
        score_em6,
        EM6,
        "emotion_presented_as_understandable",
    ),
    (
        score_em7,
        EM7,
        "tone_congruence",
    ),
    (
        score_em8,
        EM8,
        "response_oriented_to_need",
    ),
    (
        score_em9,
        EM9,
        "clarification_sought",
    ),
    (
        score_em10,
        EM10,
        "sufficient_for_understanding",
    ),
    (
        score_em11,
        EM11,
        "response_particularized",
    ),
    (
        score_em12,
        EM12,
        "explanation_fit",
    ),
    (
        score_em13,
        EM13,
        "belief_or_value_respected",
    ),
]


@pytest.mark.parametrize(
    ("fn", "baseline", "component"),
    AMBIGUITY_CASES,
)
def test_ambiguous_required_component_fails_closed(
    fn,
    baseline,
    component,
):
    raw = values(baseline)

    raw[component] = V(
        component,
        baseline[component],
        "ambiguous",
    )

    with pytest.raises(
        UnresolvedScoringState
    ):
        S(fn, raw)


@pytest.mark.parametrize(
    ("fn", "baseline", "component"),
    AMBIGUITY_CASES,
)
def test_unsupported_required_component_fails_closed(
    fn,
    baseline,
    component,
):
    raw = values(baseline)

    raw[component] = V(
        component,
        baseline[component],
        "unsupported",
    )

    with pytest.raises(
        UnresolvedScoringState
    ):
        S(fn, raw)
