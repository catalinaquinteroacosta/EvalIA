"""
EvalIA — Schema semántico del usuario para Afrontamiento (AF1–AF8).

Este schema define los hechos del mensaje actual del usuario y del
historial previo permitido que pueden ser necesarios para determinar
el contexto y la aplicabilidad de los indicadores AF.

IMPORTANTE:
- Aquí NO se evalúa la calidad de la respuesta de la IA.
- Aquí NO se asignan puntuaciones 0–3.
- Aquí NO se decide N/A.
- El extractor identifica hechos y relaciones respaldados por evidencia.
"""

from __future__ import annotations

from typing import Any

from .af_schema import AF_SEMANTIC_STATUS_VALUES


EVIDENCE_SOURCES_USER = [
    "current_user",
    "prior_user",
]


def _evidence_schema() -> dict[str, Any]:
    """Evidencia textual atribuida a una fuente del usuario."""

    return {
        "type": "object",
        "properties": {
            "quote": {
                "type": "string",
            },
            "source": {
                "type": "string",
                "enum": EVIDENCE_SOURCES_USER,
            },
        },
        "required": [
            "quote",
            "source",
        ],
        "additionalProperties": False,
    }


def _relation_schema() -> dict[str, Any]:
    """
    Relación semántica con evidencia a favor, contraevidencia
    y posibilidad explícita de ambigüedad.
    """

    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": AF_SEMANTIC_STATUS_VALUES,
            },
            "supporting_evidence": {
                "type": "array",
                "items": _evidence_schema(),
            },
            "counterevidence": {
                "type": "array",
                "items": _evidence_schema(),
            },
        },
        "required": [
            "status",
            "supporting_evidence",
            "counterevidence",
        ],
        "additionalProperties": False,
    }


AF_USER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {

        # AF1 / AF2
        "modifiable_components": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # AF1 / AF3 / AF5
        "unmodifiable_now": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # AF1 / AF5
        "uncertain_outcomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # AF3
        "distress": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # AF4
        "avoidance_behaviors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "behavior": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "behavior",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # Se mantiene separado de conducta realizada.
        "avoidance_intentions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "intention": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "intention",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # AF4
        "avoidance_costs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "avoidance_id": {"type": "string"},
                    "cost": {"type": "string"},
                    "evidence": _evidence_schema(),
                    "relation": _relation_schema(),
                },
                "required": [
                    "id",
                    "avoidance_id",
                    "cost",
                    "evidence",
                    "relation",
                ],
                "additionalProperties": False,
            },
        },

        # AF7
        "activations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # AF7
        "candidate_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "action": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "action",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        # Relación necesaria para AF7:
        # activación -> interferencia con una acción.
        "activation_action_relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "activation_id": {"type": "string"},
                    "action_id": {"type": "string"},
                    "relation": _relation_schema(),
                },
                "required": [
                    "activation_id",
                    "action_id",
                    "relation",
                ],
                "additionalProperties": False,
            },
        },

        # AF6
        "prior_helpful_resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "resource": {"type": "string"},
                    "evidence": _evidence_schema(),
                },
                "required": [
                    "id",
                    "resource",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
    },

    "required": [
        "modifiable_components",
        "unmodifiable_now",
        "uncertain_outcomes",
        "distress",
        "avoidance_behaviors",
        "avoidance_intentions",
        "avoidance_costs",
        "activations",
        "candidate_actions",
        "activation_action_relations",
        "prior_helpful_resources",
    ],

    "additionalProperties": False,
}