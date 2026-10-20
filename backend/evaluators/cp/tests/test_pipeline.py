from unittest.mock import patch

from backend.evaluators.cp.pipeline import (
    CP_CODES,
    CPPipelineResult,
    run_cp_pipeline,
)
from backend.evaluators.cp.reconciliation import (
    ReconciliationResult,
)
from backend.evaluators.cp.scoring import (
    CPIndicatorScore,
)
from backend.evaluators.cp.validated_state import (
    ValidatedCPFamilyState,
    ValidatedIndicatorState,
)


def state(
    code: str,
    *,
    blocked: bool = False,
):
    components = {
        f"value_{code.lower()}": True,
    }

    # Para tests de pipeline no necesitamos contratos CP reales:
    # __new__ evita construir ValidatedIndicatorState con
    # componentes ficticios mediante __init__.
    obj = object.__new__(ValidatedIndicatorState)

    object.__setattr__(obj, "code", code.lower())
    object.__setattr__(
        obj,
        "status",
        "blocked" if blocked else "validated",
    )
    object.__setattr__(
        obj,
        "components",
        components if not blocked else {},
    )
    object.__setattr__(
        obj,
        "blocked_components",
        (f"value_{code.lower()}",) if blocked else (),
    )
    object.__setattr__(
        obj,
        "supported_evidence_indices",
        (),
    )
    object.__setattr__(
        obj,
        "blocked_evidence_indices",
        (),
    )

    return obj


def family(*, blocked_codes=()):
    indicators = {
        code.lower(): state(
            code,
            blocked=code in blocked_codes,
        )
        for code in CP_CODES
    }

    obj = object.__new__(ValidatedCPFamilyState)
    object.__setattr__(
        obj,
        "indicators",
        indicators,
    )

    return obj


def score_for(code, status="scored"):
    if status == "scored":
        return CPIndicatorScore(
            code=code,
            status="scored",
            score=3,
            reason="fixture",
        )

    return CPIndicatorScore(
        code=code,
        status=status,
        score=None,
        reason="fixture",
    )


def reconciliation_for(
    code,
    resolved_state,
):
    return ReconciliationResult(
        code=code,
        status=(
            "resolved"
            if resolved_state.status == "validated"
            else "unresolved"
        ),
        resolved_state=resolved_state,
        resolved_components=(),
        unresolved_components=(
            ()
            if resolved_state.status == "validated"
            else resolved_state.blocked_components
        ),
        resolved_evidence_indices=(),
        unresolved_evidence_indices=(),
    )


def test_pipeline_connects_all_stages():
    initial = family()

    with (
        patch(
            "backend.evaluators.cp.pipeline."
            "extract_cp_family",
            return_value={"draft": True},
        ) as extract,
        patch(
            "backend.evaluators.cp.pipeline."
            "verify_cp_family",
            return_value={"verification": True},
        ) as verify,
        patch(
            "backend.evaluators.cp.pipeline."
            "build_validated_cp_family_state",
            return_value=initial,
        ) as build,
        patch(
            "backend.evaluators.cp.pipeline."
            "reconcile_blocked_indicator",
        ) as reconcile,
        patch(
            "backend.evaluators.cp.pipeline."
            "score_validated_indicator",
            side_effect=lambda state, **kwargs: score_for(
                state.code.upper()
            ),
        ) as score,
    ):
        result = run_cp_pipeline(
            user_text="usuario",
            response_text="respuesta",
        )

    assert extract.call_count == 1
    assert verify.call_count == 1
    assert build.call_count == 1

    # Nada estaba BLOCKED.
    reconcile.assert_not_called()

    # Todos avanzan al scoring individual.
    assert score.call_count == 8

    assert result.blocked_codes == ()
    assert result.reconciled_codes == ()
    assert result.ready_codes == CP_CODES
    assert set(result.scores) == set(CP_CODES)


def test_only_blocked_indicators_are_reconciled():
    initial = family(
        blocked_codes={"CP2", "CP7"},
    )

    resolved_cp2 = state("CP2")
    unresolved_cp7 = state(
        "CP7",
        blocked=True,
    )

    def reconcile_side_effect(*, state, **kwargs):
        code = state.code.upper()

        if code == "CP2":
            return reconciliation_for(
                code,
                resolved_cp2,
            )

        if code == "CP7":
            return reconciliation_for(
                code,
                unresolved_cp7,
            )

        raise AssertionError(
            f"No deb?a reconciliarse {code}"
        )

    def scoring_side_effect(
        current_state,
        **kwargs,
    ):
        code = current_state.code.upper()

        if current_state.status == "blocked":
            return score_for(
                code,
                status="blocked",
            )

        return score_for(code)

    with (
        patch(
            "backend.evaluators.cp.pipeline."
            "extract_cp_family",
            return_value={"draft": True},
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "verify_cp_family",
            return_value={"verification": True},
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "build_validated_cp_family_state",
            return_value=initial,
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "reconcile_blocked_indicator",
            side_effect=reconcile_side_effect,
        ) as reconcile,
        patch(
            "backend.evaluators.cp.pipeline."
            "score_validated_indicator",
            side_effect=scoring_side_effect,
        ),
    ):
        result = run_cp_pipeline(
            user_text="usuario",
            response_text="respuesta",
        )

    assert reconcile.call_count == 2

    reconciled = {
        call.kwargs["state"].code.upper()
        for call in reconcile.call_args_list
    }

    assert reconciled == {"CP2", "CP7"}

    assert result.reconciled_codes == (
        "CP2",
        "CP7",
    )

    assert result.final_states["CP2"].status == (
        "validated"
    )

    assert result.final_states["CP7"].status == (
        "blocked"
    )

    assert result.scores["CP2"].score == 3
    assert result.scores["CP7"].status == "blocked"
    assert result.scores["CP7"].score is None

    # CP7 no bloquea a los otros siete.
    assert len(result.ready_codes) == 7
    assert result.blocked_codes == ("CP7",)


