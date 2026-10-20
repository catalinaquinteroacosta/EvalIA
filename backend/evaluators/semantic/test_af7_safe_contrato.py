"""Controles offline del contrato AF7.SAFE."""

import pytest
from backend.evaluators.semantic import af_ai_af7 as af7


@pytest.mark.parametrize(
    "procedure, quote",
    [
        (
            "anotar preocupaciones y programar su revisi?n",
            "Anota tus preocupaciones y rev?salas ma?ana.",
        ),
        (
            "respirar deliberadamente hasta marearse",
            "Respira muy r?pido hasta que te marees.",
        ),
    ],
)
def test_safe_transmite_procedimiento_literal(
    monkeypatch, procedure, quote
):
    received = []

    def inspect(**kwargs):
        received.append(kwargs)
        return {
            "status": "ambiguous",
            "reason": "Prueba de transmisi?n, no de seguridad",
        }

    monkeypatch.setattr(
        af7, "validate_semantic_entailment", inspect
    )

    result = af7._validate_safe(
        item={
            "procedure": procedure,
            "procedure_evidence": {
                "quote": quote,
                "source": "current_ai",
            },
        },
        current_ai=quote,
        model="TEST",
        timeout=1,
    )

    assert result["status"] == "ambiguous"
    assert len(received) == 1
    assert received[0]["evidence"] == quote
    assert received[0]["local_context"] == quote


def test_safe_rechaza_cita_no_literal(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError(
            "No debe validar evidencia inventada"
        )

    monkeypatch.setattr(
        af7, "validate_semantic_entailment", forbidden
    )

    result = af7._validate_safe(
        item={
            "procedure": "anotar preocupaciones",
            "procedure_evidence": {
                "quote": "Anota tus preocupaciones.",
                "source": "current_ai",
            },
        },
        current_ai="Puedes descansar.",
        model="TEST",
        timeout=1,
    )

    assert result["status"] == "not_supported"
