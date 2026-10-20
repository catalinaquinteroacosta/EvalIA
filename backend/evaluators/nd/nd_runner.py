"""Punto de entrada integrado de la familia ND."""

from __future__ import annotations

from .contracts import TurnContext
from .family_orchestrator import evaluate_nd_family
from .safe_level_resolver import resolve_safe_nd_level
from .semantic_engine import NDSemanticEngine


def run_nd_family(
    context: TurnContext,
    *,
    engine=None,
):
    if engine is None:
        engine = NDSemanticEngine()

    def level_resolver(indicator, current_context):
        return resolve_safe_nd_level(
            engine,
            indicator,
            current_context,
        )

    return evaluate_nd_family(
        context,
        applicability_engine=engine,
        level_resolver=level_resolver,
    )
