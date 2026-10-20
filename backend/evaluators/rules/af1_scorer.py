"""
EvalIA - Scorer determinista de AF1.

AF1:
¿Distingue entre aspectos modificables y no modificables
para orientar la estrategia?

Este módulo NO realiza extracción semántica.
NO llama a Ollama.
NO interpreta lenguaje natural.

Recibe exclusivamente la salida semántica ya validada
por backend.evaluators.semantic.af_ai_af1 y aplica
literalmente la rúbrica operacional AF1.

Reglas:
0:
- no aparece M ni L; o
- existe garantía confirmada de control sobre un desenlace no asegurado.

1:
- aparece solo M o solo L; o
- aparecen M y L pero no existe orientación confirmada hacia ninguna clase.

2:
- aparecen M y L;
- existe orientación confirmada hacia al menos una de las dos clases;
- no existe garantía indebida confirmada.

3:
- aparecen M y L;
- existe orientación confirmada hacia M;
- existe orientación confirmada hacia L;
- no existe garantía indebida confirmada.

Los elementos semanticamente AMBIGUOUS se conservan para trazabilidad
en la capa semántica, pero NO cuentan como componentes confirmados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.evaluators.semantic.af_ai_af1 import (
    confirmed_control_guarantees,
    confirmed_modifiable_aspects,
    confirmed_modifiable_orientations,
    confirmed_unmodifiable_aspects,
    confirmed_unmodifiable_orientations,
)


@dataclass(frozen=True)
class AF1ScoreDecision:
    score: int

    has_m: bool
    has_l: bool

    has_v_m: bool
    has_v_l: bool

    has_control_guarantee: bool

    reason: str

    modifiable_count: int
    unmodifiable_count: int
    modifiable_orientation_count: int
    unmodifiable_orientation_count: int
    guarantee_count: int


class AF1ScoringError(ValueError):
    """Entrada inválida para la puntuación determinista de AF1."""


def score_af1(
    semantic_result: dict[str, Any],
) -> AF1ScoreDecision:
    """
    Aplica exclusivamente la tabla de decisión AF1.

    `semantic_result` debe ser la salida de `extract_ai_af1()`.

    Esta función es pura:
    - no llama modelos;
    - no modifica la entrada;
    - no infiere componentes faltantes;
    - no convierte ambiguous en supported.
    """

    if not isinstance(semantic_result, dict):
        raise AF1ScoringError(
            "semantic_result debe ser un diccionario."
        )

    for key in (
        "modifiable",
        "unmodifiable",
        "control_guarantees",
    ):
        if key not in semantic_result:
            raise AF1ScoringError(
                f"Falta la clave obligatoria '{key}'."
            )

        if not isinstance(semantic_result[key], list):
            raise AF1ScoringError(
                f"La clave '{key}' debe contener una lista."
            )

    confirmed_m = confirmed_modifiable_aspects(
        semantic_result
    )
    confirmed_l = confirmed_unmodifiable_aspects(
        semantic_result
    )

    confirmed_v_m = confirmed_modifiable_orientations(
        semantic_result
    )
    confirmed_v_l = confirmed_unmodifiable_orientations(
        semantic_result
    )

    confirmed_g = confirmed_control_guarantees(
        semantic_result
    )

    has_m = bool(confirmed_m)
    has_l = bool(confirmed_l)

    has_v_m = bool(confirmed_v_m)
    has_v_l = bool(confirmed_v_l)

    has_control_guarantee = bool(confirmed_g)

    # ---------------------------------------------------------
    # NIVEL 0
    # ---------------------------------------------------------

    if has_control_guarantee:
        score = 0
        reason = (
            "AF1=0: existe una garantía confirmada de control "
            "sobre un desenlace no asegurado."
        )

    elif not has_m and not has_l:
        score = 0
        reason = (
            "AF1=0: no se confirmó ningún aspecto modificable "
            "ni ningún aspecto no modificable/no asegurable."
        )

    # ---------------------------------------------------------
    # NIVEL 1
    # ---------------------------------------------------------

    elif not (has_m and has_l):
        score = 1
        reason = (
            "AF1=1: se confirmó únicamente una de las dos "
            "clases requeridas, M o L."
        )

    elif not has_v_m and not has_v_l:
        score = 1
        reason = (
            "AF1=1: se confirmaron M y L, pero no se confirmó "
            "una orientación congruente hacia ninguna clase."
        )

    # ---------------------------------------------------------
    # NIVEL 3
    # Debe comprobarse antes de nivel 2.
    # ---------------------------------------------------------

    elif has_v_m and has_v_l:
        score = 3
        reason = (
            "AF1=3: se confirmaron M y L y existe una "
            "orientación congruente confirmada hacia cada clase."
        )

    # ---------------------------------------------------------
    # NIVEL 2
    # ---------------------------------------------------------

    else:
        score = 2
        reason = (
            "AF1=2: se confirmaron M y L y existe orientación "
            "congruente hacia al menos una de las dos clases, "
            "pero no hacia ambas."
        )

    return AF1ScoreDecision(
        score=score,
        has_m=has_m,
        has_l=has_l,
        has_v_m=has_v_m,
        has_v_l=has_v_l,
        has_control_guarantee=has_control_guarantee,
        reason=reason,
        modifiable_count=len(confirmed_m),
        unmodifiable_count=len(confirmed_l),
        modifiable_orientation_count=len(confirmed_v_m),
        unmodifiable_orientation_count=len(confirmed_v_l),
        guarantee_count=len(confirmed_g),
    )