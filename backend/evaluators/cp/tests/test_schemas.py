import pytest

from backend.evaluators.cp.schemas import (
    CP1SemanticState,
    CP2SemanticState,
    CP3SemanticState,
    CP4SemanticState,
    CP5SemanticState,
    CP6SemanticState,
    CP7SemanticState,
    CP8SemanticState,
    CPFamilySemanticDraft,
    SemanticClaim,
    SemanticEvidence,
)


def test_literal_evidence_cannot_be_empty():
    with pytest.raises(ValueError):
        SemanticEvidence(
            source="response",
            quote="",
            interpretation="algo",
        )


def test_interpretation_cannot_be_empty():
    with pytest.raises(ValueError):
        SemanticEvidence(
            source="response",
            quote="texto literal",
            interpretation="",
        )


def test_family_contains_cp1_to_cp8():
    family = CPFamilySemanticDraft(
        cp1=CP1SemanticState(
            central_problem_identification="complete",
            secondary_concerns_present=False,
            secondary_concerns_coverage="complete",
            substitution_or_unfounded_problem=False,
            concrete_secondary_limitation=False,
        ),
        cp2=CP2SemanticState(
            explanation_present=True,
            explanatory_function="complete",
            clarity_comprehensibility="complete",
            case_adjustment="complete",
            concrete_secondary_limitation=False,
        ),
        cp3=CP3SemanticState(
            structural_complexity_requires_organization=False,
            serious_emotional_complexity_requires_organization=False,
            organization_present=False,
            organization_quality="none",
            concrete_secondary_limitation=False,
        ),
        cp4=CP4SemanticState(
            relationship_explanation_present=True,
            relationship_correctness="complete",
            relationship_relevance="complete",
            relationship_explanation_quality="complete",
            materially_incorrect_relationship=False,
            concrete_secondary_limitation=False,
        ),
        cp5=CP5SemanticState(
            psychological_information_present=False,
            unsupported_psychological_claim_as_fact=False,
            speculation_presented_as_fact=False,
            diagnosis_presented_as_fact=False,
            responsible_diagnostic_possibility_present=False,
            uncertainty_handling="complete",
            knowledge_support="complete",
            concrete_secondary_limitation=False,
        ),
        cp6=CP6SemanticState(
            example_or_analogy_needed=False,
            example_or_analogy_used=False,
            pertinence="none",
            clarification_value="none",
            distortion_present=False,
            trivialization_present=False,
            concrete_secondary_limitation=False,
        ),
        cp7=CP7SemanticState(
            unnecessary_jargon_present=False,
            indispensable_technical_terms_present=False,
            indispensable_terms_explanation="complete",
            accessibility="complete",
            concrete_secondary_limitation=False,
        ),
        cp8=CP8SemanticState(
            explanation_complex_enough_for_verification=False,
            direct_understanding_check_present=False,
            correction_invitation_present=False,
            generic_offer_for_more_explanation_only=False,
            verification_quality="none",
            concrete_secondary_limitation=False,
        ),
        analysis_complete=True,
    )

    for i in range(1, 9):
        assert family.by_code(f"CP{i}") is not None


def test_unknown_cp_code_fails_closed():
    family = CPFamilySemanticDraft(
        cp1=CP1SemanticState(
            "none", False, "none", False, False
        ),
        cp2=CP2SemanticState(
            False, "none", "none", "none", False
        ),
        cp3=CP3SemanticState(
            False, False, False, "none", False
        ),
        cp4=CP4SemanticState(
            False, "none", "none", "none", False, False
        ),
        cp5=CP5SemanticState(
            False, False, False, False, False,
            "none", "none", False
        ),
        cp6=CP6SemanticState(
            False, False, "none", "none", False, False, False
        ),
        cp7=CP7SemanticState(
            False, False, "none", "none", False
        ),
        cp8=CP8SemanticState(
            False, False, False, False, "none", False
        ),
        analysis_complete=True,
    )

    with pytest.raises(ValueError):
        family.by_code("CP9")


def test_claim_has_no_score_field():
    claim = SemanticClaim(
        field="example",
        value=True,
    )

    assert not hasattr(claim, "score")
