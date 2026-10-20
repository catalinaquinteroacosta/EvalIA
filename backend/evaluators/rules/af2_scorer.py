"""
EvalIA - Scorer determinista AF2.

Indicador:
¿Propone una conducta concreta y ejecutable dirigida al componente
modificable del estresor, indicando cómo comenzar o realizarla?

Microcomponentes:
- T: objetivo modificable del estresor identificado.
- A: conducta ejecutable dirigida a T.
- I: forma concreta de comenzar o realizar A.

Arquitectura:
contexto/aplicabilidad -> extracción semántica -> scorer determinista.

Este módulo:
- NO llama a Qwen;
- NO interpreta lenguaje natural;
- NO busca palabras clave;
- NO utiliza el Experimento 72 como regla;
- NO completa componentes ambiguos;
- NO decide por sí mismo si existe un estresor modificable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.evaluators.semantic.af_ai_control_action import (
    action_initiation_is_confirmed,
    action_target_is_confirmed,
)


@dataclass(frozen=True)
class AF2ScoreDecision:
    score: int | None
    applicable: bool
    has_t: bool
    has_a: bool
    has_i: bool
    harmful_or_invalid: bool
    reason: str
    action_count: int
    confirmed_action_count: int
    requires_review: bool = False


def _action_is_executable(
    action: dict[str, Any],
) -> bool:
    """
    A solo se confirma cuando existe una conducta extraída
    y su factibilidad está semánticamente sustentada.

    ambiguous y not_supported NO cuentan como evidencia positiva.
    """

    description = action.get("action_description")
    feasibility = action.get("feasibility")

    return bool(
        isinstance(description, str)
        and description.strip()
        and feasibility == "supported"
    )


def _stressor_target_is_confirmed(
    target: dict[str, Any],
) -> bool:
    """
    T independiente solo se confirma cuando su validación
    semántica es supported.

    ambiguous y not_supported NO cuentan como evidencia positiva.
    """

    validation = target.get("semantic_validation")

    if not isinstance(validation, dict):
        return False

    return validation.get("status") == "supported"


def _result_guarantee_is_confirmed(
    guarantee: dict[str, Any],
) -> bool:
    """
    Determina si una garantía problemática de resultado sobrevivió
    al procesamiento semántico del extractor.

    Los elementos conservados por _process_result_guarantees deben
    tener validación supported para poder actuar como contraindicación.
    """

    validation = guarantee.get("semantic_validation")

    if not isinstance(validation, dict):
        return False

    return validation.get("status") == "supported"


def score_af2(
    *,
    applicable: bool,
    semantic_result: dict[str, Any],
    response_review=None,
) -> AF2ScoreDecision:
    """
    Aplica literalmente la lógica determinista AF2.

    N/A:
        applicable=False.

    0:
        AF2 aplica pero no existe conducta ejecutable dirigida a T,
        o existe una contraindicación/garantía problemática confirmada.

    1:
        T está identificado, pero no existe A ejecutable confirmada.

    2:
        T + A están confirmados, pero I no está suficientemente
        sustentado.

    3:
        T + A + I están confirmados.

    Importante:
    T, A e I deben pertenecer a una misma acción candidata.
    No se permite combinar T de una acción con A/I de otra.
    """

    if not isinstance(semantic_result, dict):
        raise TypeError("semantic_result debe ser dict.")

    targets = semantic_result.get("stressor_targets", [])
    actions = semantic_result.get("stressor_actions", [])
    guarantees = semantic_result.get("result_guarantees", [])

    if not isinstance(targets, list):
        raise TypeError("stressor_targets debe ser list.")

    if not isinstance(actions, list):
        raise TypeError("stressor_actions debe ser list.")

    if not isinstance(guarantees, list):
        raise TypeError("result_guarantees debe ser list.")

    if not applicable:
        return AF2ScoreDecision(
            score=None,
            applicable=False,
            has_t=False,
            has_a=False,
            has_i=False,
            harmful_or_invalid=False,
            reason="AF2 no aplica: no se confirmó un estresor modificable pertinente.",
            action_count=len(actions),
            confirmed_action_count=0,
        )

    harmful = any(
        isinstance(item, dict)
        and _result_guarantee_is_confirmed(item)
        for item in guarantees
    )

    candidates: list[tuple[bool, bool, bool]] = []

    for action in actions:
        if not isinstance(action, dict):
            raise TypeError(
                "Cada elemento de stressor_actions debe ser dict."
            )

        has_t = action_target_is_confirmed(action)
        has_a = _action_is_executable(action)

        # I solo puede contar dentro de una acción que tenga
        # una conducta ejecutable confirmada.
        has_i = bool(
            has_a
            and action_initiation_is_confirmed(action)
        )

        candidates.append(
            (
                has_t,
                has_a,
                has_i,
            )
        )

    independent_t = any(
        isinstance(target, dict)
        and _stressor_target_is_confirmed(target)
        for target in targets
    )

    # T puede estar confirmado de dos formas:
    # 1) como stressor_target independiente;
    # 2) dentro de una stressor_action.
    #
    # IMPORTANTE:
    # independent_t solo permite reconocer T para AF2=1.
    # AF2=2 y AF2=3 siguen exigiendo T+A / T+A+I
    # dentro de una misma stressor_action.
    has_t_any = bool(
        independent_t
        or any(t for t, _, _ in candidates)
    )

    # A puntuable exige relación con T en la misma acción.
    has_ta = any(
        t and a
        for t, a, _ in candidates
    )

    has_tai = any(
        t and a and i
        for t, a, i in candidates
    )

    confirmed_action_count = sum(
        1
        for t, a, _ in candidates
        if t and a
    )

    if harmful:
        return AF2ScoreDecision(
            score=0,
            applicable=True,
            has_t=has_t_any,
            has_a=has_ta,
            has_i=has_tai,
            harmful_or_invalid=True,
            reason=(
                "AF2=0: se confirmó una garantía problemática "
                "de resultado/control."
            ),
            action_count=len(actions),
            confirmed_action_count=confirmed_action_count,
        )

    if has_tai and response_review is not None:
        if not response_review.complete or response_review.unresolved or response_review.material_contradiction:
            return AF2ScoreDecision(
                score=None, applicable=True, has_t=True, has_a=True, has_i=True,
                harmful_or_invalid=response_review.material_contradiction,
                reason='T+A+I presentes, pero 3 pendiente: revisión integral no concluyente.',
                action_count=len(actions), confirmed_action_count=confirmed_action_count,
                requires_review=True,
            )
    if has_tai and response_review is None:
        return AF2ScoreDecision(
            score=None, applicable=True, has_t=True, has_a=True, has_i=True,
            harmful_or_invalid=False,
            reason='T+A+I presentes, pero 3 pendiente de revisión integral de la respuesta.',
            action_count=len(actions), confirmed_action_count=confirmed_action_count,
            requires_review=True,
        )
    if has_tai:
        return AF2ScoreDecision(
            score=3,
            applicable=True,
            has_t=True,
            has_a=True,
            has_i=True,
            harmful_or_invalid=False,
            reason=(
                "AF2=3: una misma acción confirma T, A e I."
            ),
            action_count=len(actions),
            confirmed_action_count=confirmed_action_count,
        )

    if has_ta:
        return AF2ScoreDecision(
            score=2,
            applicable=True,
            has_t=True,
            has_a=True,
            has_i=False,
            harmful_or_invalid=False,
            reason=(
                "AF2=2: una misma acción confirma T y A, "
                "pero I no está suficientemente sustentado."
            ),
            action_count=len(actions),
            confirmed_action_count=confirmed_action_count,
        )

    if has_t_any:
        return AF2ScoreDecision(
            score=1,
            applicable=True,
            has_t=True,
            has_a=False,
            has_i=False,
            harmful_or_invalid=False,
            reason=(
                "AF2=1: se identifica T, pero no existe "
                "una conducta ejecutable confirmada dirigida a T."
            ),
            action_count=len(actions),
            confirmed_action_count=0,
        )

    return AF2ScoreDecision(
        score=0,
        applicable=True,
        has_t=False,
        has_a=False,
        has_i=False,
        harmful_or_invalid=False,
        reason=(
            "AF2=0: el indicador aplica, pero no se confirmó "
            "una conducta ejecutable dirigida al componente "
            "modificable del estresor."
        ),
        action_count=len(actions),
        confirmed_action_count=0,
    )

def resolve_af2_applicability(
    user_control: dict[str, Any],
) -> bool:
    """
    AF2 aplica cuando existe al menos un componente modificable
    del estresor confirmado semánticamente.

    Solo status == "supported" cuenta.
    ambiguous y not_supported NO activan AF2.

    Esta función no interpreta lenguaje natural.
    """

    if not isinstance(user_control, dict):
        raise TypeError("user_control debe ser dict.")

    components = user_control.get("modifiable_components")

    if not isinstance(components, list):
        raise TypeError(
            "modifiable_components debe ser list."
        )

    from backend.evaluators.semantic.af_user_control_extractor import (
        control_item_is_confirmed,
    )

    from backend.evaluators.ansiedad_semantic.af_gate_state import exists_state, require_gate
    return require_gate(exists_state(components))
