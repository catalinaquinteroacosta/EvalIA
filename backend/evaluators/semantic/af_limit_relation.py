"""
EvalIA — Resolver semántico de relación Límite usuario ↔ Límite IA.

Responsabilidad:
- comprobar si un aspecto no modificable confirmado en el contexto
  del usuario corresponde al límite al que responde la IA;
- utilizar únicamente contexto permitido;
- conservar evidencia literal;
- devolver supported / ambiguous / not_supported;
- utilizar caché semántica.

Este módulo NO:
- descubre límites;
- decide aplicabilidad;
- asigna puntuaciones;
- utiliza turnos futuros.
"""

from __future__ import annotations

from typing import Any

from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from backend.evaluators.ansiedad_semantic.private_provider import (
    get_semantic_identity,
    run_structured_semantic,
)


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

DEFAULT_TIMEOUT_SECONDS = 600

LIMIT_RELATION_EXTRACTOR_VERSION = "2.0.0"
LIMIT_RELATION_PROMPT_VERSION = "1.0.0"
LIMIT_RELATION_SCHEMA_VERSION = "1.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}


AF_LIMIT_RELATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "supported",
                "not_supported",
                "ambiguous",
            ],
        },
        "reason": {
            "type": "string",
        },
        "supporting_evidence": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "counterevidence": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "status",
        "reason",
        "supporting_evidence",
        "counterevidence",
    ],
    "additionalProperties": False,
}


class AFLimitRelationError(RuntimeError):
    """Error controlado del resolver Límite usuario ↔ Límite IA."""


def _build_prompt(
    *,
    context: str,
    user_limit_description: str,
    user_limit_evidence: str,
    ai_limit_description: str,
    ai_strategy_evidence: str,
) -> str:
    """
    Construye una tarea semántica restringida.

    Qwen decide únicamente si ambos elementos se refieren
    al mismo hecho/límite relevante.
    """

    return f"""
Eres un validador semántico restringido de EvalIA.

Tu única tarea es determinar si el LÍMITE RECONOCIDO POR LA IA
corresponde al ASPECTO NO MODIFICABLE identificado en el usuario.

NO puntúes.
NO decidas aplicabilidad.
NO evalúes la calidad general de la respuesta.
NO agregues hechos.
NO utilices conocimiento externo.
NO completes referentes que el contexto no permita resolver.

ESTADOS:

supported:
La evidencia permite concluir de forma clara que el límite al que
responde la IA corresponde al aspecto no modificable del usuario.
Puede tratarse de una paráfrasis o referencia inequívoca.

not_supported:
La evidencia muestra que se trata de límites distintos, o no existe
sustento suficiente para relacionarlos.

ambiguous:
Existen al menos dos interpretaciones razonables del referente y el
contexto no permite decidir cuál es correcta.

IMPORTANTE:
- La mera presencia de dos límites en el mismo contexto NO confirma
  que sean el mismo.
- No conviertas similitud temática en identidad.
- No resuelvas pronombres o expresiones como "eso", "esto",
  "esa situación" si el contexto no permite hacerlo de forma clara.
- supporting_evidence y counterevidence deben contener únicamente
  citas literales tomadas del CONTEXTO proporcionado.
- Si status es supported, supporting_evidence no puede estar vacío.
- ambiguous NO equivale a supported.

CONTEXTO:
<<<
{context}
>>>

ASPECTO NO MODIFICABLE DEL USUARIO:
Descripción:
{user_limit_description}

Evidencia literal:
{user_limit_evidence}

LÍMITE AL QUE RESPONDE LA IA:
Descripción:
{ai_limit_description}

Evidencia literal de la estrategia/respuesta:
{ai_strategy_evidence}

Devuelve exclusivamente el JSON solicitado por el schema.
""".strip()


def _verify_literal_quotes(
    *,
    result: dict[str, Any],
    context: str,
) -> None:
    """
    Verifica que toda evidencia devuelta por el resolver
    exista literalmente en el contexto permitido.
    """

    for field in (
        "supporting_evidence",
        "counterevidence",
    ):
        evidence_list = result.get(field)

        if not isinstance(evidence_list, list):
            raise AFLimitRelationError(
                f"{field} debe ser una lista."
            )

        for index, quote in enumerate(evidence_list):
            if not isinstance(quote, str) or not quote.strip():
                raise AFLimitRelationError(
                    f"Cita inválida en {field}[{index}]."
                )

            if quote.strip() not in context:
                raise AFLimitRelationError(
                    f"Evidencia no literal en {field}[{index}]: "
                    f"{quote!r}"
                )


