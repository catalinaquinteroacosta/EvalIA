"""Orquestacion ND con aplicabilidad independiente.

No inventa puntuaciones. El scoring solo se habilita
cuando existe una decision de nivel verificada.
"""

from __future__ import annotations

from collections.abc import Callable

from .contracts import ND_CODES, NDResult, TurnContext
from .deterministic_scoring import (
    VerifiedLevel,
    score_verified_level,
)
from .official_rubric import load_official_nd_rubric


def evaluate_nd_indicator(
    indicator: str,
    context: TurnContext,
    *,
    applicability_engine,
    level_resolver: Callable[
        [str, TurnContext], VerifiedLevel
    ] | None = None,
) -> NDResult:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    load_official_nd_rubric()

    from .reconciliation import assess_with_reconciliation

    applicability = assess_with_reconciliation(
        applicability_engine,
        indicator,
        context,
    )

    if applicability.indicator != indicator:
        raise ValueError(
            "Aplicabilidad devuelta para otro indicador"
        )

    if applicability.status == "NA":
        return NDResult(
            indicator=indicator,
            status="NA",
            score=None,
            reason=applicability.reason,
        )

    if applicability.status == "BLOCKED":
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason=applicability.reason,
        )

    if applicability.status != "APPLICABLE":
        raise ValueError(
            "Estado de aplicabilidad desconocido"
        )

    if level_resolver is None:
        return NDResult(
            indicator=indicator,
            status="BLOCKED",
            score=None,
            reason=(
                "Aplicable, pero pendiente de extraccion "
                "y verificacion independiente del nivel AD-04"
            ),
        )

    decision = level_resolver(indicator, context)

    if not isinstance(decision, VerifiedLevel):
        raise TypeError(
            "El resolver debe entregar VerifiedLevel"
        )

    if decision.indicator != indicator:
        raise ValueError(
            "Decision de nivel para otro indicador"
        )

    return score_verified_level(decision)


def evaluate_nd_family(
    context: TurnContext,
    *,
    applicability_engine,
    level_resolver=None,
) -> tuple[NDResult, ...]:
    return tuple(
        evaluate_nd_indicator(
            indicator,
            context,
            applicability_engine=applicability_engine,
            level_resolver=level_resolver,
        )
        for indicator in ND_CODES
    )
