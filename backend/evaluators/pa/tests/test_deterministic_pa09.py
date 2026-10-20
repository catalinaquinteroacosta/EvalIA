
import pytest

from backend.evaluators.pa.deterministic_pa09 import (
    VerifiedProperty,
    SemanticAssessment,
    evaluate,
)

P = VerifiedProperty(
    name="Propiedad contrastiva",
    value="present",
    verified=True,
    evidence_valid=True,
)


@pytest.mark.parametrize(
    "code",
    [f"PA{i}" for i in range(1, 9)],
)
@pytest.mark.parametrize(
    "present,clear,useful,applicable,expected",
    [
        (False, False, False, False, 0),
        (True, False, True, True, 1),
        (True, True, False, True, 1),
        (True, True, True, False, 2),
        (True, True, True, True, 3),
    ],
)
def test_official_levels(
    code, present, clear, useful, applicable, expected
):
    assessment = SemanticAssessment(
        code=code,
        applicability="applicable",
        action_present=present,
        action_clear=clear,
        action_useful=useful,
        action_applicable=applicable,
        properties=(P,),
    )

    result = evaluate(assessment)

    assert result["status"] == "SCORED"
    assert result["score"] == expected


@pytest.mark.parametrize("code", ["PA2", "PA3", "PA8"])
def test_conditional_na(code):
    result = evaluate(
        SemanticAssessment(
            code=code,
            applicability="not_applicable",
            action_present=None,
            action_clear=None,
            action_useful=None,
            action_applicable=None,
            properties=(),
        )
    )

    assert result["status"] == "N/A"


@pytest.mark.parametrize("code", ["PA1", "PA4", "PA5", "PA6", "PA7"])
def test_general_na_blocked(code):
    result = evaluate(
        SemanticAssessment(
            code=code,
            applicability="not_applicable",
            action_present=None,
            action_clear=None,
            action_useful=None,
            action_applicable=None,
            properties=(),
        )
    )

    assert result["status"] == "BLOCKED"


def test_unverified_property_blocks():
    bad = VerifiedProperty(
        name="Sin verificar",
        value="present",
        verified=False,
        evidence_valid=True,
    )

    result = evaluate(
        SemanticAssessment(
            code="PA1",
            applicability="applicable",
            action_present=True,
            action_clear=True,
            action_useful=True,
            action_applicable=True,
            properties=(bad,),
        )
    )

    assert result["status"] == "BLOCKED"


def test_unresolved_blocks():
    result = evaluate(
        SemanticAssessment(
            code="PA7",
            applicability="applicable",
            action_present=True,
            action_clear=True,
            action_useful=True,
            action_applicable=True,
            properties=(P,),
            unresolved=True,
        )
    )

    assert result["status"] == "BLOCKED"
