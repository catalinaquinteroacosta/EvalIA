from __future__ import annotations

"""
Schemas V2 de EM con evidencia trazable.

El extractor:
- NO puntua.
- NO decide N/A.
- declara fuente exacta de cada cita.
"""

from copy import deepcopy
from typing import Any

from backend.evaluators.semantic.em.schemas import (
    COMPONENT_DESCRIPTIONS,
)


EM_SCHEMA_V2_VERSION = "EM-SCHEMA-2.0.0"

TRISTATE = ["true", "false", "unknown"]

EVIDENCE_REF_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source": {
            "type": "string",
            "enum": ["history", "user", "response"],
        },
        "history_index": {
            "type": ["integer", "null"],
            "minimum": 0,
        },
        "quote": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "source",
        "history_index",
        "quote",
    ],
}


def _component_field(description: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {
                "type": "string",
                "enum": TRISTATE,
            },
            "evidence": {
                "type": "array",
                "items": deepcopy(EVIDENCE_REF_SCHEMA),
            },
            "counterevidence": {
                "type": "array",
                "items": deepcopy(EVIDENCE_REF_SCHEMA),
            },
            "reason": {
                "type": "string",
            },
        },
        "required": [
            "value",
            "evidence",
            "counterevidence",
            "reason",
        ],
        "description": description,
    }


def build_em_schema_v2(indicator_code: str) -> dict[str, Any]:
    code = str(indicator_code).strip().upper()

    if code not in COMPONENT_DESCRIPTIONS:
        raise ValueError(
            f"Indicador EM no soportado: {indicator_code!r}"
        )

    properties = {
        name: _component_field(description)
        for name, description
        in COMPONENT_DESCRIPTIONS[code].items()
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "indicator_code": {
                "type": "string",
                "enum": [code],
            },
            "components": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": list(properties),
            },
        },
        "required": [
            "indicator_code",
            "components",
        ],
    }


EM_SCHEMAS_V2 = {
    f"EM{i}": build_em_schema_v2(f"EM{i}")
    for i in range(1, 14)
}


def get_em_schema_v2(indicator_code: str) -> dict[str, Any]:
    code = str(indicator_code).strip().upper()

    if code not in EM_SCHEMAS_V2:
        raise ValueError(
            f"Indicador EM no soportado: {indicator_code!r}"
        )

    return deepcopy(EM_SCHEMAS_V2[code])
