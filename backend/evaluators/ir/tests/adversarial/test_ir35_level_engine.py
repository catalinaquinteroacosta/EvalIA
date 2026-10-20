
from backend.evaluators.ir.core import level_engine


def test_ir35_payload_uses_official_rubric():
    import json
    from backend.evaluators.nd.contracts import TurnContext
    from backend.evaluators.ansiedad_semantic.functional_review import prompt
    payload = json.loads(prompt("IR3",TurnContext("Usuario","Respuesta"),"extract"))
    assert payload["indicator"] == "IR3"
    assert "evidencia" in payload["official_construct"].lower()
    assert "favorable_evidence_invited" in payload["components"]
    assert "contrary_evidence_invited" in payload["components"]
    assert "official_levels" not in payload  # Reader no longer selects a level.


def test_ir35_blocked_components_make_no_api_calls(
    monkeypatch,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("API no autorizada")

    monkeypatch.setattr(
        level_engine, "ask_openai", forbidden
    )

    class Context:
        user = "Usuario"
        response = "Respuesta"
        prior_history = ()

    result = level_engine.evaluate_level(
        Context(),
        "IR6",
        [{"status": "BLOCKED"}],
    )

    assert result["status"] == "BLOCKED"


def test_ir35_no_numeric_score_in_engine():
    class Context:
        user = "Usuario"
        response = "Respuesta"
        prior_history = ()

    result = level_engine.evaluate_level(
        Context(), "IR1", [{"status": "BLOCKED"}]
    )

    assert "score" not in result
