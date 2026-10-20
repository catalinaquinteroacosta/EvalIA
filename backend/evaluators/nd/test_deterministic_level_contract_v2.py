import pytest

from backend.evaluators.nd.deterministic_level_contract_v2 import (
    VerifiedNDFact,
    validate_verified_facts,
)


def make_fact(**changes):
    values = {
        "indicator": "ND1",
        "fact": "avoids_reinforcement",
        "present": True,
        "extraction_verified": True,
        "independent_verified": True,
        "evidence_component_ids": (0,),
    }
    values.update(changes)
    return VerifiedNDFact(**values)


def test_verified_fact_accepted():
    assert validate_verified_facts(
        "ND1", (make_fact(),), 1
    )


def test_unverified_fact_blocked():
    assert not validate_verified_facts(
        "ND1",
        (make_fact(independent_verified=False),),
        1,
    )


def test_wrong_indicator_blocked():
    assert not validate_verified_facts(
        "ND2", (make_fact(),), 1
    )


def test_missing_evidence_blocked():
    assert not validate_verified_facts(
        "ND1",
        (make_fact(evidence_component_ids=()),),
        1,
    )


def test_nonexistent_component_blocked():
    assert not validate_verified_facts(
        "ND1",
        (make_fact(evidence_component_ids=(2,)),),
        1,
    )


def test_duplicate_fact_blocked():
    fact = make_fact()
    assert not validate_verified_facts(
        "ND1", (fact, fact), 1
    )


def test_unknown_fact_rejected():
    with pytest.raises(ValueError):
        make_fact(fact="invented_criterion")


def test_integer_not_accepted_as_boolean():
    with pytest.raises(TypeError):
        make_fact(present=1)
