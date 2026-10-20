"""
EvalIA — Esquema semántico común para Afrontamiento (AF1–AF8)

Este módulo define estructuras y estados compartidos por el extractor
semántico de afrontamiento.

Principio arquitectónico:
- El LLM extrae hechos, relaciones y evidencia textual.
- El LLM NO asigna puntuaciones 0–3 ni N/A.
- Las reglas deterministas de Python aplican posteriormente la rúbrica.
"""

from enum import Enum


class SemanticStatus(str, Enum):
    """
    Estado de soporte semántico de una relación o afirmación.

    SUPPORTED:
        Existe evidencia textual suficiente que respalda la relación.

    NOT_SUPPORTED:
        No existe evidencia textual suficiente para respaldarla.

    AMBIGUOUS:
        Existen señales razonables en más de una dirección o la evidencia
        no permite resolver la relación con suficiente claridad.
    """

    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    AMBIGUOUS = "ambiguous"


AF_SEMANTIC_STATUS_VALUES = [
    SemanticStatus.SUPPORTED.value,
    SemanticStatus.NOT_SUPPORTED.value,
    SemanticStatus.AMBIGUOUS.value,
]