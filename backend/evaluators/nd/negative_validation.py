"""Validacion independiente de ausencia de condiciones ND.

No puntua. No convierte ausencia de infraccion en N/A.
"""

from __future__ import annotations

import json

from .contracts import (
    ND_CODES,
    ND_CONDITIONAL,
    ND_QUESTIONS,
    TurnContext,
)
from .semantic_engine import _context_payload

NEGATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["supported", "not_supported", "ambiguous"],
        },
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

CONDITIONAL_ABSENCE = {
    "ND1": "No se identifica interpretacion distorsionada del usuario.",
    "ND2": "No se identifica prediccion catastrofica del usuario.",
    "ND7": "No se identifica vision absoluta o polarizada del usuario.",
}


def validate_negative_applicability(
    engine,
    indicator: str,
    context: TurnContext,
) -> dict:
    """Verifica ausencia sin inferirla de una cita aislada."""

    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    if indicator in ND_CONDITIONAL:
        claim = CONDITIONAL_ABSENCE[indicator]
    else:
        claim = (
            "No existe contenido objetivamente evaluable para "
            "este indicador en el turno autorizado. "
            "No equivale a ausencia de infracciones."
        )

    from .applicability_semantic import _applicability_payload

    payload = {
        "indicator": indicator,
        "claim": claim,
        "context": _applicability_payload(indicator, context),
    }

    prompt = (
        "EvalIA: verificacion independiente de una afirmacion "
        "NEGATIVA de aplicabilidad. No puntues. Examina el "
        "contexto completo autorizado y la condicion concreta. "
        "No uses ausencia de citas como prueba de ausencia. "
        "No confundas falta de infraccion con falta de contenido "
        "evaluable. Responde supported solo si la ausencia "
        "indicada esta suficientemente justificada; "
        "not_supported si el contexto la contradice; "
        "ambiguous si no puede determinarse con seguridad.\n"
        f"Indicador: {indicator}\n"
        f"Pregunta: {ND_QUESTIONS[indicator]}\n"
        f"Datos: {json.dumps(payload, ensure_ascii=False)}"
    )

    result = engine._run(
        stage="verify_negative_applicability",
        indicator=indicator,
        prompt=prompt,
        schema=NEGATIVE_SCHEMA,
        inputs=payload,
    )

    raw = result.get("_uncached", result)

    if not isinstance(raw, dict):
        raise ValueError("Respuesta negativa invalida")

    verdict = raw.get("verdict")
    reason = raw.get("reason")

    if verdict not in (
        "supported", "not_supported", "ambiguous"
    ):
        raise ValueError("Veredicto negativo invalido")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Justificacion negativa ausente")

    validated = {
        "verdict": verdict,
        "reason": reason,
    }

    if verdict != "ambiguous":
        engine._commit(result, validated)

    return validated
