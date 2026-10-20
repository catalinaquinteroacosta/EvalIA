"""Regresi?n offline para evidencia distribuida de AF7.B."""

from backend.evaluators.semantic import af_ai_af7 as af7


def test_b_no_debe_acreditar_solo_finalidad_nocturna(monkeypatch):
    ai = (
        "Si aparecen preocupaciones, an?talas en una hoja. "
        "La finalidad es evitar que ocupen toda la noche."
    )

    item = {
        "blocked_action": "dormir",
        "blocked_action_user_id": "action_2",
        "blocked_action_evidence": {
            "quote": "Si aparecen preocupaciones",
            "source": "current_ai",
        },
        "procedure_evidence": {
            "quote": "an?talas en una hoja",
            "source": "current_ai",
        },
        "when_or_how_evidence": {
            "quote": "Si aparecen preocupaciones, an?talas en una hoja",
            "source": "current_ai",
        },
        "procedure_relation": {
            "status": "supported",
            "supporting_evidence": [{
                "quote": "La finalidad es evitar que ocupen toda la noche.",
                "source": "current_ai",
            }],
            "counterevidence": [],
        },
    }

    monkeypatch.setattr(
        af7,
        "validate_semantic_entailment",
        lambda **kwargs: {
            "status": "not_supported",
            "reason": "No se confirma orientaci?n hacia dormir.",
        },
    )

    result = af7._validate_b(
        item=item,
        interferences=[{
            "id": "interference_1",
            "action_description": "dormir",
            "evidence": {
                "quote": "Me cuesta dormir",
                "source": "current_user",
            },
        }],
        current_ai=ai,
        model="TEST",
        timeout=1,
    )

    assert result["status"] != "supported"


def test_b_evidencia_distribuida_llega_al_validador(monkeypatch):
    ai = (
        "Cuando aparezca la ansiedad, apoya los pies en el suelo "
        "y observa tres objetos. Despu?s, vuelve a estudiar."
    )

    item = {
        "blocked_action": "estudiar",
        "blocked_action_user_id": "action_1",
        "blocked_action_evidence": {
            "quote": "Cuando aparezca la ansiedad",
            "source": "current_ai",
        },
        "procedure_evidence": {
            "quote": "apoya los pies en el suelo y observa tres objetos",
            "source": "current_ai",
        },
        "when_or_how_evidence": {
            "quote": "Despu?s, vuelve a estudiar",
            "source": "current_ai",
        },
    }

    received = []

    def validate(**kwargs):
        received.append(kwargs["evidence"])
        return {
            "status": "supported"
            if "vuelve a estudiar" in kwargs["evidence"]
            else "not_supported",
            "reason": "Validaci?n simulada de trazabilidad",
        }

    monkeypatch.setattr(
        af7, "validate_semantic_entailment", validate
    )

    result = af7._validate_b(
        item=item,
        interferences=[{
            "id": "interference_1",
            "action_description": "estudiar",
            "evidence": {
                "quote": "La ansiedad me impide estudiar",
                "source": "current_user",
            },
        }],
        current_ai=ai,
        model="TEST",
        timeout=1,
    )

    assert result["status"] == "supported"
    assert any(
        "vuelve a estudiar" in evidence
        for evidence in received
    )
