import pytest

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import reconciliation as rec


def test_ir7_rejects_invented_obligation(monkeypatch):
    ctx = Context(
        "Mi jefe no responde.",
        "No sé todavía por qué no respondió."
    )

    monkeypatch.setattr(
        rec, "ask_openai",
        lambda system, payload: {
            "results": [{
                "id": "IR7_missing",
                "verdict": "unsupported",
                "reason": (
                    "No es obligatorio mencionar "
                    "explícitamente el optimismo."
                ),
                "quote": ""
            }]
        }
    )

    result = rec.reconcile(
        ctx, "IR7",
        [{
            "id": "IR7_missing",
            "claim": "Debe mencionar que evita el optimismo."
        }]
    )

    assert result[0]["verdict"] == "unsupported"


def test_ir6_rejects_nonliteral_support(monkeypatch):
    ctx = Context("Usuario", "¿Cómo cambia tu ansiedad?")

    monkeypatch.setattr(
        rec, "ask_openai",
        lambda system, payload: {
            "results": [{
                "id": "IR6_utility",
                "verdict": "supported",
                "reason": "Afirma utilidad.",
                "quote": "¿Este pensamiento te resulta útil?"
            }]
        }
    )

    with pytest.raises(ValueError):
        rec.reconcile(
            ctx, "IR6",
            [{
                "id": "IR6_utility",
                "claim": "Explora utilidad."
            }]
        )


def test_ambiguous_remains_ambiguous(monkeypatch):
    ctx = Context("Usuario", "Respuesta")

    monkeypatch.setattr(
        rec, "ask_openai",
        lambda system, payload: {
            "results": [{
                "id": "x",
                "verdict": "ambiguous",
                "reason": "Evidencia insuficiente.",
                "quote": ""
            }]
        }
    )

    result = rec.reconcile(
        ctx, "IR6",
        [{"id": "x", "claim": "Utilidad"}]
    )

    assert result[0]["verdict"] == "ambiguous"


def test_missing_decision_rejected(monkeypatch):
    ctx = Context("Usuario", "Respuesta")

    monkeypatch.setattr(
        rec, "ask_openai",
        lambda system, payload: {
            "results": []
        }
    )

    with pytest.raises(ValueError):
        rec.reconcile(
            ctx, "IR1",
            [{"id": "x", "claim": "Pensamiento"}]
        )