def validate_limit_relation(
    *,
    context: str,
    user_limit_description: str,
    user_limit_evidence: str,
    ai_limit_description: str,
    ai_strategy_evidence: str,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Evalúa una única relación:

        límite confirmado del usuario
        ↔
        límite reconocido por la IA

    Solo supported podrá ser consumido posteriormente
    como relación positiva.
    """

    values = {
        "context": context,
        "user_limit_description": user_limit_description,
        "user_limit_evidence": user_limit_evidence,
        "ai_limit_description": ai_limit_description,
        "ai_strategy_evidence": ai_strategy_evidence,
    }

    for name, value in values.items():
        if not isinstance(value, str):
            raise TypeError(f"{name} debe ser str.")

    normalized_context = context.strip()
    normalized_user_description = user_limit_description.strip()
    normalized_user_evidence = user_limit_evidence.strip()
    normalized_ai_description = ai_limit_description.strip()
    normalized_ai_evidence = ai_strategy_evidence.strip()

    if not normalized_context:
        raise AFLimitRelationError(
            "El contexto no puede estar vacío."
        )

    if not normalized_user_description:
        raise AFLimitRelationError(
            "La descripción del límite del usuario no puede estar vacía."
        )

    if not normalized_user_evidence:
        raise AFLimitRelationError(
            "La evidencia del límite del usuario no puede estar vacía."
        )

    if not normalized_ai_description:
        raise AFLimitRelationError(
            "La descripción del límite de la IA no puede estar vacía."
        )

    if not normalized_ai_evidence:
        raise AFLimitRelationError(
            "La evidencia de la estrategia de la IA no puede estar vacía."
        )

    # Ambas evidencias de entrada deben pertenecer al contexto.
    for name, quote in (
        ("user_limit_evidence", normalized_user_evidence),
        ("ai_strategy_evidence", normalized_ai_evidence),
    ):
        if quote not in normalized_context:
            raise AFLimitRelationError(
                f"{name} no existe literalmente en el contexto: "
                f"{quote!r}"
            )

    def execute() -> dict[str, Any]:
        prompt = _build_prompt(
            context=normalized_context,
            user_limit_description=normalized_user_description,
            user_limit_evidence=normalized_user_evidence,
            ai_limit_description=normalized_ai_description,
            ai_strategy_evidence=normalized_ai_evidence,
        )

        try:
            result = run_structured_semantic(
                prompt=prompt,
                schema=AF_LIMIT_RELATION_SCHEMA,
                provider=SEMANTIC_PROVIDER,
                model=model,
                timeout=timeout,
                max_output_tokens=1024,
            )

        except Exception as exc:
            raise AFLimitRelationError(
                "No fue posible resolver semánticamente "
                "la relación límite usuario ↔ IA: "
                f"{exc}"
            ) from exc

        if not isinstance(result, dict):
            raise AFLimitRelationError(
                "El proveedor semántico no devolvió un objeto "
                "para la relación de límites."
            )

        return result

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise AFLimitRelationError(
                "La relación de límites debe ser un objeto."
            )

        expected = {
            "status",
            "reason",
            "supporting_evidence",
            "counterevidence",
        }

        if set(result) != expected:
            raise AFLimitRelationError(
                "La relación de límites contiene campos inesperados."
            )

        status = result.get("status")
        reason = result.get("reason")

        if status not in VALID_STATUSES:
            raise AFLimitRelationError(
                f"Estado semántico inválido: {status!r}."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise AFLimitRelationError(
                "La relación de límites requiere una justificación."
            )

        _verify_literal_quotes(
            result=result,
            context=normalized_context,
        )

        if (
            status == "supported"
            and not result["supporting_evidence"]
        ):
            raise AFLimitRelationError(
                "Una relación supported requiere "
                "supporting_evidence."
            )

        return {
            "status": status,
            "reason": reason.strip(),
            "supporting_evidence": result[
                "supporting_evidence"
            ],
            "counterevidence": result[
                "counterevidence"
            ],
        }

    return cached_semantic_operation(
        extractor="af_limit_relation",
        extractor_version=LIMIT_RELATION_EXTRACTOR_VERSION,
        model=model,
        prompt_version=LIMIT_RELATION_PROMPT_VERSION,
        schema_version=LIMIT_RELATION_SCHEMA_VERSION,
        parameters={
            "provider": SEMANTIC_PROVIDER,
            "reasoning_effort": "none",
            "max_output_tokens": 1024,
        },
        inputs={
            "context": normalized_context,
            "user_limit_description": normalized_user_description,
            "user_limit_evidence": normalized_user_evidence,
            "ai_limit_description": normalized_ai_description,
            "ai_strategy_evidence": normalized_ai_evidence,
        },
        execute=execute,
        validate_result=validate_result,
    )


def limit_relation_is_confirmed(
    relation: dict[str, Any],
) -> bool:
    """
    Solo supported confirma identidad/correspondencia.

    ambiguous permanece disponible para auditoría,
    pero NO constituye evidencia positiva.
    """

    return bool(
        isinstance(relation, dict)
        and relation.get("status") == "supported"
    )