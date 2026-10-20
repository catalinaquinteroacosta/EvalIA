from backend.evaluators.ir.core import component_engine


def test_ir27_ir3_prompt(monkeypatch):
    captured = {}

    def fake_openai(system, payload):
        captured["system"] = system

        return {
            "components": [
                {
                    "component": name,
                    "present": False,
                    "evidence": [],
                    "explanation": "No demostrado",
                }
                for name in payload["components"]
            ]
        }

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        fake_openai,
    )

    class Context:
        user = "Usuario"
        response = "Respuesta"
        prior_history = ()

    component_engine.extract_components(
        Context(), "IR3"
    )

    assert "REGLA ESPECIFICA IR3" in captured["system"]
    assert "copiadas literalmente" in captured["system"]
    assert "Una misma cita literal" in captured["system"]


def test_ir27_ir3_component_contract():
    assert len(component_engine.COMPONENTS["IR3"]) == 3
