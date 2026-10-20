from copy import deepcopy

import pytest

from backend.evaluators.cp.context import (
    CPEvaluationContext,
    PriorTurn,
)
from backend.evaluators.cp.evidence import (
    evidence_haystack,
    require_literal_evidence,
    verify_literal_evidence,
)
from backend.evaluators.cp.schemas import (
    SemanticEvidence,
)
from backend.evaluators.cp.verifier import (
    VERIFIER_VERSION,
    build_cp_verifier_prompt,
    family_verification_readiness,
    indicator_verification_ready,
    validate_cp_family_verification,
)


def make_indicator(**components):
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        **components,
        "concrete_secondary_limitation": False,
        "limitation_description": "",
        "evidence": [],
    }


def make_draft():
    return {
        "analysis_complete": True,

        "cp1": make_indicator(
            central_problem_identification="complete",
            secondary_concerns_present=False,
            secondary_concerns_coverage="complete",
            substitution_or_unfounded_problem=False,
        ),

        "cp2": make_indicator(
            explanation_present=True,
            explanatory_function="complete",
            clarity_comprehensibility="complete",
            case_adjustment="complete",
        ),

        "cp3": make_indicator(
            structural_complexity_requires_organization=False,
            serious_emotional_complexity_requires_organization=False,
            organization_present=False,
            organization_quality="none",
        ),

        "cp4": make_indicator(
            relationship_explanation_present=True,
            relationship_correctness="complete",
            relationship_relevance="complete",
            relationship_explanation_quality="complete",
            materially_incorrect_relationship=False,
        ),

        "cp5": make_indicator(
            psychological_information_present=True,
            unsupported_psychological_claim_as_fact=False,
            speculation_presented_as_fact=False,
            diagnosis_presented_as_fact=False,
            responsible_diagnostic_possibility_present=False,
            uncertainty_handling="complete",
            knowledge_support="complete",
        ),

        "cp6": make_indicator(
            example_or_analogy_needed=False,
            example_or_analogy_used=False,
            pertinence="none",
            clarification_value="none",
            distortion_present=False,
            trivialization_present=False,
        ),

        "cp7": make_indicator(
            unnecessary_jargon_present=False,
            indispensable_technical_terms_present=False,
            indispensable_terms_explanation="complete",
            accessibility="complete",
        ),

        "cp8": make_indicator(
            explanation_complex_enough_for_verification=False,
            direct_understanding_check_present=False,
            correction_invitation_present=False,
            generic_offer_for_more_explanation_only=False,
            verification_quality="none",
        ),
    }


def make_verification(draft):
    result = {
        "analysis_complete": True,
    }

    meta = {
        "analysis_complete",
        "full_response_audited",
        "evidence",
        "limitation_description",
    }

    for i in range(1, 9):
        code = f"cp{i}"
        source = draft[code]

        fields = [
            field
            for field in source
            if field not in meta
        ]

        result[code] = {
            "analysis_complete": True,
            "full_context_audited": True,

            "component_verdicts": [
                {
                    "field": field,
                    "status": "supported",
                    "reason": (
                        "Auditoría independiente suficiente."
                    ),
                }
                for field in fields
            ],

            "evidence_verdicts": [
                {
                    "evidence_index": index,
                    "status": "supported",
                    "reason": (
                        "La cita respalda la interpretación."
                    ),
                }
                for index, _ in enumerate(
                    source["evidence"]
                )
            ],
        }

    return result


def make_context():
    return CPEvaluationContext(
        prior_history=(
            PriorTurn(
                role="user",
                text="Me cuesta dormir desde hace días.",
            ),
            PriorTurn(
                role="assistant",
                text="Cuéntame qué ocurre antes de dormir.",
            ),
        ),
        current_user_message=(
            "Cuando me acuesto pienso en el trabajo."
        ),
        current_response=(
            "Esos pensamientos pueden mantenerte en alerta."
        ),
    )


def test_history_message_is_individual():
    ctx = make_context()

    assert evidence_haystack(
        context=ctx,
        source="history",
        history_index=1,
    ) == "Cuéntame qué ocurre antes de dormir."


def test_wrong_history_index_fails_literal_support():
    ctx = make_context()

    assert verify_literal_evidence(
        context=ctx,
        source="history",
        history_index=0,
        quote="Cuéntame qué ocurre antes de dormir.",
    ) is False


def test_history_requires_index():
    with pytest.raises(ValueError):
        evidence_haystack(
            context=make_context(),
            source="history",
            history_index=None,
        )


def test_current_sources_reject_history_index():
    with pytest.raises(ValueError):
        evidence_haystack(
            context=make_context(),
            source="user",
            history_index=0,
        )


def test_literal_gate_fails_closed():
    with pytest.raises(ValueError):
        require_literal_evidence(
            context=make_context(),
            source="response",
            history_index=None,
            quote="ESTO NO EXISTE",
        )


def test_semantic_evidence_history_contract():
    evidence = SemanticEvidence(
        source="history",
        quote="texto",
        interpretation="interpretación",
        history_index=0,
    )

    assert evidence.history_index == 0


def test_semantic_evidence_history_requires_index():
    with pytest.raises(ValueError):
        SemanticEvidence(
            source="history",
            quote="texto",
            interpretation="interpretación",
        )


