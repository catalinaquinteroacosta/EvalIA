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
        reason="Caso controlado de prueba",
    )


@pytest.mark.parametrize("code", CODES)
def test_generic_verification_cannot_authorize_full_score(code):
    result = decide(
        code,
        assessment(),
        findings=(
            Finding(component="action_present", value=True),
            Finding(component="contextual_fit", value=True),
        ),
        verification=(
            Verification(
                component="semantic_support",
                status="supported",
                reason="Verificacion generica",
            ),
        ),
    )
    assert result.score == "BLOCKED", code


@pytest.mark.parametrize("code", CODES)
def test_missing_component_verification_blocks(code):
    result = decide(
        code,
        assessment(),
        findings=(
            Finding(component="action_present", value=True),
            Finding(component="contextual_fit", value=True),
        ),
        verification=(
            Verification(
                component="action_present",
                status="supported",
                reason="Solo primer componente verificado",
            ),
        ),
    )
    assert result.score == "BLOCKED", code


@pytest.mark.parametrize("code", CODES)
def test_duplicate_verification_does_not_replace_coverage(code):
    result = decide(
        code,
        assessment(),
        findings=(
            Finding(component="action_present", value=True),
            Finding(component="contextual_fit", value=True),
        ),
        verification=(
            Verification("action_present", "supported", "Primera"),
            Verification("action_present", "supported", "Duplicada"),
        ),
    )
    assert result.score == "BLOCKED", code


@pytest.mark.parametrize("code", CODES)
def test_na_requires_applicability_verification(code):
    result = decide(
        code,
        assessment(applicable=False),
        verification=(
            Verification(
                component="semantic_support",
                status="supported",
                reason="No verifica aplicabilidad",
            ),
        ),
    )
    assert result.score == "BLOCKED", code
