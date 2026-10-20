from unittest.mock import patch

import pytest

from backend.evaluators.semantic import af_evidence_recovery as recovery


SOURCE = (
    "- **Hablar con alguien de confianza.** "
    "Compartir lo que sientes con un amigo."
)

PROPOSED = (
    "Hablar con alguien de confianza. "
    "Compartir lo que sientes con un amigo."
)

PROPOSITION = (
    "La respuesta recomienda hablar con alguien de confianza."
)


@pytest.mark.parametrize(
    "status, expected",
    [
        ("supported", True),
        ("not_supported", False),
        ("ambiguous", False),
    ],
)
def test_markdown_recovery_requires_semantic_validation(
    status,
    expected,
):
    with (
        patch.object(
            recovery,
            "get_semantic_identity",
            return_value={
                "provider": "openai",
                "model": "test-model",
            },
        ),
        patch.object(
            recovery,
            "validate_semantic_entailment",
            return_value={"status": status},
        ) as validator,
        patch.object(
            recovery,
            "cached_semantic_operation",
        ) as fallback,
    ):
        result = recovery.recover_literal_evidence(
            source_text=SOURCE,
            proposition=PROPOSITION,
            proposed_evidence=PROPOSED,
        )

    assert result["recovered"] is expected
    validator.assert_called_once()
    fallback.assert_not_called()

    if expected:
        assert result["quote"] in SOURCE
        assert "**" in result["quote"]


def test_markdown_recovery_rejects_changed_words():
    from backend.evaluators.semantic.af_literal_markdown_recovery import (
        recover_markdown_literal,
    )

    assert recover_markdown_literal(
        SOURCE,
        "Hablar con alguien garantiza aprobar.",
    ) is None
