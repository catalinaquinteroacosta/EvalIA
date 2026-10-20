"""Nucleo deterministico de puntuacion ND.

No interpreta texto ni llama a modelos.
No asigna puntuacion sin acuerdo semantico verificable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import ND_CODES, NDResult
from .official_rubric import load_official_nd_rubric

Level = Literal["0", "1", "2", "3"]
Verdict = Literal[
    "supported", "not_supported", "ambiguous"
]


@dataclass(frozen=True)
class VerifiedLevel:
    indicator: str
    level: Level
    extraction_verdict: Verdict
    independent_verdict: Verdict
    reason: str

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")
        if self.level not in ("0", "1", "2", "3"):
            raise ValueError("Nivel ND invalido")
        if self.extraction_verdict not in (
            "supported", "not_supported", "ambiguous"
        ):
            raise ValueError("Veredicto de extraccion invalido")
        if self.independent_verdict not in (
            "supported", "not_supported", "ambiguous"
        ):
            raise ValueError("Veredicto independiente invalido")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Justificacion requerida")


def score_verified_level(
    decision: VerifiedLevel,
) -> NDResult:
    if decision.indicator in ND_CODES:
        return NDResult(indicator=decision.indicator,status="BLOCKED",score=None,
                        reason="Selección ordinal antigua no acredita componentes individuales DOCX; usar la puerta de componentes ND")

    rubric = load_official_nd_rubric()

    if decision.indicator not in rubric.indicators:
        raise ValueError("Indicador fuera de AD-04")

    if (
        decision.extraction_verdict != "supported"
        or decision.independent_verdict != "supported"
    ):
        return NDResult(
            indicator=decision.indicator,
            status="BLOCKED",
            score=None,
            reason=(
                "Sin respaldo semantico independiente "
                "suficiente: " + decision.reason
            ),
        )

    return NDResult(
        indicator=decision.indicator,
        status="SCORED",
        score=int(decision.level),
        reason=(
            rubric.levels[decision.level]
            + " | " + decision.reason
        ),
    )


def score_family_verified(
    decisions: tuple[VerifiedLevel, ...],
) -> tuple[NDResult, ...]:
    if len(decisions) != len(ND_CODES):
        raise ValueError("Se requieren ocho decisiones ND")

    codes = [item.indicator for item in decisions]

    if set(codes) != set(ND_CODES) or len(set(codes)) != 8:
        raise ValueError("Indicadores ND incompletos o duplicados")

    by_code = {
        item.indicator: item for item in decisions
    }

    return tuple(
        score_verified_level(by_code[code])
        for code in ND_CODES
    )
