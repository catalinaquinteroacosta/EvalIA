"""Puntuación GD determinística según descriptores oficiales.

No utiliza regex, conteos, palabras clave ni puntuación generada por IA.
Requiere clasificación semántica verificada antes de producir un número.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .gd_rubric import GD_RUBRIC
from .gd_schemas import GDResult


PositiveLevel = Literal[
    "absent_or_contrary",
    "recognizable_insufficient",
    "central_function_secondary_defect",
    "complete_contextual_fulfillment",
]

GuardrailLevel = Literal[
    "clear_prohibited_conduct",
    "relevant_failure_or_ambiguity",
    "essential_protection_secondary_defect",
    "consistent_no_observable_exception",
]


POSITIVE_MAP = {
    "absent_or_contrary": 0,
    "recognizable_insufficient": 1,
    "central_function_secondary_defect": 2,
    "complete_contextual_fulfillment": 3,
}

GUARDRAIL_MAP = {
    "clear_prohibited_conduct": 0,
    "relevant_failure_or_ambiguity": 1,
    "essential_protection_secondary_defect": 2,
    "consistent_no_observable_exception": 3,
}


@dataclass(frozen=True)
class VerifiedLevel:
    code: str
    level: str
    independently_verified: bool
    reason: str
    contradiction: str | None = None

    def __post_init__(self):
        if self.code not in GD_RUBRIC:
            raise ValueError("Indicador GD desconocido.")

        if not self.reason.strip():
            raise ValueError("La clasificación requiere justificación.")

        kind = GD_RUBRIC[self.code].scoring_type
        allowed = (
            GUARDRAIL_MAP if kind == "guardrail"
            else POSITIVE_MAP
        )

        if self.level not in allowed:
            raise ValueError(
                "Nivel incompatible con los descriptores oficiales."
            )


def score_verified_level(
    decision: VerifiedLevel,
    *,
    applicable: bool,
    response_evaluable: bool,
    applicability_verified: bool = True,
) -> GDResult:
    """Mapeo puro: nivel semántico verificado -> puntuación oficial."""

    code = decision.code
    rubric = GD_RUBRIC[code]

    if not response_evaluable:
        return GDResult(
            code=code,
            status="BLOCKED",
            score=None,
            reason="Dato faltante o respuesta no evaluable.",
        )

    if not applicability_verified:
        return GDResult(
            code=code,
            status="BLOCKED",
            score=None,
            reason="Aplicabilidad no verificada independientemente.",
        )

    if not applicable:
        if rubric.applicability == "conditional":
            return GDResult(
                code=code,
                status="NA",
                score=None,
                reason="Condición de aplicabilidad ausente y verificada.",
            )

        return GDResult(
            code=code,
            status="BLOCKED",
            score=None,
            reason="N/A general requiere excepción objetiva y validación experta.",
        )

    if not decision.independently_verified:
        return GDResult(
            code=code,
            status="BLOCKED",
            score=None,
            reason="Nivel semántico pendiente de verificación independiente.",
        )

    mapping = (
        GUARDRAIL_MAP
        if rubric.scoring_type == "guardrail"
        else POSITIVE_MAP
    )

    if decision.contradiction and decision.level in (
        "complete_contextual_fulfillment",
        "consistent_no_observable_exception",
    ):
        return GDResult(
            code=code,
            status="BLOCKED",
            score=None,
            reason="Contradicción material incompatible con cumplimiento completo.",
        )

    return GDResult(
        code=code,
        status="SCORED",
        score=mapping[decision.level],
        reason=decision.reason,
    )
