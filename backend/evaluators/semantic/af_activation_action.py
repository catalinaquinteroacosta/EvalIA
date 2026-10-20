# -*- coding: utf-8 -*-
"""
EvalIA - Resolver semántico de relación Activación -> Acción/Interferencia.

Determina exclusivamente si una activación previamente identificada
está relacionada con una interferencia previamente identificada.

NO:
- descubre activaciones;
- descubre acciones;
- asigna puntuaciones;
- decide por sí solo la aplicabilidad final de AF7.
"""

from __future__ import annotations

from typing import Any
import re

from .af_literal_evidence import recover_literal_quote
from .af_activation_action_prompt import build_activation_action_prompt
from .af_activation_action_schema import (
    AF_ACTIVATION_ACTION_RELATION_SCHEMA,
)
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from .af_semantic_entailment import validate_semantic_entailment
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 1024

EXTRACTOR_VERSION = "2.3.0"
PROMPT_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}

_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]


class AFActivationActionError(RuntimeError):
    """Error controlado del resolver Activación -> Acción."""





def _verify_literal_quotes(
    *,
    result: dict[str, Any],
    context: str,
    provider: str,
    model: str,
    timeout: int,
) -> None:
    """
    Verifica que toda evidencia devuelta por el resolver exista
    literalmente en el contexto autorizado.
    """

    for field in (
        "supporting_evidence",
        "counterevidence",
    ):
        evidence_list = result.get(field)

        if not isinstance(evidence_list, list):
            raise AFActivationActionError(
                f"{field} no contiene una lista válida."
            )

        for index, quote in enumerate(evidence_list):
            if (
                not isinstance(quote, str)
                or not quote.strip()
            ):
                raise AFActivationActionError(
                    f"Cita inválida en {field}[{index}]."
                )

            if quote.strip() not in context:
                recovered = recover_literal_quote(
                    quote=quote,
                    context=context,
                    provider=provider,
                    model=model,
                    timeout=timeout,
                )

                if recovered is None:
                    raise AFActivationActionError(
                        "Evidencia inventada o no recuperable "
                        f"literalmente en {field}[{index}]: "
                        f"{quote!r}"
                    )

                # Sustituimos ?nicamente por texto que existe
                # literalmente en el contexto autorizado.
                evidence_list[index] = recovered


