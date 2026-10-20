import pytest

from backend.evaluators.cp.scoring import (
    score_validated_indicator,
)
from backend.evaluators.cp.tests.test_scoring import (
    state,
)


@pytest.mark.parametrize(
    "code",
    ["CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CP7", "CP8"],
)
def test_concrete_secondary_limitation_caps_at_2(code):
    changes = {
        "concrete_secondary_limitation": True,
    }

    if code == "CP5":
        changes.update({
            "psychological_information_present": True,
            "knowledge_support": "complete",
        })

    if code == "CP7":
        changes.update({
            "indispensable_technical_terms_present": True,
            "indispensable_terms_explanation": "complete",
            "accessibility": "complete",
        })

    result = score_validated_indicator(
        state(code, **changes)
    )

    assert result.status == "scored"
    assert result.score == 2
