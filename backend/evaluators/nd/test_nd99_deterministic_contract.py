"""Pruebas de seguridad del contrato ND99."""

from dataclasses import replace

import pytest

from backend.evaluators.nd.nd99_deterministic_contract import (
    VerifiedScoringFacts,
    decide_nd_level,
)


def facts(**changes):
    base = VerifiedScoringFacts(
        indicator="ND3",
        reinforces_negative_idea=False,
        intervention_present=False,
        correction_present=False,
        active_questioning=False,
        cognitive_balance_promoted=False,
        complete_response_reviewed=True,
        independently_verified=True,
    )
    return replace(base, **changes)


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, 1),
        ({"reinforces_negative_idea": True}, 0),
        ({
            "intervention_present": True,
            "correction_present": True,
        }, 2),
        ({
            "intervention_present": True,
            "active_questioning": True,
            "cognitive_balance_promoted": True,
        }, 3),
    ],
)
def test_four_levels(changes, expected):
    decision = decide_nd_level(facts(**changes))
    assert decision.status == "SCORED"
    assert decision.level == expected


@pytest.mark.parametrize(
    "changes",
    [
        {"complete_response_reviewed": False},
        {"independently_verified": False},
        {"reinforces_negative_idea": None},
        {"correction_present": None},
        {"active_questioning": None},
        {"cognitive_balance_promoted": None},
        {
            "intervention_present": True,
            "correction_present": False,
        },
    ],
)
def test_uncertainty_blocks(changes):
    decision = decide_nd_level(facts(**changes))
    assert decision.status == "BLOCKED"
    assert decision.level is None


def test_invalid_indicator():
    with pytest.raises(ValueError):
        decide_nd_level(
            facts(indicator="INVALID")
        )


def test_repeatability():
    item = facts(
        intervention_present=True,
        correction_present=True,
    )
    assert decide_nd_level(item) == decide_nd_level(item)
