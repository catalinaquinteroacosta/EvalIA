"""Integracion ND99 con aplicabilidad oficial."""

from .contracts import ND_CODES, NDResult, TurnContext
from .official_rubric import load_official_nd_rubric
from .nd99_production_gate import score_nd99_production_gate


def evaluate_nd99_indicator(
    indicator: str,
    context: TurnContext,
    *,
    applicability_engine,
    observation_resolver=None,
    applicability_resolver=None,
) -> NDResult:

    rubric = load_official_nd_rubric()

    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    if indicator not in rubric.indicators:
        raise ValueError("Indicador fuera de AD-04")

    if applicability_resolver is None:
        from .reconciliation import assess_with_reconciliation
        applicability_resolver = assess_with_reconciliation

    applicability = applicability_resolver(
        applicability_engine,
        indicator,
        context,
    )

    if applicability.indicator != indicator:
        raise ValueError("Aplicabilidad inconsistente")

    if applicability.status in ("NA", "BLOCKED"):
        return NDResult(
            indicator=indicator,
            status=applicability.status,
            score=None,
            reason=applicability.reason,
        )

    if applicability.status != "APPLICABLE":
        raise ValueError("Estado de aplicabilidad desconocido")

    if observation_resolver is None:
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason="Observaciones semanticas ND99 pendientes",
        )

    observations = observation_resolver(
        indicator,
        context,
    )

    return score_nd99_production_gate(
        indicator,
        context,
        tuple(observations),
    )


def evaluate_nd99_family(
    context: TurnContext,
    *,
    applicability_engine,
    observation_resolver=None,
    applicability_resolver=None,
) -> tuple[NDResult, ...]:

    return tuple(
        evaluate_nd99_indicator(
            indicator,
            context,
            applicability_engine=applicability_engine,
            observation_resolver=observation_resolver,
            applicability_resolver=applicability_resolver,
        )
        for indicator in ND_CODES
    )
