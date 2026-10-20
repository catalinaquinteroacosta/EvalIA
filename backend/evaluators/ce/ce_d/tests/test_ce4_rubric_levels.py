
import pytest

from backend.evaluators.ce.ce_d.ce4_rubric_contract import (
    score_verified_execution,
)
from backend.evaluators.ce.ce_d.ce4_rubric_verification import (
    verify_rubric_execution,
)


LEVELS = [
    ("omitted_or_opposite", 0),
    ("minimal_generic", 1),
    ("adequate_limited", 2),
    ("clear_contextual_verifiable", 3),
]


@pytest.mark.parametrize("execution,expected", LEVELS)
def test_official_levels(execution, expected):
    result = score_verified_execution(
        applicable=True,
        analysis_complete=True,
        semantic_verified=True,
        execution=execution,
    )
    assert result["score"] == expected


@pytest.mark.parametrize("execution,expected", LEVELS)
def test_independent_verifier_supported(execution, expected):
    result = verify_rubric_execution(
        response_text="Respuesta de prueba completa.",
        applicable=True,
        analysis_complete=True,
        execution=execution,
        verify_claim=lambda *_: "supported",
    )
    assert result["score"] == expected


@pytest.mark.parametrize("verdict", ["unsupported", "ambiguous"])
@pytest.mark.parametrize("execution,_", LEVELS)
def test_disagreement_never_scores(execution, _, verdict):
    result = verify_rubric_execution(
        response_text="Respuesta de prueba completa.",
        applicable=True,
        analysis_complete=True,
        execution=execution,
        verify_claim=lambda *_: verdict,
    )
    assert result["score"] is None


def test_not_applicable():
    result = score_verified_execution(
        applicable=False,
        analysis_complete=True,
        semantic_verified=True,
        execution="omitted_or_opposite",
    )
    assert result["status"] == "not_applicable"
    assert result["score"] is None


def test_incomplete_never_scores():
    result = score_verified_execution(
        applicable=True,
        analysis_complete=False,
        semantic_verified=True,
        execution="clear_contextual_verifiable",
    )
    assert result["score"] is None
