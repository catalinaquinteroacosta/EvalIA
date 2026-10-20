
from unittest.mock import patch

from backend.evaluators.semantic import af_ai_af6 as af6


POSITIVE = (
    "Mencionaste que escribir en tu diario te ayudo antes. "
    "Podrias recuperar ese recurso para afrontar "
    "la angustia actual."
)

NEGATIVE = (
    "Escribir en tu diario te ayudo antes. "
    "Para afrontar la angustia actual, prueba caminar."
)


def make_item(ai, resource_quote, relation_quote):
    return {
        "resource": "escribir en tu diario",
        "resource_evidence": {
            "source": "current_ai",
            "quote": resource_quote,
        },
        "reuse_evidence": {
            "source": "current_ai",
            "quote": relation_quote,
        },
        "current_difficulty_relation": {
            "status": "supported",
            "supporting_evidence": [{
                "source": "current_ai",
                "quote": relation_quote,
            }],
        },
    }


def capture(item, ai):
    calls = []

    def fake_validator(**kwargs):
        calls.append(kwargs)
        return {
            "status": "not_supported",
            "reason": "Simulacion local",
        }

    with patch.object(
        af6,
        "validate_semantic_entailment",
        side_effect=fake_validator,
    ):
        result = af6._validate_v(
            item=item,
            current_ai=ai,
            model="gpt-5.6-luna",
            timeout=600,
        )

    return calls, result


def test_af6_v_positive_uses_complete_literal_response():
    item = make_item(
        POSITIVE,
        "Mencionaste que escribir en tu diario te ayudo antes.",
        "Podrias recuperar ese recurso para afrontar la angustia actual.",
    )

    calls, result = capture(item, POSITIVE)

    assert len(calls) == 1
    assert calls[0]["evidence"] == POSITIVE
    assert calls[0]["local_context"] == POSITIVE
    assert "MISMO recurso anterior" in calls[0]["proposition"]
    assert result["status"] == "not_supported"


def test_af6_v_rejects_invented_relation_quote():
    item = make_item(
        POSITIVE,
        "Mencionaste que escribir en tu diario te ayudo antes.",
        "Puedes reutilizar tu diario para la angustia actual.",
    )

    calls, result = capture(item, POSITIVE)

    assert calls == []
    assert result["status"] == "not_supported"


def test_af6_v_different_resources_require_semantic_check():
    item = make_item(
        NEGATIVE,
        "Escribir en tu diario te ayudo antes.",
        "Para afrontar la angustia actual, prueba caminar.",
    )

    calls, result = capture(item, NEGATIVE)

    assert len(calls) == 1
    assert calls[0]["evidence"] == NEGATIVE
    assert "MISMO recurso anterior" in calls[0]["proposition"]

    # La simulacion nunca aprueba V automaticamente.
    assert result["status"] == "not_supported"


def test_af6_v_unconfirmed_general_relation_is_rejected():
    item = make_item(
        POSITIVE,
        "Mencionaste que escribir en tu diario te ayudo antes.",
        "Podrias recuperar ese recurso para afrontar la angustia actual.",
    )

    item["current_difficulty_relation"]["status"] = "not_supported"

    calls, result = capture(item, POSITIVE)

    assert calls == []
    assert result["status"] == "not_supported"
