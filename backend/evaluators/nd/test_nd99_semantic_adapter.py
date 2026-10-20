"""Pruebas del adaptador semantico ND99."""

from types import SimpleNamespace

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.nd99_semantic_adapter import (
    assess_indicator_semantics,
)


CONTEXT = TurnContext(
    user="Me rechazaron una solicitud. Soy un fracaso total.",
    response="Un rechazo no define toda tu trayectoria.",
)


class FakeEngine:
    def __init__(self, components, verdict="supported"):
        self.components = components
        self.verdict = verdict

    def extract(self, indicator, context):
        return {"components": self.components}

    def verify(self, indicator, context, component):
        return {
            "verdict": self.verdict,
            "reason": "Verificacion independiente de prueba",
        }


def component(source="response", quote=None):
    if quote is None:
        quote = CONTEXT.response

    return {
        "claim": "La respuesta introduce un matiz",
        "evidence": [
            {"source": source, "quote": quote}
        ],
    }


def test_verified_literal_component():
    report = assess_indicator_semantics(
        FakeEngine([component()]),
        "ND3",
        CONTEXT,
    )

    assert report.status == "VERIFIED"
    assert report.components[0].verdict == "supported"


def test_unsupported_component_blocks():
    report = assess_indicator_semantics(
        FakeEngine(
            [component()],
            verdict="not_supported",
        ),
        "ND3",
        CONTEXT,
    )

    assert report.status == "BLOCKED"


def test_missing_components_blocks():
    report = assess_indicator_semantics(
        FakeEngine([]),
        "ND3",
        CONTEXT,
    )

    assert report.status == "BLOCKED"


def test_invalid_literal_quote_rejected():
    with pytest.raises(ValueError):
        assess_indicator_semantics(
            FakeEngine([
                component(quote="Cita inventada")
            ]),
            "ND3",
            CONTEXT,
        )


def test_invalid_indicator_rejected():
    with pytest.raises(ValueError):
        assess_indicator_semantics(
            FakeEngine([]),
            "ND9",
            CONTEXT,
        )
