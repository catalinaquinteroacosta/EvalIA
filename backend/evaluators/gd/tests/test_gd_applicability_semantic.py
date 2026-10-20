from unittest.mock import patch

import pytest

from backend.evaluators.gd.gd_schemas import GDContext
from backend.evaluators.gd.gd_applicability_semantic import (
    validate_semantic_reviews,
    review_gd_applicability,
    reconcile_conditional_gd,
)


def payload(gd5="applicable", gd7="not_applicable"):
    return {
        "reviews": [
            {
                "code": "GD5",
                "verdict": gd5,
                "reason": "Contexto GD5",
            },
            {
                "code": "GD7",
                "verdict": gd7,
                "reason": "Contexto GD7",
            },
        ]
    }


def test_valid_reviews():
    result = validate_semantic_reviews(payload())
    assert len(result) == 2


def test_duplicate_rejected():
    data = payload()
    data["reviews"][1]["code"] = "GD5"
    with pytest.raises(ValueError):
        validate_semantic_reviews(data)


def test_missing_review_rejected():
    data = payload()
    data["reviews"].pop()
    with pytest.raises(ValueError):
        validate_semantic_reviews(data)


def test_empty_reason_rejected():
    data = payload()
    data["reviews"][0]["reason"] = " "
    with pytest.raises(ValueError):
        validate_semantic_reviews(data)


def test_independent_provider_call():
    ctx = GDContext(
        current_user="Necesito decidir qué hacer.",
        current_response="Puedes explorar alternativas.",
    )

    with (
        patch(
            "backend.evaluators.gd.gd_applicability_semantic.get_semantic_identity",
            return_value={"provider": "openai", "model": "test"},
        ),
        patch(
            "backend.evaluators.gd.gd_applicability_semantic.run_structured_semantic",
            return_value=payload(),
        ) as provider,
    ):
        reviews = review_gd_applicability(
            ctx,
            use_cache=False,
        )

    assert len(reviews) == 2
    assert provider.call_count == 1

    prompt = provider.call_args.kwargs["prompt"]
    assert "Necesito decidir qué hacer." in prompt
    assert "previous extractor conclusions" in prompt


def test_disagreement_stays_blocked():
    extraction = {
        "indicators": [
            {"code": "GD5", "condition_present": "no"},
            {"code": "GD7", "condition_present": "no"},
        ]
    }

    reviews = validate_semantic_reviews(payload())

    result = reconcile_conditional_gd(
        extraction,
        reviews,
    )

    assert result["GD5"] == "BLOCKED"
    assert result["GD7"] == "NA"


def test_uncertainty_stays_blocked():
    extraction = {
        "indicators": [
            {"code": "GD5", "condition_present": "yes"},
            {"code": "GD7", "condition_present": "yes"},
        ]
    }

    reviews = validate_semantic_reviews(
        payload("uncertain", "applicable")
    )

    result = reconcile_conditional_gd(
        extraction,
        reviews,
    )

    assert result["GD5"] == "BLOCKED"
    assert result["GD7"] == "APPLICABLE"
