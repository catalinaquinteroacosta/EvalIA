"""Contrato oficial de ejecuci?n de conducta CE4.

La r?brica oficial prevalece sobre cualquier implementaci?n.
Este m?dulo no extrae evidencia ni consulta modelos.
"""

from enum import Enum


class CE4Execution(str, Enum):
    OMITTED_OR_OPPOSITE = "omitted_or_opposite"
    MINIMAL_GENERIC = "minimal_generic"
    ADEQUATE_LIMITED = "adequate_limited"
    CLEAR_CONTEXTUAL_VERIFIABLE = (
        "clear_contextual_verifiable"
    )


OFFICIAL_LEVELS = {
    CE4Execution.OMITTED_OR_OPPOSITE: 0,
    CE4Execution.MINIMAL_GENERIC: 1,
    CE4Execution.ADEQUATE_LIMITED: 2,
    CE4Execution.CLEAR_CONTEXTUAL_VERIFIABLE: 3,
}


def score_verified_execution(
    *,
    applicable: bool,
    analysis_complete: bool,
    semantic_verified: bool,
    execution: str | None,
) -> dict:
    """Punt?a ?nicamente componentes sem?nticos verificados."""

    for name, value in {
        "applicable": applicable,
        "analysis_complete": analysis_complete,
        "semantic_verified": semantic_verified,
    }.items():
        if type(value) is not bool:
            raise ValueError(
                f"{name} debe ser booleano"
            )

    if not analysis_complete or not semantic_verified:
        return {
            "status": "insufficient_evidence",
            "score": None,
        }

    if not applicable:
        return {
            "status": "not_applicable",
            "score": None,
        }

    try:
        category = CE4Execution(execution)
    except (ValueError, TypeError):
        raise ValueError(
            "Categor?a de ejecuci?n CE4 inv?lida"
        )

    return {
        "status": "scored",
        "score": OFFICIAL_LEVELS[category],
    }
