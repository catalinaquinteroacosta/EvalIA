from dataclasses import replace

import pytest

from backend.evaluators.gd.gd_engine import (
    GDDecision,
    assess_verified,
    reconcile_blocked,
)


def fixtures():
    extraction = {"indicators": []}
    verification = {"verdicts": []}

    for i in range(1, 9):
        code = f"GD{i}"
        condition = "yes" if code in ("GD5", "GD7") else "not_required"

        extraction["indicators"].append({
            "code": code,
            "condition_present": condition,
            "components": [{
                "name": "behavior",
                "finding": "absent",
                "evidence": [],
            }],
        })

        verification["verdicts"].append({
            "code": code,
            "component_index": 0,
            "verdict": "supported",
            "reason": "Prueba sintética",
        })

    return extraction, verification


def test_eight_verified():
    extraction, verification = fixtures()
    result = assess_verified(extraction, verification)
    assert len(result) == 8
    assert all(x.status == "VERIFIED" for x in result.values())


def test_disagreement_blocks_only_one():
    extraction, verification = fixtures()
    verification["verdicts"][2]["verdict"] = "ambiguous"
    result = assess_verified(extraction, verification)
    assert result["GD3"].status == "BLOCKED"
    assert result["GD2"].status == "VERIFIED"


def test_uncertain_applicability_blocks():
    extraction, verification = fixtures()
    extraction["indicators"][4]["condition_present"] = "uncertain"
    result = assess_verified(extraction, verification)
    assert result["GD5"].status == "BLOCKED"


def test_conditional_na_is_candidate_only():
    extraction, verification = fixtures()
    extraction["indicators"][6]["condition_present"] = "no"
    result = assess_verified(extraction, verification)
    assert result["GD7"].status == "NA_CANDIDATE"


def test_reconciliation_only_calls_blocked():
    extraction, verification = fixtures()
    verification["verdicts"][0]["verdict"] = "ambiguous"
    first = assess_verified(extraction, verification)

    called = []

    def resolver(item):
        called.append(item.code)
        return item

    result = reconcile_blocked(first, resolver)
    assert called == ["GD1"]
    assert result["GD1"].status == "BLOCKED"


def test_reconciliation_rejects_false_unlock():
    extraction, verification = fixtures()
    verification["verdicts"][0]["verdict"] = "not_supported"
    first = assess_verified(extraction, verification)

    with pytest.raises(ValueError):
        reconcile_blocked(
            first,
            lambda item: replace(item, status="VERIFIED"),
        )


def test_reconciliation_preserves_valid():
    extraction, verification = fixtures()
    first = assess_verified(extraction, verification)
    result = reconcile_blocked(
        first,
        lambda _: pytest.fail("No debía llamarse"),
    )
    assert result == first
