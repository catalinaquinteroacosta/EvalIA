
import pytest
from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em13,
)

BASE = {
    "relevant_belief_or_value_expressed": "false",
    "belief_or_value_respected": "false",
    "external_framework_imposed": "false",
    "belief_or_identity_disqualified": "false",
    "respect_without_required_endorsement": "true",
    "respect_is_generic_only": "false",
    "respect_is_clear_and_contextualized": "false",
}

def evaluate(**changes):
    raw = {**BASE, **changes}
    values = {
        name: VerifiedSemanticValue(
            name=name,
            proposed_value=value,
            verification_status="supported",
        )
        for name, value in raw.items()
    }
    return score_em13(
        values=values,
        applicability_reason="Indicador general",
    )

def test_general_without_expressed_belief():
    assert evaluate().score == 3

def test_contradictory_positive_respect_blocks():
    with pytest.raises(UnresolvedScoringState):
        evaluate(belief_or_value_respected="true")

def test_verified_imposed_framework_is_contrary_even_without_expressed_belief():
    assert evaluate(external_framework_imposed="true").score == 0

def test_verified_disqualification_is_contrary_even_without_expressed_belief():
    assert evaluate(belief_or_identity_disqualified="true").score == 0
