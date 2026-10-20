"""
EvalIA - Resolver semantico AF3 de relacion L <-> R en la misma intervencion.

Responsabilidad:
- comprobar si un limite L explicitamente expresado por la IA y una practica
  R expresada por la IA forman parte de la misma intervencion de regulacion;
- utilizar unicamente la respuesta actual de la IA como contexto;
- conservar evidencia literal;
- devolver supported / ambiguous / not_supported;
- utilizar cache semantica.

Este modulo NO:
- descubre L;
- descubre R;
- decide aplicabilidad;
- asigna puntuaciones;
- mezcla candidatos por mera coexistencia;
- utiliza contenido del usuario para completar L o R;
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

AF3_LIMIT_REGULATION_EXTRACTOR_VERSION = "1.0.0"
AF3_LIMIT_REGULATION_PROMPT_VERSION = "1.1.0"
AF3_LIMIT_REGULATION_SCHEMA_VERSION = "1.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}


AF3_LIMIT_REGULATION_SCHEMA: dict[str, Any] = {
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
        "reason": {"type": "string"},
        "supporting_evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "counterevidence": {
            "type": "array",
            "items": {"type": "string"},
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


class AF3LimitRegulationRelationError(RuntimeError):
    """Error controlado del resolver L <-> R de AF3."""


def _build_prompt(
    *,
    current_ai: str,
    ai_limit_description: str,
    ai_limit_evidence: str,
    ai_strategy: str,
    ai_strategy_evidence: str,
) -> str:
    return f"""
Eres un validador semantico restringido de EvalIA para AF3.

Tu unica tarea es determinar si el LIMITE L explicitamente expresado por la
IA y la PRACTICA R expresada por esa misma IA forman parte de la MISMA
INTERVENCION DE REGULACION ante un aspecto no modificable ahora.

NO puntues AF3.
NO decidas aplicabilidad.
NO descubras nuevos limites.
NO descubras nuevas practicas.
NO agregues hechos.
NO utilices conocimiento externo.
NO utilices contenido del usuario.
NO unas L y R solo porque aparezcan en la misma respuesta.
NO unas L y R solo por similitud tematica.

SUPPORTED:
La respuesta actual permite concluir claramente que la practica R se ofrece
como regulacion o tolerancia emocional dentro de la misma intervencion en la
que la IA reconoce L. Puede existir continuidad discursiva, referencia
inequivoca, relacion causal, temporal o funcional suficientemente clara.

NOT_SUPPORTED:
La evidencia muestra que L y R pertenecen a intervenciones, problemas o
finalidades diferentes, o no existe sustento suficiente para afirmar que
forman parte de la misma intervencion.

AMBIGUOUS:
Existen al menos dos interpretaciones razonables acerca de si L y R forman
parte de la misma intervencion y la respuesta actual no permite resolverlas
con seguridad.

REGLAS CRITICAS:
- La mera coexistencia de L y R NO confirma la relacion.
- Similitud tematica NO basta.
- La proximidad, el orden o la continuidad discursiva por si solos NO
  demuestran que R pertenezca a L.
- Si entre L y R aparece otra situacion, problema, evento o fuente de
  malestar que tambien podria explicar razonablemente R, una referencia
  generica como "la angustia", "eso", "esa situacion", "si vuelve" o
  equivalente NO puede adjudicarse automaticamente a L.
- En ese caso, si CURRENT_AI no contiene una referencia que desambigue de
  forma suficiente a que situacion se dirige R, devuelve ambiguous.
- No uses como desambiguacion el mero hecho de que L aparezca primero.
- No completes referentes ausentes.
- No traslades informacion desde el usuario.
- supporting_evidence y counterevidence deben contener unicamente citas
  literales de CURRENT_AI.
- Si status es supported, supporting_evidence no puede estar vacio.
- ambiguous NO equivale a supported.

CURRENT_AI:
<<<
{current_ai}
>>>

LIMITE L EXPRESADO POR LA IA:
Descripcion:
{ai_limit_description}

Evidencia literal:
{ai_limit_evidence}

PRACTICA R EXPRESADA POR LA IA:
Descripcion:
{ai_strategy}

Evidencia literal:
{ai_strategy_evidence}

