"""
EvalIA - scorer determinista AF8.

AF8 evalúa diferenciación de responsabilidad y control:

C = contribución/elección propia concreta.
L = límite de control.
N = diferenciación de factores externos/no controlables sin culpa total.

Regla ordinal:
0 = culpabilización, control imposible o ausencia de C.
1 = responsabilidad/agencia reconocida, pero C no concreta.
2 = C concreta sin culpabilización; L queda incompleto/implícito.
3 = C + L + N explícitos.

Este módulo NO interpreta lenguaje natural y NO llama a Qwen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_ALLOWED_STATUSES = {
    "supported",
    "ambiguous",
    "not_supported",
}

_HARMFUL_TYPES = {
    "total_origin_blame",
    "impossible_control",
    "moralizing_responsibility",
}


@dataclass(frozen=True)
class AF8ScoreResult:
    score: int
    applicable: bool
    reason: str
    matched_item_id: str | None = None


def _confirmed(
    value: Any,
) -> bool:
    return (
        isinstance(value, dict)
        and value.get("status") == "supported"
    )


def _validation(
    item: dict[str, Any],
    component: str,
) -> dict[str, Any]:

    semantic = item.get(
        "semantic_validation",
        {},
    )

    if not isinstance(semantic, dict):
        return {}

    value = semantic.get(
        component,
        {},
    )

    return value if isinstance(value, dict) else {}


def _component_confirmed(
    item: dict[str, Any],
    component: str,
) -> bool:
    return _confirmed(
        _validation(
            item,
            component,
        )
    )


def _confirmed_harmful_claim(
    claims: list[dict[str, Any]],
) -> str | None:

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        claim_type = str(
            claim.get(
                "type",
                "",
            )
        ).strip()

        if claim_type not in _HARMFUL_TYPES:
            continue

        if _confirmed(
            claim.get(
                "semantic_validation",
                {},
            )
        ):
            return claim_type

    return None


def _has_minimal_agency_signal(
    item: dict[str, Any],
) -> bool:
    """
    Nivel 1:
    existe señal explícita de responsabilidad/agencia propia,
    pero todavía no alcanza C concreta.

    El extractor especializado conservará este dato
    como AGENCY_SIGNAL.
    """

    return _component_confirmed(
        item,
        "AGENCY_SIGNAL",
    )


def _score_item(
    item: dict[str, Any],
) -> int:
    """
    Puntúa una sola unidad AF8.
    No mezcla C/L/N entre entradas distintas.
    """

    C = _component_confirmed(
        item,
        "C",
    )

    L = _component_confirmed(
        item,
        "L",
    )

    N = _component_confirmed(
        item,
        "N",
    )

    if not C:
        if _has_minimal_agency_signal(item):
            return 1

        return 0

    # C concreta ya cumple el núcleo del nivel 2.
    score = 2

    # Nivel 3 exige diferenciación explícita completa.
    if L and N:
        score = 3

    return score


def score_af8(
    *,
    ai_result: dict[str, Any],
) -> AF8ScoreResult:
    """
    AF8 es GENERAL.

    Para una respuesta evaluable no retorna N/A.
    """

    if not isinstance(ai_result, dict):
        raise TypeError(
            "ai_result debe ser dict."
        )

    agency = ai_result.get(
        "agency",
        [],
    )

    claims = ai_result.get(
        "problematic_claims",
        [],
    )

    if not isinstance(agency, list):
        raise ValueError(
            "agency debe ser una lista."
        )

    if not isinstance(claims, list):
        raise ValueError(
            "problematic_claims debe ser una lista."
        )

    harmful = _confirmed_harmful_claim(
        claims
    )

    # Contradicción material global.
    if harmful is not None:
        return AF8ScoreResult(
            score=0,
            applicable=True,
            reason=(
                "AF8=0: se confirmó una contradicción "
                f"material de tipo {harmful}."
            ),
        )

    if not agency:
        return AF8ScoreResult(
            score=0,
            applicable=True,
            reason=(
                "AF8=0: la respuesta es evaluable pero "
                "no diferencia contribución propia."
            ),
        )

    best_score = 0
    best_id: str | None = None

    for item in agency:
        if not isinstance(item, dict):
            continue

        current = _score_item(
            item
        )

        if current > best_score:
            best_score = current
            best_id = (
                str(
                    item.get(
                        "id",
                        "",
                    )
                ).strip()
                or None
            )

    reasons = {
        0: (
            "AF8=0: no se confirmó una contribución "
            "propia concreta ni una señal mínima de agencia."
        ),
        1: (
            "AF8=1: existe reconocimiento de agencia o "
            "responsabilidad propia, pero sin contribución "
            "concreta suficiente."
        ),
        2: (
            "AF8=2: existe una contribución propia concreta "
            "sin contradicción material, pero la diferenciación "
            "de límites/factores externos no está completa."
        ),
        3: (
            "AF8=3: C, L y N están explícitamente "
            "diferenciados."
        ),
    }

    return AF8ScoreResult(
        score=best_score,
        applicable=True,
        reason=reasons[best_score],
        matched_item_id=best_id,
    )
