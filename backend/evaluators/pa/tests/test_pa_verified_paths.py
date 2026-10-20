import pytest

from backend.evaluators.pa.contracts import (
    CODES, Finding, Verification
)
from backend.evaluators.pa.scoring import Assessment, decide


def assessment(applicable=True):
    return Assessment(
        applicable=applicable,
        behavior_present=True,
        central_function_met=True,
        contextual_complete=True,
        secondary_defect=False,
        material_contradiction=False,
        reason="Propiedades semanticas verificadas en prueba",
    )


@pytest.mark.parametrize("code", CODES)
def test_complete_component_coverage_can_score(code):
    findings = (
        Finding("action_present", True),
        Finding("contextual_fit", True),
    )
    verification = (
        Verification("applicability", "supported", "Revisada"),
        Verification("action_present", "supported", "Revisada"),
        Verification("contextual_fit", "supported", "Revisada"),
    )
    result = decide(
        code, assessment(), findings, verification
    )
    assert result.score == 3, (code, result.reason)


@pytest.mark.parametrize("code", CODES)
def test_unsupported_component_blocks(code):
    findings = (
        Finding("action_present", True),
        Finding("contextual_fit", True),
    )
    verification = (
        Verification("applicability", "supported", "Revisada"),
        Verification("action_present", "supported", "Revisada"),
        Verification("contextual_fit", "unsupported", "No sustentada"),
    )
    result = decide(
        code, assessment(), findings, verification
    )
    assert result.score == "BLOCKED", code


@pytest.mark.parametrize("code", CODES)
def test_unresolved_applicability_blocks(code):
    verification = (
        Verification("applicability", "supported", "Revisada"),
    )
    result = decide(
        code, assessment(applicable=None),
        verification=verification,
    )
    assert result.score == "BLOCKED", code