def _validate_result_structure(
    result: dict[str, Any],
    *,
    context: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Valida estrictamente la estructura y trazabilidad del resultado.
    """

    if not isinstance(result, dict):
        raise AFActivationActionError(
            "La relación no produjo un objeto JSON."
        )

    expected_keys = {
        "status",
        "reason",
        "supporting_evidence",
        "counterevidence",
    }

    if set(result.keys()) != expected_keys:
        raise AFActivationActionError(
            "La relación contiene campos faltantes "
            "o no permitidos."
        )

    status = result.get("status")
    reason = result.get("reason")

    if status not in VALID_STATUSES:
        raise AFActivationActionError(
            f"Estado semántico inválido: {status!r}"
        )

    if (
        not isinstance(reason, str)
        or not reason.strip()
    ):
        raise AFActivationActionError(
            "La relación no contiene una justificación válida."
        )

    _verify_literal_quotes(
        result=result,
        context=context,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    if (
        status == "supported"
        and not result["supporting_evidence"]
    ):
        raise AFActivationActionError(
            "Una relación 'supported' requiere "
            "supporting_evidence."
        )

    return {
        "status": status,
        "reason": reason.strip(),
        "supporting_evidence": list(
            result["supporting_evidence"]
        ),
        "counterevidence": list(
            result["counterevidence"]
        ),
    }


def _execute_relation(
    *,
    context: str,
    activation_description: str,
    activation_evidence: str,
    action_description: str,
    interference_description: str,
    interference_evidence: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Ejecuta exclusivamente la resolución semántica de la relación.

    No descubre nuevos hechos ni asigna puntuaciones.
    """

    prompt = build_activation_action_prompt(
        context=context,
        activation_description=activation_description,
        activation_evidence=activation_evidence,
        action_description=action_description,
        interference_description=interference_description,
        interference_evidence=interference_evidence,
    )

    try:
        result = run_structured_semantic(
            prompt=prompt,
            schema=AF_ACTIVATION_ACTION_RELATION_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFActivationActionError(
            "Error ejecutando el proveedor semántico "
            f"{provider!r} con el modelo {model!r} "
            "para relación Activación -> Acción: "
            f"{exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFActivationActionError(
            "La relación no produjo un objeto JSON."
        )

    return result


def validate_activation_action_relation(
    *,
    context: str,
    activation_description: str,
    activation_evidence: str,
    action_description: str,
    interference_description: str,
    interference_evidence: str,
    provider: str = SEMANTIC_PROVIDER,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Valida si una activación identificada está realmente relacionada
    con una interferencia sobre una acción identificada.

    La coexistencia de activación e interferencia NO basta por sí sola.
    """

    if not isinstance(context, str) or not context.strip():
        raise AFActivationActionError(
            "El contexto original no puede estar vacío."
        )

    for name, value in (
        ("activation_description", activation_description),
        ("action_description", action_description),
        (
            "interference_description",
            interference_description,
        ),
    ):
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise AFActivationActionError(
                f"{name} no puede estar vacío."
            )

    recovered_input_evidence: dict[str, str] = {}

    for name, quote in (
        (
            "activation_evidence",
            activation_evidence,
        ),
        (
            "interference_evidence",
            interference_evidence,
        ),
    ):
        if (
            not isinstance(quote, str)
            or not quote.strip()
        ):
            raise AFActivationActionError(
                f"{name} no contiene evidencia v?lida."
            )

        literal_quote = quote.strip()

        if literal_quote not in context:
            recovered = recover_literal_quote(
                quote=literal_quote,
                context=context,
                provider=provider,
                model=model,
                timeout=timeout,
            )

            if recovered is None:
                raise AFActivationActionError(
                    f"{name} no existe literalmente ni puede "
                    f"recuperarse con equivalencia sem?ntica "
                    f"estricta desde el contexto original: "
                    f"{quote!r}"
                )

            literal_quote = recovered

        if literal_quote not in context:
            raise AFActivationActionError(
                f"{name} produjo evidencia recuperada "
                f"no literal: {literal_quote!r}"
            )

        recovered_input_evidence[name] = literal_quote

    selected_provider = provider.strip().lower()
    selected_model = model.strip()

    if not selected_provider:
        raise AFActivationActionError(
            "provider no puede estar vacío."
        )

    if not selected_model:
        raise AFActivationActionError(
            "model no puede estar vacío."
        )

    inputs = {
        "context": context.strip(),
        "activation_description": (
            activation_description.strip()
        ),
        "activation_evidence": (
            recovered_input_evidence[
                "activation_evidence"
            ]
        ),
        "action_description": (
            action_description.strip()
        ),
        "interference_description": (
            interference_description.strip()
        ),
        "interference_evidence": (
            recovered_input_evidence[
                "interference_evidence"
            ]
        ),
    }

    def execute() -> dict[str, Any]:
        return _execute_relation(
            **inputs,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

    def validate(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return _validate_result_structure(
            result,
            context=inputs["context"],
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

    return cached_semantic_operation(
        extractor="af_activation_action_relation",
        extractor_version=EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "relation_contract": "activation_interference_v2",
        },
        inputs=inputs,
        execute=execute,
        validate_result=validate,
    )


def relation_is_confirmed(
    relation: dict[str, Any],
) -> bool:
    """
    Solo SUPPORTED confirma la relación.

    AMBIGUOUS se conserva para trazabilidad/adjudicación,
    pero no activa AF7 como evidencia positiva.
    """

    return (
        isinstance(relation, dict)
        and relation.get("status") == "supported"
    )