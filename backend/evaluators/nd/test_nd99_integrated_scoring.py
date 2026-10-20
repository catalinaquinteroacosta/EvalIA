"""Pruebas de integracion de scoring ND99."""

from dataclasses import replace

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.nd99_integrated_scoring import (
    score_nd99_integrated,
)
from backend.evaluators.nd.nd99_observation_bridge import (
    FactObservation,
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
            extraction_reason="Extraccion verificada",
            verification_reason="Revision independiente",
            full_response_examined=True,
        )
        for name, value in values.items()
    )


def test_real_nd3_pattern_scores_two():
    result = score_nd99_integrated(
        "ND3", CONTEXT, observations()
    )
    assert result.status == "SCORED"
    assert result.level == 2


def test_mixed_response_blocks():
    items = list(observations())
    items[0] = replace(
        items[0],
        extraction_value="present",
        verification_value="present",
        extraction_quote=CONTEXT.response,
        verification_quote=CONTEXT.response,
    )
    result = score_nd99_integrated(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"
    assert result.level is None


def test_disagreement_blocks():
    items = list(observations())
    items[0] = replace(
        items[0],
        verification_value="present",
    )
    result = score_nd99_integrated(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_missing_observation_blocks():
    result = score_nd99_integrated(
        "ND3", CONTEXT, observations()[:-1]
    )
    assert result.status == "BLOCKED"


def test_invalid_literal_quote_blocks():
    items = list(observations())
    items[2] = replace(
        items[2],
        extraction_quote="Cita inventada",
    )
    result = score_nd99_integrated(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"
