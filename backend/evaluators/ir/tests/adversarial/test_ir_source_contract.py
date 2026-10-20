import pytest

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import component_engine


def test_invalid_source_is_rejected(monkeypatch):
    ctx = Context(
        user="Pienso que hice algo mal",
        response="Eso es una interpretaci?n",
    )

    monkeypatch.setattr(
        component_engine,
        "ask_openai",
        lambda *_: {
            "components": [{
                "component": component_engine.COMPONENTS["IR1"][0],
                "present": True,
                "evidence": [{
                    "source": "current_response",
                    "quote": "Eso es una interpretaci?n",
                    "history_index": None,
                }],
                "explanation": "Identificaci?n",
            }]
        },
    )

    with pytest.raises(ValueError, match="Fuente"):
        component_engine.extract_components(ctx, "IR1")


def test_prompt_defines_exact_source_values():
    prompt = component_engine.EXTRACTOR_SYSTEM

    assert '"user", "response", "history"' in prompt
    assert "history_index es el ?ndice base cero" in prompt
