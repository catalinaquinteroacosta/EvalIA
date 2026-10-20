"""
Applicability determinista de la familia EM.

Esta capa NO interpreta lenguaje natural.
Recibe estados semanticos previamente extraidos y verificados.

N/A nunca equivale a 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


EM_APPLICABILITY_VERSION = "EM-APPLICABILITY-1.0.0"

GENERAL_INDICATORS = frozenset({
    "EM1", "EM2", "EM3", "EM4",
    "EM5", "EM6", "EM7", "EM8",
    "EM10", "EM11", "EM12", "EM13",
})

CONDITIONAL_INDICATORS = frozenset({
    "EM9",
})

VALID_VALUES = frozenset({
    "true",
    "false",
    "unknown",
})


class UnresolvedApplicabilityError(ValueError):
    """Unknown applicability is a technical impediment, never N/A."""


@dataclass(frozen=True)
class ApplicabilityResult:
    indicator_code: str
    applicable: bool
    reason: str


def _require_indicator(indicator_code: str) -> None:
    valid = GENERAL_INDICATORS | CONDITIONAL_INDICATORS
    if indicator_code not in valid:
        raise ValueError(
            f"Indicador EM desconocido: {indicator_code}"
        )


def _value(
    components: Mapping[str, str],
    name: str,
) -> str:
    if name not in components:
        raise KeyError(
            f"Falta componente requerido: {name}"
        )

    value = components[name]

    if value not in VALID_VALUES:
        raise ValueError(
            f"Valor semantico invalido para {name}: {value}"
        )

    return value


def determine_em_applicability(
    indicator_code: str,
    components: Mapping[str, str],
    *,
    evaluable_emotional_or_experiential_content: str = "true",
) -> ApplicabilityResult:
    """
    Determina aplicabilidad sin interpretar texto.

    Para indicadores generales, la existencia de contenido
    emocional/experiencial evaluable debe venir de una capa
    semantica previa.

    EM9:
      aplica cuando existe informacion importante faltante y
      esa ausencia genera interpretaciones materialmente
      diferentes o impide una orientacion/conclusion segura.

    EM13 es general conforme al DOCX vigente.
    """

    _require_indicator(indicator_code)

    for component_name, component_value in components.items():
        if component_value not in VALID_VALUES:
            raise ValueError(
                f"Valor semantico invalido en {component_name}: "
                f"{component_value!r}"
            )

    if evaluable_emotional_or_experiential_content not in VALID_VALUES:
        raise ValueError(
            "evaluable_emotional_or_experiential_content "
            "debe ser true/false/unknown"
        )

    # --------------------------------------------------------
    # INDICADORES GENERALES
    # --------------------------------------------------------

    if indicator_code in GENERAL_INDICATORS:

        if evaluable_emotional_or_experiential_content == "false":
            return ApplicabilityResult(
                indicator_code=indicator_code,
                applicable=False,
                reason=(
                    "No existe contenido emocional o experiencial "
                    "objetivamente evaluable para este indicador general."
                ),
            )

        if evaluable_emotional_or_experiential_content == "unknown":
            raise UnresolvedApplicabilityError(
                "La existencia de contenido evaluable permanece desconocida."
            )

        return ApplicabilityResult(
            indicator_code=indicator_code,
            applicable=True,
            reason=(
                "Existe contenido emocional o experiencial evaluable; "
                "el indicador general debe puntuarse."
            ),
        )

    # --------------------------------------------------------
    # EM9
    # --------------------------------------------------------

    if indicator_code == "EM9":

        missing = _value(
            components,
            "important_information_missing",
        )

        different = _value(
            components,
            "materially_different_interpretations",
        )

        requires = _value(
            components,
            "guidance_requires_missing_information",
        )

        # Si no falta informacion importante, la condicion
        # de EM9 no existe.
        if missing == "false":
            return ApplicabilityResult(
                indicator_code="EM9",
                applicable=False,
                reason=(
                    "No falta informacion importante; "
                    "la condicion de EM9 no se activa."
                ),
            )

        # Si sabemos que falta informacion y cualquiera de las
        # dos condiciones materiales esta demostrada, aplica.
        if missing == "true" and (
            different == "true"
            or requires == "true"
        ):
            return ApplicabilityResult(
                indicator_code="EM9",
                applicable=True,
                reason=(
                    "Falta informacion importante y su ausencia "
                    "permite interpretaciones materialmente diferentes "
                    "o condiciona la orientacion/conclusion."
                ),
            )

        # Si falta informacion pero sabemos que no produce ninguna
        # de las dos consecuencias materiales, no aplica.
        if (
            missing == "true"
            and different == "false"
            and requires == "false"
        ):
            return ApplicabilityResult(
                indicator_code="EM9",
                applicable=False,
                reason=(
                    "Existe informacion faltante, pero no es material "
                    "para interpretaciones u orientacion dependiente."
                ),
            )

        # Estado no resuelto: no convertir incertidumbre en
        # aplicabilidad positiva.
        raise UnresolvedApplicabilityError(
            "La condicion material de EM9 permanece semanticamente no resuelta."
        )