def test_semantic_evidence_current_user_rejects_index():
    with pytest.raises(ValueError):
        SemanticEvidence(
            source="user",
            quote="texto",
            interpretation="interpretación",
            history_index=0,
        )


def test_verifier_version():
    assert VERIFIER_VERSION == "CP-VERIFY-1.1.0"


def test_prompt_marks_extractor_as_hypothesis():
    prompt = build_cp_verifier_prompt(
        draft=make_draft(),
        context=make_context(),
    )

    assert "HIPÓTESIS" in prompt
    assert "EXTRACTOR_DRAFT_UNVERIFIED" in prompt


def test_prompt_forbids_scoring():
    prompt = build_cp_verifier_prompt(
        draft=make_draft(),
        context=make_context(),
    )

    assert "NO asignes puntuaciones 0, 1, 2 o 3" in prompt
    assert "NO decidas N/A" in prompt


def test_prompt_contains_temporal_context():
    prompt = build_cp_verifier_prompt(
        draft=make_draft(),
        context=make_context(),
    )

    assert "[HISTORY_INDEX=0 | ROLE=user]" in prompt
    assert "[HISTORY_INDEX=1 | ROLE=assistant]" in prompt
    assert "CURRENT_USER" in prompt
    assert "CURRENT_RESPONSE" in prompt
    assert "No existe FUTURE_HISTORY" in prompt


def test_history_is_not_mandatory():
    prompt = build_cp_verifier_prompt(
        draft=make_draft(),
        context=make_context(),
    )

    assert (
        "Disponibilidad del historial NO implica "
        "obligación de usarlo."
    ) in prompt


def test_complete_verification_validates():
    draft = make_draft()
    result = make_verification(draft)

    assert validate_cp_family_verification(
        result,
        draft=draft,
    ) is result


def test_missing_component_is_rejected():
    draft = make_draft()
    result = make_verification(draft)

    result["cp2"]["component_verdicts"].pop()

    with pytest.raises(ValueError):
        validate_cp_family_verification(
            result,
            draft=draft,
        )


def test_extra_component_is_rejected():
    draft = make_draft()
    result = make_verification(draft)

    result["cp3"]["component_verdicts"].append({
        "field": "invented_field",
        "status": "supported",
        "reason": "No corresponde.",
    })

    with pytest.raises(ValueError):
        validate_cp_family_verification(
            result,
            draft=draft,
        )


def test_duplicate_component_is_rejected():
    draft = make_draft()
    result = make_verification(draft)

    result["cp1"]["component_verdicts"].append(
        deepcopy(
            result["cp1"]["component_verdicts"][0]
        )
    )

    with pytest.raises(ValueError):
        validate_cp_family_verification(
            result,
            draft=draft,
        )


def test_ambiguous_is_valid_but_not_ready():
    draft = make_draft()
    result = make_verification(draft)

    result["cp4"][
        "component_verdicts"
    ][0]["status"] = "ambiguous"

    validate_cp_family_verification(
        result,
        draft=draft,
    )

    assert not indicator_verification_ready(
        result,
        "CP4",
    )


def test_unsupported_is_valid_but_not_ready():
    draft = make_draft()
    result = make_verification(draft)

    result["cp5"][
        "component_verdicts"
    ][0]["status"] = "unsupported"

    validate_cp_family_verification(
        result,
        draft=draft,
    )

    assert not indicator_verification_ready(
        result,
        "CP5",
    )


def test_failure_in_one_indicator_does_not_block_others():
    draft = make_draft()
    result = make_verification(draft)

    result["cp5"][
        "component_verdicts"
    ][0]["status"] = "unsupported"

    readiness = family_verification_readiness(
        result
    )

    assert readiness["CP5"] is False
    assert readiness["CP1"] is True
    assert readiness["CP2"] is True
    assert readiness["CP3"] is True
    assert readiness["CP4"] is True
    assert readiness["CP6"] is True
    assert readiness["CP7"] is True
    assert readiness["CP8"] is True


def test_exact_evidence_index_coverage():
    draft = make_draft()

    draft["cp1"]["evidence"] = [
        {
            "field": "central_problem_identification",
            "source": "user",
            "history_index": None,
            "quote": (
                "Cuando me acuesto pienso en el trabajo."
            ),
            "interpretation": (
                "El usuario describe pensamientos "
                "al acostarse."
            ),
        }
    ]

    result = make_verification(draft)

    validate_cp_family_verification(
        result,
        draft=draft,
    )

    assert result["cp1"][
        "evidence_verdicts"
    ][0]["evidence_index"] == 0


def test_missing_evidence_index_is_rejected():
    draft = make_draft()

    draft["cp1"]["evidence"] = [
        {
            "field": "central_problem_identification",
            "source": "user",
            "history_index": None,
            "quote": (
                "Cuando me acuesto pienso en el trabajo."
            ),
            "interpretation": "Interpretación.",
        }
    ]

    result = make_verification(draft)

    result["cp1"]["evidence_verdicts"] = []

    with pytest.raises(ValueError):
        validate_cp_family_verification(
            result,
            draft=draft,
        )


def test_all_supported_is_ready():
    draft = make_draft()
    result = make_verification(draft)

    readiness = family_verification_readiness(
        result
    )

    assert all(readiness.values())
