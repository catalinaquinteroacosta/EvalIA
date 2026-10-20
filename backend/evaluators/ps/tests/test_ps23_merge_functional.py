
from copy import deepcopy

import pytest

from backend.evaluators.ps.runner import _merge_reconciliation


def payload(code):
    return {
        "indicator": code,
        "applicability": {
            "predicate": "applies",
            "verification": "unsupported",
            "evidence": [],
            "counterevidence": [],
        },
        "levels": {
            str(n): {
                "verification": "unsupported",
                "evidence": [],
                "counterevidence": [],
            }
            for n in range(4)
        },
    }


@pytest.mark.parametrize("code", ("PS2", "PS3"))
def test_applicability_merge_preserves_levels(code):
    original = payload(code)
    proposed = deepcopy(original)

    proposed["applicability"] = {
        "predicate": "not_applicable",
        "verification": "supported",
        "evidence": [],
        "counterevidence": [],
    }
    proposed["levels"]["3"]["verification"] = "supported"

    merged = _merge_reconciliation(
        original, proposed, "Applicability unverified"
    )

    assert merged["applicability"] == proposed["applicability"]
    assert merged["levels"] == original["levels"]


@pytest.mark.parametrize("code", ("PS2", "PS3"))
def test_level_merge_preserves_applicability(code):
    original = payload(code)
    original["applicability"]["verification"] = "supported"
    original["levels"]["2"]["verification"] = "supported"
    original["levels"]["3"]["verification"] = "supported"

    proposed = deepcopy(original)
    proposed["applicability"]["predicate"] = "not_applicable"
    proposed["levels"]["2"]["verification"] = "unsupported"

    merged = _merge_reconciliation(
        original,
        proposed,
        "Rubric level not uniquely supported",
    )

    assert merged["applicability"] == original["applicability"]
    assert merged["levels"]["2"]["verification"] == "unsupported"
    assert merged["levels"]["3"]["verification"] == "supported"


@pytest.mark.parametrize("code", ("PS2", "PS3"))
def test_unknown_reason_preserves_original(code):
    original = payload(code)
    proposed = deepcopy(original)
    proposed["applicability"]["predicate"] = "not_applicable"

    merged = _merge_reconciliation(
        original, proposed, "Unknown blocked reason"
    )

    assert merged == original


@pytest.mark.parametrize("code", ("PS2", "PS3"))
def test_indicator_mismatch_rejected(code):
    original = payload(code)
    proposed = payload("PS3" if code == "PS2" else "PS2")

    with pytest.raises(ValueError):
        _merge_reconciliation(
            original,
            proposed,
            "Applicability unverified",
        )
