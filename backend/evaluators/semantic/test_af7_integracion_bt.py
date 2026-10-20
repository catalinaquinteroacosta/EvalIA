from copy import deepcopy

from backend.evaluators.semantic import af_ai_af7 as af7
from backend.evaluators.rules.af7_scorer import _score_item


def test_af7_false_link_no_obtiene_dos_puntos(monkeypatch):
    ai = (
        "La preocupacion puede afectar tu sueno. "
        "Si necesitas hablar, cuentaselo a alguien de confianza."
    )

    item = {
        "id": "af7_recovery_5",
        "blocked_action": "hablar con alguien",
        "blocked_action_user_id": "",
        "blocked_action_evidence": {
            "quote": "Si necesitas hablar",
            "source": "current_ai",
        },
        "procedure": "contarselo a alguien de confianza",
        "procedure_evidence": {
            "quote": "cuentaselo a alguien de confianza",
            "source": "current_ai",
        },
        "when_or_how_evidence": {
            "quote": "",
            "source": "current_ai",
        },
    }

    interferences = [{
        "id": "interference_1",
        "action_description": "dormir",
        "evidence": {
            "quote": "Me cuesta dormir por la preocupacion",
            "source": "current_user",
        },
        "semantic_validation": {"status": "supported"},
    }]

    monkeypatch.setattr(
        af7,
        "_recover_ai_item_literal_evidence",
        lambda **kwargs: kwargs["item"],
    )

    # Simulamos el falso positivo original de B.
    monkeypatch.setattr(
        af7,
        "_validate_b",
        lambda **kwargs: {
            "status": "supported",
            "matched_interference_id": "interference_1",
        },
    )

    for name in (
        "_validate_t",
        "_validate_safe",
        "_validate_proportional",
    ):
        monkeypatch.setattr(
            af7,
            name,
            lambda **kwargs: {"status": "supported"},
        )

    monkeypatch.setattr(
        af7,
        "_validate_m",
        lambda **kwargs: {"status": "not_supported"},
    )

    calls = []

    def semantic_validator(**kwargs):
        calls.append(kwargs)
        return {
            "status": "not_supported",
            "reason": "Hablar no es un procedimiento para retomar el sueno.",
        }

    monkeypatch.setattr(
        af7,
        "validate_semantic_entailment",
        semantic_validator,
    )

    result = af7._process_item(
        item=deepcopy(item),
        interferences=deepcopy(interferences),
        current_ai=ai,
        activation_context="Me preocupa no poder dormir",
        model="TEST",
        timeout=1,
    )

    validation = result["semantic_validation"]

    assert len(calls) == 1
    assert validation["B"]["status"] == "supported"
    assert validation["BT_COHERENCE"]["status"] == "not_supported"
    assert validation["T"]["status"] != "supported"

    score = _score_item(
        result,
        elimination_guarantee=False,
    )

    assert score <= 1, f"Falso positivo: AF7 obtuvo {score}"
