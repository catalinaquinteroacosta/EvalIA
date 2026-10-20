"""
EvalIA - Integrador semántico de AF1.

AF1:
¿Distingue entre aspectos modificables y no modificables para orientar
la estrategia?

Este módulo NO realiza extracción semántica directamente.

Integra los tres extractores atómicos ya validados:

- AF1-M: aspectos modificables y su orientación;
- AF1-L: aspectos no modificables/no asegurables y su orientación;
- AF1-G: garantías indebidas de control.

Este módulo:
- NO llama directamente a Ollama;
- NO asigna puntuaciones AF1;
- NO decide aplicabilidad;
- NO convierte ambigüedad en evidencia confirmada;
- NO inventa relaciones entre componentes.

La puntuación determinista 0-3 se implementa en una capa posterior.
"""

from __future__ import annotations

from typing import Any

from backend.evaluators.ansiedad_semantic.private_provider import get_semantic_identity

from .af_ai_af1_modifiable import (
    extract_ai_af1_modifiable,
    aspect_is_confirmed as modifiable_aspect_is_confirmed,
    orientation_is_confirmed as modifiable_orientation_is_confirmed,
)

from .af_ai_af1_unmodifiable import (
    extract_ai_af1_unmodifiable,
    aspect_is_confirmed as unmodifiable_aspect_is_confirmed,
    orientation_is_confirmed as unmodifiable_orientation_is_confirmed,
)

from .af_ai_af1_guarantee import (
    extract_ai_af1_guarantee,
    guarantee_is_confirmed as atomic_guarantee_is_confirmed,
)


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

DEFAULT_TIMEOUT_SECONDS = 600

AF1_INTEGRATOR_VERSION = "2.0.0"


class AFAF1IntegrationError(RuntimeError):
    """Error controlado de integración semántica de AF1."""


def extract_ai_af1(
    *,
    current_ai: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:
    """
    Ejecuta los tres extractores atómicos de AF1 y unifica sus salidas.

    No modifica las decisiones semánticas producidas por cada extractor.
    No elimina elementos ambiguos: se conservan para trazabilidad.
    La confirmación se decide posteriormente mediante los helpers
    `*_is_confirmed`.
    """

    if not isinstance(current_ai, str):
        raise AFAF1IntegrationError(
            "current_ai debe ser una cadena de texto."
        )

    if not current_ai.strip():
        return {
            "modifiable": [],
            "unmodifiable": [],
            "control_guarantees": [],
        }

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    selected_provider = identity["provider"]
    selected_model = identity["model"]

    try:
        modifiable_result = extract_ai_af1_modifiable(
            current_ai=current_ai,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        unmodifiable_result = extract_ai_af1_unmodifiable(
            current_ai=current_ai,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        guarantee_result = extract_ai_af1_guarantee(
            current_ai=current_ai,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

    except Exception as exc:
        raise AFAF1IntegrationError(
            f"Error integrando los extractores atómicos de AF1: {exc}"
        ) from exc

    modifiable = modifiable_result.get("modifiable")
    unmodifiable = unmodifiable_result.get("unmodifiable")
    guarantees = guarantee_result.get("control_guarantees")

    if not isinstance(modifiable, list):
        raise AFAF1IntegrationError(
            "AF1-M no devolvió una lista 'modifiable' válida."
        )

    if not isinstance(unmodifiable, list):
        raise AFAF1IntegrationError(
            "AF1-L no devolvió una lista 'unmodifiable' válida."
        )

    if not isinstance(guarantees, list):
        raise AFAF1IntegrationError(
            "AF1-G no devolvió una lista 'control_guarantees' válida."
        )

    return {
        "modifiable": modifiable,
        "unmodifiable": unmodifiable,
        "control_guarantees": guarantees,
    }


def aspect_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Compatibilidad con la interfaz histórica de AF1.

    Determina si un aspecto M o L está confirmado exclusivamente
    cuando su validación semántica es SUPPORTED.

    No convierte AMBIGUOUS en evidencia confirmada.
    """

    return (
        item
        .get("semantic_validation", {})
        .get("aspect", {})
        .get("status")
        == "supported"
    )


def orientation_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Compatibilidad con la interfaz histórica de AF1.

    Una orientación solo está confirmada cuando su propia validación
    semántica es SUPPORTED.

    La confirmación del aspecto y de la orientación permanecen
    conceptualmente separadas.
    """

    validation = (
        item.get("semantic_validation") or {}
    )

    orientation_validation = (
        validation.get("orientation") or {}
    )

    return (
        orientation_validation.get("status")
        == "supported"
    )


def guarantee_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Compatibilidad con la interfaz histórica de AF1.

    Una garantía solo se considera confirmada cuando el extractor
    atómico AF1-G la validó como SUPPORTED.
    """

    return atomic_guarantee_is_confirmed(item)


def confirmed_modifiable_aspects(
    result: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Devuelve únicamente aspectos modificables confirmados.

    Se conserva el objeto completo para mantener evidencia,
    orientación, validaciones e identificadores.
    """

    return [
        item
        for item in result.get("modifiable", [])
        if modifiable_aspect_is_confirmed(item)
    ]


def confirmed_unmodifiable_aspects(
    result: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Devuelve únicamente aspectos no modificables confirmados.
    """

    return [
        item
        for item in result.get("unmodifiable", [])
        if unmodifiable_aspect_is_confirmed(item)
    ]


def confirmed_control_guarantees(
    result: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Devuelve únicamente garantías indebidas confirmadas.
    """

    return [
        item
        for item in result.get("control_guarantees", [])
        if atomic_guarantee_is_confirmed(item)
    ]


def confirmed_modifiable_orientations(
    result: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Devuelve aspectos M confirmados que además poseen
    orientación M confirmada.

    Exigir también que el aspecto esté confirmado evita utilizar
    una orientación aislada cuyo referente M no quedó sustentado.
    """

    return [
        item
        for item in result.get("modifiable", [])
        if (
            modifiable_aspect_is_confirmed(item)
            and modifiable_orientation_is_confirmed(item)
        )
    ]


def confirmed_unmodifiable_orientations(
    result: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Devuelve aspectos L confirmados que además poseen
    orientación L confirmada.

    No interpreta el mero reconocimiento del límite como orientación.
    """

    return [
        item
        for item in result.get("unmodifiable", [])
        if (
            unmodifiable_aspect_is_confirmed(item)
            and unmodifiable_orientation_is_confirmed(item)
        )
    ]