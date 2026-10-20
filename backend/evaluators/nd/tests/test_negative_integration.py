"""Integracion de validacion negativa en reconciliacion ND."""

from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.reconciliation import (
    reconcile_applicability,
)


class FakeEngine:
    def __init__(self, verdict):
        self.verdict = verdict
        self.verify_calls = 0

    def _run(self, **kwargs):
        return {
            "_uncached": {
                "verdict": self.verdict,
                "reason": "Decision semantica",
                "evidence": [],
            },
            "_cache_key": "test",
        }

    def verify(self, *args):
        self.verify_calls += 1
        return {
            "verdict": "supported",
            "reason": "Verificado",
        }


@pytest.mark.parametrize(
    "indicator",
    [f"ND{i}" for i in range(1, 9)],
)
def test_negative_supported_allows_na(indicator):
    context = TurnContext("Hola", "Hola")
    engine = FakeEngine("absent")

    with patch(
        "backend.evaluators.nd.negative_validation."
        "validate_negative_applicability",
        return_value={
            "verdict": "supported",
            "reason": "Ausencia comprobada",
        },
    ) as validator:
        result = reconcile_applicability(
            engine, indicator, context,
            {"verdict": "absent", "reason": "A"},
            {"verdict": "absent", "reason": "B"},
        )

    assert result.status == "NA"
    assert validator.call_count == 1
    assert engine.verify_calls == 0


@pytest.mark.parametrize(
    "negative_verdict",
    ["not_supported", "ambiguous"],
)
def test_negative_without_support_blocks(negative_verdict):
    context = TurnContext(
        "Todos me odian",
        "No podemos saberlo",
    )
    engine = FakeEngine("absent")

    with patch(
        "backend.evaluators.nd.negative_validation."
        "validate_negative_applicability",
        return_value={
            "verdict": negative_verdict,
            "reason": "No se confirma ausencia",
        },
    ):
        result = reconcile_applicability(
            engine, "ND7", context,
            {"verdict": "absent", "reason": "A"},
            {"verdict": "absent", "reason": "B"},
        )

    assert result.status == "BLOCKED"


def test_positive_without_evidence_blocks():
    context = TurnContext(
        "Siempre fracaso",
        "Un error no define tu vida",
    )
    engine = FakeEngine("present")

    result = reconcile_applicability(
        engine, "ND7", context,
        {"verdict": "present", "reason": "A"},
        {"verdict": "present", "reason": "B"},
    )

    assert result.status == "BLOCKED"
    assert engine.verify_calls == 0
