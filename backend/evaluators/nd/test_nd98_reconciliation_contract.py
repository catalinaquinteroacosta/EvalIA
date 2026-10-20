import pytest

from backend.evaluators.nd.nd98_reconciliation_contract import (
    IndependentReview,
    reconcile,
)


def review(**changes):
    data = dict(
        indicator="ND1",
        fact_name="reinforcement",
        verdict="present",
        evidence_verified=True,
        independent=True,
        reason="Evidencia revisada",
    )
    data.update(changes)
    return IndependentReview(**data)


@pytest.mark.parametrize("verdict", ["present", "absent"])
def test_verified_agreement(verdict):
    result = reconcile(
        review(verdict=verdict),
        review(verdict=verdict),
    )
    assert result.status == "VERIFIED"
    assert result.verified_verdict == verdict


def test_disagreement_blocks():
    result = reconcile(
        review(verdict="present"),
        review(verdict="absent"),
    )
    assert result.status == "BLOCKED"


def test_uncertain_blocks():
    result = reconcile(
        review(verdict="uncertain"),
        review(verdict="uncertain"),
    )
    assert result.status == "BLOCKED"


def test_unverified_evidence_blocks():
    result = reconcile(
        review(),
        review(evidence_verified=False),
    )
    assert result.status == "BLOCKED"


def test_not_independent_blocks():
    result = reconcile(
        review(),
        review(independent=False),
    )
    assert result.status == "BLOCKED"


def test_wrong_indicator_blocks():
    result = reconcile(
        review(),
        review(indicator="ND2"),
    )
    assert result.status == "BLOCKED"


def test_wrong_fact_blocks():
    result = reconcile(
        review(),
        review(fact_name="light_correction"),
    )
    assert result.status == "BLOCKED"


def test_missing_reason_blocks():
    result = reconcile(
        review(),
        review(reason=""),
    )
    assert result.status == "BLOCKED"
