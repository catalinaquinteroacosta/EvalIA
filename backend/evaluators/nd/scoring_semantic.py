"""Extraccion y verificacion semantica para ND.

Reutiliza NDSemanticEngine y su cache privada.
No calcula puntuaciones ni decide aplicabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ND_CODES, Evidence, TurnContext
from .scoring_components import (
    NDScoringComponent,
    VerifiedScoringComponent,
    validate_component_evidence,
)


@dataclass(frozen=True)
class NDScoringEvidenceReport:
    indicator: str
    confirmed: tuple[NDScoringComponent, ...]
    unresolved: tuple[VerifiedScoringComponent, ...]
    status: str

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        if self.status not in ("VERIFIED", "BLOCKED"):
            raise ValueError("Estado de evidencia invalido")

        if self.unresolved and self.status != "BLOCKED":
            raise ValueError(
                "No se pueden ignorar componentes sin resolver"
            )


def extract_and_verify_scoring_components(
    engine,
    indicator: str,
    context: TurnContext,
) -> NDScoringEvidenceReport:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    extracted = engine.extract(indicator, context)

    if not isinstance(extracted, dict):
        raise ValueError("Extraccion invalida")

    raw_components = extracted.get("components")

    if not isinstance(raw_components, list):
        raise ValueError("Lista de componentes invalida")

    confirmed = []
    unresolved = []

    for raw in raw_components:
        if not isinstance(raw, dict):
            raise ValueError("Componente invalido")

        evidence = tuple(
            Evidence(
                source=item["source"],
                quote=item["quote"],
                history_index=item.get("history_index"),
            )
            for item in raw["evidence"]
        )

        component = NDScoringComponent(
            indicator=indicator,
            claim=raw["claim"],
            evidence=evidence,
        )

        if not validate_component_evidence(component, context):
            raise ValueError(
                "Evidencia no coincide literalmente"
            )

        verdict = engine.verify(
            indicator,
            context,
            raw,
        )

        if not isinstance(verdict, dict):
            raise ValueError("Verificacion invalida")

        verified = VerifiedScoringComponent(
            component=component,
            verification=verdict["verdict"],
            reason=verdict["reason"],
        )

        if verified.verification == "supported":
            confirmed.append(component)
        else:
            unresolved.append(verified)

    status = "BLOCKED" if unresolved else "VERIFIED"

    return NDScoringEvidenceReport(
        indicator=indicator,
        confirmed=tuple(confirmed),
        unresolved=tuple(unresolved),
        status=status,
    )
