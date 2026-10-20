from backend.evaluators.ir.core import component_engine


def test_ir25_ir1_single_component():
    assert len(component_engine.COMPONENTS["IR1"]) == 1


def test_ir25_ir3_three_components():
    assert len(component_engine.COMPONENTS["IR3"]) == 3


def test_ir25_strict_prompt_contract(monkeypatch):
    captured = {}

    def fake_openai(system, payload):
        captured["system"] = system
        captured["payload"] = payload

        return {
            "components": [
                {
                    "component": name,
                    "present": False,
                    "evidence": [],
                    "explanation": "Ausente",
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

    result = component_engine.extract_components(
        Context(), "IR1"
    )

    assert len(result) == 1
    assert "Devuelve exactamente 1 objetos" in (
        captured["system"]
    )
    assert "subcadena textual" in captured["system"]
