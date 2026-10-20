
import pytest

from backend.evaluators.ce.ce_d.ce4_semantic_identity import (
    ce4_cache_key,
)


BASE = {
    "stage": "extraction",
    "provider": "openai",
    "model": "test-model",
    "rubric_version": "rubric-v1",
    "prompt_version": "prompt-v1",
    "schema_version": "schema-v1",
    "inputs": {
        "user_text": "Necesito ayuda.",
        "response_text": "Podemos organizarlo.",
        "prior_context": "",
    },
}


def key(**changes):
    values = dict(BASE)
    values.update(changes)
    return ce4_cache_key(**values)


def test_key_is_deterministic():
    assert key() == key()


@pytest.mark.parametrize(
    "stage", ["verification", "reconciliation"]
)
def test_stages_are_independent(stage):
    assert key(stage=stage) != key()


def test_model_changes_key():
    assert key(model="another-model") != key()


def test_provider_changes_key():
    assert key(provider="ollama") != key()


def test_rubric_changes_key():
    assert key(rubric_version="rubric-v2") != key()


def test_prompt_changes_key():
    assert key(prompt_version="prompt-v2") != key()


def test_schema_changes_key():
    assert key(schema_version="schema-v2") != key()


def test_context_changes_key():
    inputs = dict(BASE["inputs"])
    inputs["prior_context"] = "Contexto previo."
    assert key(inputs=inputs) != key()


def test_response_changes_key():
    inputs = dict(BASE["inputs"])
    inputs["response_text"] = "Respuesta diferente."
    assert key(inputs=inputs) != key()


def test_invalid_stage_rejected():
    with pytest.raises(ValueError):
        key(stage="scoring")
