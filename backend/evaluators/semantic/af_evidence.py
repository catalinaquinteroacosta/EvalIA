"""
EvalIA — Verificación de evidencia semántica para AF1–AF8.

El extractor LLM puede proponer fragmentos de evidencia textual,
pero EvalIA debe comprobar de forma determinista que esos fragmentos
realmente existen en la fuente declarada.

Este módulo NO interpreta la rúbrica y NO asigna puntuaciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceSource(str, Enum):
    CURRENT_USER = "current_user"
    PRIOR_USER = "prior_user"
    PRIOR_AI = "prior_ai"
    CURRENT_AI = "current_ai"


@dataclass(frozen=True)
class EvidenceCheck:
    valid: bool
    evidence: str
    source: EvidenceSource
    reason: str


def verify_exact_evidence(
    *,
    evidence: str,
    source: EvidenceSource,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
) -> EvidenceCheck:
    """
    Comprueba que una evidencia no vacía sea una cita textual exacta
    de la fuente que Qwen declara.

    No realiza coincidencias aproximadas ni corrige el texto.
    """

    texts = {
        EvidenceSource.CURRENT_USER: current_user,
        EvidenceSource.PRIOR_USER: prior_user,
        EvidenceSource.PRIOR_AI: prior_ai,
        EvidenceSource.CURRENT_AI: current_ai,
    }

    evidence = evidence.strip()

    if not evidence:
        return EvidenceCheck(
            valid=False,
            evidence="",
            source=source,
            reason="empty_evidence",
        )

    source_text = texts[source]

    if not source_text:
        return EvidenceCheck(
            valid=False,
            evidence=evidence,
            source=source,
            reason="source_unavailable",
        )

    if evidence not in source_text:
        return EvidenceCheck(
            valid=False,
            evidence=evidence,
            source=source,
            reason="not_exact_substring",
        )

    return EvidenceCheck(
        valid=True,
        evidence=evidence,
        source=source,
        reason="exact_match",
    )