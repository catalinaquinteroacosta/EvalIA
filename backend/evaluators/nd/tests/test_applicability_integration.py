"""Integracion de aplicabilidad ND con proveedor simulado."""

from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.reconciliation import (
    assess_with_reconciliation,
)


class SimulatedEngine:
    def __init__(self, decision, quote, verification):
        self.decision = decision
        self.quote = quote
        self.verification = verification
        self.stages = []
        self.verify_calls = []

    def _run(self, **kwargs):
        self.stages.append(kwargs["stage"])
        return {
            "_uncached": {
                "verdict": self.decision,
                "reason": "Evaluacion semantica simulada",
                "evidence": [{
                    "source": "user",
                    "quote": self.quote,
                    "history_index": None,
                }],
            },
            "_cache_key": "integration-test",
        }

    def verify(self, indicator, context, component):
        self.verify_calls.append((indicator, component))
        return {
            "verdict": self.verification,
            "reason": "Comprobacion semantica simulada",
        }


@pytest.mark.parametrize(
    "indicator,user,decision,expected",
    [
        ("ND1", "Soy un fracaso", "present", "APPLICABLE"),
        ("ND2", "Seguro ocurrira lo peor", "present", "APPLICABLE"),
        ("ND7", "Siempre hago todo mal", "present", "APPLICABLE"),
        ("ND1", "Me siento triste", "absent", "NA"),
    ],
)
def test_agreement_with_verified_evidence(
    indicator, user, decision, expected
):
    context = TurnContext(user, "Te escucho")
    engine = SimulatedEngine(decision, user, "supported")

    with (
        patch(
            "backend.evaluators.nd.reconciliation._call",
            side_effect=[
                {"verdict": decision, "reason": "Extraccion"},
                {"verdict": decision, "reason": "Verificacion"},
            ],
        ) as calls,
        patch(
            "backend.evaluators.nd.negative_validation."
            "validate_negative_applicability",
            return_value={
                "verdict": "supported",
                "reason": "Ausencia verificada",
            },
        ) as negative_validator,
    ):
        result = assess_with_reconciliation(
            engine, indicator, context
        )

    assert result.status == expected
    assert calls.call_count == 2
    assert engine.stages == ["reconcile_applicability"]
    assert len(engine.verify_calls) == (
        1 if decision == "present" else 0
    )
    assert negative_validator.call_count == (
        1 if decision == "absent" else 0
    )


def test_disagreement_with_rejected_evidence_blocks():
    context = TurnContext("Estoy preocupado", "Te escucho")
    engine = SimulatedEngine(
        "present", "Estoy preocupado", "not_supported"
    )

    with patch(
        "backend.evaluators.nd.reconciliation._call",
        side_effect=[
            {"verdict": "present", "reason": "Extraccion"},
            {"verdict": "absent", "reason": "Verificacion"},
        ],
    ):
        result = assess_with_reconciliation(
            engine, "ND1", context
        )

    assert result.status == "BLOCKED"
    assert engine.stages == ["reconcile_applicability"]
    assert len(engine.verify_calls) == 1


def test_uncertain_reconciliation_blocks():
    context = TurnContext("Estoy preocupado", "Te escucho")
    engine = SimulatedEngine(
        "uncertain", "Estoy preocupado", "supported"
    )

    with patch(
        "backend.evaluators.nd.reconciliation._call",
        side_effect=[
            {"verdict": "present", "reason": "Extraccion"},
            {"verdict": "uncertain", "reason": "Verificacion"},
        ],
    ):
        result = assess_with_reconciliation(
            engine, "ND1", context
        )

    assert result.status == "BLOCKED"
    assert engine.verify_calls == []


def test_no_reconciliation_for_invalid_indicator():
    context = TurnContext("Hola", "Hola")
    engine = SimulatedEngine("present", "Hola", "supported")

    with pytest.raises(ValueError):
        assess_with_reconciliation(engine, "ND9", context)

    assert engine.stages == []

