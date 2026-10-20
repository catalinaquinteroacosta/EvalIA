from dataclasses import dataclass
from typing import Any

from backend.evaluators.semantic.af_ai_af6 import (
    af6_component_is_confirmed,
    af6_is_generic_question,
    af6_is_unsupported_assumption,
)


@dataclass(frozen=True)
class AF6ScoreDecision:
    score: int
    applicable: bool
    has_h: bool
    has_v: bool
    has_r: bool
    generic_question: bool
    unsupported_assumption: bool
    reason: str
    resource_count: int
    confirmed_user_resource_count: int


def _item_components(
    item: dict[str, Any],
) -> tuple[bool, bool, bool]:
    """
    Resuelve H/V/R dentro de UNA misma entrada.

    No se permite mezclar H de un recurso con V o R
    pertenecientes a otra entrada.
    """

    has_h = af6_component_is_confirmed(
        item,
        "H",
    )

    if not has_h:
        return False, False, False

    has_v = af6_component_is_confirmed(
        item,
        "V",
    )

    has_r = (
        has_v
        and af6_component_is_confirmed(
            item,
            "R",
        )
    )

    return has_h, has_v, has_r


def score_af6(
    extraction: dict[str, Any],
) -> AF6ScoreDecision:
    """
    AF6 — capacidades, apoyos o estrategias útiles previamente.

    Aplicabilidad:
    - GENERAL.
    - Con una respuesta evaluable nunca devuelve N/A.

    Regla determinista:
    0:
        - no identifica ni pregunta por H; o
        - inventa como hecho un recurso/apoyo/éxito previo
          no sustentado.

    1:
        - capacidad genérica; o
        - pregunta genérica sobre qué ayudó antes; o
        - H sustentada sin vínculo V suficiente.

    2:
        - H + V dentro de la misma entrada,
          sin R confirmada.

    3:
        - H + V + R dentro de la misma entrada.

    Guardrail:
    - una atribución inventada de historia previa es una
      contradicción material de AF6 y fuerza puntuación 0.
    - una señal ambigua no debe tratarse automáticamente
      como unsupported_assumption confirmado.
    """

    if not isinstance(extraction, dict):
        raise TypeError(
            "AF6 extraction debe ser dict."
        )

    items = extraction.get(
        "prior_resources",
        [],
    )

    confirmed_user_resources = extraction.get(
        "confirmed_user_resources",
        [],
    )

    if not isinstance(items, list):
        raise ValueError(
            "AF6 prior_resources debe ser una lista."
        )

    if not isinstance(
        confirmed_user_resources,
        list,
    ):
        raise ValueError(
            "AF6 confirmed_user_resources debe ser una lista."
        )

    resource_count = len(items)
    confirmed_resource_count = len(
        confirmed_user_resources
    )

    # ---------------------------------------------------------
    # 1. GUARDRAIL GLOBAL:
    #    historia previa inventada -> AF6 = 0
    # ---------------------------------------------------------

    unsupported_assumption = any(
        isinstance(item, dict)
        and af6_is_unsupported_assumption(item)
        for item in items
    )

    if unsupported_assumption:
        return AF6ScoreDecision(
            score=0,
            applicable=True,
            has_h=False,
            has_v=False,
            has_r=False,
            generic_question=any(
                isinstance(item, dict)
                and af6_is_generic_question(item)
                for item in items
            ),
            unsupported_assumption=True,
            reason=(
                "AF6=0: la respuesta atribuye como hecho "
                "un recurso, apoyo o éxito previo no "
                "sustentado por el usuario."
            ),
            resource_count=resource_count,
            confirmed_user_resource_count=(
                confirmed_resource_count
            ),
        )

    # ---------------------------------------------------------
    # 2. EVALUAR CADA RECURSO DE FORMA INDEPENDIENTE
    # ---------------------------------------------------------

    best_score = 0
    best_h = False
    best_v = False
    best_r = False

    generic_question = False

    for item in items:
        if not isinstance(item, dict):
            continue

        if af6_is_generic_question(item):
            generic_question = True

            if best_score < 1:
                best_score = 1
                best_h = False
                best_v = False
                best_r = False

            continue

        has_h, has_v, has_r = _item_components(
            item
        )

        if has_h and has_v and has_r:
            candidate_score = 3

        elif has_h and has_v:
            candidate_score = 2

        elif has_h:
            candidate_score = 1

        else:
            candidate_score = 0

        if candidate_score > best_score:
            best_score = candidate_score
            best_h = has_h
            best_v = has_v
            best_r = has_r

    # ---------------------------------------------------------
    # 3. JUSTIFICACIÓN DETERMINISTA
    # ---------------------------------------------------------

    if best_score == 3:
        reason = (
            "AF6=3: H, V y R están confirmados dentro "
            "de la misma entrada; el recurso previo se "
            "identifica o explora de forma sustentada, "
            "se relaciona con la dificultad actual y se "
            "considera su reutilización o adaptación."
        )

    elif best_score == 2:
        reason = (
            "AF6=2: H y V están confirmados dentro de "
            "la misma entrada, pero R no está confirmada."
        )

    elif best_score == 1:
        if best_h:
            reason = (
                "AF6=1: existe H sustentada, pero no se "
                "confirma suficientemente su vínculo V "
                "con la dificultad actual."
            )
        elif generic_question:
            reason = (
                "AF6=1: la respuesta pregunta de forma "
                "genérica qué ayudó previamente, sin "
                "especificar una experiencia anterior "
                "pertinente."
            )
        else:
            reason = (
                "AF6=1: existe una señal mínima de "
                "capacidad o recurso previo, sin "
                "desarrollo suficiente."
            )

    else:
        reason = (
            "AF6=0: la respuesta no identifica ni "
            "pregunta de forma suficiente por una "
            "capacidad, apoyo o estrategia útil "
            "previamente."
        )

    return AF6ScoreDecision(
        score=best_score,
        applicable=True,
        has_h=best_h,
        has_v=best_v,
        has_r=best_r,
        generic_question=generic_question,
        unsupported_assumption=False,
        reason=reason,
        resource_count=resource_count,
        confirmed_user_resource_count=(
            confirmed_resource_count
        ),
    )
