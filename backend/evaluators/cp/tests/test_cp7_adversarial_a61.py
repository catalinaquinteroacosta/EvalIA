import pytest

from backend.evaluators.cp.scoring import (
    score_validated_indicator,
)
from backend.evaluators.cp.validated_state import (
    ValidatedIndicatorState,
)


BASE = {
    "unnecessary_jargon_present": False,
    "indispensable_technical_terms_present": False,
    "indispensable_terms_explanation": "complete",
    "accessibility": "complete",
    "concrete_secondary_limitation": False,
}


@pytest.mark.parametrize(
    "case_id,changes,expected",
    [
        ("A01", {
            "unnecessary_jargon_present": True,
            "accessibility": "none",
        }, 0),
        ("A02", {
            "unnecessary_jargon_present": True,
            "accessibility": "minimal",
        }, 1),
        ("A03", {
            "unnecessary_jargon_present": True,
            "accessibility": "adequate",
        }, 2),
        ("A04", {}, 3),
        ("A05", {
            "unnecessary_jargon_present": True,
            "accessibility": "adequate",
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "none",
        }, 0),
        ("A06", {
            "unnecessary_jargon_present": True,
            "accessibility": "adequate",
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "minimal",
        }, 1),
        ("A07", {
            "unnecessary_jargon_present": True,
            "accessibility": "adequate",
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "adequate",
        }, 2),
        ("A08", {
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "complete",
        }, 3),
        ("A09", {
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "none",
        }, 0),
        ("A10", {
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "minimal",
        }, 1),
        ("A11", {
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "adequate",
        }, 2),
        ("A12", {
            "concrete_secondary_limitation": True,
        }, 2),
    ],
)
def test_cp7_adversarial(case_id, changes, expected):
    components = dict(BASE)
    components.update(changes)

    state = ValidatedIndicatorState(
        code="CP7",
        status="validated",
        components=components,
        blocked_components=(),
        supported_evidence_indices=(),
        blocked_evidence_indices=(),
    )

    result = score_validated_indicator(state)

    assert result.status == "scored", case_id
    assert result.score == expected, case_id
