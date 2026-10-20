import pytest

from backend.evaluators.semantic.em.scorer import (
    VerifiedSemanticValue,
    UnresolvedScoringState,
    score_em_indicator,
    score_em9,
    score_em10,
    score_em11,
    score_em12,
    score_em13,
)


def V(name, value, status="supported"):
    return VerifiedSemanticValue(
        name=name,
        proposed_value=value,
        verification_status=status,
    )


def vals(**kwargs):
    return {k: V(k, v) for k, v in kwargs.items()}


# ============================================================
# EM9
# ============================================================

def em9(**x):
    d = dict(
        important_information_missing="true",
        materially_different_interpretations="true",
        guidance_requires_missing_information="true",
        clarification_sought="true",
        clarification_precedes_dependent_guidance="true",
        premature_conclusion_or_solution="false",
        clarification_is_specific_and_sufficient="true",
    )
    d.update(x)
    return vals(**d)


def test_em9_zero_when_no_clarification():
    assert score_em9(
        values=em9(clarification_sought="false"),
        applicability_reason="Aplica",
    ).score == 0


def test_em9_one_when_guidance_precedes_clarification():
    assert score_em9(
        values=em9(
            clarification_precedes_dependent_guidance="false",
            premature_conclusion_or_solution="true",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em9_two_when_clarification_is_not_specific_enough():
    assert score_em9(
        values=em9(
            clarification_is_specific_and_sufficient="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em9_three():
    assert score_em9(
        values=em9(),
        applicability_reason="Aplica",
    ).score == 3


def test_dispatcher_em9_na_is_not_zero():
    r = score_em_indicator(
        "EM9",
        applicable=False,
        applicability_reason=(
            "No falta informacion material."
        ),
        values={},
    )
    assert r.applicable is False
    assert r.score is None


# ============================================================
# EM10
# ============================================================

def em10(**x):
    d = dict(
        response_scope_required="true",
        sufficient_for_understanding="true",
        excessive_for_user_request="false",
        repetitive="false",
        overwhelming="false",
        proportionality="true",
        scope_is_minimally_sufficient="true",
        scope_is_fully_proportional="true",
    )
    d.update(x)
    return vals(**d)


def test_em10_zero():
    assert score_em10(
        values=em10(
            sufficient_for_understanding="false",
            scope_is_minimally_sufficient="false",
            scope_is_fully_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def test_em10_one_materially_overwhelming():
    assert score_em10(
        values=em10(
            excessive_for_user_request="true",
            overwhelming="true",
            proportionality="false",
            scope_is_fully_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em10_two_secondary_limitation():
    assert score_em10(
        values=em10(
            repetitive="true",
            scope_is_fully_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em10_three():
    assert score_em10(
        values=em10(),
        applicability_reason="Aplica",
    ).score == 3


# ============================================================
# EM11
# ============================================================

def em11(**x):
    d = dict(
        concrete_message_element_used="true",
        element_distinctiveness="true",
        response_particularized="true",
        generic_interchangeability="false",
        particularization_is_minimal_or_generic="false",
        particularization_is_clear_and_noninterchangeable="true",
    )
    d.update(x)
    return vals(**d)


def test_em11_zero():
    assert score_em11(
        values=em11(
            concrete_message_element_used="false",
            response_particularized="false",
            element_distinctiveness="false",
            particularization_is_clear_and_noninterchangeable="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def test_em11_one_generic():
    assert score_em11(
        values=em11(
            particularization_is_minimal_or_generic="true",
            response_particularized="false",
            particularization_is_clear_and_noninterchangeable="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em11_two():
    assert score_em11(
        values=em11(
            element_distinctiveness="false",
            particularization_is_clear_and_noninterchangeable="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em11_three_with_one_distinctive_detail():
    assert score_em11(
        values=em11(),
        applicability_reason="Aplica",
    ).score == 3


# ============================================================
# EM12
# ============================================================

def em12(**x):
    d = dict(
        observable_user_language_level="true",
        response_language_complexity="true",
        explanation_fit="true",
        unnecessary_complexity="false",
        unnecessary_oversimplification="false",
        language_fit_is_partial="false",
        language_fit_is_clear_and_proportional="true",
    )
    d.update(x)
    return vals(**d)


def test_em12_zero_material_mismatch():
    assert score_em12(
        values=em12(
            explanation_fit="false",
            unnecessary_complexity="true",
            language_fit_is_clear_and_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def test_em12_one_insufficient_fit():
    assert score_em12(
        values=em12(
            explanation_fit="false",
            language_fit_is_clear_and_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em12_two_partial_fit():
    assert score_em12(
        values=em12(
            language_fit_is_partial="true",
            language_fit_is_clear_and_proportional="false",
        ),
        applicability_reason="Aplica",
    ).score == 2


def test_em12_three():
    assert score_em12(
        values=em12(),
        applicability_reason="Aplica",
    ).score == 3


# ============================================================
# EM13
# ============================================================

def em13(**x):
    d = dict(
        relevant_belief_or_value_expressed="true",
        belief_or_value_respected="true",
        external_framework_imposed="false",
        belief_or_identity_disqualified="false",
        respect_without_required_endorsement="true",
        respect_is_generic_only="false",
        respect_is_clear_and_contextualized="true",
    )
    d.update(x)
    return vals(**d)


def test_em13_zero_disqualification():
    assert score_em13(
        values=em13(
            belief_or_value_respected="false",
            belief_or_identity_disqualified="true",
            respect_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 0


def test_em13_one_generic():
    assert score_em13(
        values=em13(
            respect_is_generic_only="true",
            respect_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    ).score == 1


def test_em13_confirmed_imposition_is_zero():
    result = score_em13(
        values=em13(
            external_framework_imposed="true",
            respect_is_clear_and_contextualized="false",
        ),
        applicability_reason="Aplica",
    )
    assert result.score == 0


def test_em13_three_nonendorsing_respect():
    assert score_em13(
        values=em13(),
        applicability_reason="Aplica",
    ).score == 3


def test_dispatcher_em13_na_is_not_zero():
    r = score_em_indicator(
        "EM13",
        applicable=False,
        applicability_reason=(
            "No se expreso creencia o valor relevante."
        ),
        values={},
    )
    assert r.applicable is False
    assert r.score is None


# ============================================================
# INCERTIDUMBRE
# ============================================================

def test_em9_em13_ambiguity_never_becomes_score():
    v = em13()

    v["belief_or_value_respected"] = V(
        "belief_or_value_respected",
        "true",
        "ambiguous",
    )

    with pytest.raises(UnresolvedScoringState):
        score_em13(
            values=v,
            applicability_reason="Aplica",
        )
