import pytest

from backend.evaluators.pa.applicability_guard import (
    assess_applicability,
)
from backend.evaluators.pa.scoring_guard import PropertyRecord


def evidence():
    return (
        PropertyRecord(
            "accion especifica", "present", True, True
        ),
    )


@pytest.mark.parametrize("code", ["PA2", "PA3", "PA8"])
def test_conditional_not_applicable(code):
    result = assess_applicability(
        code, False, True, "Condicion ausente"
    )
    assert result.status == "NOT_APPLICABLE"
    assert result.score == "N/A"


@pytest.mark.parametrize(
    "code", ["PA1", "PA4", "PA5", "PA6", "PA7"]
)
def test_general_not_auto_na(code):
    result = assess_applicability(
        code, False, True, "Sin accion"
    )
    assert result.status == "BLOCKED"


def test_applicable_ready_without_score():
    result = assess_applicability(
        "PA1", True, True, "Aplicable", evidence()
    )
    assert result.status == "READY_FOR_RULE_MAPPING"
    assert result.score is None


def test_unverified_applicability_blocks():
    result = assess_applicability(
        "PA2", False, False, "Condicion ausente"
    )
    assert result.status == "BLOCKED"


def test_unresolved_discrepancy_blocks():
    result = assess_applicability(
        "PA7", True, True, "Aplicable",
        evidence(), unresolved_discrepancy=True
    )
    assert result.status == "BLOCKED"
