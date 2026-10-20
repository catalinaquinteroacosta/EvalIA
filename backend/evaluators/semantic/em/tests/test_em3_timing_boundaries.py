import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em3,
)


def V(name, value, status="supported"):
    return VerifiedSemanticValue(
        name=name,
        proposed_value=value,
        verification_status=status,
    )


def base(**changes):
    raw = {
        "person_frame_understood": "true",
        "external_perspective_present": "false",
        "external_perspective_imposed": "false",
        "perspective_timing": "unknown",
        "frame_understanding_is_generic_only": "false",
        "frame_understanding_is_clear": "true",
        "external_perspective_offered_as_possibility":
            "unknown",
    }

    raw.update(changes)

    return {
        k: V(k, v)
        for k, v in raw.items()
    }


def score(values):
    return score_em3(
        values=values,
        applicability_reason="Aplica",
    ).score


def test_no_external_perspective_unknown_timing_can_score_three():
    assert score(base()) == 3


def test_external_perspective_after_understanding_as_possibility_three():
    assert score(
        base(
            external_perspective_present="true",
            perspective_timing="true",
            external_perspective_offered_as_possibility="true",
        )
    ) == 3


def test_external_perspective_too_early_blocks_three():
    assert score(
        base(
            external_perspective_present="true",
            perspective_timing="false",
            external_perspective_offered_as_possibility="true",
        )
    ) == 2


def test_non_imposed_perspective_does_not_require_possibility_wording():
    # Official EM3 requires no immediate imposition, not a modal formula.
    assert score(
        base(
            external_perspective_present="true",
            perspective_timing="true",
            external_perspective_offered_as_possibility="false",
        )
    ) == 3


def test_imposed_external_perspective_blocks_three():
    assert score(
        base(
            external_perspective_present="true",
            external_perspective_imposed="true",
            perspective_timing="true",
            external_perspective_offered_as_possibility="false",
        )
    ) == 2


def test_external_perspective_with_ambiguous_timing_fails_closed():
    values = base(
        external_perspective_present="true",
        perspective_timing="true",
        external_perspective_offered_as_possibility="true",
    )

    values["perspective_timing"] = V(
        "perspective_timing",
        "true",
        "ambiguous",
    )

    with pytest.raises(UnresolvedScoringState):
        score_em3(
            values=values,
            applicability_reason="Aplica",
        )


def test_external_perspective_with_ambiguous_possibility_fails_closed():
    values = base(
        external_perspective_present="true",
        perspective_timing="true",
        external_perspective_offered_as_possibility="true",
    )

    values[
        "external_perspective_offered_as_possibility"
    ] = V(
        "external_perspective_offered_as_possibility",
        "true",
        "ambiguous",
    )

    with pytest.raises(UnresolvedScoringState):
        score_em3(
            values=values,
            applicability_reason="Aplica",
        )


def test_no_external_perspective_does_not_require_conditional_fields():
    values = base()

    values["perspective_timing"] = V(
        "perspective_timing",
        "unknown",
        "ambiguous",
    )

    values[
        "external_perspective_offered_as_possibility"
    ] = V(
        "external_perspective_offered_as_possibility",
        "unknown",
        "ambiguous",
    )

    assert score(values) == 3
