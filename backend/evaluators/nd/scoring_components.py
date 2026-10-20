"""Componentes verificables para puntuacion ND.

Los componentes describen evidencia, no niveles.
Ninguna salida de este modulo es una puntuacion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import (
    ND_CODES,
    Evidence,
    TurnContext,
)

FindingStatus = Literal[
    "present",
    "absent",
    "uncertain",
]

VerificationStatus = Literal[
    "supported",
    "not_supported",
    "ambiguous",
]


@dataclass(frozen=True)
class NDScoringComponent:
    indicator: str
    claim: str
    evidence: tuple[Evidence, ...]

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        if not isinstance(self.claim, str) or not self.claim.strip():
            raise ValueError("Afirmacion vacia")

        if not self.evidence:
            raise ValueError("Componente sin evidencia")


@dataclass(frozen=True)
class VerifiedScoringComponent:
    component: NDScoringComponent
    verification: VerificationStatus
    reason: str

    def __post_init__(self):
        if self.verification not in (
            "supported",
            "not_supported",
            "ambiguous",
        ):
            raise ValueError("Veredicto invalido")

        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Justificacion obligatoria")


def validate_component_evidence(
    component: NDScoringComponent,
    context: TurnContext,
) -> bool:
    return all(
        evidence.verify_exact(context)
        for evidence in component.evidence
    )


def verified_components_only(
    components: tuple[VerifiedScoringComponent, ...],
    context: TurnContext,
) -> tuple[NDScoringComponent, ...]:
    accepted = []

    for item in components:
        if item.verification != "supported":
            continue

        if not validate_component_evidence(
            item.component,
            context,
        ):
            raise ValueError(
                "Evidencia literal invalida"
            )

        accepted.append(item.component)

    return tuple(accepted)
