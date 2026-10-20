import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em1,
)


def V(name, value, status="supported"):
    return VerifiedSemanticValue(
        name=name,
        proposed_value=value,
        verification_status=status,
    )


def base(**changes):
    raw = {
        "emotion_present_or_inferable": "true",
        "emotion_recognized": "true",
        "recognition_congruence": "true",
        "unsupported_emotion_attribution": "false",
        "unsupported_attribution_is_material": "false",
        "recognition_is_generic_only": "false",
        "recognition_is_specific_or_contextualized": "true",
    }

    raw.update(changes)

    return {
        key: V(key, value)
        for key, value in raw.items()
    }


def score(values):
    return score_em1(
        values=values,
        applicability_reason="Aplica",
    ).score


def test_complete_supported_recognition_scores_three():
    assert score(base()) == 3


def test_secondary_unsupported_attribution_caps_two():
    assert score(
        base(
            unsupported_emotion_attribution="true",
            unsupported_attribution_is_material="false",
        )
    ) == 2


def test_material_unsupported_attribution_scores_one():
    assert score(
        base(
            unsupported_emotion_attribution="true",
            unsupported_attribution_is_material="true",
        )
    ) == 1


def test_incongruent_recognition_scores_zero():
    assert score(
        base(
            recognition_congruence="false",
        )
    ) == 0


def test_generic_recognition_scores_one():
    assert score(
        base(
            recognition_is_generic_only="true",
            recognition_is_specific_or_contextualized="false",
        )
    ) == 1


def test_adequate_non_specific_recognition_scores_two():
    assert score(
        base(
            recognition_is_specific_or_contextualized="false",
        )
    ) == 2


def test_impossible_materiality_state_fails_closed():
    with pytest.raises(UnresolvedScoringState):
        score(
            base(
                unsupported_emotion_attribution="false",
                unsupported_attribution_is_material="true",
            )
        )


def test_ambiguous_materiality_fails_closed():
    values = base(
        unsupported_emotion_attribution="true",
        unsupported_attribution_is_material="true",
    )

    values[
        "unsupported_attribution_is_material"
    ] = V(
        "unsupported_attribution_is_material",
        "true",
        "ambiguous",
    )

    with pytest.raises(UnresolvedScoringState):
        score(values)
