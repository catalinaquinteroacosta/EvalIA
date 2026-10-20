"""Pruebas del puente ND99."""

from dataclasses import replace

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.nd99_observation_bridge import (
    FactObservation,
    score_from_observations,
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
                CONTEXT.response
                if value == "present" else ""
            ),
            verification_quote=(
                CONTEXT.response
                if value == "present" else ""
            ),
            extraction_reason="Evaluacion semantica",
            verification_reason="Verificacion independiente",
            full_response_examined=True,
        )
        for name, value in values.items()
    )


def test_level_two():
    result = score_from_observations(
        "ND3", CONTEXT, observations()
    )
    assert result.status == "SCORED"
    assert result.level == 2


def test_disagreement_blocks():
    items = list(observations())
    items[0] = replace(
        items[0],
        verification_value="present",
    )
    result = score_from_observations(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_uncertainty_blocks():
    items = list(observations())
    items[0] = replace(
        items[0],
        extraction_value="uncertain",
        verification_value="uncertain",
    )
    result = score_from_observations(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_invalid_quote_blocks():
    items = list(observations())
    items[2] = replace(
        items[2],
        extraction_quote="Texto inexistente",
    )
    result = score_from_observations(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_missing_fact_blocks():
    result = score_from_observations(
        "ND3", CONTEXT, observations()[:-1]
    )
    assert result.status == "BLOCKED"


def test_incomplete_review_blocks():
    items = list(observations())
    items[1] = replace(
        items[1],
        full_response_examined=False,
    )
    result = score_from_observations(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"
