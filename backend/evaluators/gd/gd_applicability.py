"""Validación independiente de aplicabilidad GD.

No asigna puntajes. No interpreta ausencia de evidencia como N/A.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .gd_rubric import GD_RUBRIC, CONDITIONAL


ApplicabilityVerdict = Literal[
    "applicable",
    "not_applicable",
    "uncertain",
]


@dataclass(frozen=True)
class ApplicabilityReview:
    code: str
    verdict: ApplicabilityVerdict
    reason: str

    def __post_init__(self):
        if self.code not in ("GD5", "GD7"):
            raise ValueError("Revisión condicional solo para GD5 y GD7.")
        if self.verdict not in (
            "applicable",
            "not_applicable",
            "uncertain",
        ):
            raise ValueError("Veredicto de aplicabilidad inválido.")
        if not self.reason.strip():
            raise ValueError("La revisión requiere justificación.")


def reconcile_applicability(
    code: str,
    extractor_condition: str,
    independent_review: ApplicabilityReview,
) -> str:
    """Acuerdo independiente; discrepancias permanecen BLOCKED."""

    if code not in GD_RUBRIC:
        raise ValueError("Indicador desconocido.")

    if GD_RUBRIC[code].applicability != CONDITIONAL:
        raise ValueError("Indicador no condicional.")

    if independent_review.code != code:
        raise ValueError("La revisión corresponde a otro indicador.")

    expected = {
        "yes": "applicable",
        "no": "not_applicable",
    }

    if extractor_condition not in ("yes", "no", "uncertain"):
        raise ValueError("Condición de extracción inválida.")

    if extractor_condition == "uncertain":
        return "BLOCKED"

    if independent_review.verdict == "uncertain":
        return "BLOCKED"

    if independent_review.verdict != expected[extractor_condition]:
        return "BLOCKED"

    if independent_review.verdict == "not_applicable":
        return "NA"

    return "APPLICABLE"


def validate_reviews(
    reviews: tuple[ApplicabilityReview, ...],
) -> None:
    codes = [review.code for review in reviews]

    if len(codes) != 2 or set(codes) != {"GD5", "GD7"}:
        raise ValueError("Se requieren revisiones únicas de GD5 y GD7.")
