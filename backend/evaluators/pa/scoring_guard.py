"""Control de procedencia antes del scoring PA."""

from dataclasses import dataclass
from typing import Literal

from .contracts import CODES


GateStatus = Literal[
    "READY_FOR_RULE_MAPPING",
    "BLOCKED",
]


@dataclass(frozen=True)
class PropertyRecord:
    name: str
    value: str
    verified: bool
    evidence_valid: bool


@dataclass(frozen=True)
class ScoringGate:
    indicator: str
    status: GateStatus
    reason: str
    score: None = None


def check_scoring_readiness(
    code: str,
    applicable: bool | None,
    properties: tuple[PropertyRecord, ...],
    unresolved_discrepancy: bool = False,
) -> ScoringGate:
    if code not in CODES:
        raise ValueError(f"Indicador PA desconocido: {code}")

    if applicable is None:
        return ScoringGate(
            code, "BLOCKED", "Aplicabilidad no resuelta"
        )

    if unresolved_discrepancy:
        return ScoringGate(
            code, "BLOCKED", "Discrepancia semantica pendiente"
        )

    if not properties:
        return ScoringGate(
            code, "BLOCKED", "Sin propiedades verificadas"
        )

    if any(not p.name.strip() for p in properties):
        return ScoringGate(
            code, "BLOCKED", "Propiedad sin identificacion"
        )

    if any(
        p.value not in ("present", "absent")
        for p in properties
    ):
        return ScoringGate(
            code, "BLOCKED", "Propiedad no resuelta"
        )

    if any(not p.verified for p in properties):
        return ScoringGate(
            code, "BLOCKED", "Verificacion independiente incompleta"
        )

    if any(not p.evidence_valid for p in properties):
        return ScoringGate(
            code, "BLOCKED", "Evidencia no validada"
        )

    return ScoringGate(
        code,
        "READY_FOR_RULE_MAPPING",
        "Propiedades verificadas; falta correspondencia "
        "oficial entre propiedades y niveles",
    )
