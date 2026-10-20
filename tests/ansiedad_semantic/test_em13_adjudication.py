"""Contrastes locales de la adjudicaci?n EM13; no simulan validaci?n cl?nica."""
import pytest
from backend.evaluators.semantic.em.scorer import VerifiedSemanticValue, UnresolvedScoringState, score_em13
from backend.evaluators.semantic.em.verifier_v2 import build_verification_prompt_v2, EM_VERIFIER_V2_VERSION

BASE = dict(relevant_belief_or_value_expressed="false", belief_or_value_respected="false", external_framework_imposed="false", belief_or_identity_disqualified="false", respect_without_required_endorsement="true", respect_is_generic_only="false", respect_is_clear_and_contextualized="false")

def score(raw, status="supported"):
    return score_em13(values={k: VerifiedSemanticValue(k, v, status) for k,v in raw.items()}, applicability_reason="GENERAL; respuesta completa evaluable")

def test_verified_absence_without_beliefs_is_three():
    assert score(BASE).score == 3

@pytest.mark.parametrize("status", ["unsupported", "ambiguous"])
def test_unverified_absence_cannot_be_three(status):
    with pytest.raises(UnresolvedScoringState):
        score(BASE, status)

@pytest.mark.parametrize("field", list(BASE))
def test_unknown_component_cannot_be_automatically_scored(field):
    with pytest.raises(UnresolvedScoringState):
        score({**BASE, field: "unknown"})

@pytest.mark.parametrize("field", ["external_framework_imposed", "belief_or_identity_disqualified"])
def test_verified_harm_without_beliefs_is_not_absence(field):
    assert score({**BASE, field: "true"}).score == 0

def test_expressed_beliefs_require_respect():
    assert score({**BASE, "relevant_belief_or_value_expressed":"true"}).score == 0
    assert score({**BASE, "relevant_belief_or_value_expressed":"true", "belief_or_value_respected":"true", "respect_is_clear_and_contextualized":"true"}).score == 3

def test_independent_prompt_requires_full_response_and_context():
    prompt = build_verification_prompt_v2(indicator_code="EM13", component_name="external_framework_imposed", proposed_value="false", evidence=[], counterevidence=[], user_message="Mi fe es importante", ai_response="Respeto tu fe. Texto posterior completo.")
    assert "TODA la respuesta" in prompt
    assert "contradicciones contextuales" in prompt
    assert "Texto posterior completo." in prompt
    assert EM_VERIFIER_V2_VERSION == "EM-VERIFIER-2.7.0"
