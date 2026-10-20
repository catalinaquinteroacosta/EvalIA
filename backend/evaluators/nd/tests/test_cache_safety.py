from pathlib import Path
from unittest.mock import patch

from backend.evaluators.nd.semantic_engine import (
    NDSemanticEngine,
    CACHE_PATH,
    COMPONENT_SCHEMA,
    VERIFY_SCHEMA,
    _cache_key,
)


def test_cache_keys_change_with_prompt():
    identity = {"provider": "openai", "model": "test-model"}
    common = dict(
        stage="extract",
        indicator="ND1",
        identity=identity,
        schema=COMPONENT_SCHEMA,
    )

    first = _cache_key(
        **common,
        inputs={"user": "hola", "_actual_prompt": "prompt A"},
    )
    second = _cache_key(
        **common,
        inputs={"user": "hola", "_actual_prompt": "prompt B"},
    )

    assert first != second


def test_extraction_and_verification_keys_differ():
    identity = {"provider": "openai", "model": "test-model"}
    inputs = {"user": "Tengo miedo"}

    extraction = _cache_key(
        stage="extract",
        indicator="ND1",
        identity=identity,
        inputs=inputs,
        schema=COMPONENT_SCHEMA,
    )
    verification = _cache_key(
        stage="verify",
        indicator="ND1",
        identity=identity,
        inputs=inputs,
        schema=VERIFY_SCHEMA,
    )

    assert extraction != verification


def test_cache_cannot_leave_nd():
    with patch(
        "backend.evaluators.nd.semantic_engine.SemanticCache"
    ):
        try:
            NDSemanticEngine(
                provider="openai",
                model="test-model",
                cache_path=Path.cwd() / "cache_global.sqlite3",
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "ND permitio una cache fuera de su carpeta"
            )


def test_default_cache_is_private():
    assert CACHE_PATH.parent.name == ".cache"
    assert CACHE_PATH.parent.parent.name == "nd"
