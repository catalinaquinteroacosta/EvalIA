import pytest

from backend.evaluators.nd.nd94_indicator_facts import (
    FACTS,
    TARGETS,
    ND94Fact,
    validate_fact_set,
)


def fact(**changes):
    values = dict(
        indicator="ND5",
        name="reinforcement",
        verdict="present",
        extraction_verified=True,
        independent_verified=True,
        component_ids=(0,),
    )
    values.update(changes)
    return ND94Fact(**values)


def test_eight_targets():
    assert set(TARGETS) == {
        f"ND{i}" for i in range(1, 9)
    }


def test_six_fact_dimensions():
    assert len(FACTS) == 6
    assert len(set(FACTS)) == 6


def test_valid_fact():
    assert validate_fact_set(
        "ND5", (fact(),), 1
    )


def test_uncertain_blocks():
    assert not validate_fact_set(
        "ND5",
        (fact(verdict="uncertain"),),
        1,
    )


def test_independent_disagreement_blocks():
    assert not validate_fact_set(
        "ND5",
        (fact(independent_verified=False),),
        1,
    )


def test_missing_component_blocks():
    assert not validate_fact_set(
        "ND5",
        (fact(component_ids=()),),
        1,
    )


def test_wrong_indicator_blocks():
    assert not validate_fact_set(
        "ND6", (fact(),), 1
    )


def test_duplicate_fact_blocks():
    assert not validate_fact_set(
        "ND5", (fact(), fact()), 1
    )


def test_unknown_fact_rejected():
    with pytest.raises(ValueError):
        fact(name="invented")


def test_component_out_of_range_blocks():
    assert not validate_fact_set(
        "ND5",
        (fact(component_ids=(4,)),),
        1,
    )
