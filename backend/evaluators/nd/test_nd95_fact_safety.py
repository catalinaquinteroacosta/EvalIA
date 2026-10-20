from backend.evaluators.nd.nd94_indicator_facts import (
    ND94Fact,
    validate_fact_set,
)


def make_fact(
    verdict="present",
    extraction_verified=True,
    independent_verified=True,
):
    return ND94Fact(
        indicator="ND1",
        name="reinforcement",
        verdict=verdict,
        extraction_verified=extraction_verified,
        independent_verified=independent_verified,
        component_ids=(0,),
    )


def test_present_verified_allowed():
    assert validate_fact_set(
        "ND1", (make_fact(),), 1
    )


def test_absence_not_proven_by_positive_citation():
    assert not validate_fact_set(
        "ND1",
        (make_fact(verdict="absent"),),
        1,
    )


def test_uncertain_rejected():
    assert not validate_fact_set(
        "ND1",
        (make_fact(verdict="uncertain"),),
        1,
    )


def test_unverified_extraction_rejected():
    assert not validate_fact_set(
        "ND1",
        (
            make_fact(
                extraction_verified=False
            ),
        ),
        1,
    )


def test_unverified_independent_check_rejected():
    assert not validate_fact_set(
        "ND1",
        (
            make_fact(
                independent_verified=False
            ),
        ),
        1,
    )
