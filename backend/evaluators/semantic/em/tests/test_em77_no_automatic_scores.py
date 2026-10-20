import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em13,
)


def test_em13_no_belief_no_automatic_three():
    raw = {
        "relevant_belief_or_value_expressed": "false",
        "belief_or_value_respected": "true",
        "external_framework_imposed": "false",
        "belief_or_identity_disqualified": "false",
        "respect_without_required_endorsement": "true",
        "respect_is_generic_only": "false",
        "respect_is_clear_and_contextualized": "true",
    }

    values = {
        name: VerifiedSemanticValue(
            name=name,
            proposed_value=value,
            verification_status="supported",
        )
        for name, value in raw.items()
    }

    with pytest.raises(UnresolvedScoringState):
        score_em13(
            values=values,
            applicability_reason="Indicador general",
        )
