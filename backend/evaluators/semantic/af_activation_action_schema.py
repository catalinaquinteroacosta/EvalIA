"""
EvalIA - Schema semántico de relación Activación -> Acción/Interferencia.

Objetivo:
determinar si una activación previamente identificada está relacionada
con la dificultad para iniciar, sostener o completar una acción.

Este bloque NO:
- descubre nuevas emociones;
- descubre nuevas acciones;
- asigna puntuaciones;
- decide por sí solo la aplicabilidad final de AF7.
"""

from __future__ import annotations


AF_ACTIVATION_ACTION_RELATION_SCHEMA = {
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
                "Estado de sustentación de la relación entre la activación "
                "y la interferencia con la acción."
            ),
        },
        "reason": {
            "type": "string",
            "description": (
                "Explicación breve basada exclusivamente en la evidencia "
                "proporcionada."
            ),
        },
        "supporting_evidence": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": (
                "Citas literales que apoyan la relación. Debe quedar vacía "
                "si no existe evidencia literal pertinente."
            ),
        },
        "counterevidence": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": (
                "Citas literales que contradicen o debilitan la relación."
            ),
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