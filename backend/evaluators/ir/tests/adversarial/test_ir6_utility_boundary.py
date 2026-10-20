from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import component_engine


def test_ir6_utility_not_proven_by_reformulation_alone():
    """
    Caso adversarial documentado.

    Una reformulacion y una tecnica no son, por si solas,
    evidencia suficiente de exploracion de utilidad.

    Este test registra la distincion metodologica y evita
    confundir el componente con el de relacion emocional.
    """
    components = component_engine.COMPONENTS["IR6"]

    assert len(components) == 2
    assert "emoción o conducta" in components[0]
    assert "resulta útil" in components[1]
    assert components[0] != components[1]


def test_ir6_utility_disagreement_must_block(monkeypatch):
    ctx = Context(
        user="Pienso que hice algo mal",
        response=(
            "Podrias pensar que aun no sabes que ocurrio."
        ),
    )

    component = component_engine.COMPONENTS["IR6"][1]

    extracted = [{
        "component": component,
        "present": True,
        "evidence": [{
            "source": "response",
            "quote": ctx.response,
            "history_index": None,
        }],
        "explanation": "El extractor afirma utilidad",
    }]

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        lambda *_: {
            "results": [{
                "component": component,
                "status": "unsupported",
                "reason": (
                    "La reformulacion no demuestra "
                    "exploracion de utilidad."
                ),
            }]
        },
    )

    result = component_engine.verify_components(
        ctx, "IR6", extracted
    )

    assert result[0]["status"] == "BLOCKED"


def test_ir6_utility_absence_can_be_verified(monkeypatch):
    ctx = Context(
        user="Pienso que hice algo mal",
        response="Podrias considerar otra posibilidad.",
    )

    component = component_engine.COMPONENTS["IR6"][1]

    extracted = [{
        "component": component,
        "present": False,
        "evidence": [],
        "explanation": (
            "No se explora si el pensamiento resulta util"
        ),
    }]

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        lambda *_: {
            "results": [{
                "component": component,
                "status": "supported",
                "reason": (
                    "Se verifica la ausencia en "
                    "la respuesta completa."
                ),
            }]
        },
    )

    result = component_engine.verify_components(
        ctx, "IR6", extracted
    )

    assert result[0]["status"] == "absent_verified"