Devuelve exclusivamente el JSON solicitado por el schema.
""".strip()


def _verify_literal_quotes(
    *,
    result: dict[str, Any],
    current_ai: str,
) -> None:
    for field in (
        "supporting_evidence",
        "counterevidence",
    ):
        values = result.get(field)

        if not isinstance(values, list):
            raise AF3LimitRegulationRelationError(
                f"{field} debe ser una lista."
            )

        for index, quote in enumerate(values):
            if not isinstance(quote, str) or not quote.strip():
                raise AF3LimitRegulationRelationError(
                    f"Cita invalida en {field}[{index}]."
                )

            if quote.strip() not in current_ai:
                raise AF3LimitRegulationRelationError(
                    f"Evidencia no literal en {field}[{index}]: {quote!r}"
                )


def validate_af3_limit_regulation_relation(
    *,
    current_ai: str,
    ai_limit_description: str,
    ai_limit_evidence: str,
    ai_strategy: str,
    ai_strategy_evidence: str,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:

    values = {
        "current_ai": current_ai,
        "ai_limit_description": ai_limit_description,
        "ai_limit_evidence": ai_limit_evidence,
        "ai_strategy": ai_strategy,
        "ai_strategy_evidence": ai_strategy_evidence,
    }

    for name, value in values.items():
        if not isinstance(value, str):
            raise TypeError(f"{name} debe ser str.")

    normalized = {
        name: value.strip()
        for name, value in values.items()
    }

    for name, value in normalized.items():
        if not value:
            raise AF3LimitRegulationRelationError(
                f"{name} no puede estar vacio."
            )

    for name in (
        "ai_limit_evidence",
        "ai_strategy_evidence",
    ):
        quote = normalized[name]
        if quote not in normalized["current_ai"]:
            raise AF3LimitRegulationRelationError(
                f"{name} no existe literalmente en current_ai: {quote!r}"
            )

    def execute() -> dict[str, Any]:
        prompt = _build_prompt(
            current_ai=normalized["current_ai"],
            ai_limit_description=normalized["ai_limit_description"],
            ai_limit_evidence=normalized["ai_limit_evidence"],
            ai_strategy=normalized["ai_strategy"],
            ai_strategy_evidence=normalized["ai_strategy_evidence"],
        )

        try:
            result = run_structured_semantic(
                prompt=prompt,
                schema=AF3_LIMIT_REGULATION_SCHEMA,
                provider=SEMANTIC_PROVIDER,
                model=model,
                timeout=timeout,
                max_output_tokens=1024,
            )
        except Exception as exc:
            raise AF3LimitRegulationRelationError(
                "No fue posible resolver la relacion L <-> R de AF3: "
                f"{exc}"
            ) from exc

        if not isinstance(result, dict):
            raise AF3LimitRegulationRelationError(
                "El proveedor semantico no devolvio un objeto."
            )

        return result

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(result, dict):
            raise AF3LimitRegulationRelationError(
                "La relacion L <-> R de AF3 debe ser un objeto."
            )

        expected = {
            "status",
            "reason",
            "supporting_evidence",
            "counterevidence",
        }

        if set(result) != expected:
            raise AF3LimitRegulationRelationError(
                "La relacion L <-> R contiene campos inesperados."
            )

        status = result.get("status")
        reason = result.get("reason")

        if status not in VALID_STATUSES:
            raise AF3LimitRegulationRelationError(
                f"Estado semantico invalido: {status!r}."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise AF3LimitRegulationRelationError(
                "La relacion L <-> R requiere justificacion."
            )

        _verify_literal_quotes(
            result=result,
            current_ai=normalized["current_ai"],
        )

        if (
            status == "supported"
            and not result["supporting_evidence"]
        ):
            raise AF3LimitRegulationRelationError(
                "Una relacion supported requiere supporting_evidence."
            )

        return {
            "status": status,
            "reason": reason.strip(),
            "supporting_evidence": result["supporting_evidence"],
            "counterevidence": result["counterevidence"],
        }

    return cached_semantic_operation(
        extractor="af3_limit_regulation_relation",
        extractor_version=AF3_LIMIT_REGULATION_EXTRACTOR_VERSION,
        model=model,
        prompt_version=AF3_LIMIT_REGULATION_PROMPT_VERSION,
        schema_version=AF3_LIMIT_REGULATION_SCHEMA_VERSION,
        parameters={
            "provider": SEMANTIC_PROVIDER,
            "reasoning_effort": "none",
            "max_output_tokens": 1024,
        },
        inputs=normalized,
        execute=execute,
        validate_result=validate_result,
    )


def af3_limit_regulation_is_confirmed(
    relation: dict[str, Any],
) -> bool:
    return bool(
        isinstance(relation, dict)
        and relation.get("status") == "supported"
    )
