"""
EvalIA - Schema semántico del bloque Acción e Interferencia del usuario.

Objetivo:
- identificar acciones concretas del usuario;
- identificar si existe evidencia de dificultad o interferencia
  para iniciar, sostener o completar una acción;
- representar explícitamente la relación entre interferencia y acción.

NO:
- decide aplicabilidad de AF7;
- asigna puntuaciones;
- infiere que una emoción interfiere con una acción;
- inventa acciones implícitas a partir de una situación.
"""

from __future__ import annotations


ACTION_EVIDENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "quote": {
            "type": "string",
            "description": (
                "Cita literal y exacta del texto analizado que sustenta "
                "el elemento extraído."
            ),
        },
    },
    "required": ["quote"],
    "additionalProperties": False,
}


CANDIDATE_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": (
                "Acción concreta que el usuario realiza, intenta realizar, "
                "planea realizar, necesita realizar, debe realizar o "
                "identifica inequívocamente como conducta propia."
            ),
        },
        "evidence": ACTION_EVIDENCE_SCHEMA,
    },
    "required": [
        "description",
        "evidence",
    ],
    "additionalProperties": False,
}


ACTION_INTERFERENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "action_description": {
            "type": "string",
            "description": (
                "Descripción de la acción concreta cuya ejecución aparece "
                "afectada en el texto."
            ),
        },
        "interference_description": {
            "type": "string",
            "description": (
                "Descripción breve de cómo se dificulta iniciar, sostener "
                "o completar la acción."
            ),
        },
        "evidence": ACTION_EVIDENCE_SCHEMA,
    },
    "required": [
        "action_description",
        "interference_description",
        "evidence",
    ],
    "additionalProperties": False,
}


AF_USER_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_actions": {
            "type": "array",
            "items": CANDIDATE_ACTION_SCHEMA,
            "description": (
                "Acciones concretas del usuario realmente sustentadas "
                "por el texto."
            ),
        },
        "action_interferences": {
            "type": "array",
            "items": ACTION_INTERFERENCE_SCHEMA,
            "description": (
                "Casos en los que el texto sustenta que una acción concreta "
                "del usuario presenta dificultad o interferencia para "
                "iniciarse, sostenerse o completarse."
            ),
        },
    },
    "required": [
        "candidate_actions",
        "action_interferences",
    ],
    "additionalProperties": False,
}