
from unittest.mock import patch

from backend.evaluators.gd import gd_verifier


def test_verification_prompt_defines_absence_correctly():
    from backend.evaluators.gd.gd_schemas import GDContext

    context = GDContext(
        current_user="?Qu? hago?",
        current_response="Debes terminar inmediatamente.",
        prior_history=(),
    )

    extraction = {
        "indicators": [
            {
                "code": f"GD{i}",
                "condition_present": (
                    "uncertain" if i in (5, 7)
                    else "not_required"
                ),
                "components": [],
            }
            for i in range(1, 9)
        ]
    }

    captured = []

    def fake_semantic(**kwargs):
        captured.append(kwargs["prompt"])
        return {"verdicts": []}

    with (
        patch.object(
            gd_verifier,
            "run_structured_semantic",
            side_effect=fake_semantic,
        ),
        patch.object(
            gd_verifier,
            "get_semantic_identity",
            return_value={
                "provider": "openai",
                "model": "test",
            },
        ),
    ):
        gd_verifier.verify_gd(
            context,
            extraction,
            use_cache=False,
        )

    prompt = captured[0]

    assert "supported means the EXTRACTOR CLAIM" in prompt
    assert "correctly identified absence" in prompt
    assert "not_supported means the EXTRACTOR CLAIM" in prompt
    assert "different indicators" in prompt


def test_verification_version_is_updated():
    assert gd_verifier.VERSION == "GD-VERIFY-1.1.0"
