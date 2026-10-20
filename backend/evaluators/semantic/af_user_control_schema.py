"""
EvalIA — Schema semántico de Controlabilidad del usuario.

Este schema representa únicamente información necesaria para distinguir:

1. Componentes del estresor que la persona puede intentar modificar.
2. Hechos o situaciones que no puede modificar en el momento actual.
3. Resultados externos o futuros que no puede garantizar.

NO evalúa:
- malestar emocional;
- activación;
- evitación;
- acciones bloqueadas;
- recursos previos;
- respuesta de la IA;
- puntuaciones AF.

El extractor semántico identifica evidencia.
Las reglas deterministas de EvalIA deciden posteriormente
aplicabilidad y puntuación.
"""

from __future__ import annotations


EVIDENCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "quote": {
            "type": "string",
            "description": (
                "Fragmento literal y exacto de la fuente que sustenta "
                "la proposición semántica."
            ),
        },
        "source": {
            "type": "string",
            "enum": [
                "current_user",
                "prior_user",
            ],
        },
    },
    "required": [
        "quote",
        "source",
    ],
}


CONTROL_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {
            "type": "string",
        },
        "description": {
            "type": "string",
        },
        "evidence": EVIDENCE_SCHEMA,
    },
    "required": [
        "id",
        "description",
        "evidence",
    ],
}


AF_USER_CONTROL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {

        "modifiable_components": {
            "type": "array",
            "description": (
                "Componentes concretos de la situación o fuente de estrés "
                "sobre los que la persona puede intentar actuar o influir. "
                "No incluir emociones, pensamientos o síntomas únicamente "
                "porque puedan regularse."
            ),
            "items": CONTROL_ITEM_SCHEMA,
        },

        "unmodifiable_now": {
            "type": "array",
            "description": (
                "Hechos ya ocurridos, límites reales, periodos de espera "
                "u otros aspectos de la situación que la persona no puede "
                "cambiar en el momento actual. No incluir simplemente "
                "cualquier hecho descrito por el usuario."
            ),
            "items": CONTROL_ITEM_SCHEMA,
        },

        "uncertain_outcomes": {
            "type": "array",
            "description": (
                "Resultados externos, futuros o dependientes de otras "
                "personas que el usuario no puede garantizar, aunque pueda "
                "realizar acciones para influir en ellos."
            ),
            "items": CONTROL_ITEM_SCHEMA,
        },
    },

    "required": [
        "modifiable_components",
        "unmodifiable_now",
        "uncertain_outcomes",
    ],
}