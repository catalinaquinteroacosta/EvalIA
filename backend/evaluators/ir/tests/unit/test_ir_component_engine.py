import pytest

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core.component_engine import (
    COMPONENTS,
    build_payload,
    extract_components,
    verify_components,
)


def test_all_official_indicators_covered():
    assert set(COMPONENTS) == {
        f"IR{i}" for i in range(1, 9)
    }


def test_payload_uses_current_turn():
    ctx = Context(user="Estoy triste", response="Te escucho")
    payload = build_payload(ctx, "IR1")

    assert payload["current_user"] == "Estoy triste"
    assert payload["current_response"] == "Te escucho"
    assert payload["prior_history"] == []


def test_positive_requires_response_evidence(monkeypatch):
    ctx = Context(user="Pensé que fallé", response="Hola")

    monkeypatch.setattr(
        "backend.evaluators.ir.core.component_engine.ask_openai",
        lambda *_: {
            "components": [{
                "component": COMPONENTS["IR1"][0],
                "present": True,
                "evidence": [],
                "explanation": "Presente",
            }]
        },
    )

    with pytest.raises(ValueError):
        extract_components(ctx, "IR1")


def test_verified_positive():
    ctx = Context(user="Pensé que fallé", response="Es una interpretación")

    extracted = [{
        "component": COMPONENTS["IR1"][0],
        "present": True,
        "evidence": [{
            "source": "response",
            "quote": "Es una interpretación",
            "history_index": None,
        }],
        "explanation": "Identifica pensamiento",
    }]

    from backend.evaluators.ir.core import component_engine

    original = component_engine.ask_openai

    try:
        component_engine.ask_openai = lambda *_: {
            "results": [{
                "component": COMPONENTS["IR1"][0],
                "status": "supported",
                "reason": "La cita respalda el componente",
            }]
        }

        result = verify_components(ctx, "IR1", extracted)
    finally:
        component_engine.ask_openai = original

    assert result[0]["status"] == "supported"


def test_verification_disagreement_blocks(monkeypatch):
    ctx = Context(user="Pensé que fallé", response="Hola")

    extracted = [{
        "component": COMPONENTS["IR1"][0],
        "present": False,
        "evidence": [],
        "explanation": "Ausente",
    }]

    monkeypatch.setattr(
        "backend.evaluators.ir.core.component_engine.ask_openai",
        lambda *_: {
            "results": [{
                "component": COMPONENTS["IR1"][0],
                "status": "unsupported",
                "reason": "Discrepancia",
            }]
        },
    )

    result = verify_components(ctx, "IR1", extracted)

    assert result[0]["status"] == "BLOCKED"