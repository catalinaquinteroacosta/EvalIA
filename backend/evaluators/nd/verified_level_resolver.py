"""Resolver ND: evidencia y acuerdo antes de puntuar.

No decide aplicabilidad.
No interpreta niveles con reglas regex.
"""

from __future__ import annotations

from .contracts import ND_CODES, TurnContext
from .deterministic_scoring import VerifiedLevel
from .level_semantic import assess_nd_level
from .scoring_semantic import (
    extract_and_verify_scoring_components,
)


def resolve_verified_nd_level(
    engine,
    indicator: str,
    context: TurnContext,
) -> VerifiedLevel:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    report = extract_and_verify_scoring_components(
        engine,
        indicator,
        context,
    )

    if report.status != "VERIFIED":
        return VerifiedLevel(
            indicator=indicator,
            level="0",
            extraction_verdict="ambiguous",
            independent_verdict="ambiguous",
            reason=(
                "BLOCKED: componentes sin verificacion "
                "independiente suficiente"
            ),
        )

    agreement = assess_nd_level(
        engine,
        indicator,
        context,
        report,
    )

    if agreement.status != "AGREED":
        return VerifiedLevel(
            indicator=indicator,
            level="0",
            extraction_verdict="ambiguous",
            independent_verdict="ambiguous",
            reason=(
                "BLOCKED: " + agreement.reason
            ),
        )

    return VerifiedLevel(
        indicator=indicator,
        level=agreement.level,
        extraction_verdict="supported",
        independent_verdict="supported",
        reason=(
            "Descriptor AD-04 verificado mediante "
            "componentes confirmados: "
            + str(agreement.component_ids)
        ),
    )
