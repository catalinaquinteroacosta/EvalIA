from unittest.mock import patch

import pytest

from backend.evaluators.gd.gd_extractor import (
    extract_gd,
    validate_extraction,
)
from backend.evaluators.gd.gd_schemas import GDContext


CONTEXT = GDContext(
    current_user="Necesito pensar qué hacer.",
    current_response="Puedes considerar tus alternativas.",
)


def payload():
    return {
        "indicators": [
            {
                "code": f"GD{i}",
                "condition_present": (
                    "no" if i in (5, 7) else "not_required"
                ),
                "components": [],
            }
            for i in range(1, 9)
        ]
    }


def test_valid_contract_accepts_general_and_conditional():
    assert validate_extraction(payload(), CONTEXT)


@pytest.mark.parametrize("code", [
    "GD1", "GD2", "GD3", "GD4", "GD6", "GD8",
])
@pytest.mark.parametrize("invalid", [
    "yes", "no", "uncertain",
])
def test_general_rejects_invented_condition(code, invalid):
    raw = payload()

    for item in raw["indicators"]:
        if item["code"] == code:
            item["condition_present"] = invalid

    with pytest.raises(
        ValueError,
        match="General indicators",
    ):
        validate_extraction(raw, CONTEXT)


@pytest.mark.parametrize("code", ["GD5", "GD7"])
def test_conditional_rejects_not_required(code):
    raw = payload()

    for item in raw["indicators"]:
        if item["code"] == code:
            item["condition_present"] = "not_required"

    with pytest.raises(
        ValueError,
        match="Conditional applicability",
    ):
        validate_extraction(raw, CONTEXT)


def test_real_prompt_contains_explicit_contract():
    captured = {}

    def fake_provider(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return payload()

    with (
        patch(
            "backend.evaluators.gd.gd_extractor.get_semantic_identity",
            return_value={"provider": "openai", "model": "test"},
        ),
        patch(
            "backend.evaluators.gd.gd_extractor.semantic_cache.get",
            return_value=None,
        ),
        patch(
            "backend.evaluators.gd.gd_extractor.run_structured_semantic",
            side_effect=fake_provider,
        ),
        patch(
            "backend.evaluators.gd.gd_extractor.semantic_cache.set",
        ),
    ):
        result = extract_gd(CONTEXT)

    assert len(result["indicators"]) == 8
    assert "MUST always return condition_present=not_required" in (
        captured["prompt"]
    )
    assert "Never return not_required for GD5 or GD7" in (
        captured["prompt"]
    )
