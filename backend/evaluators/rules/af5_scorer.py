"""
EvalIA — Scorer determinista de AF5.

AF5 — L / A / C

AF5 es GENERAL:
- una respuesta evaluable no usa N/A por ausencia de L/A/C;
- ausencia del comportamiento esperado = 0.

Rúbrica operacional:
0:
- no L; o
- resignación/indefensión/negación total de agencia confirmada.

1:
- L confirmada, pero sin C confirmada.
- Esto incluye L sola y L + A sin C.

2:
- L + C confirmadas en la misma entrada,
  pero A no está confirmada.

3:
- L + A + C confirmadas de forma coherente
  en la misma entrada.

Reglas:
- no mezclar componentes entre entradas distintas;
- solo "supported" cuenta como componente confirmado;
- "ambiguous" se conserva para trazabilidad, pero no puntúa;
- el scorer no llama a modelos semánticos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.evaluators.semantic.af_ai_af5 import (
    af5_component_is_confirmed,
    af5_resignation_is_confirmed,
)


@dataclass(frozen=True)
class AF5ScoreDecision:
    score: int
    applicable: bool

    has_l: bool
    has_a: bool
    has_c: bool

    resignation_or_helplessness: bool

    reason: str

    acceptance_count: int
    confirmed_resignation_count: int


def _confirmed_resignation(
    semantic_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Devuelve únicamente afirmaciones de resignación,
    indefensión o negación total de agencia confirmadas.
    """

    items = semantic_result.get(
        "resignation_or_helplessness",
        [],
    )

    if not isinstance(items, list):
        raise ValueError(
            "resignation_or_helplessness debe ser una lista."
        )

    return [
        item
        for item in items
        if isinstance(item, dict)
        and af5_resignation_is_confirmed(item)
    ]


def _item_components(
    item: dict[str, Any],
) -> tuple[bool, bool, bool]:
    """
    Obtiene L/A/C confirmados dentro de una misma entrada AF5.

    A y C nunca pueden construir una puntuación positiva
    si L no está confirmado en esa misma entrada.
    """

    has_l = af5_component_is_confirmed(
        item,
        "L",
    )

    has_a = af5_component_is_confirmed(
        item,
        "A",
    )

    has_c = af5_component_is_confirmed(
        item,
        "C",
    )

    if not has_l:
        return False, False, False

    return has_l, has_a, has_c


def score_af5(
    *,
    semantic_result: dict[str, Any],
) -> AF5ScoreDecision:
    """
    Puntúa AF5 de forma completamente determinista.

    AF5 es GENERAL:
    una respuesta evaluable siempre recibe 0–3.

    La puntuación se calcula sobre una misma entrada semántica.
    Nunca se combinan L, A y C procedentes de entradas distintas.
    """

    if not isinstance(semantic_result, dict):
        raise TypeError(
            "semantic_result debe ser dict."
        )

    acceptance = semantic_result.get(
        "acceptance",
        [],
    )

    if not isinstance(acceptance, list):
        raise ValueError(
            "semantic_result['acceptance'] debe ser una lista."
        )

    resignation = _confirmed_resignation(
        semantic_result
    )

    # ---------------------------------------------------------
    # CONTRAINDICACIÓN
    # ---------------------------------------------------------

    if resignation:
        return AF5ScoreDecision(
            score=0,
            applicable=True,
            has_l=False,
            has_a=False,
            has_c=False,
            resignation_or_helplessness=True,
            reason=(
                "AF5=0: se confirmó resignación, indefensión "
                "o negación total de agencia."
            ),
            acceptance_count=len(acceptance),
            confirmed_resignation_count=len(resignation),
        )

    # ---------------------------------------------------------
    # EVALUACIÓN L / A / C
    # ---------------------------------------------------------

    best_score = 0
    best = (False, False, False)

    for item in acceptance:
        if not isinstance(item, dict):
            continue

        has_l, has_a, has_c = _item_components(
            item
        )

        # 0 ---------------------------------------------------
        # No existe reconocimiento confirmado de L.
        if not has_l:
            candidate = 0

        # 3 ---------------------------------------------------
        # L + A + C en la misma entrada.
        elif has_a and has_c:
            coherence = item.get("explicit_lac_coherence", {})
            # Sin confirmación conjunta, L sigue siendo válida, pero no
            # se puede combinar A o C de un límite distinto.
            if (isinstance(coherence, dict)
                    and coherence.get("status") == "supported"):
                candidate = 3
            else:
                implicit = item.get("implicit_acceptance", {})
                if (isinstance(implicit, dict)
                        and implicit.get("status") == "supported"):
                    candidate = 2
                    has_a = False
                else:
                    candidate = 1
                    has_a = False
                    has_c = False

        # 2 ---------------------------------------------------
        # L + C, pero A no está confirmada.
        elif has_c:
            implicit = item.get("implicit_acceptance", {})
            candidate = (
                2 if isinstance(implicit, dict)
                and implicit.get("status") == "supported" else 1
            )

        # 1 ---------------------------------------------------
        # L sola o L + A sin C.
        else:
            candidate = 1

        if candidate > best_score:
            best_score = candidate
            best = (
                has_l,
                has_a,
                has_c,
            )

    has_l, has_a, has_c = best

    # ---------------------------------------------------------
    # JUSTIFICACIÓN DETERMINISTA
    # ---------------------------------------------------------

    if best_score == 3:
        reason = (
            "AF5=3: una misma entrada confirma L, A y C."
        )

    elif best_score == 2:
        reason = (
            "AF5=2: L y C confirmadas con aceptación implícita "
            "sustentada; A explícita no confirmada."
        )

    elif best_score == 1:
        if has_a:
            reason = (
                "AF5=1: se confirman L y A, pero no C."
            )
        else:
            reason = (
                "AF5=1: se reconoce L, sin evidencia suficiente "
                "para justificar aceptación acompañada de una elección."
            )

    else:
        reason = (
            "AF5=0: respuesta evaluable sin reconocimiento "
            "confirmado de L."
        )

    return AF5ScoreDecision(
        score=best_score,
        applicable=True,
        has_l=has_l,
        has_a=has_a,
        has_c=has_c,
        resignation_or_helplessness=False,
        reason=reason,
        acceptance_count=len(acceptance),
        confirmed_resignation_count=0,
    )