from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import component_engine


def fake_result(code, status):
    return {
        "results": [{
            "component": component_engine.COMPONENTS[code][0],
            "status": status,
            "reason": "Verificación independiente",
        }]
    }


def test_verified_absence_has_distinct_status(monkeypatch):
    ctx = Context(user="Estoy preocupado", response="Hola")

    extracted = [{
        "component": component_engine.COMPONENTS["IR1"][0],
        "present": False,
        "evidence": [],
        "explanation": "No aparece",
    }]

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        lambda *_: fake_result("IR1", "supported"),
    )

    result = component_engine.verify_components(
        ctx, "IR1", extracted
    )

    assert result[0]["status"] == "absent_verified"


def test_absence_disagreement_blocks(monkeypatch):
    ctx = Context(user="Estoy preocupado", response="Hola")

    extracted = [{
        "component": component_engine.COMPONENTS["IR1"][0],
        "present": False,
        "evidence": [],
        "explanation": "No aparece",
    }]

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        lambda *_: fake_result("IR1", "unsupported"),
    )

    result = component_engine.verify_components(
        ctx, "IR1", extracted
    )

    assert result[0]["status"] == "BLOCKED"


def test_ambiguous_absence_blocks(monkeypatch):
    ctx = Context(user="Estoy preocupado", response="Hola")

    extracted = [{
        "component": component_engine.COMPONENTS["IR1"][0],
        "present": False,
        "evidence": [],
        "explanation": "No aparece",
    }]

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        lambda *_: fake_result("IR1", "ambiguous"),
    )

    result = component_engine.verify_components(
        ctx, "IR1", extracted
    )

    assert result[0]["status"] == "BLOCKED"