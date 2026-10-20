from backend.evaluators.semantic import af_ai_af7


def test_af7_no_confunde_mencion_con_objetivo(monkeypatch):
    ai = (
        "La preocupación puede afectar tu sueño. "
        "Si necesitas hablar, cuéntaselo a alguien de confianza."
    )

    item = {
        "blocked_action": "hablar con alguien",
        "blocked_action_user_id": "",
        "blocked_action_evidence": {
            "quote": "Si necesitas hablar",
            "source": "current_ai",
        },
        "procedure_evidence": {
            "quote": "cuéntaselo a alguien de confianza",
            "source": "current_ai",
        },
    }

    interferences = [{
        "id": "interference_1",
        "action_description": "dormir",
        "evidence": {
            "quote": "Me cuesta dormir por la preocupación",
            "source": "current_user",
        },
        "semantic_validation": {"status": "supported"},
    }]

    def fake_entailment(*, evidence, proposition, **kwargs):
        # Simula una validación excesivamente permisiva.
        return {
            "status": "supported",
            "reason": "Coinciden en el contexto de preocupación.",
        }

    monkeypatch.setattr(
        af_ai_af7,
        "validate_semantic_entailment",
        fake_entailment,
    )

    result = af_ai_af7._validate_b(
        item=item,
        interferences=interferences,
        current_ai=ai,
        model="TEST",
        timeout=1,
    )

    assert result["status"] != "supported", (
        "ERROR: AF7 aceptó dormir como objetivo "
        "de una intervención dirigida a hablar."
    )
