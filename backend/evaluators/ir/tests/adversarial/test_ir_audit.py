import pytest

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import audit


def test_audit_preserves_partial_ir6(monkeypatch):
    ctx = Context(
        "Mi jefe no respondió.",
        "¿Cómo cambia tu ansiedad si piensas otra cosa?"
    )

    monkeypatch.setattr(
        audit, "ask_openai",
        lambda system, payload: {
            "supported_components": [{
                "component": "Explora influencia emocional",
                "quote": ctx.response
            }],
            "missing_components": [{
                "component": "Explorar utilidad del pensamiento",
                "reason": "No se examina si resulta útil"
            }],
            "contradictions": []
        }
    )

    result = audit.audit_indicator(ctx, "IR6")

    assert len(result["supported_components"]) == 1
    assert len(result["missing_components"]) == 1
    assert result["contradictions"] == []


def test_audit_rejects_fabricated_quote(monkeypatch):
    ctx = Context("Hola", "Entiendo.")

    monkeypatch.setattr(
        audit, "ask_openai",
        lambda system, payload: {
            "supported_components": [{
                "component": "Componente",
                "quote": "Frase inexistente"
            }],
            "missing_components": [],
            "contradictions": []
        }
    )

    with pytest.raises(ValueError):
        audit.audit_indicator(ctx, "IR1")


def test_contradiction_requires_reconciliation():
    result = audit.reconcile_findings(
        [{"verification": "supported"}],
        {
            "supported_components": [],
            "missing_components": [],
            "contradictions": [{
                "component": "Contradicción",
                "reason": "Incompatibilidad real"
            }]
        }
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_partial_does_not_automatically_block():
    result = audit.reconcile_findings(
        [{"verification": "supported"}],
        {
            "supported_components": [{
                "component": "Parte demostrada"
            }],
            "missing_components": [{
                "component": "Parte no demostrada"
            }],
            "contradictions": []
        }
    )

    assert result["status"] == "AUDITED"
    assert len(result["missing_components"]) == 1
    assert result["score"] is None


def test_ambiguity_blocks():
    result = audit.reconcile_findings(
        [{"verification": "ambiguous"}],
        {
            "supported_components": [],
            "missing_components": [],
            "contradictions": []
        }
    )

    assert result["status"] == "BLOCKED"


def test_no_components_never_implies_score_zero():
    result = audit.reconcile_findings(
        [],
        {
            "supported_components": [],
            "missing_components": [],
            "contradictions": []
        }
    )

    assert result["score"] is None
    assert result["status"] == "AUDITED"