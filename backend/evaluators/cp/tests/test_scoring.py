import pytest

from backend.evaluators.cp.scoring import (
    CPIndicatorScore,
    score_validated_indicator,
)
from backend.evaluators.cp.validated_state import (
    ValidatedIndicatorState,
)


BASE = {
    "CP1": {
        "central_problem_identification": "complete",
        "secondary_concerns_present": False,
        "secondary_concerns_coverage": "complete",
        "substitution_or_unfounded_problem": False,
        "concrete_secondary_limitation": False,
    },
    "CP2": {
        "explanation_present": True,
        "explanatory_function": "complete",
        "clarity_comprehensibility": "complete",
        "case_adjustment": "complete",
        "concrete_secondary_limitation": False,
    },
    "CP3": {
        "structural_complexity_requires_organization": True,
        "serious_emotional_complexity_requires_organization": False,
        "organization_present": True,
        "organization_quality": "complete",
        "concrete_secondary_limitation": False,
    },
    "CP4": {
        "relationship_explanation_present": True,
        "relationship_correctness": "complete",
        "relationship_relevance": "complete",
        "relationship_explanation_quality": "complete",
        "materially_incorrect_relationship": False,
        "concrete_secondary_limitation": False,
    },
    "CP5": {
        "psychological_information_present": False,
        "unsupported_psychological_claim_as_fact": False,
        "speculation_presented_as_fact": False,
        "diagnosis_presented_as_fact": False,
        "responsible_diagnostic_possibility_present": False,
        "uncertainty_handling": "none",
        "knowledge_support": "none",
        "concrete_secondary_limitation": False,
    },
    "CP6": {
        "example_or_analogy_needed": True,
        "example_or_analogy_used": True,
        "pertinence": "complete",
        "clarification_value": "complete",
        "distortion_present": False,
        "trivialization_present": False,
        "concrete_secondary_limitation": False,
    },
    "CP7": {
        "unnecessary_jargon_present": False,
        "indispensable_technical_terms_present": False,
        "indispensable_terms_explanation": "none",
        "accessibility": "complete",
        "concrete_secondary_limitation": False,
    },
    "CP8": {
        "explanation_complex_enough_for_verification": True,
        "direct_understanding_check_present": True,
        "correction_invitation_present": False,
        "generic_offer_for_more_explanation_only": False,
        "verification_quality": "complete",
        "concrete_secondary_limitation": False,
    },
}


def state(code, **changes):
    components = dict(BASE[code])
    components.update(changes)

    return ValidatedIndicatorState(
        code=code,
        status="validated",
        components=components,
        blocked_components=(),
        supported_evidence_indices=(),
        blocked_evidence_indices=(),
    )


@pytest.mark.parametrize(
    "code",
    ["CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CP7", "CP8"],
)
def test_complete_boundary_scores_3(code):
    result = score_validated_indicator(state(code))
    assert result.status == "scored"
    assert result.score == 3


def test_blocked_never_scores():
    components = dict(BASE["CP1"])
    components.pop("central_problem_identification")

    blocked = ValidatedIndicatorState(
        code="CP1",
        status="blocked",
        components=components,
        blocked_components=("central_problem_identification",),
        supported_evidence_indices=(),
        blocked_evidence_indices=(),
    )

    result = score_validated_indicator(blocked)

    assert result.status == "blocked"
    assert result.score is None


@pytest.mark.parametrize(
    "code,changes",
    [
        (
            "CP3",
            {
                "structural_complexity_requires_organization": False,
                "serious_emotional_complexity_requires_organization": False,
            },
        ),
        (
            "CP6",
            {
                "example_or_analogy_needed": False,
                "example_or_analogy_used": False,
            },
        ),
        (
            "CP8",
            {
                "explanation_complex_enough_for_verification": False,
            },
        ),
    ],
)
def test_condition_absent_is_na(code, changes):
    result = score_validated_indicator(
        state(code, **changes)
    )

    assert result.status == "not_applicable"
    assert result.score is None


@pytest.mark.parametrize(
    "code",
    ["CP1", "CP2", "CP4", "CP5", "CP7"],
)
def test_missing_response_general_is_outside_scale(code):
    result = score_validated_indicator(
        state(code),
        evaluable_response_present=False,
    )

    assert result.status == "insufficient_evidence"
    assert result.score is None


