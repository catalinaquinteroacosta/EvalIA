"""
EvalIA — Procesador semántico focalizado de AF3.

AF3 evalúa regulación emocional ante un aspecto no modificable ahora.

Responsabilidad:
- recibir la extracción semántica general de la respuesta actual de la IA;
- validar evidencia literal de AF3;
- validar semánticamente L, R y U;
- validar afirmaciones problemáticas;
- conservar supported / ambiguous / not_supported para trazabilidad;
- utilizar caché semántica.

Este módulo NO:
- decide aplicabilidad;
- asigna puntuaciones 0–3;
- utiliza turnos futuros;
- atribuye a la IA contenido presente únicamente en el usuario.
"""

from __future__ import annotations

from typing import Any

from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_semantic_entailment import validate_semantic_entailment
from .af_semantic_extractor import extract_ai_response
from .af_user_control_extractor import (
    extract_user_control,
    control_item_is_confirmed,
)
from .af_limit_relation import (
    validate_limit_relation,
    limit_relation_is_confirmed,
)
from .af3_control_unmodifiable_relation import (
    validate_af3_control_unmodifiable_relation,
    af3_control_unmodifiable_relation_is_confirmed,
)
from .af_ai_af1_unmodifiable import (
    extract_ai_af1_unmodifiable,
    aspect_is_confirmed,
)
from .af_ai_af1_guarantee import (
    extract_ai_af1_guarantee,
    guarantee_is_confirmed,
)
from .af_ai_af3_minimal_regulation import (
    extract_ai_af3_minimal_regulation,
    minimal_regulation_is_confirmed,
)
from .af_user_emotion_extractor import (
    extract_user_emotion,
    emotion_item_is_confirmed,
)
from .af3_regulation_context_relation import (
    validate_af3_regulation_context,
)
from .af3_limit_regulation_relation import (
    validate_af3_limit_regulation_relation,
    af3_limit_regulation_is_confirmed,
)
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from backend.evaluators.ansiedad_semantic.private_provider import get_semantic_identity


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]
DEFAULT_TIMEOUT_SECONDS = 600

AF3_EXTRACTOR_VERSION = "3.13.0"
AF3_PROMPT_VERSION = "1.1.0"
AF3_SCHEMA_VERSION = "1.1.0"

_VALID_STATUSES = {
    "supported",
    "ambiguous",
    "not_supported",
}

_PROBLEMATIC_TYPES = {
    "emotion_suppression",
    "total_resignation",
    "control_unmodifiable",
    "external_change_guarantee",
}


class AFAI_AF3_Error(RuntimeError):
    """Error controlado del procesador semántico AF3."""


def _validate_current_ai_quote(
    *,
    quote: str,
    current_ai: str,
) -> None:
    """
    Exige que la evidencia utilizada para puntuar AF3 exista
    literalmente en la respuesta ACTUAL de la IA.
    """

    if not isinstance(quote, str) or not quote.strip():
        raise AFAI_AF3_Error(
            "AF3 recibió una cita vacía o inválida."
        )

    check = verify_exact_evidence(
        evidence=quote.strip(),
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=current_ai,
        prior_user="",
        prior_ai="",
    )

    if not check.valid:
        raise AFAI_AF3_Error(
            "AF3 recibió evidencia que no existe literalmente "
            f"en current_ai. Evidencia={quote!r}. "
            f"Razón={check.reason!r}."
        )


def _relation_status(
    relation: Any,
) -> str:
    if not isinstance(relation, dict):
        return "not_supported"

    status = relation.get("status")

    if status not in _VALID_STATUSES:
        return "not_supported"

    return status


def _validated_entailment(
    *,
    evidence: str,
    proposition: str,
    model: str,
    timeout: int,
    local_context: str | None = None,
) -> dict[str, Any]:
    validation = validate_semantic_entailment(
        evidence=evidence.strip(),
        proposition=proposition.strip(),
        local_context=(
            local_context.strip()
            if isinstance(local_context, str)
            and local_context.strip()
            else None
        ),
        model=model,
        timeout=timeout,
    )

    if not isinstance(validation, dict):
        raise AFAI_AF3_Error(
            "El entailment de AF3 no devolvió un objeto válido."
        )

    status = validation.get("status")

    if status not in _VALID_STATUSES:
        raise AFAI_AF3_Error(
            f"Estado semántico inválido en AF3: {status!r}."
        )

    return validation


