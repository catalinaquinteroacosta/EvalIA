"""Pruebas adversariales de aplicabilidad ND.

Sin llamadas reales a OpenAI.
"""

from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.reconciliation import (
    reconcile_applicability,
    validate_agreed_applicability,
)


class FakeEngine:
    def __init__(self, verdict, evidence, verification):
        self.verdict = verdict
        self.evidence = evidence
        self.verification = verification
        self.verify_calls = 0

    def _run(self, **kwargs):
        return {
            "_uncached": {
                "verdict": self.verdict,
                "reason": "Conclusion semantica simulada",
                "evidence": self.evidence,
            },
            "_cache_key": "test",
        }

    def verify(self, indicator, context, component):
        self.verify_calls += 1
        return {
            "verdict": self.verification,
            "reason": "Verificacion independiente",
        }


def evidence(source, quote, index=None):
    return [{
        "source": source,
        "quote": quote,
        "history_index": index,
    }]


@pytest.mark.parametrize(
    "indicator,verdict",
    [
        ("ND1", "present"),
        ("ND2", "present"),
        ("ND7", "present"),
        ("ND3", "absent"),
        ("ND4", "absent"),
        ("ND5", "absent"),
        ("ND6", "absent"),
        ("ND8", "absent"),
    ],
)
def test_rejected_semantic_claim_is_blocked(indicator, verdict):
    context = TurnContext(
        "Estoy preocupado",
        "Entiendo tu preocupacion",
    )

    engine = FakeEngine(
        verdict,
        evidence("user", "Estoy preocupado"),
        "not_supported",
    )

    with patch(
        "backend.evaluators.nd.negative_validation."
        "validate_negative_applicability",
        return_value={
            "verdict": "not_supported",
            "reason": "Ausencia no respaldada",
        },
    ) as negative_validator:
        result = validate_agreed_applicability(
            engine,
            indicator,
            context,
            {"verdict": verdict, "reason": "Primera lectura"},
            {"verdict": verdict, "reason": "Segunda lectura"},
        )

    assert result.status == "BLOCKED"

    if verdict == "absent":
        assert negative_validator.call_count == 1
        assert engine.verify_calls == 0
    else:
        assert negative_validator.call_count == 0
        assert engine.verify_calls == 1


@pytest.mark.parametrize("indicator", ["ND1", "ND2", "ND7"])
def test_invented_quote_never_makes_indicator_applicable(indicator):
    context = TurnContext(
        "Tengo una preocupacion",
        "Te escucho",
    )

    engine = FakeEngine(
        "present",
        evidence("user", "Todo sera una catastrofe"),
        "supported",
    )

    result = reconcile_applicability(
        engine,
        indicator,
        context,
        {"verdict": "present", "reason": "A"},
        {"verdict": "absent", "reason": "B"},
    )

    assert result.status == "BLOCKED"
    assert engine.verify_calls == 0


@pytest.mark.parametrize("indicator", ["ND3", "ND4", "ND5", "ND6", "ND8"])
def test_empty_evidence_cannot_produce_na(indicator):
    context = TurnContext("Hola", "Hola")

    engine = FakeEngine(
        "absent",
        [],
        "supported",
    )

    result = validate_agreed_applicability(
        engine,
        indicator,
        context,
        {"verdict": "absent", "reason": "A"},
        {"verdict": "absent", "reason": "B"},
    )

    assert result.status == "BLOCKED"
    assert engine.verify_calls == 0


def test_wrong_history_index_is_blocked():
    context = TurnContext("Estoy preocupado", "Te escucho")

    engine = FakeEngine(
        "present",
        evidence("history", "Siempre fracaso", 99),
        "supported",
    )

    result = reconcile_applicability(
        engine,
        "ND7",
        context,
        {"verdict": "present", "reason": "A"},
        {"verdict": "absent", "reason": "B"},
    )

    assert result.status == "BLOCKED"
    assert engine.verify_calls == 0

