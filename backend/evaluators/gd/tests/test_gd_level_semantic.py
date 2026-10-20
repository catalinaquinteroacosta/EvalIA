from unittest.mock import patch

import pytest

from backend.evaluators.gd.gd_schemas import GDContext
from backend.evaluators.gd.gd_level_semantic import (
    LEVEL_DESCRIPTORS,
    classify_gd_levels,
    validate_levels,
    validate_level_verification,
    resolve_verified_levels,
)


def context():
    return GDContext(
        current_user="Tengo una decisión importante.",
        current_response="Puedes considerar tus preferencias.",
    )


def classification():
    items = []
    for i in range(1, 9):
        code = f"GD{i}"
        guardrail = code in ("GD2", "GD6", "GD7")
        items.append({
            "code": code,
            "level": (
                "consistent_no_observable_exception"
                if guardrail else "absent_or_contrary"
            ),
            "reason": "Evaluación sintética",
            "evidence": [],
            "contradiction": "",
        })
    return {"indicators": items}


def verification():
    return {
        "verdicts": [
            {
                "code": f"GD{i}",
                "verdict": "supported",
                "reason": "Verificación sintética",
            }
            for i in range(1, 9)
        ]
    }


def applicability():
    return {"GD5": "APPLICABLE", "GD7": "APPLICABLE"}


def test_all_levels_defined():
    assert len(LEVEL_DESCRIPTORS["positive"]) == 4
    assert len(LEVEL_DESCRIPTORS["guardrail"]) == 4


def test_valid_classification():
    assert len(validate_levels(
        classification(), context()
    )["indicators"]) == 8


def test_duplicate_code_rejected():
    data = classification()
    data["indicators"][1]["code"] = "GD1"
    with pytest.raises(ValueError):
        validate_levels(data, context())


def test_positive_requires_response_evidence():
    data = classification()
    data["indicators"][0]["level"] = (
        "complete_contextual_fulfillment"
    )
    with pytest.raises(ValueError):
        validate_levels(data, context())


def test_guardrail_three_without_positive_quote():
    data = classification()
    assert validate_levels(data, context())


def test_material_contradiction_requires_literal_quote():
    data = classification()
    data["indicators"][5]["contradiction"] = "Texto inventado"
    with pytest.raises(ValueError):
        validate_levels(data, context())


def test_verifier_must_cover_all_eight():
    data = verification()
    data["verdicts"].pop()
    with pytest.raises(ValueError):
        validate_level_verification(data)


def test_verified_levels_map_to_scores():
    result = resolve_verified_levels(
        context(),
        classification(),
        verification(),
        applicability=applicability(),
    )
    assert result["GD1"].score == 0
    assert result["GD2"].score == 3
    assert result["GD6"].score == 3


def test_verifier_disagreement_blocks_only_one():
    data = verification()
    data["verdicts"][2]["verdict"] = "ambiguous"

    result = resolve_verified_levels(
        context(),
        classification(),
        data,
        applicability=applicability(),
    )

    assert result["GD3"].status == "BLOCKED"
    assert result["GD2"].status == "SCORED"


def test_conditional_na():
    app = applicability()
    app["GD5"] = "NA"

    result = resolve_verified_levels(
        context(),
        classification(),
        verification(),
        applicability=app,
    )

    assert result["GD5"].status == "NA"
    assert result["GD5"].score is None


def test_missing_turn_blocks():
    empty = GDContext("", "")
    result = resolve_verified_levels(
        empty,
        classification(),
        verification(),
        applicability=applicability(),
    )
    assert all(x.status == "BLOCKED" for x in result.values())


def test_real_provider_interface_mocked():
    with patch(
        "backend.evaluators.gd.gd_level_semantic.run_structured_semantic",
        return_value=classification(),
    ) as provider:
        result = classify_gd_levels(
            context(),
            model="test-model",
        )

    assert len(result["indicators"]) == 8
    assert provider.call_count == 1
    assert "numeric scores" in provider.call_args.kwargs["prompt"]
