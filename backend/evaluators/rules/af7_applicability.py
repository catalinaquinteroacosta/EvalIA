"""
EvalIA - Aplicabilidad de AF7.

AF7 aplica únicamente cuando existen:

1. activación emocional/fisiológica confirmada;
2. interferencia confirmada sobre una acción concreta; y
3. relación semántica SUPPORTED entre esa activación y esa interferencia.

La mera coexistencia de activación e interferencia NO activa AF7.

Este módulo:
- no puntúa B/T/M;
- no descubre nuevas emociones;
- no descubre nuevas acciones;
- utiliza hechos previamente extraídos;
- valida únicamente la relación Activación -> Acción/Interferencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.evaluators.semantic.af_user_emotion_extractor import (
    emotion_item_is_confirmed,
)
from backend.evaluators.semantic.af_activation_action import (
    validate_activation_action_relation,
    relation_is_confirmed,
    SEMANTIC_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class AF7ApplicabilityDecision:
    applicable: bool
    has_activation: bool
    has_action_interference: bool
    has_activation_action_relation: bool
    activation_ids: tuple[str, ...]
    interference_ids: tuple[str, ...]
    confirmed_relation_pairs: tuple[
        tuple[str, str],
        ...
    ]
    evaluated_relations: tuple[dict[str, Any], ...]
    reason: str


def _semantic_item_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Solo supported cuenta como evidencia positiva.
    """

    validation = item.get("semantic_validation")

    return bool(
        isinstance(validation, dict)
        and validation.get("status") == "supported"
    )


def _extract_evidence_quote(
    item: dict[str, Any],
) -> str:
    """
    Recupera evidencia literal desde el formato común
    de los extractores de usuario.
    """

    evidence = item.get("evidence")

    if isinstance(evidence, dict):
        quote = evidence.get("quote", "")

        if isinstance(quote, str):
            return quote.strip()

    if isinstance(evidence, str):
        return evidence.strip()

    return ""


