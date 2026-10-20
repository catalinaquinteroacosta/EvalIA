
import pytest

from backend.evaluators.ce.ce_d.ce4_semantic_operations import (
    CE4SemanticContractError,
    semantic_verdict,
    validate_verdict,
)


VALID = {
    "verdict": "supported",
    "reason": "La evidencia sustenta la proposicion.",
    "counterevidence": "",
}


def test_valid_verdict():
    assert validate_verdict(VALID) == VALID


@pytest.mark.parametrize(
    "invalid",
    [
        {},
        None,
        {"verdict": "supported"},
        {
            "verdict": "scored",
            "reason": "Incorrecto",
            "counterevidence": "",
        },
        {
            "verdict": "supported",
            "reason": "",
            "counterevidence": "",
        },
    ],
)
def test_invalid_verdict_rejected(invalid):
    with pytest.raises(CE4SemanticContractError):
        validate_verdict(invalid)


def test_cached_result_is_revalidated():
    def cache_operation(**kwargs):
        return {
            "verdict": "scored",
            "reason": "Invalido",
            "counterevidence": "",
        }

    with pytest.raises(CE4SemanticContractError):
        semantic_verdict(
            stage="verification",
            original="Texto completo.",
            quote="Texto",
            condition="Proposicion",
            component="applicability",
            rubric_version="test-rubric",
            prompt_version="test-prompt",
            provider="openai",
            model="test-model",
            cache_operation=cache_operation,
        )


def test_stage_is_part_of_cache_identity():
    calls = []

    def cache_operation(**kwargs):
        calls.append(kwargs)
        return dict(VALID)

    for stage in ("verification", "reconciliation"):
        semantic_verdict(
            stage=stage,
            original="Texto completo.",
            quote="Texto",
            condition="Proposicion",
            component="applicability",
            rubric_version="test-rubric",
            prompt_version="test-prompt",
            provider="openai",
            model="test-model",
            cache_operation=cache_operation,
        )

    assert calls[0]["extractor"] != calls[1]["extractor"]


def test_runner_not_called_when_cache_hit():
    def runner(**kwargs):
        raise AssertionError("No debe llamar API")

    def cache_operation(**kwargs):
        return dict(VALID)

    result = semantic_verdict(
        stage="verification",
        original="Texto completo.",
        quote="Texto",
        condition="Proposicion",
        component="applicability",
        rubric_version="test-rubric",
        prompt_version="test-prompt",
        provider="openai",
        model="test-model",
        runner=runner,
        cache_operation=cache_operation,
    )

    assert result["verdict"] == "supported"
