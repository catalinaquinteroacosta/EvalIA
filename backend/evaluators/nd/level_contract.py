"""Contrato de correspondencia con niveles oficiales AD-04.

No interpreta lenguaje natural ni asigna niveles.
Solo valida decisiones ya verificadas.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ND_CODES
from .official_rubric import load_official_nd_rubric


@dataclass(frozen=True)
class NDLevelFinding:
    indicator: str
    descriptor: str
    level: str
    evidence_component_ids: tuple[int, ...]
    verification: str
    reason: str

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        if self.level not in ("0", "1", "2", "3"):
            raise ValueError("Nivel fuera de rubrica")

        if self.verification not in (
            "supported",
            "not_supported",
            "ambiguous",
        ):
            raise ValueError("Verificacion invalida")

        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Justificacion obligatoria")

        if not isinstance(self.evidence_component_ids, tuple):
            raise TypeError("Referencias deben ser tupla")

        if any(
            type(index) is not int or index < 0
            for index in self.evidence_component_ids
        ):
            raise ValueError("Referencia de componente invalida")


def validate_level_finding(
    finding: NDLevelFinding,
    confirmed_component_count: int,
) -> bool:
    rubric = load_official_nd_rubric()

    if finding.descriptor != rubric.levels[finding.level]:
        raise ValueError(
            "Descriptor diferente de la rubrica oficial"
        )

    if (
        type(confirmed_component_count) is not int
        or confirmed_component_count < 0
    ):
        raise ValueError("Conteo de componentes invalido")

    if finding.verification != "supported":
        return False

    if not finding.evidence_component_ids:
        return False

    if len(set(finding.evidence_component_ids)) != len(
        finding.evidence_component_ids
    ):
        raise ValueError("Componentes duplicados")

    if any(
        index >= confirmed_component_count
        for index in finding.evidence_component_ids
    ):
        raise ValueError(
            "Referencia a componente inexistente"
        )

    return True
