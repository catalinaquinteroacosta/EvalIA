"""Puerta deterministica ND99 sin seleccion LLM de nivel."""

from .contracts import NDResult, TurnContext
from .official_rubric import load_official_nd_rubric
from .nd99_integrated_scoring import score_nd99_integrated
from .nd99_observation_bridge import FactObservation


def score_nd99_production_gate(
    indicator: str,
    context: TurnContext,
    observations: tuple[FactObservation, ...],
) -> NDResult:
    if indicator != "ND1":
        from .nd1_official import ComponentReview
        from .docx_components import score
        if all(isinstance(item, ComponentReview) for item in observations):
            return score(indicator, context, observations)
        return NDResult(indicator, "BLOCKED", None,
                        "Hechos genéricos AD-04 no acreditan el constructo individual DOCX; se requieren componentes verificados")
    if indicator == "ND1":
        from .nd1_official import ComponentReview, score_nd1
        if all(isinstance(item, ComponentReview) for item in observations):
            return score_nd1(context, observations)
        return NDResult(indicator="ND1", status="BLOCKED", score=None,
                        reason="ND1 requiere componentes DOCX verificados; hechos AD-04 antiguos insuficientes")

    rubric = load_official_nd_rubric()

    if indicator not in rubric.indicators:
        raise ValueError("Indicador fuera de AD-04")

    decision = score_nd99_integrated(
        indicator,
        context,
        observations,
    )

    if decision.indicator != indicator:
        raise ValueError("Indicador de decision inconsistente")

    if decision.status != "SCORED":
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason=decision.reason,
        )

    if type(decision.level) is not int:
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason="Nivel deterministico no valido",
        )

    descriptor = rubric.levels.get(str(decision.level))

    if descriptor is None:
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason="Nivel fuera de la rubrica oficial",
        )

    return NDResult(
        indicator=indicator,
        status="SCORED",
        score=decision.level,
        reason=descriptor + " | " + decision.reason,
    )