@pytest.mark.parametrize(
    "code,changes,expected",
    [
        ("CP1", {"central_problem_identification": "none"}, 0),
        ("CP1", {"central_problem_identification": "minimal"}, 1),
        ("CP1", {"central_problem_identification": "adequate"}, 2),

        ("CP2", {
            "explanation_present": False,
            "explanatory_function": "none",
        }, 0),
        ("CP2", {"explanatory_function": "minimal"}, 1),
        ("CP2", {
            "case_adjustment": "adequate",
            "concrete_secondary_limitation": True,
        }, 2),

        ("CP3", {
            "organization_present": False,
            "organization_quality": "none",
        }, 0),
        ("CP3", {"organization_quality": "minimal"}, 1),
        ("CP3", {"organization_quality": "adequate"}, 2),

        ("CP4", {
            "relationship_explanation_present": False,
            "relationship_explanation_quality": "none",
        }, 0),
        ("CP4", {"relationship_explanation_quality": "minimal"}, 1),
        ("CP4", {"relationship_explanation_quality": "adequate"}, 2),

        ("CP5", {
            "psychological_information_present": True,
            "unsupported_psychological_claim_as_fact": True,
            "knowledge_support": "complete",
        }, 0),
        ("CP5", {
            "psychological_information_present": True,
            "knowledge_support": "minimal",
        }, 1),
        ("CP5", {
            "psychological_information_present": True,
            "knowledge_support": "adequate",
        }, 2),

        ("CP6", {
            "example_or_analogy_used": False,
            "pertinence": "none",
            "clarification_value": "none",
        }, 0),
        ("CP6", {
            "pertinence": "minimal",
            "clarification_value": "minimal",
        }, 1),
        ("CP6", {
            "pertinence": "adequate",
            "clarification_value": "adequate",
        }, 2),

        ("CP7", {"accessibility": "none", 
            "unnecessary_jargon_present": True,
        }, 0),
        ("CP7", {
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "minimal",
        }, 1),
        ("CP7", {
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "adequate",
        }, 2),

        ("CP8", {
            "direct_understanding_check_present": False,
            "correction_invitation_present": False,
            "generic_offer_for_more_explanation_only": False,
            "verification_quality": "none",
        }, 0),
        ("CP8", {
            "direct_understanding_check_present": False,
            "correction_invitation_present": False,
            "generic_offer_for_more_explanation_only": True,
            "verification_quality": "minimal",
        }, 1),
        ("CP8", {
            "verification_quality": "adequate",
        }, 2),
    ],
)
def test_boundaries_0_1_2(code, changes, expected):
    result = score_validated_indicator(
        state(code, **changes)
    )

    assert result.status == "scored"
    assert result.score == expected


@pytest.mark.parametrize(
    "field",
    [
        "unsupported_psychological_claim_as_fact",
        "speculation_presented_as_fact",
        "diagnosis_presented_as_fact",
    ],
)
def test_cp5_prohibited_behavior_is_zero(field):
    result = score_validated_indicator(
        state(
            "CP5",
            psychological_information_present=True,
            knowledge_support="complete",
            **{field: True},
        )
    )
    assert result.score == 0


def test_cp6_voluntary_example_without_need_is_not_applicable():
    result = score_validated_indicator(
        state(
            "CP6",
            example_or_analogy_needed=False,
            example_or_analogy_used=True,
            pertinence="complete",
            clarification_value="complete",
            distortion_present=False,
            trivialization_present=False,
            concrete_secondary_limitation=False,
        )
    )

    assert result.status == "not_applicable"
    assert result.score is None



def test_non_scored_cannot_have_numeric_score():
    with pytest.raises(ValueError):
        CPIndicatorScore(
            code="CP3",
            status="not_applicable",
            score=0,
            reason="invalid",
        )



# ============================================================
# FRONTERAS NORMATIVAS ANTI-SOBREEXIGENCIA
# ============================================================

def test_cp1_secondary_concerns_are_not_independent_requirement_for_3():
    result = score_validated_indicator(
        state(
            "CP1",
            central_problem_identification="complete",
            secondary_concerns_present=True,
            secondary_concerns_coverage="minimal",
            substitution_or_unfounded_problem=False,
            concrete_secondary_limitation=False,
        )
    )

    assert result.status == "scored"
    assert result.score == 3


def test_cp1_real_secondary_limitation_still_caps_at_2():
    result = score_validated_indicator(
        state(
            "CP1",
            central_problem_identification="complete",
            secondary_concerns_present=True,
            secondary_concerns_coverage="minimal",
            concrete_secondary_limitation=True,
        )
    )

    assert result.status == "scored"
    assert result.score == 2


def test_cp2_case_adjustment_alone_is_not_extra_requirement_for_3():
    result = score_validated_indicator(
        state(
            "CP2",
            explanation_present=True,
            explanatory_function="complete",
            clarity_comprehensibility="complete",
            case_adjustment="adequate",
            concrete_secondary_limitation=False,
        )
    )

    assert result.status == "scored"
    assert result.score == 3


def test_cp2_concrete_adjustment_limitation_still_caps_at_2():
    result = score_validated_indicator(
        state(
            "CP2",
            explanation_present=True,
            explanatory_function="complete",
            clarity_comprehensibility="complete",
            case_adjustment="adequate",
            concrete_secondary_limitation=True,
        )
    )

    assert result.status == "scored"
    assert result.score == 2



def test_cp7_jargon_accesibilidad_none_score_0():
    result = score_validated_indicator(
        state(
            "CP7",
            unnecessary_jargon_present=True,
            accessibility="none",
        )
    )
    assert result.status == "scored"
    assert result.score == 0


def test_cp7_jargon_accesibilidad_minimal_score_1():
    result = score_validated_indicator(
        state(
            "CP7",
            unnecessary_jargon_present=True,
            accessibility="minimal",
        )
    )
    assert result.status == "scored"
    assert result.score == 1


def test_cp7_jargon_accesibilidad_adequate_score_2():
    result = score_validated_indicator(
        state(
            "CP7",
            unnecessary_jargon_present=True,
            accessibility="adequate",
        )
    )
    assert result.status == "scored"
    assert result.score == 2


def test_cp7_sin_jargon_ni_terminos_score_3():
    result = score_validated_indicator(
        state(
            "CP7",
            unnecessary_jargon_present=False,
            indispensable_technical_terms_present=False,
            accessibility="complete",
        )
    )
    assert result.status == "scored"
    assert result.score == 3