def test_pipeline_preserves_causal_history():
    initial = family()

    from backend.evaluators.cp.context import PriorTurn

    history = (
        PriorTurn(
            role="user",
            text="Mensaje previo.",
        ),
        PriorTurn(
            role="assistant",
            text="Respuesta previa.",
        ),
    )

    with (
        patch(
            "backend.evaluators.cp.pipeline."
            "extract_cp_family",
            return_value={"draft": True},
        ) as extract,
        patch(
            "backend.evaluators.cp.pipeline."
            "verify_cp_family",
            return_value={"verification": True},
        ) as verify,
        patch(
            "backend.evaluators.cp.pipeline."
            "build_validated_cp_family_state",
            return_value=initial,
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "score_validated_indicator",
            side_effect=lambda state, **kwargs: score_for(
                state.code.upper()
            ),
        ),
    ):
        run_cp_pipeline(
            user_text="Mensaje actual.",
            response_text="Respuesta actual.",
            prior_history=history,
        )

    assert (
        extract.call_args.kwargs["prior_history"]
        is history
    )

    assert (
        verify.call_args.kwargs["prior_history"]
        is history
    )


def test_pipeline_propagates_provider_model_and_limits():
    initial = family()

    with (
        patch(
            "backend.evaluators.cp.pipeline."
            "extract_cp_family",
            return_value={"draft": True},
        ) as extract,
        patch(
            "backend.evaluators.cp.pipeline."
            "verify_cp_family",
            return_value={"verification": True},
        ) as verify,
        patch(
            "backend.evaluators.cp.pipeline."
            "build_validated_cp_family_state",
            return_value=initial,
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "score_validated_indicator",
            side_effect=lambda state, **kwargs: score_for(
                state.code.upper()
            ),
        ),
    ):
        run_cp_pipeline(
            user_text="u",
            response_text="r",
            provider="openai",
            model="modelo-prueba",
            timeout=321,
            extraction_max_output_tokens=111,
            verification_max_output_tokens=222,
            reconciliation_max_output_tokens=333,
        )

    assert extract.call_args.kwargs["provider"] == "openai"
    assert extract.call_args.kwargs["model"] == (
        "modelo-prueba"
    )
    assert extract.call_args.kwargs["timeout"] == 321
    assert (
        extract.call_args.kwargs["max_output_tokens"]
        == 111
    )

    assert verify.call_args.kwargs["provider"] == "openai"
    assert verify.call_args.kwargs["model"] == (
        "modelo-prueba"
    )
    assert verify.call_args.kwargs["timeout"] == 321
    assert (
        verify.call_args.kwargs["max_output_tokens"]
        == 222
    )


def test_empty_response_is_forwarded_as_not_evaluable():
    initial = family()

    observed = []

    def scoring_side_effect(
        current_state,
        *,
        evaluable_response_present,
    ):
        observed.append(
            evaluable_response_present
        )

        return score_for(
            current_state.code.upper(),
            status="insufficient_evidence",
        )

    with (
        patch(
            "backend.evaluators.cp.pipeline."
            "extract_cp_family",
            return_value={"draft": True},
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "verify_cp_family",
            return_value={"verification": True},
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "build_validated_cp_family_state",
            return_value=initial,
        ),
        patch(
            "backend.evaluators.cp.pipeline."
            "score_validated_indicator",
            side_effect=scoring_side_effect,
        ),
    ):
        result = run_cp_pipeline(
            user_text="usuario",
            response_text="   ",
        )

    assert observed == [False] * 8

    assert all(
        result.scores[code].status
        == "insufficient_evidence"
        for code in CP_CODES
    )


def test_pipeline_result_requires_all_scores():
    initial = family()

    try:
        CPPipelineResult(
            draft={},
            verification={},
            initial_validated_state=initial,
            final_states={
                code: state(code)
                for code in CP_CODES
            },
            reconciliations={},
            scores={},
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Deb?a rechazar resultado familiar incompleto."
        )
