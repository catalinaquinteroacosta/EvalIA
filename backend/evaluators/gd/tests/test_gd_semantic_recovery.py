
from unittest.mock import patch

import pytest

from backend.evaluators.gd import gd_extractor
from backend.evaluators.gd import gd_level_semantic


def test_extractor_repairs_invalid_response():
    ctx = gd_extractor.GDContext(
        current_user="Necesito decidir.",
        current_response="La decisi?n es tuya.",
        prior_history=(),
    )

    invalid = {"indicators": []}
    valid = {"indicators": []}

    with (
        patch.object(
            gd_extractor,
            "run_structured_semantic",
            side_effect=[invalid, valid],
        ) as api,
        patch.object(
            gd_extractor,
            "validate_extraction",
            side_effect=[
                ValueError("invalid"),
                valid,
            ],
        ),
        patch.object(
            gd_extractor,
            "get_semantic_identity",
            return_value={"provider": "openai", "model": "test"},
        ),
    ):
        result = gd_extractor.extract_gd(
            ctx,
            use_cache=False,
        )

    assert result == valid
    assert api.call_count == 2


def test_extractor_rejects_second_invalid_response():
    ctx = gd_extractor.GDContext(
        current_user="Necesito decidir.",
        current_response="La decisi?n es tuya.",
        prior_history=(),
    )

    with (
        patch.object(
            gd_extractor,
            "run_structured_semantic",
            side_effect=[
                {"indicators": []},
                {"indicators": []},
            ],
        ) as api,
        patch.object(
            gd_extractor,
            "validate_extraction",
            side_effect=ValueError("invalid"),
        ),
        patch.object(
            gd_extractor,
            "get_semantic_identity",
            return_value={"provider": "openai", "model": "test"},
        ),
    ):
        with pytest.raises(ValueError):
            gd_extractor.extract_gd(
                ctx,
                use_cache=False,
            )

    assert api.call_count == 2


def test_classifier_repairs_invalid_response():
    ctx = gd_level_semantic.GDContext(
        current_user="Necesito decidir.",
        current_response="La decisi?n es tuya.",
        prior_history=(),
    )

    invalid = {"indicators": []}
    valid = {"indicators": []}

    with (
        patch.object(
            gd_level_semantic,
            "run_structured_semantic",
            side_effect=[invalid, valid],
        ) as api,
        patch.object(
            gd_level_semantic,
            "validate_levels",
            side_effect=[
                ValueError("invalid"),
                valid,
            ],
        ),
    ):
        result = gd_level_semantic.classify_gd_levels(ctx)

    assert result == valid
    assert api.call_count == 2


def test_classifier_rejects_second_invalid_response():
    ctx = gd_level_semantic.GDContext(
        current_user="Necesito decidir.",
        current_response="La decisi?n es tuya.",
        prior_history=(),
    )

    with (
        patch.object(
            gd_level_semantic,
            "run_structured_semantic",
            side_effect=[
                {"indicators": []},
                {"indicators": []},
            ],
        ) as api,
        patch.object(
            gd_level_semantic,
            "validate_levels",
            side_effect=ValueError("invalid"),
        ),
    ):
        with pytest.raises(ValueError):
            gd_level_semantic.classify_gd_levels(ctx)

    assert api.call_count == 2
