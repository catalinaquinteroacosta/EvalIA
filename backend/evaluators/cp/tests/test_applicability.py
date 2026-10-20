import pytest

from backend.evaluators.cp.applicability import (
    CONDITIONAL_CP_CODES,
    GENERAL_CP_CODES,
    cp3_applicability,
    cp6_applicability,
    cp8_applicability,
    general_applicability,
)
from backend.evaluators.cp.schemas import (
    CP3SemanticState,
    CP6SemanticState,
    CP8SemanticState,
)


def test_general_and_conditional_partition_cp_family():
    assert GENERAL_CP_CODES == {
        "CP1", "CP2", "CP4", "CP5", "CP7"
    }

    assert CONDITIONAL_CP_CODES == {
        "CP3", "CP6", "CP8"
    }

    assert GENERAL_CP_CODES | CONDITIONAL_CP_CODES == {
        f"CP{i}" for i in range(1, 9)
    }

    assert not (GENERAL_CP_CODES & CONDITIONAL_CP_CODES)


@pytest.mark.parametrize(
    "code",
    ["CP1", "CP2", "CP4", "CP5", "CP7"],
)
def test_general_indicator_is_applicable_with_evaluable_response(code):
    decision = general_applicability(
        code,
        evaluable_response_present=True,
    )

    assert decision.state == "applicable"
    assert decision.applicable is True


@pytest.mark.parametrize(
    "code",
    ["CP1", "CP2", "CP4", "CP5", "CP7"],
)
def test_general_indicator_missing_response_is_not_fake_na(code):
    decision = general_applicability(
        code,
        evaluable_response_present=False,
    )

    assert decision.state == "insufficient_evidence"
    assert decision.applicable is False


def test_general_applicability_rejects_conditional_code():
    with pytest.raises(ValueError):
        general_applicability(
            "CP3",
            evaluable_response_present=True,
        )


def test_cp3_na_without_required_complexity():
    state = CP3SemanticState(
        structural_complexity_requires_organization=False,
        serious_emotional_complexity_requires_organization=False,
        organization_present=False,
        organization_quality="none",
        concrete_secondary_limitation=False,
    )

    decision = cp3_applicability(state)

    assert decision.state == "not_applicable"


def test_cp3_applies_with_structural_complexity():
    state = CP3SemanticState(
        structural_complexity_requires_organization=True,
        serious_emotional_complexity_requires_organization=False,
        organization_present=False,
        organization_quality="none",
        concrete_secondary_limitation=False,
    )

    assert cp3_applicability(state).state == "applicable"


def test_cp3_applies_with_serious_emotional_complexity():
    state = CP3SemanticState(
        structural_complexity_requires_organization=False,
        serious_emotional_complexity_requires_organization=True,
        organization_present=False,
        organization_quality="none",
        concrete_secondary_limitation=False,
    )

    assert cp3_applicability(state).state == "applicable"


def test_cp6_na_when_not_needed_and_not_used():
    state = CP6SemanticState(
        example_or_analogy_needed=False,
        example_or_analogy_used=False,
        pertinence="none",
        clarification_value="none",
        distortion_present=False,
        trivialization_present=False,
        concrete_secondary_limitation=False,
    )

    assert cp6_applicability(state).state == "not_applicable"


def test_cp6_applies_when_needed_even_if_missing():
    state = CP6SemanticState(
        example_or_analogy_needed=True,
        example_or_analogy_used=False,
        pertinence="none",
        clarification_value="none",
        distortion_present=False,
        trivialization_present=False,
        concrete_secondary_limitation=False,
    )

    assert cp6_applicability(state).state == "applicable"


def test_cp6_unneeded_spontaneous_example_does_not_activate_official_gate():
    state = CP6SemanticState(
        example_or_analogy_needed=False,
        example_or_analogy_used=True,
        pertinence="complete",
        clarification_value="complete",
        distortion_present=False,
        trivialization_present=False,
        concrete_secondary_limitation=False,
        claims=(),
    )

    decision = cp6_applicability(state)

    # Supersedes the old necessity-or-use gate, contrary to the official DOCX.
    assert decision.state == "not_applicable"




def test_cp8_na_without_semantic_complexity():
    state = CP8SemanticState(
        explanation_complex_enough_for_verification=False,
        direct_understanding_check_present=False,
        correction_invitation_present=False,
        generic_offer_for_more_explanation_only=False,
        verification_quality="none",
        concrete_secondary_limitation=False,
    )

    assert cp8_applicability(state).state == "not_applicable"


def test_cp8_applies_when_explanation_requires_verification():
    state = CP8SemanticState(
        explanation_complex_enough_for_verification=True,
        direct_understanding_check_present=False,
        correction_invitation_present=False,
        generic_offer_for_more_explanation_only=False,
        verification_quality="none",
        concrete_secondary_limitation=False,
    )

    assert cp8_applicability(state).state == "applicable"
