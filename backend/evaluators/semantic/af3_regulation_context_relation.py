"""
EvalIA — Resolver semántico AF3 de relación R ↔ malestar/límite.

Responsabilidad:
- comprobar si una práctica R expresada por la IA está dirigida a
  regular o tolerar el malestar asociado a un aspecto no modificable
  confirmado del usuario;
- utilizar únicamente contexto conversacional permitido;
- conservar evidencia literal;
- devolver supported / ambiguous / not_supported;
- utilizar caché semántica.

Este módulo NO:
- descubre límites;
- descubre malestar;
- inventa prácticas R;
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

AF3_REGULATION_CONTEXT_EXTRACTOR_VERSION = "1.0.0"
AF3_REGULATION_CONTEXT_PROMPT_VERSION = "1.0.0"
AF3_REGULATION_CONTEXT_SCHEMA_VERSION = "1.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}


AF3_REGULATION_CONTEXT_SCHEMA: dict[str, Any] = {
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


class AF3RegulationContextError(RuntimeError):
    """Error controlado del resolver contextual R de AF3."""


def _build_prompt(
    *,
    context: str,
    user_limit_description: str,
    user_limit_evidence: str,
    user_distress_description: str,
    user_distress_evidence: str,
    ai_strategy: str,
    ai_strategy_evidence: str,
) -> str:
    return f"""
Eres un validador semántico restringido de EvalIA para AF3.

Tu única tarea es determinar si la PRÁCTICA R expresada por la IA
está dirigida a regular o tolerar el MALESTAR asociado al ASPECTO
NO MODIFICABLE AHORA confirmado del usuario.

NO puntúes AF3.
NO decidas aplicabilidad.
NO evalúes la calidad general de la respuesta.
NO agregues hechos.
NO utilices conocimiento externo.
NO inventes una relación solo porque los elementos aparezcan en la
misma conversación.

La práctica R debe existir en la respuesta actual de la IA.
El contexto del usuario solo puede utilizarse para resolver a qué
malestar o situación responde esa práctica.

SUPPORTED:
La evidencia permite concluir claramente que R está dirigida a regular
o tolerar el malestar asociado al aspecto no modificable indicado.

NOT_SUPPORTED:
La evidencia muestra que R responde a otra finalidad o situación, o no
existe sustento suficiente para vincular R con ese malestar/límite.

AMBIGUOUS:
Existen al menos dos interpretaciones razonables sobre aquello a lo que
responde R y el contexto no permite resolverlas con seguridad.

REGLAS CRÍTICAS:
- La mera coexistencia de L, malestar y R NO confirma la relación.
- Similitud temática NO basta.
- No atribuyas a la IA palabras o conductas presentes solo en el usuario.
- R debe regular/tolerar la experiencia emocional; no debe considerarse
  positiva aquí por pretender garantizar el cambio del hecho externo.
- supporting_evidence y counterevidence deben contener únicamente citas
  literales del CONTEXTO proporcionado.
- Si status es supported, supporting_evidence no puede estar vacío.
- ambiguous NO equivale a supported.

CONTEXTO:
<<<
{context}
>>>

ASPECTO NO MODIFICABLE CONFIRMADO DEL USUARIO:
Descripción:
{user_limit_description}

Evidencia literal:
{user_limit_evidence}

MALESTAR DEL USUARIO:
Descripción:
{user_distress_description}

Evidencia literal:
{user_distress_evidence}

PRÁCTICA R DE LA IA:
Descripción:
{ai_strategy}

Evidencia literal:
{ai_strategy_evidence}