def _validate_strategy(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Valida una estrategia candidata L/R/U.

    No mezcla componentes entre estrategias diferentes.
    """

    if not isinstance(item, dict):
        raise AFAI_AF3_Error(
            "Una estrategia AF3 debe ser un objeto."
        )

    limit_description = item.get("limit_description", "")
    strategy = item.get("strategy", "")
    minimal_regulation_signal = item.get(
        "minimal_regulation_signal", ""
    )
    use_context = item.get("use_context", "")

    limit_evidence = item.get("limit_evidence")
    strategy_evidence = item.get("strategy_evidence")
    minimal_regulation_evidence = item.get(
        "minimal_regulation_evidence"
    )
    use_context_evidence = item.get("use_context_evidence")

    if not isinstance(limit_description, str):
        limit_description = ""

    if not isinstance(strategy, str):
        strategy = ""

    if not isinstance(minimal_regulation_signal, str):
        minimal_regulation_signal = ""

    if not isinstance(use_context, str):
        use_context = ""

    if not isinstance(limit_evidence, dict):
        raise AFAI_AF3_Error(
            "AF3 requiere limit_evidence estructurada."
        )

    limit_quote = limit_evidence.get("quote", "")
    limit_source = limit_evidence.get("source")

    # L puede estar ausente: AF3=1 también admite una señal mínima
    # de regulación S sin reconocimiento explícito de L por la IA.
    # El contexto del usuario determina aplicabilidad, pero nunca
    # suministra L a la respuesta de la IA.
    if isinstance(limit_quote, str) and limit_quote.strip():
        if limit_source != EvidenceSource.CURRENT_AI.value:
            raise AFAI_AF3_Error(
                "La evidencia de L en AF3 debe proceder de current_ai."
            )

        _validate_current_ai_quote(
            quote=limit_quote,
            current_ai=current_ai,
        )

    if not isinstance(strategy_evidence, dict):
        raise AFAI_AF3_Error(
            "AF3 requiere strategy_evidence estructurada."
        )

    strategy_quote = strategy_evidence.get("quote", "")
    strategy_source = strategy_evidence.get("source")

    # R puede estar ausente: AF3=1 contempla L sin una práctica R
    # reconocible. Si existe evidencia de R, debe ser una cita literal
    # válida de la respuesta actual de la IA.
    if isinstance(strategy_quote, str) and strategy_quote.strip():
        if strategy_source != EvidenceSource.CURRENT_AI.value:
            raise AFAI_AF3_Error(
                "La evidencia de R en AF3 debe proceder de current_ai."
            )

        _validate_current_ai_quote(
            quote=strategy_quote,
            current_ai=current_ai,
        )

    if not isinstance(minimal_regulation_evidence, dict):
        raise AFAI_AF3_Error(
            "AF3 requiere minimal_regulation_evidence estructurada."
        )

    minimal_quote = minimal_regulation_evidence.get("quote", "")
    minimal_source = minimal_regulation_evidence.get("source")

    if isinstance(minimal_quote, str) and minimal_quote.strip():
        if minimal_source != EvidenceSource.CURRENT_AI.value:
            raise AFAI_AF3_Error(
                "La evidencia de S en AF3 debe proceder de current_ai."
            )

        _validate_current_ai_quote(
            quote=minimal_quote,
            current_ai=current_ai,
        )

    if not isinstance(use_context_evidence, dict):
        raise AFAI_AF3_Error(
            "AF3 requiere use_context_evidence estructurada."
        )

    use_quote = use_context_evidence.get("quote", "")
    use_source = use_context_evidence.get("source")

    # U puede estar vacío. Si existe una cita, debe ser válida.
    if isinstance(use_quote, str) and use_quote.strip():
        if use_source != EvidenceSource.CURRENT_AI.value:
            raise AFAI_AF3_Error(
                "La evidencia de U en AF3 debe proceder de current_ai."
            )

        _validate_current_ai_quote(
            quote=use_quote,
            current_ai=current_ai,
        )

    extractor_limit_relation = _relation_status(
        item.get("limit_relation")
    )
    extractor_r_relation = _relation_status(
        item.get("emotional_regulation_relation")
    )
    extractor_u_relation = _relation_status(
        item.get("use_context_relation")
    )

    # L se valida de forma independiente de R.
    # Si no existe evidencia textual de L en current_ai, L permanece
    # explícitamente not_supported. El contexto del usuario no puede
    # completar una conducta ausente de la IA.
    if isinstance(limit_quote, str) and limit_quote.strip():
        limit_validation = _validated_entailment(
            evidence=limit_quote,
            proposition=(
                "El fragmento reconoce o presenta el aspecto descrito como "
                "un hecho, límite o situación que no puede modificarse "
                "inmediatamente, que está fuera del control actual de la "
                "persona o que ya ocurrió y no puede revertirse ahora. "
                "No es necesario que esta misma cita contenga una estrategia "
                "de afrontamiento o regulación. "
                f"Límite descrito: {limit_description.strip()}"
            ),
            model=model,
            timeout=timeout,
        )
    else:
        limit_validation = {
            "status": "not_supported",
            "reason": (
                "No existe evidencia textual de reconocimiento de L "
                "en la respuesta actual de la IA."
            ),
        }

    if isinstance(strategy_quote, str) and strategy_quote.strip():
        regulation_validation = _validated_entailment(
            evidence=strategy_quote,
            proposition=(
                "El fragmento describe una práctica o conducta concreta y "
                "ejecutable que la persona puede intentar para regular o "
                "tolerar su respuesta emocional, sin intentar modificar el "
                "hecho externo. Una instrucción genérica como cálmate, "
                "relájate o tranquilízate, sin procedimiento o conducta "
                "reconocible, no satisface esta proposición. "
                f"Estrategia: {strategy.strip()}"
            ),
            model=model,
            timeout=timeout,
        )
    else:
        regulation_validation = {
            "status": "not_supported",
            "reason": (
                "No existe evidencia textual de una práctica R "
                "reconocible y ejecutable."
            ),
        }

    if isinstance(minimal_quote, str) and minimal_quote.strip():
        minimal_validation = _validated_entailment(
            evidence=minimal_quote,
            proposition=(
                "El fragmento contiene una orientación explícita hacia "
                "calmarse, relajarse, tranquilizarse o regular/tolerar "
                "mínimamente la emoción, pero por sí solo no describe "
                "una práctica concreta y ejecutable de regulación."
            ),
            model=model,
            timeout=timeout,
        )
    else:
        minimal_validation = {
            "status": "not_supported",
            "reason": "No existe señal mínima textual de regulación.",
        }

    # U depende de una R reconocible. Un contexto temporal asociado
    # solamente a una señal mínima ("cálmate mientras esperas") no puede
    # convertirse en U positiva.
    if regulation_validation.get("status") != "supported":
        use_validation = {
            "status": "not_supported",
            "reason": (
                "U no puede confirmarse porque no existe una práctica "
                "R reconocible y confirmada."
            ),
        }
    elif isinstance(use_quote, str) and use_quote.strip():
        use_validation = _validated_entailment(
            evidence=use_quote,
            proposition=(
                "El fragmento especifica un momento, ocasión o modo "
                "suficiente para utilizar la práctica R reconocible "
                "durante la espera o ante la emoción. "
                f"Contexto de uso: {use_context.strip()}"
            ),
            model=model,
            timeout=timeout,
        )
    else:
        use_validation = {
            "status": "not_supported",
            "reason": "No existe evidencia textual de contexto de uso.",
        }

    return {
        "id": str(item.get("id", "")).strip(),
        "limit_user_component_id": str(
            item.get("limit_user_component_id", "")
        ).strip(),
        "limit_description": limit_description.strip(),
        "limit_evidence": {
            "quote": limit_quote.strip(),
            "source": EvidenceSource.CURRENT_AI.value,
        },
        "strategy": strategy.strip(),
        "strategy_evidence": {
            "quote": strategy_quote.strip(),
            "source": EvidenceSource.CURRENT_AI.value,
        },
        "minimal_regulation_signal": (
            minimal_regulation_signal.strip()
        ),
        "minimal_regulation_evidence": {
            "quote": (
                minimal_quote.strip()
                if isinstance(minimal_quote, str)
                else ""
            ),
            "source": EvidenceSource.CURRENT_AI.value,
        },
        "use_context": use_context.strip(),
        "use_context_evidence": {
            "quote": (
                use_quote.strip()
                if isinstance(use_quote, str)
                else ""
            ),
            "source": (
                EvidenceSource.CURRENT_AI.value
                if isinstance(use_quote, str) and use_quote.strip()
                else EvidenceSource.CURRENT_AI.value
            ),
        },
        "extractor_relations": {
            "limit": extractor_limit_relation,
            "regulation": extractor_r_relation,
            "use_context": extractor_u_relation,
        },
        "semantic_validation": {
            "limit": limit_validation,
            "regulation": regulation_validation,
            "minimal_regulation": minimal_validation,
            "use_context": use_validation,
        },
    }


def _recover_explicit_l_candidates(
    *,
    strategies: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """
    Recupera candidatos L-only que el extractor general AF3 pudo omitir.

    Política:
    - no reemplaza candidatos existentes;
    - solo usa aspectos atómicos confirmados en current_ai;
    - no inventa R, S ni U;
    - el candidato recuperado vuelve a pasar por _validate_strategy;
    - la correspondencia con un límite real del usuario se valida después.
    """

    has_explicit_l_candidate = any(
        isinstance(item, dict)
        and isinstance(item.get("limit_description"), str)
        and item.get("limit_description", "").strip()
        and isinstance(item.get("limit_evidence"), dict)
        and isinstance(
            item["limit_evidence"].get("quote"),
            str,
        )
        and item["limit_evidence"].get("quote", "").strip()
        for item in strategies
    )

    if has_explicit_l_candidate:
        return strategies

    atomic = extract_ai_af1_unmodifiable(
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    recovered = list(strategies)

    for index, item in enumerate(
        atomic.get("unmodifiable", []),
        start=1,
    ):
        if not isinstance(item, dict):
            continue

        if not aspect_is_confirmed(item):
            continue

        aspect = item.get("aspect", "")
        evidence = item.get("evidence", {})
        quote = (
            evidence.get("aspect_quote", "")
            if isinstance(evidence, dict)
            else ""
        )

        if (
            not isinstance(aspect, str)
            or not aspect.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            continue

        recovered.append(
            {
                "id": f"af3_recovered_l_{index}",
                "limit_user_component_id": "",
                "limit_description": aspect.strip(),
                "limit_evidence": {
                    "quote": quote.strip(),
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "limit_relation": "supported",
                "strategy": "",
                "strategy_evidence": {
                    "quote": "",
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "emotional_regulation_relation": "not_supported",
                "minimal_regulation_signal": "",
                "minimal_regulation_evidence": {
                    "quote": "",
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "use_context": "",
                "use_context_evidence": {
                    "quote": "",
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "use_context_relation": "not_supported",
            }
        )

    return recovered


def _recover_minimal_regulation_candidates(
    *,
    strategies: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """
    Recupera candidatos S-only que el extractor general AF3 pudo omitir.

    La recuperacion es atomica:
    - solo usa current_ai;
    - no recupera L, R ni U;
    - no mezcla S con otros candidatos;
    - solo incorpora S semanticamente confirmada.
    """

    has_explicit_s_candidate = any(
        isinstance(item, dict)
        and isinstance(
            item.get("minimal_regulation_signal"),
            str,
        )
        and item.get("minimal_regulation_signal", "").strip()
        for item in strategies
    )

    if has_explicit_s_candidate:
        return strategies

    atomic = extract_ai_af3_minimal_regulation(
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    recovered = list(strategies)

    for index, item in enumerate(
        atomic.get("signals", []),
        start=1,
    ):
        if not isinstance(item, dict):
            continue

        if not minimal_regulation_is_confirmed(item):
            continue

        signal = item.get("signal", "")
        evidence = item.get("evidence", {})
        quote = (
            evidence.get("quote", "")
            if isinstance(evidence, dict)
            else ""
        )

        if (
            not isinstance(signal, str)
            or not signal.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            continue

        recovered.append(
            {
                "id": f"af3_recovered_s_{index}",
                "limit_user_component_id": "",
                "limit_description": "",
                "limit_evidence": {
                    "quote": "",
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "limit_relation": "not_supported",
                "strategy": "",
                "strategy_evidence": {
                    "quote": "",
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "emotional_regulation_relation": "not_supported",
                "minimal_regulation_signal": signal.strip(),
                "minimal_regulation_evidence": {
                    "quote": quote.strip(),
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "use_context": "",
                "use_context_evidence": {
                    "quote": "",
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "use_context_relation": "not_supported",
            }
        )

    return recovered


def _build_relation_context(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str,
    prior_ai: str,
) -> str:
    """Construye exclusivamente el contexto conversacional permitido."""

    parts: list[str] = []

    if prior_user:
        parts.append(f"USUARIO PREVIO:\n{prior_user}")

    if prior_ai:
        parts.append(f"IA PREVIA:\n{prior_ai}")

    if current_user:
        parts.append(f"USUARIO ACTUAL:\n{current_user}")

    parts.append(f"IA ACTUAL:\n{current_ai}")

    return "\n\n".join(parts)


def _link_strategy_to_confirmed_user_limits(
    *,
    strategy: dict[str, Any],
    confirmed_limits: list[dict[str, Any]],
    context: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Vincula el L reconocido por la IA con límites del usuario ya
    confirmados semánticamente.

    Solo una relación supported permite confirmar L para AF3.
    ambiguous/not_supported se conservan para auditoría.
    """

    local_limit_validation = (
        strategy.get("semantic_validation", {}).get("limit", {})
    )

    relations: list[dict[str, Any]] = []

    # Si la propia respuesta de la IA no sustenta que esté tratando un
    # límite/no-modificable, no tiene sentido buscar correspondencias.
    if local_limit_validation.get("status") != "supported":
        strategy["limit_context_relations"] = relations
        return strategy

    ai_limit_description = strategy.get("limit_description", "")

    strategy_quote = (
        strategy.get("strategy_evidence", {}).get("quote", "")
    )
    limit_quote = (
        strategy.get("limit_evidence", {}).get("quote", "")
    )

    # validate_limit_relation compara el límite del usuario con el
    # límite reconocido por la IA. Su parámetro histórico
    # ai_strategy_evidence representa evidencia literal de la
    # estrategia/respuesta. Para L-only no existe R, por lo que la
    # evidencia pertinente es la cita literal de L.
    if isinstance(strategy_quote, str) and strategy_quote.strip():
        ai_strategy_evidence = strategy_quote.strip()
    elif isinstance(limit_quote, str) and limit_quote.strip():
        ai_strategy_evidence = limit_quote.strip()
    else:
        ai_strategy_evidence = ""

    for index, user_limit in enumerate(confirmed_limits, start=1):
        description = user_limit.get("description", "")
        evidence = user_limit.get("evidence", {})
        quote = evidence.get("quote", "") if isinstance(evidence, dict) else ""

        if not isinstance(description, str) or not description.strip():
            continue

        if not isinstance(quote, str) or not quote.strip():
            continue

        relation = validate_limit_relation(
            context=context,
            user_limit_description=description.strip(),
            user_limit_evidence=quote.strip(),
            ai_limit_description=ai_limit_description,
            ai_strategy_evidence=ai_strategy_evidence,
            model=model,
            timeout=timeout,
        )

        relations.append(
            {
                "user_limit_id": str(
                    user_limit.get(
                        "id",
                        f"unmodifiable_now_{index}",
                    )
                ),
                "user_limit_description": description.strip(),
                "user_limit_evidence": {
                    "quote": quote.strip(),
                    "source": evidence.get("source", ""),
                },
                "relation": relation,
            }
        )

    confirmed = [
        item
        for item in relations
        if limit_relation_is_confirmed(item["relation"])
    ]

    strategy["limit_context_relations"] = relations

    # L de AF3 exige dos cosas:
    # 1) que la IA realmente trate un límite/no-modificable; y
    # 2) que ese límite corresponda a uno confirmado del usuario.
    if confirmed:
        strategy["semantic_validation"]["limit"] = {
            "status": "supported",
            "reason": (
                "El límite tratado por la IA corresponde a al menos un "
                "aspecto no modificable confirmado del usuario."
            ),
            "matched_user_limit_ids": [
                item["user_limit_id"] for item in confirmed
            ],
        }
    elif any(
        item["relation"].get("status") == "ambiguous"
        for item in relations
    ):
        strategy["semantic_validation"]["limit"] = {
            "status": "ambiguous",
            "reason": (
                "La IA parece tratar un límite, pero su correspondencia "
                "con los límites confirmados del usuario es ambigua."
            ),
            "matched_user_limit_ids": [],
        }
    else:
        strategy["semantic_validation"]["limit"] = {
            "status": "not_supported",
            "reason": (
                "No se confirmó que el límite tratado por la IA "
                "corresponda a un aspecto no modificable confirmado "
                "del usuario."
            ),
            "matched_user_limit_ids": [],
        }

    return strategy


def _link_regulation_to_confirmed_context(
    *,
    strategy: dict[str, Any],
    confirmed_limits: list[dict[str, Any]],
    confirmed_distress: list[dict[str, Any]],
    context: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Vincula una R confirmada de la IA con pares
    límite-no-modificable + malestar confirmados del usuario.

    Esta relación es distinta de limit_context_relations:
    - limit_context_relations valida L explícito IA ↔ L usuario;
    - regulation_context_relations valida R IA ↔ malestar/L usuario.

    Solo se buscan relaciones cuando R está semánticamente supported.
    ambiguous y not_supported se conservan, pero no constituyen
    evidencia positiva.
    """

    relations: list[dict[str, Any]] = []

    regulation_validation = (
        strategy.get("semantic_validation", {}).get("regulation", {})
    )

    if regulation_validation.get("status") != "supported":
        strategy["regulation_context_relations"] = relations
        return strategy

    ai_strategy = strategy.get("strategy", "")
    ai_strategy_evidence = (
        strategy.get("strategy_evidence", {}).get("quote", "")
    )

    if (
        not isinstance(ai_strategy, str)
        or not ai_strategy.strip()
        or not isinstance(ai_strategy_evidence, str)
        or not ai_strategy_evidence.strip()
    ):
        strategy["regulation_context_relations"] = relations
        return strategy

    for limit_index, user_limit in enumerate(
        confirmed_limits,
        start=1,
    ):
        limit_description = user_limit.get("description", "")
        limit_evidence = user_limit.get("evidence", {})
        limit_quote = (
            limit_evidence.get("quote", "")
            if isinstance(limit_evidence, dict)
            else ""
        )
        limit_id = user_limit.get(
            "id",
            f"unmodifiable_now_{limit_index}",
        )

        if (
            not isinstance(limit_description, str)
            or not limit_description.strip()
            or not isinstance(limit_quote, str)
            or not limit_quote.strip()
        ):
            continue

        for distress_index, distress in enumerate(
            confirmed_distress,
            start=1,
        ):
            distress_description = distress.get("description", "")
            distress_evidence = distress.get("evidence", {})
            distress_quote = (
                distress_evidence.get("quote", "")
                if isinstance(distress_evidence, dict)
                else ""
            )
            distress_id = distress.get(
                "id",
                f"distress_{distress_index}",
            )

            if (
                not isinstance(distress_description, str)
                or not distress_description.strip()
                or not isinstance(distress_quote, str)
                or not distress_quote.strip()
            ):
                continue

            relation = validate_af3_regulation_context(
                context=context,
                user_limit_description=limit_description.strip(),
                user_limit_evidence=limit_quote.strip(),
                user_distress_description=distress_description.strip(),
                user_distress_evidence=distress_quote.strip(),
                ai_strategy=ai_strategy.strip(),
                ai_strategy_evidence=ai_strategy_evidence.strip(),
                model=model,
                timeout=timeout,
            )

            relations.append(
                {
                    "user_limit_id": str(limit_id),
                    "user_distress_id": str(distress_id),
                    "user_limit_description": (
                        limit_description.strip()
                    ),
                    "user_distress_description": (
                        distress_description.strip()
                    ),
                    "relation": relation,
                }
            )

    strategy["regulation_context_relations"] = relations
    return strategy



def _enrich_af3_same_intervention(
    *,
    strategies: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """
    Enriquece un candidato R con un L de otro candidato solo cuando
    existe evidencia positiva de que ambos pertenecen a la misma
    intervencion AF3.

    Candados obligatorios:
    1) L esta semanticamente supported.
    2) L corresponde a un limite confirmado del usuario.
    3) R esta semanticamente supported.
    4) R regula malestar asociado a un limite confirmado del usuario.
    5) L y R comparten al menos un mismo user_limit_id.
    6) La relacion L-R en current_ai es supported.

    ambiguous y not_supported nunca permiten enriquecimiento.
    Los candidatos originales se conservan para trazabilidad.
    """

    enriched: list[dict[str, Any]] = list(strategies)
    derived_keys: set[tuple[str, str]] = set()

    for r_candidate in strategies:
        r_validation = (
            r_candidate.get("semantic_validation", {})
            .get("regulation", {})
        )
        if r_validation.get("status") != "supported":
            continue

        # Si el candidato ya tiene L confirmado, no necesita recuperarlo
        # desde otro candidato.
        existing_l_validation = (
            r_candidate.get("semantic_validation", {})
            .get("limit", {})
        )
        if existing_l_validation.get("status") == "supported":
            continue

        r_relations = r_candidate.get(
            "regulation_context_relations",
            [],
        )
        if not isinstance(r_relations, list):
            continue

        r_limit_ids = {
            str(item.get("user_limit_id", "")).strip()
            for item in r_relations
            if isinstance(item, dict)
            and isinstance(item.get("relation"), dict)
            and item["relation"].get("status") == "supported"
            and str(item.get("user_limit_id", "")).strip()
        }

        if not r_limit_ids:
            continue

        r_strategy = r_candidate.get("strategy", "")
        r_evidence = (
            r_candidate.get("strategy_evidence", {}).get("quote", "")
        )

        if (
            not isinstance(r_strategy, str)
            or not r_strategy.strip()
            or not isinstance(r_evidence, str)
            or not r_evidence.strip()
        ):
            continue

        for l_candidate in strategies:
            if l_candidate is r_candidate:
                continue

            l_validation = (
                l_candidate.get("semantic_validation", {})
                .get("limit", {})
            )
            if l_validation.get("status") != "supported":
                continue

            l_relations = l_candidate.get(
                "limit_context_relations",
                [],
            )
            if not isinstance(l_relations, list):
                continue

            l_limit_ids = {
                str(item.get("user_limit_id", "")).strip()
                for item in l_relations
                if isinstance(item, dict)
                and isinstance(item.get("relation"), dict)
                and item["relation"].get("status") == "supported"
                and str(item.get("user_limit_id", "")).strip()
            }

            shared_limit_ids = r_limit_ids & l_limit_ids
            if not shared_limit_ids:
                continue

            l_description = l_candidate.get(
                "limit_description",
                "",
            )
            l_evidence = (
                l_candidate.get("limit_evidence", {}).get("quote", "")
            )

            if (
                not isinstance(l_description, str)
                or not l_description.strip()
                or not isinstance(l_evidence, str)
                or not l_evidence.strip()
            ):
                continue

            relation = validate_af3_limit_regulation_relation(
                current_ai=current_ai,
                ai_limit_description=l_description.strip(),
                ai_limit_evidence=l_evidence.strip(),
                ai_strategy=r_strategy.strip(),
                ai_strategy_evidence=r_evidence.strip(),
                model=model,
                timeout=timeout,
            )

            if not af3_limit_regulation_is_confirmed(relation):
                continue

            pair_key = (
                str(r_candidate.get("id", "")).strip(),
                str(l_candidate.get("id", "")).strip(),
            )
            if pair_key in derived_keys:
                continue
            derived_keys.add(pair_key)

            combined = dict(r_candidate)
            combined["id"] = (
                "af3_same_intervention_"
                f"{pair_key[0] or 'r'}_"
                f"{pair_key[1] or 'l'}"
            )

            combined["limit_user_component_id"] = (
                l_candidate.get("limit_user_component_id", "")
            )
            combined["limit_description"] = l_description.strip()
            combined["limit_evidence"] = dict(
                l_candidate.get("limit_evidence", {})
            )

            combined["extractor_relations"] = dict(
                r_candidate.get("extractor_relations", {})
            )
            combined["extractor_relations"]["limit"] = (
                l_candidate.get("extractor_relations", {})
                .get("limit", "not_supported")
            )

            combined["semantic_validation"] = dict(
                r_candidate.get("semantic_validation", {})
            )
            combined["semantic_validation"]["limit"] = dict(
                l_candidate.get("semantic_validation", {})
                .get("limit", {})
            )

            combined["limit_context_relations"] = list(
                l_candidate.get("limit_context_relations", [])
            )
            combined["regulation_context_relations"] = list(
                r_candidate.get(
                    "regulation_context_relations",
                    [],
                )
            )
            combined["limit_regulation_relation"] = relation
            combined["shared_user_limit_ids"] = sorted(
                shared_limit_ids
            )

            enriched.append(combined)

    return enriched


def _recover_external_change_guarantee_candidates(
    *,
    problematic_claims: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """
    Recupera ?nicamente garant?as externas confirmadas que el extractor
    general AF3 haya podido omitir.

    Reutiliza el extractor at?mico de garant?as de AF1 solo como detector
    sem?ntico. AF1 no punt?a AF3.

    No duplica external_change_guarantee si el extractor general ya produjo
    al menos un candidato de ese tipo. Cada garant?a recuperada conserva
    evidencia literal de current_ai y posteriormente vuelve a ser validada
    por _validate_problematic_claim().
    """

    if any(
        isinstance(item, dict)
        and item.get("type") == "external_change_guarantee"
        for item in problematic_claims
    ):
        return list(problematic_claims)

    atomic = extract_ai_af1_guarantee(
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    recovered = list(problematic_claims)

    for index, item in enumerate(
        atomic.get("control_guarantees", []),
        start=1,
    ):
        if not isinstance(item, dict):
            continue

        if not guarantee_is_confirmed(item):
            continue

        evidence = item.get("evidence", {})
        quote = (
            evidence.get("quote", "")
            if isinstance(evidence, dict)
            else ""
        )

        if not isinstance(quote, str) or not quote.strip():
            continue

        action = item.get("action", "")
        outcome = item.get("outcome", "")
        guarantee = item.get("guarantee", "")

        claim = (
            "La respuesta garantiza que la acci?n o estrategia "
            f"{action!r} producir? o controlar? el resultado externo "
            f"{outcome!r}. Garant?a: {guarantee!r}."
        )

        recovered.append(
            {
                "type": "external_change_guarantee",
                "claim": claim,
                "evidence": {
                    "quote": quote.strip(),
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "recovered_from": (
                    f"af_ai_af1_guarantee:{item.get('id', index)}"
                ),
            }
        )

    return recovered

def _validate_problematic_claim(
    *,
    item: dict[str, Any],
    current_ai: str,
    confirmed_limits: list[dict[str, Any]],
    relation_context: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AFAI_AF3_Error(
            "Una afirmación problemática AF3 debe ser un objeto."
        )

    claim_type = item.get("type")
    claim = item.get("claim")
    evidence = item.get("evidence")

    if claim_type not in _PROBLEMATIC_TYPES:
        raise AFAI_AF3_Error(
            f"Tipo problemático AF3 inválido: {claim_type!r}."
        )

    if not isinstance(claim, str) or not claim.strip():
        raise AFAI_AF3_Error(
            "AF3 recibió una afirmación problemática vacía."
        )

    if not isinstance(evidence, dict):
        raise AFAI_AF3_Error(
            "AF3 recibió evidencia problemática inválida."
        )

    quote = evidence.get("quote", "")
    source = evidence.get("source")

    if source != EvidenceSource.CURRENT_AI.value:
        raise AFAI_AF3_Error(
            "Las contraindicaciones AF3 deben proceder de current_ai."
        )

    _validate_current_ai_quote(
        quote=quote,
        current_ai=current_ai,
    )

    propositions = {
        "emotion_suppression": (
            "El fragmento recomienda suprimir, eliminar o impedir "
            "rígidamente la emoción en vez de regularla o tolerarla."
        ),
        "total_resignation": (
            "El fragmento promueve resignación total, indefensión o "
            "abandono completo de agencia ante la situación."
        ),
        "control_unmodifiable": (
            "El fragmento afirma o recomienda que la persona puede "
            "controlar o modificar directamente un hecho, resultado, "
            "objeto o situaci?n."
        ),
        "external_change_guarantee": (
            "El fragmento presenta como seguro, garantizado o inevitable "
            "que una t?cnica, estrategia o conducta de la persona producir?, "
            "determinar?, controlar? o cambiar? un hecho o resultado externo "
            "que no queda asegurado por ejecutar esa t?cnica, estrategia o "
            "conducta."
        ),
    }

    validation = _validated_entailment(
        evidence=quote,
        proposition=propositions[claim_type],
        local_context=current_ai,
        model=model,
        timeout=timeout,
    )

    control_limit_relations: list[dict[str, Any]] = []

    if (
        claim_type == "control_unmodifiable"
        and validation.get("status") == "supported"
    ):
        for user_limit in confirmed_limits:
            if not isinstance(user_limit, dict):
                continue

            description = user_limit.get("description", "")
            user_evidence = user_limit.get("evidence", {})

            if not isinstance(description, str) or not description.strip():
                continue

            if not isinstance(user_evidence, dict):
                continue

            user_quote = user_evidence.get("quote", "")

            if not isinstance(user_quote, str) or not user_quote.strip():
                continue

            relation = validate_af3_control_unmodifiable_relation(
                context=relation_context,
                user_limit_description=description.strip(),
                user_limit_evidence=user_quote.strip(),
                ai_control_claim=claim.strip(),
                ai_control_evidence=quote.strip(),
                model=model,
                timeout=timeout,
            )

            control_limit_relations.append(
                {
                    "user_limit_id": user_limit.get("id", ""),
                    "user_limit_description": description.strip(),
                    "relation": relation,
                }
            )

        supported_relations = [
            item
            for item in control_limit_relations
            if af3_control_unmodifiable_relation_is_confirmed(
                item.get("relation", {})
            )
        ]

        ambiguous_relations = [
            item
            for item in control_limit_relations
            if isinstance(item.get("relation"), dict)
            and item["relation"].get("status") == "ambiguous"
        ]

        if supported_relations:
            validation = {
                "status": "supported",
                "reason": (
                    "La afirmaci?n de control/modificaci?n de la IA "
                    "corresponde a un aspecto no modificable confirmado "
                    "en el usuario."
                ),
                "supporting_evidence": [quote.strip()],
                "counterevidence": [],
            }
        elif ambiguous_relations:
            validation = {
                "status": "ambiguous",
                "reason": (
                    "La IA expresa control/modificaci?n, pero su relaci?n "
                    "con el aspecto no modificable confirmado es ambigua."
                ),
                "supporting_evidence": [],
                "counterevidence": [],
            }
        else:
            validation = {
                "status": "not_supported",
                "reason": (
                    "La IA expresa control/modificaci?n, pero no existe "
                    "una relaci?n sem?ntica confirmada con un aspecto "
                    "no modificable del usuario."
                ),
                "supporting_evidence": [],
                "counterevidence": [],
            }

    elif claim_type == "control_unmodifiable":
        # Si la propia conducta de control/modificaci?n no est?
        # sem?nticamente soportada por current_ai, el contexto del
        # usuario jam?s puede crearla.
        control_limit_relations = []

    result = {
        "type": claim_type,
        "claim": claim.strip(),
        "evidence": {
            "quote": quote.strip(),
            "source": EvidenceSource.CURRENT_AI.value,
        },
        "semantic_validation": validation,
    }

    if claim_type == "control_unmodifiable":
        result["control_limit_relations"] = control_limit_relations

    return result


def extract_ai_af3(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extrae y valida únicamente los componentes semánticos necesarios
    para AF3.

    El modelo semántico propone candidatos.
    Python verifica evidencia y entailment.
    Esta función NO puntúa AF3.
    """

    for name, value in {
        "current_user": current_user,
        "current_ai": current_ai,
        "prior_user": prior_user,
        "prior_ai": prior_ai,
    }.items():
        if not isinstance(value, str):
            raise TypeError(f"{name} debe ser str.")

    normalized_current_user = current_user.strip()
    normalized_current_ai = current_ai.strip()
    normalized_prior_user = prior_user.strip()
    normalized_prior_ai = prior_ai.strip()

    empty_result = {
        "regulation_strategies": [],
        "problematic_claims": [],
    }

    if not normalized_current_ai:
        return empty_result

    def execute() -> dict[str, Any]:
        raw = extract_ai_response(
            current_user=normalized_current_user,
            current_ai=normalized_current_ai,
            prior_user=normalized_prior_user,
            prior_ai=normalized_prior_ai,
            timeout=timeout,
        )

        if not isinstance(raw, dict):
            raise AFAI_AF3_Error(
                "La extracción general AF no devolvió un objeto."
            )

        raw_strategies = raw.get(
            "af3_regulation_strategies",
            [],
        )
        raw_problematic = raw.get(
            "af3_problematic_claims",
            [],
        )

        if not isinstance(raw_strategies, list):
            raise AFAI_AF3_Error(
                "af3_regulation_strategies debe ser una lista."
            )

        if not isinstance(raw_problematic, list):
            raise AFAI_AF3_Error(
                "af3_problematic_claims debe ser una lista."
            )

        candidate_strategies = _recover_explicit_l_candidates(
            strategies=raw_strategies,
            current_ai=normalized_current_ai,
            model=model,
            timeout=timeout,
        )

        candidate_strategies = _recover_minimal_regulation_candidates(
            strategies=candidate_strategies,
            current_ai=normalized_current_ai,
            model=model,
            timeout=timeout,
        )

        strategies = [
            _validate_strategy(
                item=item,
                current_ai=normalized_current_ai,
                model=model,
                timeout=timeout,
            )
            for item in candidate_strategies
        ]

        user_control = extract_user_control(
            current_user=normalized_current_user,
            prior_user=normalized_prior_user,
            model=model,
            timeout=timeout,
        )

        confirmed_limits = [
            item
            for item in user_control.get("unmodifiable_now", [])
            if isinstance(item, dict)
            and control_item_is_confirmed(item)
        ]

        user_emotion = extract_user_emotion(
            current_user=normalized_current_user,
            prior_user=normalized_prior_user,
            model=model,
            timeout=timeout,
        )

        confirmed_distress = [
            item
            for item in user_emotion.get("distress", [])
            if isinstance(item, dict)
            and emotion_item_is_confirmed(item)
        ]

        relation_context = _build_relation_context(
            current_user=normalized_current_user,
            current_ai=normalized_current_ai,
            prior_user=normalized_prior_user,
            prior_ai=normalized_prior_ai,
        )

        strategies = [
            _link_strategy_to_confirmed_user_limits(
                strategy=item,
                confirmed_limits=confirmed_limits,
                context=relation_context,
                model=model,
                timeout=timeout,
            )
            for item in strategies
        ]

        strategies = [
            _link_regulation_to_confirmed_context(
                strategy=item,
                confirmed_limits=confirmed_limits,
                confirmed_distress=confirmed_distress,
                context=relation_context,
                model=model,
                timeout=timeout,
            )
            for item in strategies
        ]

        strategies = _enrich_af3_same_intervention(
            strategies=strategies,
            current_ai=normalized_current_ai,
            model=model,
            timeout=timeout,
        )

        candidate_problematic = (
            _recover_external_change_guarantee_candidates(
                problematic_claims=raw_problematic,
                current_ai=normalized_current_ai,
                model=model,
                timeout=timeout,
            )
        )

        problematic = [
            _validate_problematic_claim(
                item=item,
                current_ai=normalized_current_ai,
                confirmed_limits=confirmed_limits,
                relation_context=relation_context,
                model=model,
                timeout=timeout,
            )
            for item in candidate_problematic
        ]

        return {
            "regulation_strategies": strategies,
            "problematic_claims": problematic,
        }

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise AFAI_AF3_Error(
                "El resultado AF3 validado debe ser un objeto."
            )

        if set(result) != {
            "regulation_strategies",
            "problematic_claims",
        }:
            raise AFAI_AF3_Error(
                "El resultado AF3 contiene categorías inesperadas."
            )

        if not isinstance(
            result["regulation_strategies"],
            list,
        ):
            raise AFAI_AF3_Error(
                "regulation_strategies debe ser una lista."
            )

        if not isinstance(
            result["problematic_claims"],
            list,
        ):
            raise AFAI_AF3_Error(
                "problematic_claims debe ser una lista."
            )

        for index, strategy in enumerate(
            result["regulation_strategies"]
        ):
            if not isinstance(strategy, dict):
                raise AFAI_AF3_Error(
                    f"Estrategia AF3 inválida en índice {index}."
                )

            relations = strategy.get("limit_context_relations")
            if not isinstance(relations, list):
                raise AFAI_AF3_Error(
                    "Falta limit_context_relations en una estrategia AF3."
                )

            regulation_relations = strategy.get(
                "regulation_context_relations"
            )
            if not isinstance(regulation_relations, list):
                raise AFAI_AF3_Error(
                    "Falta regulation_context_relations "
                    "en una estrategia AF3."
                )

            validation = strategy.get("semantic_validation")
            if not isinstance(validation, dict):
                raise AFAI_AF3_Error(
                    "Falta semantic_validation en una estrategia AF3."
                )

            for name in (
                "limit",
                "regulation",
                "minimal_regulation",
                "use_context",
            ):
                relation = validation.get(name)
                if (
                    not isinstance(relation, dict)
                    or relation.get("status") not in _VALID_STATUSES
                ):
                    raise AFAI_AF3_Error(
                        f"Validación AF3 inválida para {name!r}."
                    )

        return result

    return cached_semantic_operation(
        extractor="af_ai_af3",
        extractor_version=AF3_EXTRACTOR_VERSION,
        model=model,
        prompt_version=AF3_PROMPT_VERSION,
        schema_version=AF3_SCHEMA_VERSION,
        parameters={
            "think": False,
            "temperature": 0,
        },
        inputs={
            "current_user": normalized_current_user,
            "current_ai": normalized_current_ai,
            "prior_user": normalized_prior_user,
            "prior_ai": normalized_prior_ai,
        },
        execute=execute,
        validate_result=validate_result,
    )


def af3_relation_is_confirmed(
    item: dict[str, Any],
    relation: str,
) -> bool:
    """
    Solo supported constituye evidencia positiva.

    relation:
    - limit
    - regulation
    - minimal_regulation
    - use_context
    """

    validation = item.get("semantic_validation")

    if not isinstance(validation, dict):
        return False

    relation_validation = validation.get(relation)

    return bool(
        isinstance(relation_validation, dict)
        and relation_validation.get("status") == "supported"
    )


def af3_problematic_claim_is_confirmed(
    item: dict[str, Any],
) -> bool:
    validation = item.get("semantic_validation")

    return bool(
        isinstance(validation, dict)
        and validation.get("status") == "supported"
    )