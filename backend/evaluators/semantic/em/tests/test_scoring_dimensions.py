import pytest

from backend.evaluators.semantic.em.scoring_dimensions import (
    EM_SCORING_DIMENSIONS_VERSION,
    QUALITY_STATES,
    LIMITATION_STATES,
    SCORING_DIMENSIONS,
    DIMENSION_MEANINGS,
    validate_scoring_dimensions_registry,
)


def test_registry_has_exactly_em1_to_em13():
    assert set(SCORING_DIMENSIONS) == {
        f"EM{i}" for i in range(1, 14)
    }


@pytest.mark.parametrize(
    "indicator",
    [f"EM{i}" for i in range(1, 14)],
)
def test_each_indicator_has_independent_scoring_dimensions(indicator):
    assert set(SCORING_DIMENSIONS[indicator]) == {
        "execution_quality",
        "limitation_materiality",
    }


def test_quality_states_are_semantic_not_numeric():
    assert QUALITY_STATES == (
        "absent",
        "generic",
        "specific",
        "contextualized",
        "unknown",
    )

    assert not any(
        value in {"0", "1", "2", "3"}
        for value in QUALITY_STATES
    )


def test_limitation_states_are_semantic_not_numeric():
    assert LIMITATION_STATES == (
        "none",
        "secondary",
        "material",
        "unknown",
    )

    assert not any(
        value in {"0", "1", "2", "3"}
        for value in LIMITATION_STATES
    )


def test_no_score_language_in_dimension_names():
    for dimensions in SCORING_DIMENSIONS.values():
        for name in dimensions:
            assert "score" not in name.lower()
            assert "puntaje" not in name.lower()


def test_dimension_meanings_exist_for_every_state():
    assert set(DIMENSION_MEANINGS["execution_quality"]) == set(
        QUALITY_STATES
    )

    assert set(DIMENSION_MEANINGS["limitation_materiality"]) == set(
        LIMITATION_STATES
    )


def test_registry_validation():
    validate_scoring_dimensions_registry()


def test_version():
    assert (
        EM_SCORING_DIMENSIONS_VERSION
        == "EM-SCORING-DIMENSIONS-1.0.0"
    )
