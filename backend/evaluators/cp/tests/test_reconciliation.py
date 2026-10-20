from unittest.mock import patch

import pytest

from backend.evaluators.cp.reconciliation import (
    apply_reconciliation,
    build_reconciliation_schema,
    reconcile_blocked_indicator,
    validate_reconciliation_result,
)
from backend.evaluators.cp.context import CPEvaluationContext
from backend.evaluators.cp.validated_state import (
    ValidatedIndicatorState,
)


def blocked_cp1():
    return ValidatedIndicatorState(
        code="cp1",
        status="blocked",
        components={
            "secondary_concerns_present": False,
            "secondary_concerns_coverage": "complete",
            "substitution_or_unfounded_problem": False,
            "concrete_secondary_limitation": False,
        },
        blocked_components=(
            "central_problem_identification",
        ),
        supported_evidence_indices=(1,),
        blocked_evidence_indices=(0,),
    )


def draft():
    return {
        "analysis_complete": True,
        "cp1": {
            "analysis_complete": True,
            "full_response_audited": True,
            "central_problem_identification": "complete",
            "secondary_concerns_present": False,
            "secondary_concerns_coverage": "complete",
            "substitution_or_unfounded_problem": False,
            "concrete_secondary_limitation": False,
            "evidence": [
                {
                    "field": "central_problem_identification",
                    "source": "response",
                    "history_index": None,
                    "quote": (
                        "Tu preocupaci?n central parece ser que los "
                        "pensamientos sobre el trabajo est?n "
                        "interfiriendo con tu sue?o."
                    ),
                    "interpretation": (
                        "Identifica expl?citamente el problema central."
                    ),
                }
            ],
            "limitation_description": "",
        },
    }


def verification():
    return {
        "cp1": {
            "component_verdicts": [
                {
                    "field": "central_problem_identification",
                    "status": "ambiguous",
                    "reason": "Lectura disputada.",
                }
            ],
            "evidence_verdicts": [
                {
                    "evidence_index": 0,
                    "status": "ambiguous",
                    "reason": "Soporte discutible.",
                }
            ],
        }
    }


def context():
    return CPEvaluationContext(
        prior_history=(),
        current_user_message=(
            "Me preocupa no poder dormir por pensar en el trabajo."
        ),
        current_response=(
            "Tu preocupaci?n central parece ser que los "
            "pensamientos sobre el trabajo est?n interfiriendo "
            "con tu sue?o."
        ),
    )


def resolved_raw():
    return {
        "analysis_complete": True,
        "component_resolutions": [
            {
                "field": "central_problem_identification",
                "resolution": "resolved",
                "value_json": '"complete"',
                "reason": "El problema central est? expl?cito.",
                "evidence": [
                    {
                        "source": "response",
                        "history_index": None,
                        "quote": (
                            "Tu preocupaci?n central parece ser que "
                            "los pensamientos sobre el trabajo est?n "
                            "interfiriendo con tu sue?o."
                        ),
                        "interpretation": (
                            "Identifica expl?citamente el problema central."
                        ),
                    }
                ],
            }
        ],
        "evidence_resolutions": [
            {
                "evidence_index": 0,
                "resolution": "supported",
                "reason": "La cita respalda la interpretaci?n.",
            }
        ],
    }


def unresolved_raw():
    return {
        "analysis_complete": True,
        "component_resolutions": [
            {
                "field": "central_problem_identification",
                "resolution": "unresolved",
                "value_json": "null",
                "reason": "Persisten dos lecturas razonables.",
                "evidence": [],
            }
        ],
        "evidence_resolutions": [
            {
                "evidence_index": 0,
                "resolution": "unresolved",
                "reason": "El soporte sigue siendo ambiguo.",
            }
        ],
    }


def test_schema_requires_blocked_material():
    with pytest.raises(ValueError):
        build_reconciliation_schema((), ())


def test_resolved_reconciliation_unblocks_indicator():
    raw = resolved_raw()

    validate_reconciliation_result(
        raw,
        state=blocked_cp1(),
        draft=draft(),
        context=context(),
    )

    result = apply_reconciliation(
        state=blocked_cp1(),
        draft=draft(),
        reconciliation=raw,
    )

    assert result.status == "resolved"
    assert result.resolved_state.status == "validated"
    assert (
        result.resolved_state.components[
            "central_problem_identification"
        ]
        == "complete"
    )
    assert result.resolved_state.blocked_components == ()
    assert result.resolved_state.blocked_evidence_indices == ()


def test_unresolved_remains_blocked():
    raw = unresolved_raw()

    validate_reconciliation_result(
        raw,
        state=blocked_cp1(),
        draft=draft(),
        context=context(),
    )

    result = apply_reconciliation(
        state=blocked_cp1(),
        draft=draft(),
        reconciliation=raw,
    )

    assert result.status == "unresolved"
    assert result.resolved_state.status == "blocked"
    assert result.resolved_state.blocked_components == (
        "central_problem_identification",
    )
    assert result.resolved_state.blocked_evidence_indices == (0,)


def test_cannot_modify_nonblocked_component():
    raw = resolved_raw()
    raw["component_resolutions"][0]["field"] = (
        "secondary_concerns_present"
    )

    with pytest.raises(ValueError):
        validate_reconciliation_result(
            raw,
            state=blocked_cp1(),
            draft=draft(),
            context=context(),
        )


def test_unresolved_cannot_transport_value():
    raw = unresolved_raw()
    raw["component_resolutions"][0]["value_json"] = (
        '"complete"'
    )

    with pytest.raises(ValueError):
        validate_reconciliation_result(
            raw,
            state=blocked_cp1(),
            draft=draft(),
            context=context(),
        )


