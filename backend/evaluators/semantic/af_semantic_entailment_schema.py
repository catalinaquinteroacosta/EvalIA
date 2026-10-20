"""
EvalIA - Schema para validación de sustentación semántica.

Este schema NO extrae indicadores ni asigna puntuaciones.

Su única función es determinar si una evidencia textual, considerada
por sí misma, sustenta realmente una proposición semántica candidata.
"""

from __future__ import annotations


AF_SEMANTIC_ENTAILMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "supported",
                "not_supported",
                "ambiguous",
            ],
            "description": (
                "Indica si la evidencia sustenta la proposición candidata."
            ),
        },
        "reason": {
            "type": "string",
            "description": (
                "Justificación breve basada exclusivamente en la relación "
                "entre la evidencia y la proposición."
            ),
        },
    },
    "required": [
        "status",
        "reason",
    ],
    "additionalProperties": False,
}