import pytest

from backend.evaluators.nd.contracts import (
    ND_CODES,
    ND_CONDITIONAL,
)
from backend.evaluators.nd.applicability import (
    VerifiedApplicability,
    resolve_applicability,
    resolve_family_applicability,
)


@pytest.mark.parametrize("indicator", ND_CODES)
def test_present_is_applicable(indicator):
    result = resolve_applicability(
        VerifiedApplicability(
            indicator, "present", True,
            "Condicion acreditada",
        )
    )
    assert result.status == "APPLICABLE"


@pytest.mark.parametrize("indicator", ND_CODES)
def test_verified_absence_is_na(indicator):
    result = resolve_applicability(
        VerifiedApplicability(
            indicator, "absent", True,
            "Ausencia objetiva acreditada",
        )
    )
    assert result.status == "NA"


@pytest.mark.parametrize("indicator", ND_CODES)
def test_uncertain_is_blocked(indicator):
    result = resolve_applicability(
        VerifiedApplicability(
            indicator, "uncertain", True,
            "Evidencia contradictoria",
        )
    )
    assert result.status == "BLOCKED"


@pytest.mark.parametrize("indicator", ND_CODES)
def test_unverified_is_blocked(indicator):
    result = resolve_applicability(
        VerifiedApplicability(
            indicator, "absent", False,
            "Extraccion sin verificar",
        )
    )
    assert result.status == "BLOCKED"


def test_general_and_conditional_are_distinct():
    assert ND_CONDITIONAL == {"ND1", "ND2", "ND7"}


def test_family_requires_eight_unique_findings():
    findings = [
        VerifiedApplicability(
            code, "present", True, "Evaluable"
        )
        for code in ND_CODES
    ]
    result = resolve_family_applicability(findings)
    assert len(result) == 8
    assert all(
        item.status == "APPLICABLE"
        for item in result.values()
    )

    with pytest.raises(ValueError):
        resolve_family_applicability(findings[:-1])

    with pytest.raises(ValueError):
        resolve_family_applicability(
            findings[:-1] + [findings[0]]
        )
