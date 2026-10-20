import pytest

from backend.evaluators.pa.contracts import (
    CODES,
    CONDITIONAL,
    Verification,
)
from backend.evaluators.pa.scoring import (
    Assessment,
    decide,
)


def assessment(applicable=True):
    return Assessment(
        applicable=applicable,
        behavior_present=True,
        central_function_met=True,
        contextual_complete=True,
        secondary_defect=False,
        material_contradiction=False,
        reason="Evaluacion sintetica de seguridad",
    )


def verification():
    return (
        Verification(
            component="applicability",
            status="supported",
            reason="Aplicabilidad verificada en prueba sintetica",
        ),
    )


@pytest.mark.parametrize("code", CODES)
def test_missing_verification_blocks(code):
    result = decide(
        code,
        assessment(),
        verification=(),
    )
    assert result.score == "BLOCKED"


@pytest.mark.parametrize(
    "code",
    [code for code in CODES if code not in CONDITIONAL],
)
def test_general_indicators_never_na(code):
    result = decide(
        code,
        assessment(applicable=False),
        verification=verification(),
    )
    assert result.score == "BLOCKED"


@pytest.mark.parametrize("code", CONDITIONAL)
def test_conditional_na_requires_verification(code):
    result = decide(
        code,
        assessment(applicable=False),
        verification=(),
    )
    assert result.score == "BLOCKED"
