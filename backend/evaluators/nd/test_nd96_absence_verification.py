from backend.evaluators.nd.nd94_indicator_facts import (
    ND94Fact,
)
from backend.evaluators.nd.nd96_absence_verification import (
    VerifiedAbsence,
    certify_absence,
)


def fact(**changes):
    values = dict(
        indicator="ND1",
        name="reinforcement",
        verdict="absent",
        extraction_verified=True,
        independent_verified=True,
        component_ids=(),
    )
    values.update(changes)
    return ND94Fact(**values)


def certificate(**changes):
    values = dict(
        indicator="ND1",
        fact_name="reinforcement",
        full_response_examined=True,
        independent_verdict="absent",
        independent_verified=True,
        reason="Revision independiente completa",
    )
    values.update(changes)
    return VerifiedAbsence(**values)


def test_valid_absence():
    assert certify_absence(fact(), certificate())


def test_partial_response_blocks():
    assert not certify_absence(
        fact(),
        certificate(full_response_examined=False),
    )


def test_disagreement_blocks():
    assert not certify_absence(
        fact(),
        certificate(independent_verdict="present"),
    )


def test_unverified_certificate_blocks():
    assert not certify_absence(
        fact(),
        certificate(independent_verified=False),
    )


def test_empty_reason_blocks():
    assert not certify_absence(
        fact(),
        certificate(reason=""),
    )


def test_wrong_fact_blocks():
    assert not certify_absence(
        fact(),
        certificate(fact_name="light_correction"),
    )


def test_wrong_indicator_blocks():
    assert not certify_absence(
        fact(),
        certificate(indicator="ND5"),
    )


def test_present_is_not_absence():
    assert not certify_absence(
        fact(verdict="present"),
        certificate(),
    )


def test_unverified_extraction_blocks():
    assert not certify_absence(
        fact(extraction_verified=False),
        certificate(),
    )
