"""Acuerdo independiente sobre descriptores AD-04.

No llama modelos. No interpreta texto.
Bloquea desacuerdos, ambiguedades y evidencia inexistente.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ND_CODES
from .level_contract import (
    NDLevelFinding,
    validate_level_finding,
)


@dataclass(frozen=True)
class NDLevelAgreement:
    indicator: str
    status: str
    level: str | None
    reason: str
    component_ids: tuple[int, ...]

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        if self.status not in ("AGREED", "BLOCKED"):
            raise ValueError("Estado invalido")

        if self.status == "AGREED":
            if self.level not in ("0", "1", "2", "3"):
                raise ValueError("Acuerdo sin nivel valido")
            if not self.component_ids:
                raise ValueError("Acuerdo sin evidencia")
        elif self.level is not None:
            raise ValueError(
                "Un resultado bloqueado no tiene nivel"
            )


def reconcile_level_findings(
    first: NDLevelFinding,
    second: NDLevelFinding,
    *,
    confirmed_component_count: int,
) -> NDLevelAgreement:
    if first.indicator != second.indicator:
        raise ValueError(
            "Los hallazgos corresponden a indicadores distintos"
        )

    first_valid = validate_level_finding(
        first,
        confirmed_component_count,
    )
    second_valid = validate_level_finding(
        second,
        confirmed_component_count,
    )

    if not first_valid or not second_valid:
        return NDLevelAgreement(
            indicator=first.indicator,
            status="BLOCKED",
            level=None,
            reason="Correspondencia sin respaldo suficiente",
            component_ids=(),
        )

    if first.level != second.level:
        return NDLevelAgreement(
            indicator=first.indicator,
            status="BLOCKED",
            level=None,
            reason="Desacuerdo independiente entre niveles",
            component_ids=(),
        )

    common = tuple(sorted(
        set(first.evidence_component_ids)
        & set(second.evidence_component_ids)
    ))

    if not common:
        return NDLevelAgreement(
            indicator=first.indicator,
            status="BLOCKED",
            level=None,
            reason="No existe evidencia comun verificada",
            component_ids=(),
        )

    return NDLevelAgreement(
        indicator=first.indicator,
        status="AGREED",
        level=first.level,
        reason=(
            "Dos evaluaciones independientes coinciden "
            "en el descriptor oficial"
        ),
        component_ids=common,
    )
