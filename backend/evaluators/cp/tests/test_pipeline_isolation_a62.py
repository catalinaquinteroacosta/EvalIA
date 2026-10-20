from unittest.mock import patch

from backend.evaluators.cp.pipeline import (
    CP_CODES,
    run_cp_pipeline,
)
from backend.evaluators.cp.scoring import CPIndicatorScore
from backend.evaluators.cp.tests.test_pipeline import (
    family,
    score_for,
)


def test_reconciliation_exception_does_not_abort_family():
    initial = family(blocked_codes={"CP2"})

    def reconcile_failure(**kwargs):
        raise RuntimeError("fallo simulado de reconciliacion")

    def scoring(current_state, **kwargs):
        if current_state.status == "blocked":
            return score_for("CP2", status="blocked")
        return score_for(current_state.code.upper())

    with (
        patch(
            "backend.evaluators.cp.pipeline.extract_cp_family",
            return_value={},
        ),
        patch(
            "backend.evaluators.cp.pipeline.verify_cp_family",
            return_value={},
        ),
        patch(
            "backend.evaluators.cp.pipeline.build_validated_cp_family_state",
            return_value=initial,
        ),
        patch(
            "backend.evaluators.cp.pipeline.reconcile_blocked_indicator",
            side_effect=reconcile_failure,
        ),
        patch(
            "backend.evaluators.cp.pipeline.score_validated_indicator",
            side_effect=scoring,
        ),
    ):
        result = run_cp_pipeline(
            user_text="usuario",
            response_text="respuesta",
        )

    assert len(result.scores) == 8
    assert result.scores["CP2"].score is None
    assert result.final_states["CP2"].status == "blocked"
    assert result.scores["CP1"].score == 3
    assert "CP2" in result.technical_errors


def test_scoring_exception_does_not_abort_family():
    initial = family()

    def scoring(current_state, **kwargs):
        code = current_state.code.upper()
        if code == "CP4":
            raise ValueError("fallo simulado de scoring")
        return score_for(code)

    with (
        patch(
            "backend.evaluators.cp.pipeline.extract_cp_family",
            return_value={},
        ),
        patch(
            "backend.evaluators.cp.pipeline.verify_cp_family",
            return_value={},
        ),
        patch(
            "backend.evaluators.cp.pipeline.build_validated_cp_family_state",
            return_value=initial,
        ),
        patch(
            "backend.evaluators.cp.pipeline.score_validated_indicator",
            side_effect=scoring,
        ),
    ):
        result = run_cp_pipeline(
            user_text="usuario",
            response_text="respuesta",
        )

    assert len(result.scores) == len(CP_CODES)
    assert result.scores["CP4"].score is None
    assert result.scores["CP4"].status == "technical_error"
    assert result.scores["CP5"].score == 3
    assert "CP4" in result.technical_errors



def test_technical_error_is_distinct_from_missing_evidence():
    result = CPIndicatorScore(
        code="CP4",
        status="technical_error",
        score=None,
        reason="Fallo t?cnico simulado.",
    )

    assert result.status == "technical_error"
    assert result.score is None


def test_technical_error_cannot_have_numeric_score():
    import pytest

    with pytest.raises(ValueError):
        CPIndicatorScore(
            code="CP4",
            status="technical_error",
            score=0,
            reason="No debe aceptarse.",
        )


def test_unknown_score_status_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        CPIndicatorScore(
            code="CP4",
            status="unknown_status",
            score=None,
            reason="Estado inv?lido.",
        )
