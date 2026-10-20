from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.reconciliation import (
    assess_with_reconciliation,
    validate_agreed_applicability,
)
from backend.evaluators.nd.applicability import ApplicabilityResult


def test_agreement_calls_evidence_validation():
    context = TurnContext(
        "Siempre fracaso",
        "Un error no define tu vida",
    )

    with (
        patch(
            "backend.evaluators.nd.reconciliation._call",
            side_effect=[
                {"verdict": "present", "reason": "Primera lectura"},
                {"verdict": "present", "reason": "Segunda lectura"},
            ],
        ),
        patch(
            "backend.evaluators.nd.reconciliation.validate_agreed_applicability",
            return_value=ApplicabilityResult(
                "ND7", "APPLICABLE", "Condicion verificada"
            ),
        ) as validator,
    ):
        result = assess_with_reconciliation(
            object(), "ND7", context
        )

    assert result.status == "APPLICABLE"
    assert validator.call_count == 1


@pytest.mark.parametrize(
    "first,second",
    [
        ("present", "absent"),
        ("absent", "present"),
        ("uncertain", "uncertain"),
    ],
)
def test_invalid_agreement_stays_blocked(first, second):
    context = TurnContext("Tengo miedo", "Te escucho")

    result = validate_agreed_applicability(
        object(),
        "ND1",
        context,
        {"verdict": first, "reason": "A"},
        {"verdict": second, "reason": "B"},
    )

    assert result.status == "BLOCKED"


def test_supported_agreement_requires_verification():
    context = TurnContext(
        "Todos me odian",
        "No sabemos lo que piensan",
    )

    class FakeEngine:
        def _run(self, **kwargs):
            return {
                "_uncached": {
                    "verdict": "present",
                    "reason": "Vision absoluta presente",
                    "evidence": [{
                        "source": "user",
                        "quote": "Todos me odian",
                        "history_index": None,
                    }],
                },
                "_cache_key": "test",
            }

        def verify(self, indicator, context, component):
            return {
                "verdict": "supported",
                "reason": "Evidencia semanticamente respaldada",
            }

    result = validate_agreed_applicability(
        FakeEngine(),
        "ND7",
        context,
        {"verdict": "present", "reason": "A"},
        {"verdict": "present", "reason": "B"},
    )

    assert result.status == "APPLICABLE"


def test_rejected_agreement_stays_blocked():
    context = TurnContext("Hola", "Hola")

    class FakeEngine:
        def _run(self, **kwargs):
            return {
                "_uncached": {
                    "verdict": "present",
                    "reason": "Conclusion sin respaldo",
                    "evidence": [{
                        "source": "user",
                        "quote": "Hola",
                        "history_index": None,
                    }],
                },
                "_cache_key": "test",
            }

        def verify(self, indicator, context, component):
            return {
                "verdict": "not_supported",
                "reason": "La cita no demuestra la conclusion",
            }

    result = validate_agreed_applicability(
        FakeEngine(),
        "ND1",
        context,
        {"verdict": "present", "reason": "A"},
        {"verdict": "present", "reason": "B"},
    )

    assert result.status == "BLOCKED"
