# -*- coding: utf-8 -*-
"""
EvalIA - Validador de sustentación semántica V2.

Comprueba si una evidencia textual, interpretada únicamente dentro
de un contexto local autorizado, sustenta una proposición candidata.

Este módulo:
- NO extrae indicadores;
- NO asigna puntuaciones EvalIA;
- NO decide aplicabilidad;
- NO usa conocimiento externo;
- conserva evidencia y contexto separados para trazabilidad.
"""

from __future__ import annotations

from typing import Any

from .af_semantic_entailment_prompt import (
    build_semantic_entailment_prompt,
)
from .af_semantic_entailment_schema import (
    AF_SEMANTIC_ENTAILMENT_SCHEMA,
)
from backend.evaluators.ansiedad_semantic.private_cache import (
    build_cache_key,
    semantic_cache,
)
from backend.evaluators.ansiedad_semantic.private_provider import (
    DEFAULT_PROVIDER,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    SemanticProviderError,
    run_structured_semantic,
)


DEFAULT_TIMEOUT_SECONDS = 600

# V2 cambia el contrato semántico:
# evidence + local_context -> proposition
#
# Las claves V1 no pueden reutilizarse para V2.
ENTAILMENT_EXTRACTOR_VERSION = "2.0.0"
ENTAILMENT_PROMPT_VERSION = "2.0.0"
ENTAILMENT_SCHEMA_VERSION = "1.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}


class AFSemanticEntailmentError(RuntimeError):
    """Error controlado del validador de sustentación semántica."""


def _resolve_model(
    *,
    provider: str,
    model: str | None,
) -> str:
    if isinstance(model, str) and model.strip():
        return model.strip()

    if provider == "openai":
        return DEFAULT_OPENAI_MODEL

    if provider == "ollama":
        return DEFAULT_OLLAMA_MODEL

    raise AFSemanticEntailmentError(
        f"Proveedor semántico no soportado: {provider!r}."
    )


def _validate_result(
    result: Any,
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise AFSemanticEntailmentError(
            "El validador semántico no produjo un objeto JSON."
        )

    status = result.get("status")
    reason = result.get("reason")

    if status not in VALID_STATUSES:
        raise AFSemanticEntailmentError(
            f"Estado semántico inválido: {status!r}."
        )

    if not isinstance(reason, str) or not reason.strip():
        raise AFSemanticEntailmentError(
            "El validador no proporcionó una justificación válida."
        )

    return {
        "status": status,
        "reason": reason.strip(),
    }


def validate_semantic_entailment(
    *,
    evidence: str,
    proposition: str,
    local_context: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Evalúa:

        evidence + local_context -> proposition

    `evidence` sigue siendo la evidencia literal trazable.

    `local_context` solo autoriza contexto para interpretar
    correctamente el significado local de esa evidencia.

    Compatibilidad transitoria:
    si local_context=None, se utiliza únicamente la propia evidencia.
    Esto permite migrar de forma controlada los call sites V1 sin
    ampliar silenciosamente el contexto disponible.

    El caché reutiliza únicamente resultados completamente validados
    bajo la misma configuración, proveedor, modelo y contexto.
    """

    if not isinstance(evidence, str) or not evidence.strip():
        raise AFSemanticEntailmentError(
            "La evidencia no puede estar vacía."
        )

    if not isinstance(proposition, str) or not proposition.strip():
        raise AFSemanticEntailmentError(
            "La proposición no puede estar vacía."
        )

    if local_context is not None and not isinstance(local_context, str):
        raise AFSemanticEntailmentError(
            "local_context debe ser str o None."
        )

    normalized_evidence = evidence.strip()
    normalized_proposition = proposition.strip()

    normalized_context = (
        local_context.strip()
        if isinstance(local_context, str) and local_context.strip()
        else normalized_evidence
    )

    selected_provider = (
        provider or DEFAULT_PROVIDER
    ).strip().lower()

    selected_model = _resolve_model(
        provider=selected_provider,
        model=model,
    )

    # El timeout no pertenece a la clave:
    # solo controla cuánto esperamos, no el significado.
    cache_key = build_cache_key(
        extractor="af_semantic_entailment",
        extractor_version=ENTAILMENT_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=ENTAILMENT_PROMPT_VERSION,
        schema_version=ENTAILMENT_SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
            "reasoning_effort": (
                "none"
                if selected_provider == "openai"
                else None
            ),
            "think": (
                False
                if selected_provider == "ollama"
                else None
            ),
            "temperature": (
                0
                if selected_provider == "ollama"
                else None
            ),
            "max_output_tokens": 1024,
        },
        inputs={
            "evidence": normalized_evidence,
            "local_context": normalized_context,
            "proposition": normalized_proposition,
        },
    )

    cached = semantic_cache.get(cache_key)

    if cached is not None:
        return _validate_result(cached)

    prompt = build_semantic_entailment_prompt(
        evidence=normalized_evidence,
        proposition=normalized_proposition,
        local_context=normalized_context,
    )

    try:
        result = run_structured_semantic(
            prompt=prompt,
            schema=AF_SEMANTIC_ENTAILMENT_SCHEMA,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
            max_output_tokens=1024,
        )

    except SemanticProviderError as exc:
        raise AFSemanticEntailmentError(
            "Error ejecutando la validación semántica: "
            f"{exc}"
        ) from exc

    validated_result = _validate_result(result)

    # Solo resultados estructuralmente válidos llegan al caché.
    semantic_cache.set(
        cache_key,
        validated_result,
    )

    return validated_result