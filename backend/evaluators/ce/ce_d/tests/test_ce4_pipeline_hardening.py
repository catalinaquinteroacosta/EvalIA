
import pytest

from backend.evaluators.ce.ce_d.ce4_semantic_operations import (
    CE4SemanticContractError,
    semantic_verdict,
)
from backend.evaluators.ce.ce_d.ce4_semantic_pipeline import (
    evaluate_ce4_semantic,
)


def test_reconciliation_with_counterevidence_is_rejected():
    def cache_operation(**kwargs):
        return {
            "verdict": "supported",
            "reason": "Decision propuesta.",
            "counterevidence": "Existe contradiccion.",
        }

    with pytest.raises(CE4SemanticContractError):
        semantic_verdict(
            stage="reconciliation",
            original="Texto completo.",
            quote="Texto",
            condition="Proposicion",
            component="applicability",
            rubric_version="rubric-test",
            prompt_version="prompt-test",
            provider="openai",
            model="test-model",
            cache_operation=cache_operation,
        )


def test_extraction_failure_remains_blocked():
    def failing_cache(**kwargs):
        raise RuntimeError("Cache unavailable")

    result = evaluate_ce4_semantic(
        user_text="Necesito ayuda.",
        response_text="Primero, revisa la situacion.",
        cache_operation=failing_cache,
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None
    assert result["blocked_components"] == ["extraction"]
