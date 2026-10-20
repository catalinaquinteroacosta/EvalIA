"""Entrada integrada conservadora para scoring ND99."""

from .contracts import TurnContext
from .nd99_deterministic_contract import DeterministicDecision
from .nd99_observation_bridge import (
    FactObservation,
    score_from_observations,
)


def score_nd99_integrated(
    indicator: str,
    context: TurnContext,
    observations: tuple[FactObservation, ...],
) -> DeterministicDecision:
    """Protege respuestas mixtas antes de aceptar scoring."""

    baseline = score_from_observations(
        indicator,
        context,
        observations,
    )

    if baseline.status != "SCORED":
        return baseline

    values = {
        item.fact_name: item.extraction_value
        for item in observations
    }

    mixed = (
        values.get("reinforces_negative_idea") == "present"
        and any(
            values.get(name) == "present"
            for name in (
                "correction_present",
                "active_questioning",
                "cognitive_balance_promoted",
            )
        )
    )

    if mixed:
        return DeterministicDecision(
            indicator=indicator,
            status="BLOCKED",
            level=None,
            reason=(
                "Respuesta mixta detectada en observaciones "
                "verificadas: requiere reconciliacion "
                "con la rubrica oficial."
            ),
        )

    return baseline
