# -*- coding: utf-8 -*-
"""
EvalIA — Extractor semántico general de Afrontamiento (AF1–AF8).

Responsabilidad:
- Extraer el contexto semántico del usuario/historial permitido.
- Extraer conductas semánticas de la respuesta actual de la IA.
- Utilizar el proveedor semántico común con salida JSON estructurada.
- Mantener separada la extracción semántica de las reglas de puntuación.

Este módulo NO:
- asigna puntuaciones 0, 1, 2 o 3;
- decide N/A;
- sustituye las reglas deterministas de la rúbrica.

Arquitectura:
texto -> extracción semántica -> verificación de evidencia
      -> reglas deterministas -> puntuación
"""

from __future__ import annotations

from typing import Any

from .af_ai_schema import AF_AI_SCHEMA
from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_prompts import (
    build_ai_extraction_prompt,
    build_user_extraction_prompt,
)
from .af_user_schema import AF_USER_SCHEMA
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


DEFAULT_TIMEOUT_SECONDS = 600
GENERAL_MAX_OUTPUT_TOKENS = 8192


# ------------------------------------------------------------
# Identidad semántica efectiva
# ------------------------------------------------------------

_SEMANTIC_IDENTITY = get_semantic_identity()

SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]


# Alias TRANSITORIO de compatibilidad.
#
# Algunos módulos AF4/AF5 todavía importan OLLAMA_MODEL desde este
# módulo para comprobar que su identidad de caché coincide con la
# identidad del extractor general.
#
# Durante la migración conservamos el nombre para no romper esos
# imports, pero su valor es ahora el MODELO SEMÁNTICO EFECTIVO.
#
# Este alias deberá eliminarse cuando todos los consumidores hayan
# sido migrados a SEMANTIC_MODEL / get_semantic_identity().
OLLAMA_MODEL = SEMANTIC_MODEL


class AFSemanticExtractorError(RuntimeError):
    """Error controlado del extractor semántico de AF."""


def _call_semantic_provider(
    *,
    prompt: str,
    schema: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Ejecuta una extracción estructurada mediante el proveedor
    semántico configurado.

    El modelo interpreta lenguaje natural, pero NO asigna
    puntuaciones EvalIA.
    """

    try:
        result = run_structured_semantic(
            prompt=prompt,
            schema=schema,
            provider=SEMANTIC_PROVIDER,
            model=SEMANTIC_MODEL,
            timeout=timeout,
            max_output_tokens=GENERAL_MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFSemanticExtractorError(
            "No fue posible ejecutar el proveedor semántico "
            f"{SEMANTIC_PROVIDER!r} con el modelo "
            f"{SEMANTIC_MODEL!r}: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFSemanticExtractorError(
            "La extracción semántica debe ser un objeto JSON."
        )

    return result


def extract_user_context(
    *,
    current_user: str,
    prior_user: str = "",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extrae hechos y relaciones del usuario necesarios para
    determinar posteriormente la aplicabilidad de AF1–AF8.

    No evalúa la respuesta de la IA.
    No asigna puntuaciones.
    """

    prompt = build_user_extraction_prompt(
        current_user=current_user,
        prior_user=prior_user,
    )

    return _call_semantic_provider(
        prompt=prompt,
        schema=AF_USER_SCHEMA,
        timeout=timeout,
    )


def extract_ai_response(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extrae conductas y relaciones presentes en la respuesta
    actual de la IA.

    El contexto previo sirve para resolver referentes.
    La conducta evaluada debe encontrarse en current_ai.
    """

    prompt = build_ai_extraction_prompt(
        current_user=current_user,
        current_ai=current_ai,
        prior_user=prior_user,
        prior_ai=prior_ai,
    )

    return _call_semantic_provider(
        prompt=prompt,
        schema=AF_AI_SCHEMA,
        timeout=timeout,
    )


def verify_evidence_object(
    *,
    evidence_object: dict[str, Any],
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
) -> dict[str, Any]:
    """
    Verifica un objeto individual de evidencia producido
    por el extractor.

    Devuelve un resultado serializable para auditoría.
    """

    quote = evidence_object.get("quote", "")
    source_value = evidence_object.get("source", "")

    try:
        source = EvidenceSource(source_value)

    except ValueError:
        return {
            "valid": False,
            "evidence": quote,
            "source": source_value,
            "reason": "invalid_source",
        }

    check = verify_exact_evidence(
        evidence=quote,
        source=source,
        current_user=current_user,
        current_ai=current_ai,
        prior_user=prior_user,
        prior_ai=prior_ai,
    )

    return {
        "valid": check.valid,
        "evidence": check.evidence,
        "source": check.source.value,
        "reason": check.reason,
    }


def extract_ai_response_af7(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extracci?n focalizada para AF7.
    Reutiliza el esquema y las instrucciones oficiales del
    extractor general sin solicitar campos de otros indicadores.
    """
    from copy import deepcopy

    fields = (
        "af7_regulation_for_action",
        "af7_problematic_claims",
    )

    schema = {
        "type": "object",
        "properties": {
            name: deepcopy(AF_AI_SCHEMA["properties"][name])
            for name in fields
        },
        "required": list(fields),
        "additionalProperties": False,
    }

    prompt = build_ai_extraction_prompt(
        current_user=current_user,
        current_ai=current_ai,
        prior_user=prior_user,
        prior_ai=prior_ai,
    )

    prompt += (
        "\n\nALCANCE DE ESTA EXTRACCION: "
        "extrae exclusivamente los dos campos AF7 solicitados "
        "por el esquema. No extraigas indicadores de otras familias."
    )

    return _call_semantic_provider(
        prompt=prompt,
        schema=schema,
        timeout=timeout,
    )
