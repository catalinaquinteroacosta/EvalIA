from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import backend.evaluators.semantic.em.pipeline_v2 as pipeline
import backend.evaluators.semantic.em.em_private_cache as cacheop
from backend.evaluators.semantic.em.em_private_cache import (
    EMPrivateCache,
)


USER = "Me preocupa perder mi trabajo."
RESPONSE = (
    "Tiene sentido que estés preocupada ante "
    "la posibilidad de perder tu trabajo."
)


def _identity(*args, **kwargs):
    return {
        "provider": "openai",
        "model": "test-model",
    }


def _component(
    value="true",
    evidence=None,
    counterevidence=None,
):
    return {
        "value": value,
        "reason": "test",
        "evidence": evidence or [],
        "counterevidence": counterevidence or [],
    }


def _verification(
    status="supported",
    *,
    error=None,
):
    return {
        "status": status,
        "reason": f"status={status}",
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "verification_error": error,
    }


@pytest.fixture
def isolated_cache(tmp_path):
    cache = EMPrivateCache(
        tmp_path / "semantic_cache.sqlite3"
    )

    old = cacheop._em_cache
    cacheop._em_cache = cache

    try:
        yield cache
    finally:
        cacheop._em_cache = old


def test_cached_operation_miss_write_hit_without_second_execute(
    isolated_cache,
):
    calls = {
        "n": 0,
    }

    def execute():
        calls["n"] += 1
        return {
            "answer": "valid",
        }

    kwargs = dict(
        extractor="em.test",
        extractor_version="1",
        model="openai:test",
        prompt_version="1",
        schema_version="1",
        parameters={
            "indicator": "EM1",
        },
        inputs={
            "user": USER,
            "response": RESPONSE,
        },
        execute=execute,
        validate_result=lambda x: x,
    )

    first = cacheop.cached_semantic_operation(
        **kwargs
    )

    second = cacheop.cached_semantic_operation(
        **kwargs
    )

    assert first == second
    assert calls["n"] == 1

    assert isolated_cache.misses == 1
    assert isolated_cache.writes == 1
    assert isolated_cache.hits == 1
    assert isolated_cache.count() == 1


def test_cache_key_changes_when_temporal_history_changes(
    isolated_cache,
):
    calls = {
        "n": 0,
    }

    def execute():
        calls["n"] += 1
        return {
            "call": calls["n"],
        }

    common = dict(
        extractor="em.test.history",
        extractor_version="1",
        model="openai:test",
        prompt_version="1",
        schema_version="1",
        parameters={
            "indicator": "EM1",
        },
        execute=execute,
        validate_result=lambda x: x,
    )

    a = cacheop.cached_semantic_operation(
        **common,
        inputs={
            "prior_history": [
                {
                    "role": "user",
                    "text": "Historia A",
                }
            ],
            "user_message": USER,
            "ai_response": RESPONSE,
        },
    )

    b = cacheop.cached_semantic_operation(
        **common,
        inputs={
            "prior_history": [
                {
                    "role": "user",
                    "text": "Historia B",
                }
            ],
            "user_message": USER,
            "ai_response": RESPONSE,
        },
    )

    assert a != b
    assert calls["n"] == 2
    assert isolated_cache.count() == 2


@patch.object(
    pipeline,
    "verify_component_semantics_v2",
)
def test_unsupported_primary_gets_exactly_one_reconciliation(
    mocked_verify,
    isolated_cache,
):
    mocked_verify.side_effect = [
        _verification(
            "unsupported"
        ),
        _verification(
            "supported"
        ),
    ]

    components = {
        "emotion_recognized": _component(
            "true"
        ),
    }

    value, primary, reconciliation = (
        pipeline._verify_component_with_reconciliation(
            indicator_code="EM1",
            component_name="emotion_recognized",
            components=components,
            prior_history=[],
            user_message=USER,
            ai_response=RESPONSE,
            provider="openai",
            model="test-model",
        )
    )

    assert mocked_verify.call_count == 2

    assert primary["status"] == "unsupported"
    assert reconciliation["status"] == "supported"

    assert value is not None
    assert value.proposed_value == "true"
    assert value.verification_status == "supported"

    # unsupported no fue cacheado;
    # supported de reconciliación sí.
    assert isolated_cache.count() == 1


