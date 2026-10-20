# -*- coding: utf-8 -*-
"""
EvalIA - Proveedor semántico común.

Centraliza la ejecución de modelos semánticos.

Responsabilidades:
- ejecutar prompts;
- solicitar salida JSON estructurada;
- permitir OpenAI API u Ollama;
- devolver un dict Python validado a nivel estructural básico.

NO:
- asigna puntuaciones EvalIA;
- decide aplicabilidad;
- interpreta rúbricas;
- modifica evidencia;
- implementa reglas AF.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests


DEFAULT_PROVIDER = os.getenv(
    "EVALIA_SEMANTIC_PROVIDER",
    "openai",
).strip().lower()

DEFAULT_OPENAI_MODEL = os.getenv(
    "EVALIA_OPENAI_MODEL",
    "gpt-5.6-luna",
)

DEFAULT_OLLAMA_MODEL = os.getenv(
    "EVALIA_OLLAMA_MODEL",
    "qwen3.5:9b",
)

OLLAMA_URL = os.getenv(
    "EVALIA_OLLAMA_URL",
    "http://localhost:11434/api/chat",
)

DEFAULT_TIMEOUT_SECONDS = 600


class SemanticProviderError(RuntimeError):
    """Error controlado del proveedor semántico."""


def _validate_common_inputs(
    *,
    prompt: str,
    schema: dict[str, Any],
    provider: str,
) -> None:
    if not isinstance(prompt, str) or not prompt.strip():
        raise SemanticProviderError(
            "El prompt no puede estar vacío."
        )

    if not isinstance(schema, dict) or not schema:
        raise SemanticProviderError(
            "El schema debe ser un diccionario no vacío."
        )

    if provider not in {"openai", "ollama"}:
        raise SemanticProviderError(
            f"Proveedor semántico no soportado: {provider!r}."
        )


def _run_openai(
    *,
    prompt: str,
    schema: dict[str, Any],
    model: str,
    max_output_tokens: int,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SemanticProviderError(
            "El paquete 'openai' no está instalado."
        ) from exc

    client = OpenAI()

    max_attempts = 2
    response = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.responses.create(
                model=model,
                reasoning={
                    "effort": "none",
                },
                input=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "evalia_semantic_result",
                        "strict": True,
                        "schema": schema,
                    }
                },
                max_output_tokens=max_output_tokens,
            )

        except Exception as exc:
            raise SemanticProviderError(
                f"Error consultando OpenAI API: {exc}"
            ) from exc

        response_status = getattr(
            response,
            "status",
            None,
        )

        if response_status == "completed":
            break

        incomplete_details = getattr(
            response,
            "incomplete_details",
            None,
        )

        incomplete_reason = getattr(
            incomplete_details,
            "reason",
            None,
        )

        retryable_max_output = (
            response_status == "incomplete"
            and incomplete_reason == "max_output_tokens"
        )

        if (
            retryable_max_output
            and attempt < max_attempts
        ):
            continue

        raise SemanticProviderError(
            "OpenAI no completó la respuesta estructurada. "
            f"status={response_status!r}; "
            f"incomplete_details={incomplete_details!r}; "
            f"attempt={attempt}/{max_attempts}."
        )

    if response is None:
        raise SemanticProviderError(
            "OpenAI no produjo ninguna respuesta."
        )

    raw = response.output_text

    if not isinstance(raw, str) or not raw.strip():
        raise SemanticProviderError(
            "OpenAI completó la solicitud pero no devolvió "
            "contenido estructurado utilizable."
        )

    try:
        result = json.loads(raw)

    except json.JSONDecodeError as exc:
        raise SemanticProviderError(
            "OpenAI reportó status='completed', pero la salida "
            "estructurada no pudo interpretarse como JSON válido. "
            f"json_error_pos={exc.pos}; "
            f"output_chars={len(raw)}."
        ) from exc

    if not isinstance(result, dict):
        raise SemanticProviderError(
            "OpenAI no produjo un objeto JSON."
        )

    return result


def _run_ollama(
    *,
    prompt: str,
    schema: dict[str, Any],
    model: str,
    timeout: int,
    max_output_tokens: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {
            "temperature": 0,
            "num_predict": max_output_tokens,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise SemanticProviderError(
            f"Error consultando Ollama: {exc}"
        ) from exc

    try:
        data = response.json()
        raw = data["message"]["content"]

    except (ValueError, KeyError, TypeError) as exc:
        raise SemanticProviderError(
            "Ollama devolvió una respuesta inesperada."
        ) from exc

    if not isinstance(raw, str) or not raw.strip():
        raise SemanticProviderError(
            "Ollama no devolvió contenido utilizable."
        )

    try:
        result = json.loads(raw)

    except json.JSONDecodeError as exc:
        raise SemanticProviderError(
            "Ollama devolvió contenido que no pudo "
            "interpretarse como JSON."
        ) from exc

    if not isinstance(result, dict):
        raise SemanticProviderError(
            "Ollama no produjo un objeto JSON."
        )

    return result


def run_structured_semantic(
    *,
    prompt: str,
    schema: dict[str, Any],
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_tokens: int = 4096,
) -> dict[str, Any]:
    """
    Ejecuta una operación semántica estructurada.

    La selección del proveedor es explícita o se obtiene de:
        EVALIA_SEMANTIC_PROVIDER

    Por defecto:
        openai -> gpt-5.6-luna
        ollama -> qwen3.5:9b
    """

    selected_provider = (
        provider or DEFAULT_PROVIDER
    ).strip().lower()

    _validate_common_inputs(
        prompt=prompt,
        schema=schema,
        provider=selected_provider,
    )

    if (
        not isinstance(max_output_tokens, int)
        or max_output_tokens <= 0
    ):
        raise SemanticProviderError(
            "max_output_tokens debe ser un entero positivo."
        )

    if selected_provider == "openai":
        selected_model = (
            model or DEFAULT_OPENAI_MODEL
        )

        return _run_openai(
            prompt=prompt.strip(),
            schema=schema,
            model=selected_model,
            max_output_tokens=max_output_tokens,
        )

    selected_model = (
        model or DEFAULT_OLLAMA_MODEL
    )

    return _run_ollama(
        prompt=prompt.strip(),
        schema=schema,
        model=selected_model,
        timeout=timeout,
        max_output_tokens=max_output_tokens,
    )

def get_semantic_identity(
    *,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, str]:
    """
    Devuelve la identidad efectiva del proveedor semántico.

    Esta identidad debe utilizarse para trazabilidad y para construir
    claves de caché que correspondan al modelo que realmente ejecuta
    la inferencia.
    """

    selected_provider = (
        provider or DEFAULT_PROVIDER
    ).strip().lower()

    if selected_provider == "openai":
        selected_model = (
            model or DEFAULT_OPENAI_MODEL
        )

    elif selected_provider == "ollama":
        selected_model = (
            model or DEFAULT_OLLAMA_MODEL
        )

    else:
        raise SemanticProviderError(
            f"Proveedor semántico no soportado: "
            f"{selected_provider!r}."
        )

    if not isinstance(selected_model, str) or not selected_model.strip():
        raise SemanticProviderError(
            "El modelo semántico no puede estar vacío."
        )

    return {
        "provider": selected_provider,
        "model": selected_model.strip(),
    }