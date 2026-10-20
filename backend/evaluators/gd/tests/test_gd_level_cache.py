
from unittest.mock import patch

from backend.evaluators.gd import gd_level_cache


def test_cache_stages_have_different_keys():
    from backend.evaluators.gd.gd_schemas import GDContext

    ctx = GDContext(
        current_user="Necesito ayuda.",
        current_response="Puedes decidir.",
        prior_history=(),
    )

    common = dict(
        context=ctx,
        provider="openai",
        model="test",
        rubric={"GD1": "rubrica"},
        schema_version="1",
        prompt_version="test",
    )

    classification = gd_level_cache.make_level_key(
        stage="classification",
        **common,
    )

    verification = gd_level_cache.make_level_key(
        stage="verification",
        classification={"indicators": []},
        **common,
    )

    assert classification != verification


def test_cache_rejects_unconfirmed_verification():
    value = {
        "verdicts": [
            {
                "code": f"GD{i}",
                "verdict": (
                    "ambiguous" if i == 1 else "supported"
                ),
                "reason": "Revisi?n independiente.",
            }
            for i in range(1, 9)
        ]
    }

    with patch.object(
        gd_level_cache.semantic_cache,
        "set",
    ) as write:
        stored = gd_level_cache.set_validated_level(
            "test-key",
            value,
            stage="verification",
        )

    assert stored is False
    write.assert_not_called()
