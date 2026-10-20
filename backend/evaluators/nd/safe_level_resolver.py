"""Puerta de seguridad para el resolver de niveles ND."""

from __future__ import annotations

from .contracts import ND_CODES, TurnContext
from .deterministic_scoring import VerifiedLevel
from .scoring_components import validate_component_evidence
from .scoring_semantic import (
    extract_and_verify_scoring_components,
    NDScoringEvidenceReport,
)
from .level_semantic import assess_nd_level


def _blocked(indicator: str, reason: str) -> VerifiedLevel:
    # El valor tecnico no se puntua: los veredictos son ambiguos.
    return VerifiedLevel(
        indicator=indicator,
        level="0",
        extraction_verdict="ambiguous",
        independent_verdict="ambiguous",
        reason="BLOCKED: " + reason,
    )


def resolve_safe_nd_level(
    engine,
    indicator: str,
    context: TurnContext,
) -> VerifiedLevel:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    report = extract_and_verify_scoring_components(
        engine, indicator, context
    )

    if not isinstance(report, NDScoringEvidenceReport):
        return _blocked(indicator, "Reporte no verificable")

    if report.indicator != indicator:
        return _blocked(indicator, "Indicador inconsistente")

    if report.status != "VERIFIED" or report.unresolved:
        return _blocked(
            indicator, "Componentes pendientes de verificacion"
        )

    if not report.confirmed:
        return _blocked(
            indicator, "Sin componentes confirmados"
        )

    for component in report.confirmed:
        if component.indicator != indicator:
            return _blocked(
                indicator, "Componente de otro indicador"
            )

        if not validate_component_evidence(component, context):
            return _blocked(
                indicator, "Cita literal no verificable"
            )

    agreement = assess_nd_level(
        engine, indicator, context, report
    )

    if agreement.status != "AGREED":
        return _blocked(
            indicator, "Correspondencia de nivel no resuelta"
        )

    if agreement.level not in ("0", "1", "2", "3"):
        return _blocked(
            indicator, "Nivel fuera de rubrica"
        )

    if not agreement.component_ids:
        return _blocked(
            indicator, "Nivel sin componentes respaldados"
        )

    if any(
        type(index) is not int
        or index < 0
        or index >= len(report.confirmed)
        for index in agreement.component_ids
    ):
        return _blocked(
            indicator, "Referencias de evidencia invalidas"
        )

    return VerifiedLevel(
        indicator=indicator,
        level=agreement.level,
        extraction_verdict="supported",
        independent_verdict="supported",
        reason=(
            "Nivel AD-04 respaldado por componentes "
            + str(agreement.component_ids)
        ),
    )
