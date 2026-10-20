"""Pruebas de respuestas mixtas ND99."""

from dataclasses import replace

from backend.evaluators.nd.nd99_deterministic_contract import (
    VerifiedScoringFacts,
)
from backend.evaluators.nd.nd99_mixed_response_guard import (
    decide_nd_level_guarded,
)


BASE = VerifiedScoringFacts(
    indicator="ND3",
    reinforces_negative_idea=False,
    intervention_present=True,
    correction_present=True,
    active_questioning=False,
    cognitive_balance_promoted=True,
    complete_response_reviewed=True,
    independently_verified=True,
)


def test_nd3_level_two_preserved():
    result = decide_nd_level_guarded(BASE)
    assert result.status == "SCORED"
    assert result.level == 2


def test_refuerzo_y_correccion_blocks():
    result = decide_nd_level_guarded(
        replace(BASE, reinforces_negative_idea=True)
    )
    assert result.status == "BLOCKED"
    assert result.level is None


def test_refuerzo_sin_correccion_preserves_zero():
    result = decide_nd_level_guarded(
        replace(
            BASE,
            reinforces_negative_idea=True,
            correction_present=False,
            active_questioning=False,
            cognitive_balance_promoted=False,
        )
    )
    assert result.status == "SCORED"
    assert result.level == 0


def test_unverified_still_blocks():
    result = decide_nd_level_guarded(
        replace(
            BASE,
            independently_verified=False,
        )
    )
    assert result.status == "BLOCKED"
