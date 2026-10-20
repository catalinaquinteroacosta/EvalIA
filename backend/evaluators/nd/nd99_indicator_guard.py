"""Vinculacion explicita de observaciones con AD-04."""

from dataclasses import dataclass

from .contracts import ND_CODES, TurnContext
from .official_rubric import load_official_nd_rubric
from .nd99_observation_bridge import FactObservation
from .nd99_production_gate import score_nd99_production_gate
from .contracts import NDResult


@dataclass(frozen=True)
class IndicatorObservationBatch:
    indicator: str
    official_question: str
    observations: tuple[FactObservation, ...]
    indicator_specific_reviewed: bool


def score_indicator_batch(
    indicator: str,
    context: TurnContext,
    batch: IndicatorObservationBatch,
) -> NDResult:
    rubric = load_official_nd_rubric()

    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    def blocked(reason):
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason=reason,
        )

    if batch.indicator != indicator:
        return blocked("Observaciones de otro indicador")

    official_question = rubric.indicators[indicator]["question"]

    if batch.official_question != official_question:
        return blocked("Pregunta oficial no coincide")

    if not batch.indicator_specific_reviewed:
        return blocked(
            "No consta revision especifica del indicador"
        )

    return score_nd99_production_gate(
        indicator,
        context,
        batch.observations,
    )
