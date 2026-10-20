
from unittest.mock import patch

import pytest

from backend.evaluators.gd import gd_level_cache
from backend.evaluators.gd.gd_schemas import GDContext


def context():
    return GDContext(
        current_user="Necesito decidir.",
        current_response="La decisi?n es tuya.",
        prior_history=(),
    )


def verification(verdict="supported"):
    return {
        "verdicts": [
            {
                "code": f"GD{i}",
                "verdict": (
                    verdict if i == 1 else "supported"
                ),
                "reason": "Verificaci?n independiente.",
            }
            for i in range(1, 9)
        ]
    }


def test_ambiguous_verification_not_cached():
    with patch.object(
        gd_level_cache.semantic_cache,
        "set",
    ) as write:
        stored = gd_level_cache.set_validated_level(
            "gd-test-ambiguous",
            verification("ambiguous"),
            stage="verification",
        )

    assert stored is False
    write.assert_not_called()


def test_not_supported_verification_not_cached():
    with patch.object(
        gd_level_cache.semantic_cache,
        "set",
    ) as write:
        stored = gd_level_cache.set_validated_level(
            "gd-test-rejected",
            verification("not_supported"),
            stage="verification",
        )

    assert stored is False
    write.assert_not_called()


def test_validated_verification_can_be_cached():
    with patch.object(
        gd_level_cache.semantic_cache,
        "set",
    ) as write:
        stored = gd_level_cache.set_validated_level(
            "gd-test-supported",
            verification(),
            stage="verification",
        )

    assert stored is True
    write.assert_called_once()


def test_cache_key_changes_with_context():
    common = dict(
        stage="classification",
        provider="openai",
        model="test",
        rubric={"GD1": "rubrica"},
        schema_version="1",
        prompt_version="test",
    )

    first = context()

    second = GDContext(
        current_user="Necesito decidir.",
        current_response="Debes obedecerme.",
        prior_history=(),
    )

    assert gd_level_cache.make_level_key(
        context=first,
        **common,
    ) != gd_level_cache.make_level_key(
        context=second,
        **common,
    )
