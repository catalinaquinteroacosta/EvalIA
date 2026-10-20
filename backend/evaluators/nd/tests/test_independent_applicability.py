"""Garantias de independencia en aplicabilidad ND."""

from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.applicability import ApplicabilityResult
from backend.evaluators.nd.reconciliation import (
    assess_with_reconciliation,
)


@pytest.mark.parametrize(
    "indicator",
    ["ND1", "ND2", "ND3", "ND4", "ND5", "ND6", "ND7", "ND8"],
)
def test_verifier_does_not_receive_extractor_result(indicator):
    context = TurnContext(
        "Siempre hago todo mal",
        "Un error no define todo lo que haces",
    )

    with (
        patch(
            "backend.evaluators.nd.reconciliation._call",
            side_effect=[
                {"verdict": "present", "reason": "Extractor"},
                {"verdict": "present", "reason": "Verificador"},
            ],
        ) as calls,
        patch(
            "backend.evaluators.nd.reconciliation."
            "validate_agreed_applicability",
            return_value=ApplicabilityResult(
                indicator, "BLOCKED", "Prueba aislada"
            ),
        ),
    ):
        assess_with_reconciliation(
            object(), indicator, context
        )

    assert calls.call_count == 2

    first_kwargs = calls.call_args_list[0].kwargs
    second_kwargs = calls.call_args_list[1].kwargs

    assert first_kwargs == {}
    assert second_kwargs == {}

    first_args = calls.call_args_list[0].args
    second_args = calls.call_args_list[1].args

    assert first_args[3] == "extract_applicability"
    assert second_args[3] == "verify_applicability"


def test_disagreement_reconciles_only_after_both_reads():
    context = TurnContext(
        "Todos me rechazan",
        "No sabemos lo que piensan todos",
    )
    events = []

    def fake_call(*args, **kwargs):
        events.append(args[3])
        if args[3] == "extract_applicability":
            return {"verdict": "present", "reason": "A"}
        return {"verdict": "absent", "reason": "B"}

    def fake_reconcile(*args, **kwargs):
        events.append("reconcile")
        return ApplicabilityResult(
            "ND7", "BLOCKED", "Conflicto pendiente"
        )

    with (
        patch(
            "backend.evaluators.nd.reconciliation._call",
            side_effect=fake_call,
        ),
        patch(
            "backend.evaluators.nd.reconciliation."
            "reconcile_applicability",
            side_effect=fake_reconcile,
        ),
    ):
        result = assess_with_reconciliation(
            object(), "ND7", context
        )

    assert events == [
        "extract_applicability",
        "verify_applicability",
        "reconcile",
    ]
    assert result.status == "BLOCKED"