@patch.object(
    pipeline,
    "verify_component_semantics_v2",
)
def test_unresolved_after_second_pass_remains_blocked(
    mocked_verify,
    isolated_cache,
):
    mocked_verify.side_effect = [
        _verification(
            "unsupported"
        ),
        _verification(
            "ambiguous"
        ),
    ]

    components = {
        "emotion_recognized": _component(
            "true"
        ),
    }

    value, primary, reconciliation = (
        pipeline._verify_component_with_reconciliation(
            indicator_code="EM1",
            component_name="emotion_recognized",
            components=components,
            prior_history=[],
            user_message=USER,
            ai_response=RESPONSE,
            provider="openai",
            model="test-model",
        )
    )

    assert mocked_verify.call_count == 2
    assert value is None
    assert primary["status"] == "unsupported"
    assert reconciliation["status"] == "ambiguous"

    # Ningún estado irresuelto queda persistido.
    assert isolated_cache.count() == 0


@patch.object(
    pipeline,
    "verify_component_semantics_v2",
)
def test_supported_primary_does_not_trigger_reconciliation(
    mocked_verify,
    isolated_cache,
):
    mocked_verify.return_value = (
        _verification(
            "supported"
        )
    )

    components = {
        "emotion_recognized": _component(
            "true"
        ),
    }

    value, primary, reconciliation = (
        pipeline._verify_component_with_reconciliation(
            indicator_code="EM1",
            component_name="emotion_recognized",
            components=components,
            prior_history=[],
            user_message=USER,
            ai_response=RESPONSE,
            provider="openai",
            model="test-model",
        )
    )

    assert mocked_verify.call_count == 1
    assert value is not None
    assert primary["status"] == "supported"
    assert reconciliation is None
    assert isolated_cache.count() == 1


@patch.object(
    pipeline,
    "get_semantic_identity",
    side_effect=_identity,
)
@patch.object(
    pipeline,
    "_extract_cached",
)
def test_em13_incomplete_components_are_blocked(
    mocked_extract,
    mocked_identity,
):
    mocked_extract.return_value = {
        "indicator_code": "EM13",
        "literal_evidence_valid": True,
        "components": {
            "relevant_belief_or_value_expressed": (
                _component(
                    "false"
                )
            ),
        },
    }

    with patch.object(
        pipeline,
        "_verify_component_with_reconciliation",
    ) as mocked_component:

        from backend.evaluators.semantic.em.scorer import (
            VerifiedSemanticValue,
        )

        mocked_component.return_value = (
            VerifiedSemanticValue(
                name=(
                    "relevant_belief_or_value_expressed"
                ),
                proposed_value="false",
                verification_status="supported",
            ),
            _verification(
                "supported"
            ),
            None,
        )

        result = pipeline.evaluate_em_indicator_v2(
            "EM13",
            user_message=(
                "Hoy fue un día pesado."
            ),
            ai_response=(
                "Entiendo."
            ),
            prior_history=[],
        )

    assert result["status"] == "blocked"
    assert result["applicable"] is None
    assert result["score"] is None


@patch.object(
    pipeline,
    "get_semantic_identity",
    side_effect=_identity,
)
@patch.object(
    pipeline,
    "_extract_cached",
)
def test_em13_unresolved_condition_is_blocked_not_na(
    mocked_extract,
    mocked_identity,
):
    mocked_extract.return_value = {
        "indicator_code": "EM13",
        "literal_evidence_valid": True,
        "components": {
            "relevant_belief_or_value_expressed": (
                _component(
                    "unknown"
                )
            ),
        },
    }

    with patch.object(
        pipeline,
        "_verify_component_with_reconciliation",
    ) as mocked_component:

        mocked_component.return_value = (
            None,
            _verification(
                "ambiguous"
            ),
            _verification(
                "ambiguous"
            ),
        )

        result = pipeline.evaluate_em_indicator_v2(
            "EM13",
            user_message="No sé qué pensar.",
            ai_response="Te escucho.",
            prior_history=[],
        )

    assert result["status"] == "blocked"
    assert result["applicable"] is None
    assert result["score"] is None


def test_family_isolation_continues_after_one_indicator_error():
    def fake_indicator(
        code,
        **kwargs,
    ):
        if code == "EM4":
            raise RuntimeError(
                "fallo controlado"
            )

        return {
            "indicator_code": code,
            "status": "ok",
            "applicable": True,
            "score": 3,
        }

    with patch.object(
        pipeline,
        "evaluate_em_indicator_v2",
        side_effect=fake_indicator,
    ):
        result = pipeline.evaluate_em_family_v2(
            user_message=USER,
            ai_response=RESPONSE,
            prior_history=[],
        )

    assert len(
        result["indicators"]
    ) == 13

    assert (
        result["indicators"]["EM4"]["status"]
        == "error"
    )

    assert (
        result["indicators"]["EM3"]["status"]
        == "ok"
    )

    assert (
        result["indicators"]["EM5"]["status"]
        == "ok"
    )