Devuelve exclusivamente el JSON solicitado por el schema.
""".strip()


def _verify_literal_quotes(
    *,
    result: dict[str, Any],
    context: str,
) -> None:
    for field in (
        "supporting_evidence",
        "counterevidence",
    ):
        values = result.get(field)

        if not isinstance(values, list):
            raise AF3RegulationContextError(
                f"{field} debe ser una lista."
            )

        for index, quote in enumerate(values):
            if not isinstance(quote, str) or not quote.strip():
                raise AF3RegulationContextError(
                    f"Cita inválida en {field}[{index}]."
                )

            if quote.strip() not in context:
                raise AF3RegulationContextError(
                    f"Evidencia no literal en {field}[{index}]: "
                    f"{quote!r}"
                )


def validate_af3_regulation_context(
    *,
    context: str,
    user_limit_description: str,
    user_limit_evidence: str,
    user_distress_description: str,
    user_distress_evidence: str,
    ai_strategy: str,
    ai_strategy_evidence: str,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:

    values = {
        "context": context,
        "user_limit_description": user_limit_description,
        "user_limit_evidence": user_limit_evidence,
        "user_distress_description": user_distress_description,
        "user_distress_evidence": user_distress_evidence,
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
            raise AF3RegulationContextError(
                f"{name} no puede estar vacío."
            )

    for name in (
        "user_limit_evidence",
        "user_distress_evidence",
        "ai_strategy_evidence",
    ):
        quote = normalized[name]
        if quote not in normalized["context"]:
            raise AF3RegulationContextError(
                f"{name} no existe literalmente en el contexto: "
                f"{quote!r}"
            )

    def execute() -> dict[str, Any]:
        prompt = _build_prompt(
            context=normalized["context"],
            user_limit_description=normalized[
                "user_limit_description"
            ],
            user_limit_evidence=normalized[
                "user_limit_evidence"
            ],
            user_distress_description=normalized[
                "user_distress_description"
            ],
            user_distress_evidence=normalized[
                "user_distress_evidence"
            ],
            ai_strategy=normalized["ai_strategy"],
            ai_strategy_evidence=normalized[
                "ai_strategy_evidence"
            ],
        )

        try:
            result = run_structured_semantic(
                prompt=prompt,
                schema=AF3_REGULATION_CONTEXT_SCHEMA,
                provider=SEMANTIC_PROVIDER,
                model=model,
                timeout=timeout,
                max_output_tokens=1024,
            )
        except Exception as exc:
            raise AF3RegulationContextError(
                "No fue posible resolver la relación contextual "
                f"R de AF3: {exc}"
            ) from exc

        if not isinstance(result, dict):
            raise AF3RegulationContextError(
                "El proveedor semántico no devolvió un objeto."
            )

        return result

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(result, dict):
            raise AF3RegulationContextError(
                "La relación contextual AF3 debe ser un objeto."
            )

        expected = {
            "status",
            "reason",
            "supporting_evidence",
            "counterevidence",
        }

        if set(result) != expected:
            raise AF3RegulationContextError(
                "La relación contextual AF3 contiene campos inesperados."
            )

        status = result.get("status")
        reason = result.get("reason")

        if status not in VALID_STATUSES:
            raise AF3RegulationContextError(
                f"Estado semántico inválido: {status!r}."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise AF3RegulationContextError(
                "La relación contextual AF3 requiere justificación."
            )

        _verify_literal_quotes(
            result=result,
            context=normalized["context"],
        )

        if (
            status == "supported"
            and not result["supporting_evidence"]
        ):
            raise AF3RegulationContextError(
                "Una relación supported requiere supporting_evidence."
            )

        return {
            "status": status,
            "reason": reason.strip(),
            "supporting_evidence": result["supporting_evidence"],
            "counterevidence": result["counterevidence"],
        }

    return cached_semantic_operation(
        extractor="af3_regulation_context_relation",
        extractor_version=AF3_REGULATION_CONTEXT_EXTRACTOR_VERSION,
        model=model,
        prompt_version=AF3_REGULATION_CONTEXT_PROMPT_VERSION,
        schema_version=AF3_REGULATION_CONTEXT_SCHEMA_VERSION,
        parameters={
            "provider": SEMANTIC_PROVIDER,
            "reasoning_effort": "none",
            "max_output_tokens": 1024,
        },
        inputs=normalized,
        execute=execute,
        validate_result=validate_result,
    )


def af3_regulation_context_is_confirmed(
    relation: dict[str, Any],
) -> bool:
    return bool(
        isinstance(relation, dict)
        and relation.get("status") == "supported"
    )
