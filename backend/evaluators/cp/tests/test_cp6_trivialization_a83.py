
import pytest

from backend.evaluators.cp.scoring import _score_cp6


def components(
    *,
    distortion=False,
    trivialization=False,
    pertinence="complete",
    clarification="complete",
    limitation=False,
):
    return {
        "example_or_analogy_used": True,
        "distortion_present": distortion,
        "trivialization_present": trivialization,
        "pertinence": pertinence,
        "clarification_value": clarification,
        "concrete_secondary_limitation": limitation,
    }


@pytest.mark.parametrize(
    "trivialization",
    [False, True],
)
def test_cp6_trivialization_alone_does_not_force_zero(
    trivialization,
):
    result = _score_cp6(
        components(trivialization=trivialization)
    )

    assert result.status == "scored"
    assert result.score == 3


@pytest.mark.parametrize(
    "level,expected",
    [
        ("none", 0),
        ("minimal", 1),
        ("adequate", 2),
        ("complete", 3),
    ],
)
def test_cp6_quality_levels_control_score(
    level,
    expected,
):
    result = _score_cp6(
        components(
            trivialization=True,
            pertinence=level,
            clarification=level,
        )
    )

    assert result.score == expected


def test_cp6_distortion_still_forces_zero():
    result = _score_cp6(
        components(
            distortion=True,
            trivialization=False,
        )
    )

    assert result.score == 0


def test_cp6_secondary_limitation_caps_at_two():
    result = _score_cp6(
        components(
            trivialization=True,
            limitation=True,
        )
    )

    assert result.score == 2
