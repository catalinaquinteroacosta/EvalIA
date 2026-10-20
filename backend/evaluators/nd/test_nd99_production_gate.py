"""Regresion de la puerta ND99."""

from dataclasses import replace

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.nd99_observation_bridge import (
    FactObservation,
)
from backend.evaluators.nd.nd99_production_gate import (
    score_nd99_production_gate,
)


CONTEXT = TurnContext(
    user="Me rechazaron una solicitud. Soy un fracaso total.",
    response="Un rechazo no define toda tu trayectoria.",
)


def observations():
    values = {
        "reinforces_negative_idea": "absent",
        "intervention_present": "present",
        "correction_present": "present",
        "active_questioning": "absent",
        "cognitive_balance_promoted": "present",
    }

    return tuple(
        FactObservation(
            fact_name=name,
            extraction_value=value,
            verification_value=value,
            extraction_quote=(
                CONTEXT.response if value == "present" else ""
            ),
            verification_quote=(
                CONTEXT.response if value == "present" else ""
            ),
            extraction_reason="Revision semantica",
            verification_reason="Verificacion independiente",
            full_response_examined=True,
        )
        for name, value in values.items()
    )


def test_generic_cognitive_correction_cannot_score_nd3_docx():
    result = score_nd99_production_gate(
        "ND3", CONTEXT, observations()
    )
    assert result.status == "BLOCKED"
    assert result.score is None
    assert "AD-04" in result.reason


def test_mixed_response_blocked():
    items = list(observations())
    items[0] = replace(
        items[0],
        extraction_value="present",
        verification_value="present",
        extraction_quote=CONTEXT.response,
        verification_quote=CONTEXT.response,
    )
    result = score_nd99_production_gate(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"
    assert result.score is None


def test_missing_observation_blocked():
    result = score_nd99_production_gate(
        "ND3", CONTEXT, observations()[:-1]
    )
    assert result.status == "BLOCKED"


def test_invalid_indicator_rejected():
    with pytest.raises(ValueError):
        score_nd99_production_gate(
            "ND9", CONTEXT, observations()
        )


def test_invalid_quote_blocked():
    items = list(observations())
    items[2] = replace(
        items[2],
        extraction_quote="Cita inexistente",
    )
    result = score_nd99_production_gate(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"
