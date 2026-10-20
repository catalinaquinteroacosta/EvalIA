"""
EvalIA - Operación semántica cacheada reutilizable.

Responsabilidad:
- Estandarizar el ciclo:
      construir clave -> buscar -> ejecutar -> validar -> guardar.
- Reutilizar el caché semántico persistente de EvalIA.
- Evitar duplicar la infraestructura de caché entre extractores.

Este módulo NO:
- interpreta lenguaje;
- llama directamente a Ollama;
- asigna puntuaciones;
- decide aplicabilidad;
- valida semántica por sí mismo.

El resultado de una operación nueva solo se almacena después de que
la función validate_result lo haya aceptado.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from .semantic_cache import build_cache_key, semantic_cache


T = TypeVar("T")


def cached_semantic_operation(
    *,
    extractor: str,
    extractor_version: str,
    model: str,
    prompt_version: str,
    schema_version: str,
    parameters: dict[str, Any] | None,
    inputs: dict[str, Any],
    execute: Callable[[], T],
    validate_result: Callable[[T], T],
) -> T:
    """
    Ejecuta una operación semántica con caché persistente.

    Flujo:
    1. Construye una clave reproducible.
    2. Si existe HIT, devuelve el resultado almacenado.
    3. Si existe MISS, ejecuta la operación.
    4. Valida completamente el resultado.
    5. Solo después de validar, almacena el resultado.
    6. Devuelve el resultado validado.

    Importante:
    - execute() debe realizar la operación costosa, por ejemplo Qwen.
    - validate_result() debe lanzar una excepción si el resultado
      no es válido.
    - Los errores de execute() o validate_result() nunca se cachean.
    """

    cache_key = build_cache_key(
        extractor=extractor,
        extractor_version=extractor_version,
        model=model,
        prompt_version=prompt_version,
        schema_version=schema_version,
        parameters=parameters,
        inputs=inputs,
    )

    cached = semantic_cache.get(cache_key)

    if cached is not None:
        return cached

    raw_result = execute()

    validated_result = validate_result(raw_result)

    semantic_cache.set(
        cache_key,
        validated_result,
    )

    return validated_result