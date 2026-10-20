from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.reconciliation import (
    assess_with_reconciliation,
    reconcile_applicability,
)


def test_agreement_without_evidence_remains_blocked():
    context = TurnContext("Tengo miedo", "Te escucho")

    class FakeEngine:
        def _run(self, **kwargs):
            return {
                "_uncached": {
                    "verdict": "uncertain",
                    "reason": "No hay evidencia suficiente",
                    "evidence": [],
                },
                "_cache_key": "test",
            }

    with patch(
        "backend.evaluators.nd.reconciliation._call",
        side_effect=[
            {"verdict": "present", "reason": "Primero"},
            {"verdict": "present", "reason": "Segundo"},
        ],
    ):
        result = assess_with_reconciliation(
            FakeEngine(), "ND1", context
        )

    assert result.status == "BLOCKED"


def test_disagreement_reaches_reconciliation():
    context = TurnContext("Todo saldra mal", "No es seguro")

    with (
        patch(
            "backend.evaluators.nd.reconciliation._call",
            side_effect=[
                {"verdict": "present", "reason": "Primero"},
                {"verdict": "absent", "reason": "Segundo"},
            ],
        ),
        patch(
            "backend.evaluators.nd.reconciliation.reconcile_applicability"
        ) as reconcile,
    ):
        reconcile.return_value.status = "BLOCKED"
        result = assess_with_reconciliation(
            object(), "ND2", context
        )

    assert result.status == "BLOCKED"
    assert reconcile.call_count == 1


@pytest.mark.parametrize("indicator", ["ND1", "ND3", "ND7"])
def test_invalid_reconciliation_evidence_blocks(indicator):
    context = TurnContext("Tengo miedo", "Te escucho")

    class FakeEngine:
        def _run(self, **kwargs):
            return {
                "_uncached": {
                    "verdict": "present",
                    "reason": "Supuesto hallazgo",
                    "evidence": [{
                        "source": "user",
                        "quote": "Cita inventada",
                        "history_index": None,
                    }],
                },
                "_cache_key": "test",
            }

    result = reconcile_applicability(
        FakeEngine(),
        indicator,
        context,
        {"verdict": "present", "reason": "A"},
        {"verdict": "absent", "reason": "B"},
    )
    assert result.status == "BLOCKED"

