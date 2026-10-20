from unittest.mock import patch

import pytest

from backend.evaluators.nd.contracts import (
    ND_CODES,
    ND_CONDITIONAL,
    TurnContext,
)
from backend.evaluators.nd.applicability_semantic import (
    _applicability_payload,
    assess_applicability,
)
from backend.evaluators.nd.applicability import ApplicabilityResult


@pytest.mark.parametrize("indicator", ND_CODES)
@pytest.mark.parametrize(
    "first,second,expected",
    [
        ("present", "present", "APPLICABLE"),
        ("absent", "absent", "NA"),
        ("present", "absent", "BLOCKED"),
        ("absent", "present", "BLOCKED"),
        ("uncertain", "present", "BLOCKED"),
        ("present", "uncertain", "BLOCKED"),
    ],
)
def test_semantic_agreement(
    indicator, first, second, expected
):
    context = TurnContext(
        user="Me preocupa lo que sucedio",
        response="Entiendo tu preocupacion",
    )

    responses = [
        {"verdict": first, "reason": "Primer analisis"},
        {
            "verdict": second,
            "reason": "Verificacion independiente",
        },
    ]

    # Se simulan las dos extracciones independientes,
    # pero la decision final pasa por el protocolo
    # de validacion/reconciliacion.
    with (
        patch(
            "backend.evaluators.nd.reconciliation._call",
            side_effect=responses,
        ) as mocked,
        patch(
            "backend.evaluators.nd.reconciliation."
            "validate_agreed_applicability",
            return_value=ApplicabilityResult(
                indicator,
                expected,
                "Resultado simulado del protocolo",
            ),
        ) as agreed,
        patch(
            "backend.evaluators.nd.reconciliation."
            "reconcile_applicability",
            return_value=ApplicabilityResult(
                indicator,
                expected,
                "Resultado simulado de reconciliacion",
            ),
        ) as reconciled,
    ):
        result = assess_applicability(
            object(), indicator, context
        )

    assert result.status == expected
    assert mocked.call_count == 2

    assert mocked.call_args_list[0].args[3] == (
        "extract_applicability"
    )
    assert mocked.call_args_list[1].args[3] == (
        "verify_applicability"
    )

    # El verificador no recibe el resultado previo.
    assert all(
        "previous" not in call.kwargs
        for call in mocked.call_args_list
    )

    if first == second and first != "uncertain":
        agreed.assert_called_once()
        reconciled.assert_not_called()
    else:
        reconciled.assert_called_once()
        agreed.assert_not_called()


@pytest.mark.parametrize("indicator", ND_CODES)
def test_applicability_context_isolation(indicator):
    context = TurnContext(
        user="Siempre hago todo mal",
        response="Esta respuesta no debe influir",
    )

    payload = _applicability_payload(
        indicator, context
    )

    assert payload["current_user"] == context.user

    if indicator in ND_CONDITIONAL:
        assert "current_response" not in payload
    else:
        assert (
            payload["current_response"]
            == context.response
        )


def test_invalid_indicator_is_rejected():
    with pytest.raises(ValueError):
        assess_applicability(
            object(),
            "ND9",
            TurnContext("Hola", "Hola"),
        )
