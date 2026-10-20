"""Contratos GD: evidencia, aplicabilidad y resultado sin inferencia regex."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .gd_rubric import GD_RUBRIC, GENERAL, CONDITIONAL


Source = Literal["CURRENT_USER", "CURRENT_RESPONSE", "PRIOR_HISTORY"]
VerificationStatus = Literal["supported", "not_supported", "ambiguous"]
ResultStatus = Literal["SCORED", "NA", "BLOCKED"]


@dataclass(frozen=True)
class HistoryMessage:
    role: Literal["user", "assistant"]
    text: str


@dataclass(frozen=True)
class Evidence:
    quote: str
    source: Source
    history_index: int | None = None


@dataclass(frozen=True)
class VerifiedEvidence:
    evidence: Evidence
    status: VerificationStatus
    reason: str


@dataclass(frozen=True)
class GDContext:
    current_user: str
    current_response: str
    prior_history: tuple[HistoryMessage, ...] = ()


@dataclass(frozen=True)
class GDResult:
    code: str
    status: ResultStatus
    score: int | None
    reason: str
    evidence: tuple[VerifiedEvidence, ...] = ()
    missing_components: tuple[str, ...] = ()
    rule_version: str = "GD-RUBRIC-OFFICIAL-V1"

    def __post_init__(self) -> None:
        if self.code not in GD_RUBRIC:
            raise ValueError("Indicador GD desconocido.")

        if self.status == "SCORED":
            if type(self.score) is not int or self.score not in (0, 1, 2, 3):
                raise ValueError("SCORED requiere un entero entre 0 y 3.")
        elif self.score is not None:
            raise ValueError("NA y BLOCKED no pueden tener puntuacion.")


def verify_exact_quote(
    evidence: Evidence,
    context: GDContext,
) -> bool:
    """Verifica procedencia literal, no equivalencia semántica."""

    if not evidence.quote:
        return False

    if evidence.source == "CURRENT_USER":
        if evidence.history_index is not None:
            return False
        return evidence.quote in context.current_user

    if evidence.source == "CURRENT_RESPONSE":
        if evidence.history_index is not None:
            return False
        return evidence.quote in context.current_response

    if evidence.source == "PRIOR_HISTORY":
        index = evidence.history_index
        if type(index) is not int:
            return False
        if index < 0 or index >= len(context.prior_history):
            return False
        return evidence.quote in context.prior_history[index].text

    return False


def validate_evidence(
    evidence: tuple[Evidence, ...],
    context: GDContext,
) -> None:
    for item in evidence:
        if not verify_exact_quote(item, context):
            raise ValueError(
                "Evidencia no literal o con fuente/indice incorrecto."
            )


def applicability_category(code: str) -> str:
    """Devuelve la clasificación oficial, sin decidir aún N/A."""
    return GD_RUBRIC[code].applicability


def validate_applicability_decision(
    code: str,
    applicable: bool,
    *,
    condition_present: bool | None = None,
    objectively_unevaluable: bool = False,
) -> None:
    """Control estructural; no sustituye la decisión semántica."""

    category = applicability_category(code)

    if category == CONDITIONAL:
        if condition_present is None:
            raise ValueError("Indicador condicional sin condición verificada.")
        if applicable != condition_present:
            raise ValueError("Aplicabilidad contradice la condición verificada.")
        return

    if category == GENERAL:
        if not applicable and not objectively_unevaluable:
            raise ValueError(
                "Un indicador general no puede ser N/A sin excepción justificada."
            )
        return

    raise ValueError("Clasificación de aplicabilidad desconocida.")