def resolve_af7_applicability(
    *,
    user_emotion: dict[str, Any],
    user_action: dict[str, Any],
    context: str,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> AF7ApplicabilityDecision:
    """
    Resuelve exclusivamente la aplicabilidad de AF7.

    Procedimiento:
    1. filtra activaciones confirmadas;
    2. filtra interferencias confirmadas;
    3. evalúa cada pareja activación-interferencia;
    4. AF7 aplica solo si al menos una relación es supported.

    ambiguous se conserva para trazabilidad, pero no activa AF7.
    """

    if not isinstance(user_emotion, dict):
        raise TypeError(
            "user_emotion debe ser dict."
        )

    if not isinstance(user_action, dict):
        raise TypeError(
            "user_action debe ser dict."
        )

    if not isinstance(context, str) or not context.strip():
        raise ValueError(
            "context debe contener el contexto original."
        )

    activation = user_emotion.get(
        "activation",
        None,
    )

    interferences = user_action.get(
        "action_interferences",
        None,
    )

    if not isinstance(activation, list):
        raise ValueError(
            "user_emotion['activation'] debe ser una lista."
        )

    if not isinstance(interferences, list):
        raise ValueError(
            "user_action['action_interferences'] debe ser una lista."
        )

    from backend.evaluators.ansiedad_semantic.af_gate_state import exists_state, require_gate, conjunction
    require_gate(conjunction(exists_state(activation),exists_state(interferences)))

    confirmed_activation = [
        item
        for item in activation
        if isinstance(item, dict)
        and emotion_item_is_confirmed(item)
    ]

    confirmed_interferences = [
        item
        for item in interferences
        if isinstance(item, dict)
        and _semantic_item_is_confirmed(item)
    ]

    activation_ids = tuple(
        str(item.get("id", ""))
        for item in confirmed_activation
        if item.get("id")
    )

    interference_ids = tuple(
        str(item.get("id", ""))
        for item in confirmed_interferences
        if item.get("id")
    )

    has_activation = bool(
        confirmed_activation
    )

    has_action_interference = bool(
        confirmed_interferences
    )

    evaluated_relations: list[
        dict[str, Any]
    ] = []

    confirmed_relation_pairs: list[
        tuple[str, str]
    ] = []

    # No hacemos ninguna llamada semántica si falta
    # alguno de los dos lados de la condición.
    if has_activation and has_action_interference:

        for activation_item in confirmed_activation:

            activation_id = str(
                activation_item.get("id", "")
            )

            activation_description = str(
                activation_item.get(
                    "description",
                    "",
                )
            ).strip()

            activation_evidence = (
                _extract_evidence_quote(
                    activation_item
                )
            )

            if (
                not activation_id
                or not activation_description
                or not activation_evidence
            ):
                continue

            for interference_item in confirmed_interferences:

                interference_id = str(
                    interference_item.get(
                        "id",
                        "",
                    )
                )

                action_description = str(
                    interference_item.get(
                        "action_description",
                        "",
                    )
                ).strip()

                interference_description = str(
                    interference_item.get(
                        "interference_description",
                        "",
                    )
                ).strip()

                interference_evidence = (
                    _extract_evidence_quote(
                        interference_item
                    )
                )

                if (
                    not interference_id
                    or not action_description
                    or not interference_description
                    or not interference_evidence
                ):
                    continue

                relation = (
                    validate_activation_action_relation(
                        context=context,
                        activation_description=(
                            activation_description
                        ),
                        activation_evidence=(
                            activation_evidence
                        ),
                        action_description=(
                            action_description
                        ),
                        interference_description=(
                            interference_description
                        ),
                        interference_evidence=(
                            interference_evidence
                        ),
                        model=model,
                        timeout=timeout,
                    )
                )

                relation_record = {
                    "activation_id": activation_id,
                    "interference_id": interference_id,
                    "status": relation.get(
                        "status"
                    ),
                    "reason": relation.get(
                        "reason"
                    ),
                    "supporting_evidence": (
                        relation.get(
                            "supporting_evidence",
                            [],
                        )
                    ),
                    "counterevidence": (
                        relation.get(
                            "counterevidence",
                            [],
                        )
                    ),
                }

                evaluated_relations.append(
                    relation_record
                )

                if relation_is_confirmed(
                    relation
                ):
                    confirmed_relation_pairs.append(
                        (
                            activation_id,
                            interference_id,
                        )
                    )

    has_activation_action_relation = bool(
        confirmed_relation_pairs
    )
    if has_activation and has_action_interference and not has_activation_action_relation:
        if not evaluated_relations or any(row.get("status") != "not_supported" for row in evaluated_relations):
            raise ValueError("AF7: relación activación-interferencia pendiente; no es gate ausente verificado")

    applicable = bool(
        has_activation
        and has_action_interference
        and has_activation_action_relation
    )

    if applicable:
        reason = (
            "AF7 aplica: existe activación confirmada, "
            "interferencia confirmada sobre una acción "
            "concreta y al menos una relación semántica "
            "Activación -> Interferencia confirmada."
        )

    elif not has_activation:
        reason = (
            "AF7 no aplica: no existe activación "
            "emocional/fisiológica confirmada."
        )

    elif not has_action_interference:
        reason = (
            "AF7 no aplica: existe activación confirmada, "
            "pero no existe interferencia confirmada sobre "
            "una acción concreta."
        )

    else:
        reason = (
            "AF7 no aplica: existen activación e "
            "interferencia confirmadas, pero no se confirmó "
            "que la activación sea la que interfiera con "
            "la acción."
        )

    return AF7ApplicabilityDecision(
        applicable=applicable,
        has_activation=has_activation,
        has_action_interference=(
            has_action_interference
        ),
        has_activation_action_relation=(
            has_activation_action_relation
        ),
        activation_ids=activation_ids,
        interference_ids=interference_ids,
        confirmed_relation_pairs=tuple(
            confirmed_relation_pairs
        ),
        evaluated_relations=tuple(
            evaluated_relations
        ),
        reason=reason,
    )
