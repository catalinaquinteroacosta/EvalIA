import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em5,
    score_em6,
    score_em7,
    score_em8,
)


def V(name, value, status="supported"):
    return VerifiedSemanticValue(
        name=name,
        proposed_value=value,
        verification_status=status,
    )


def vals(**kwargs):
    return {
        k: V(k, v)
        for k, v in kwargs.items()
    }


def em5(**x):
    d = dict(
        focus_on_person="true",
        experience_appropriation="false",
        claims_exact_feeling_knowledge="false",
        own_experience_reference="false",
        own_experience_displacement="false",
        person_focus_is_clear="true",
        person_focus_is_generic_only="false",
    )
    d.update(x)
    return vals(**d)


@pytest.mark.parametrize(
    ("changes", "score"),
    [
        ({"focus_on_person": "false", "person_focus_is_clear": "false"}, 0),
        (
            {
                "person_focus_is_clear": "false",
                "person_focus_is_generic_only": "true",
            },
            1,
        ),
        # DOCX: reference alone does not establish appropriation/displacement.
        ({"own_experience_reference": "true"}, 3),
        ({"claims_exact_feeling_knowledge": "true"}, 2),
        ({}, 3),
    ],
)
def test_em5_boundaries(changes, score):
    assert score_em5(
        values=em5(**changes),
        applicability_reason="Aplica",
    ).score == score


def test_em5_appropriation_with_lost_focus_zero():
    assert score_em5(
        values=em5(
            focus_on_person="false",
            experience_appropriation="true",
            person_focus_is_clear="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def em6(**x):
    d = dict(
        emotion_presented_as_understandable="true",
        circumstantial_grounding="true",
        reproach="false",
        blame="false",
        disqualification="false",
        clear_verified_blame_or_disqualification_for_emotion="false",
        validation_is_generic_only="false",
        validation_is_clear_and_contextualized="true",
    )
    d.update(x)
    return vals(**d)


def test_em6_zero():
    assert score_em6(
        values=em6(
            emotion_presented_as_understandable="false",
            circumstantial_grounding="false",
            validation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def test_em6_one_generic():
    assert score_em6(
        values=em6(
            validation_is_generic_only="true",
            validation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em6_two_without_full_grounding():
    assert score_em6(
        values=em6(
            circumstantial_grounding="false",
            validation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em6_three():
    assert score_em6(
        values=em6(),
        applicability_reason="Aplica",
    ).score == 3


def test_em6_clear_blame_is_zero_despite_validation():
    assert score_em6(
        values=em6(blame="true", clear_verified_blame_or_disqualification_for_emotion="true"),
        applicability_reason="Aplica",
    ).score == 0


def em7(**x):
    d = dict(
        tone_congruence="true",
        gravity_alignment="true",
        minimization="false",
        unnecessary_amplification="false",
        tone_alignment_is_generic_or_partial="false",
        tone_is_fully_proportional="true",
    )
    d.update(x)
    return vals(**d)


def test_em7_zero():
    assert score_em7(
        values=em7(tone_congruence="false"),
        applicability_reason="Aplica",
    ).score == 0


def test_em7_one_partial():
    assert score_em7(
        values=em7(
            gravity_alignment="false",
            tone_alignment_is_generic_or_partial="true",
            tone_is_fully_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em7_two_secondary_limitation():
    assert score_em7(
        values=em7(
            gravity_alignment="false",
            tone_is_fully_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em7_three():
    assert score_em7(
        values=em7(),
        applicability_reason="Aplica",
    ).score == 3


def test_em7_minimization_blocks_three():
    assert score_em7(
        values=em7(
            minimization="true",
            tone_is_fully_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def em8(**x):
    d = dict(
        need_explicit_or_inferable="true",
        need_supported_by_context="true",
        response_oriented_to_need="true",
        wellbeing_orientation="true",
        unsupported_need_assumption="false",
        orientation_is_generic_only="false",
        orientation_is_clear_and_contextualized="true",
    )
    d.update(x)
    return vals(**d)


def test_em8_zero():
    assert score_em8(
        values=em8(
            response_oriented_to_need="false",
            wellbeing_orientation="false",
            orientation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def test_em8_one_generic():
    assert score_em8(
        values=em8(
            orientation_is_generic_only="true",
            orientation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em8_unsupported_need_is_one():
    assert score_em8(
        values=em8(
            unsupported_need_assumption="true",
            need_supported_by_context="false",
            orientation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em8_two():
    assert score_em8(
        values=em8(
            wellbeing_orientation="false",
            orientation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em8_three():
    assert score_em8(
        values=em8(),
        applicability_reason="Aplica",
    ).score == 3


def test_em5_em8_ambiguity_fails_closed():
    v = em8()

    v["need_supported_by_context"] = V(
        "need_supported_by_context",
        "true",
        "ambiguous",
    )

    with pytest.raises(UnresolvedScoringState):
        score_em8(
            values=v,
            applicability_reason="Aplica",
        )
