import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em1,
    score_em2,
    score_em3,
    score_em4,
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


def em1(**x):
    d = dict(
        emotion_present_or_inferable="true",
        emotion_recognized="true",
        recognition_congruence="true",
        unsupported_emotion_attribution="false",
        unsupported_attribution_is_material="false",
        recognition_is_generic_only="false",
        recognition_is_specific_or_contextualized="true",
    )
    d.update(x)
    return vals(**d)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"emotion_recognized": "false"}, 0),
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
                "recognition_is_specific_or_contextualized":
                    "false",
            },
            2,
        ),
        ({}, 3),
    ],
)
def test_em1_boundaries(changes, expected):
    assert score_em1(
        values=em1(**changes),
        applicability_reason="Aplica",
    ).score == expected


def test_em1_unsupported_attribution_blocks_three():
    assert score_em1(
        values=em1(
            unsupported_emotion_attribution="true",
        ),
        applicability_reason="Aplica",
    ).score == 2


def em2(**x):
    d = dict(
        experience_understood="true",
        emotional_state_identified="true",
        emotion_situation_relation="true",
        relation_quality="true",
        understanding_is_generic_only="false",
        emotion_and_situation_only_listed="false",
        relation_is_clear_and_contextualized="true",
    )
    d.update(x)
    return vals(**d)


def test_em2_zero():
    assert score_em2(
        values=em2(experience_understood="false"),
        applicability_reason="Aplica",
    ).score == 0


def test_em2_one():
    assert score_em2(
        values=em2(
            understanding_is_generic_only="true",
            relation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em2_listing_without_relation_is_two_not_three():
    assert score_em2(
        values=em2(
            emotion_situation_relation="false",
            emotion_and_situation_only_listed="true",
            relation_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em2_three():
    assert score_em2(
        values=em2(),
        applicability_reason="Aplica",
    ).score == 3


def em3(**x):
    d = dict(
        person_frame_understood="true",
        external_perspective_present="false",
        external_perspective_imposed="false",
        frame_understanding_is_generic_only="false",
        frame_understanding_is_clear="true",
    )
    d.update(x)
    return vals(**d)


def test_em3_zero():
    assert score_em3(
        values=em3(person_frame_understood="false"),
        applicability_reason="Aplica",
    ).score == 0


def test_em3_one():
    assert score_em3(
        values=em3(
            frame_understanding_is_generic_only="true",
            frame_understanding_is_clear="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em3_imposition_blocks_three():
    assert score_em3(
        values=em3(
            external_perspective_present="true",
            external_perspective_imposed="true",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em3_three_without_external_perspective():
    assert score_em3(
        values=em3(),
        applicability_reason="Aplica",
    ).score == 3


def em4(**x):
    d = dict(
        understanding_communicated="true",
        understanding_concreteness="true",
        understood_target="true",
        communication_is_generic_only="false",
        communication_is_clear_and_concrete="true",
    )
    d.update(x)
    return vals(**d)


def test_em4_zero():
    assert score_em4(
        values=em4(understanding_communicated="false"),
        applicability_reason="Aplica",
    ).score == 0


def test_em4_one():
    assert score_em4(
        values=em4(
            communication_is_generic_only="true",
            communication_is_clear_and_concrete="false",
            understanding_concreteness="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em4_two():
    assert score_em4(
        values=em4(
            communication_is_clear_and_concrete="false",
            understanding_concreteness="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em4_three():
    assert score_em4(
        values=em4(),
        applicability_reason="Aplica",
    ).score == 3


def test_ambiguity_never_becomes_numeric_score():
    v = em1()
    v["recognition_congruence"] = V(
        "recognition_congruence",
        "true",
        "ambiguous",
    )

    with pytest.raises(UnresolvedScoringState):
        score_em1(
            values=v,
            applicability_reason="Aplica",
        )