def test_resolved_requires_literal_quote():
    raw = resolved_raw()
    raw["component_resolutions"][0]["evidence"][0][
        "quote"
    ] = "Cita inventada que no existe."

    with pytest.raises(ValueError):
        validate_reconciliation_result(
            raw,
            state=blocked_cp1(),
            draft=draft(),
            context=context(),
        )


def test_nonblocked_state_does_not_call_semantic_provider():
    state = ValidatedIndicatorState(
        code="cp1",
        status="validated",
        components={
            "central_problem_identification": "complete",
            "secondary_concerns_present": False,
            "secondary_concerns_coverage": "complete",
            "substitution_or_unfounded_problem": False,
            "concrete_secondary_limitation": False,
        },
        blocked_components=(),
        supported_evidence_indices=(),
        blocked_evidence_indices=(),
    )

    with patch(
        "backend.evaluators.cp.reconciliation."
        "run_structured_semantic"
    ) as mocked:
        result = reconcile_blocked_indicator(
            state=state,
            draft={},
            verification={},
            user_text="usuario",
            response_text="respuesta",
        )

    mocked.assert_not_called()
    assert result.status == "resolved"
    assert result.resolved_state is state


def test_reconcile_uses_cache_and_semantic_operation():
    raw = resolved_raw()

    with (
        patch(
            "backend.evaluators.cp.reconciliation."
            "get_semantic_identity",
            return_value={
                "provider": "openai",
                "model": "test-model",
            },
        ),
        patch(
            "backend.evaluators.cp.reconciliation."
            "cached_semantic_operation",
        ) as cached,
    ):
        cached.side_effect = lambda **kwargs: kwargs[
            "validate_result"
        ](raw)

        result = reconcile_blocked_indicator(
            state=blocked_cp1(),
            draft=draft(),
            verification=verification(),
            user_text=context().current_user_message,
            response_text=context().current_response,
        )

    assert cached.call_count == 1
    assert result.status == "resolved"

    kwargs = cached.call_args.kwargs

    assert kwargs["extractor"] == (
        "cp_blocked_semantic_reconciler"
    )
    assert kwargs["extractor_version"] == "CP-RECON-1.0.0"


def test_only_blocked_component_is_sent_for_reconciliation():
    raw = resolved_raw()

    with (
        patch(
            "backend.evaluators.cp.reconciliation."
            "get_semantic_identity",
            return_value={
                "provider": "openai",
                "model": "test-model",
            },
        ),
        patch(
            "backend.evaluators.cp.reconciliation."
            "cached_semantic_operation",
        ) as cached,
    ):
        cached.side_effect = lambda **kwargs: kwargs[
            "validate_result"
        ](raw)

        reconcile_blocked_indicator(
            state=blocked_cp1(),
            draft=draft(),
            verification=verification(),
            user_text=context().current_user_message,
            response_text=context().current_response,
        )

    inputs = cached.call_args.kwargs["inputs"]

    assert inputs["blocked_components"] == [
        "central_problem_identification"
    ]


def test_fail_closed_if_not_all_blocked_components_returned():
    raw = resolved_raw()
    raw["component_resolutions"] = []

    with pytest.raises(ValueError):
        validate_reconciliation_result(
            raw,
            state=blocked_cp1(),
            draft=draft(),
            context=context(),
        )



def test_blocked_evidence_supported_revalidates_original_literal_quote():
    raw = resolved_raw()
    altered_draft = draft()

    altered_draft["cp1"]["evidence"][0]["quote"] = (
        "Esta cita original fue inventada."
    )

    with pytest.raises(ValueError):
        validate_reconciliation_result(
            raw,
            state=blocked_cp1(),
            draft=altered_draft,
            context=context(),
        )


def test_blocked_evidence_index_must_exist_in_original_draft():
    state = ValidatedIndicatorState(
        code="cp1",
        status="blocked",
        components={
            "central_problem_identification": "complete",
            "secondary_concerns_present": False,
            "secondary_concerns_coverage": "complete",
            "substitution_or_unfounded_problem": False,
            "concrete_secondary_limitation": False,
        },
        blocked_components=(),
        supported_evidence_indices=(),
        blocked_evidence_indices=(99,),
    )

    raw = {
        "analysis_complete": True,
        "component_resolutions": [],
        "evidence_resolutions": [
            {
                "evidence_index": 99,
                "resolution": "supported",
                "reason": "Intento de resolver ?ndice inexistente.",
            }
        ],
    }

    with pytest.raises(ValueError):
        validate_reconciliation_result(
            raw,
            state=state,
            draft=draft(),
            context=context(),
        )


def test_unresolved_blocked_evidence_does_not_fake_support():
    state = ValidatedIndicatorState(
        code="cp1",
        status="blocked",
        components={
            "central_problem_identification": "complete",
            "secondary_concerns_present": False,
            "secondary_concerns_coverage": "complete",
            "substitution_or_unfounded_problem": False,
            "concrete_secondary_limitation": False,
        },
        blocked_components=(),
        supported_evidence_indices=(),
        blocked_evidence_indices=(0,),
    )

    raw = {
        "analysis_complete": True,
        "component_resolutions": [],
        "evidence_resolutions": [
            {
                "evidence_index": 0,
                "resolution": "unresolved",
                "reason": "El soporte sem?ntico sigue sin resolverse.",
            }
        ],
    }

    validate_reconciliation_result(
        raw,
        state=state,
        draft=draft(),
        context=context(),
    )

    result = apply_reconciliation(
        state=state,
        draft=draft(),
        reconciliation=raw,
    )

    assert result.status == "unresolved"
    assert result.resolved_state.status == "blocked"
    assert result.resolved_state.blocked_evidence_indices == (0,)
