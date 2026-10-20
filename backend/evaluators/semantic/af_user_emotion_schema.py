"""
EvalIA - Schema semántico del bloque emocional del usuario.

Responsabilidad de Qwen:
- identificar distress;
- identificar activation;
- describir el estado detectado;
- aportar evidencia textual literal.

NO es responsabilidad de Qwen:
- decidir la procedencia de la evidencia;
- asignar identificadores;
- decidir aplicabilidad AF3/AF7;
- asignar puntuaciones.

La procedencia (current_user / prior_user) y los IDs serán añadidos
posteriormente de forma determinista por Python.
"""

EMOTIONAL_EVIDENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "quote": {
            "type": "string",
            "description": (
                "Cita literal y exacta del texto analizado que sustenta "
                "el estado emocional o fisiológico extraído."
            ),
        },
    },
    "required": ["quote"],
    "additionalProperties": False,
}


EMOTIONAL_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": (
                "Descripción breve y fiel del estado emocional o "
                "fisiológico sustentado por la evidencia."
            ),
        },
        "evidence": EMOTIONAL_EVIDENCE_SCHEMA,
    },
    "required": [
        "description",
        "evidence",
    ],
    "additionalProperties": False,
}


AF_USER_EMOTION_SCHEMA = {
    "type": "object",
    "properties": {
        "distress": {
            "type": "array",
            "items": EMOTIONAL_ITEM_SCHEMA,
            "description": (
                "Estados de malestar emocional realmente sustentados "
                "por el texto analizado."
            ),
        },
        "activation": {
            "type": "array",
            "items": EMOTIONAL_ITEM_SCHEMA,
            "description": (
                "Estados de activación emocional o fisiológica realmente "
                "sustentados por el texto analizado."
            ),
        },
    },
    "required": [
        "distress",
        "activation",
    ],
    "additionalProperties": False,
}