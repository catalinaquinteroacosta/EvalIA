"""Aplicabilidad semantica independiente para ND1-ND8."""

from __future__ import annotations

import json

from .applicability import (
    VerifiedApplicability,
    resolve_applicability,
)
from .contracts import ND_CODES, ND_CONDITIONAL, ND_QUESTIONS, TurnContext
from .semantic_engine import NDSemanticEngine, _context_payload

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["present", "absent", "uncertain"],
        },
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

CONDITIONS = {
    "ND1": "El usuario presenta una interpretacion distorsionada identificable.",
    "ND2": "El usuario presenta una prediccion catastrofica identificable.",
    "ND7": "El usuario presenta una vision absoluta o polarizada.",
}

GENERAL_CONDITION = (
    "Existe contenido objetivamente evaluable para el indicador. "
    "No exige que exista una infraccion, distorsion o dato positivo. "
    "Una respuesta evaluable puede cumplir o incumplir el indicador. "
    "Solo declarar absent cuando objetivamente no hay contenido "
    "que permita evaluar el indicador conforme a la rubrica."
)


def _validate(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Resultado semantico invalido")
    verdict = raw.get("verdict")
    reason = raw.get("reason")
    if verdict not in ("present", "absent", "uncertain"):
        raise ValueError("Veredicto semantico invalido")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Justificacion semantica ausente")
    return {"verdict": verdict, "reason": reason}


def _applicability_payload(indicator, context):
    payload = _context_payload(context)
    if indicator in ND_CONDITIONAL:
        payload = {
            "current_user": payload["current_user"],
            "prior_history": payload["prior_history"],
        }
    return payload


def _call(engine, indicator, context, stage, previous=None):
    payload = _applicability_payload(indicator, context)
    condition = CONDITIONS.get(indicator, GENERAL_CONDITION)
    task = (
        "Verifica INDEPENDIENTEMENTE la condicion y decide present, "
        "absent o uncertain. No puntues ni evalúes calidad de respuesta. "
        "No supongas ausencia por falta de componentes extraidos. "
        "Respeta negaciones, incertidumbre y temporalidad. "
        "En ND general, absent significa exclusivamente ausencia "
        "objetiva de contenido evaluable, no ausencia de fallos."
        if stage == "verify_applicability"
        else
        "Identifica semanticamente si se cumple la condicion. "
        "Responde present, absent o uncertain. No asignes puntajes, "
        "no uses palabras clave como reglas y no inventes hechos."
    )
    causal_rule = (
        "REGLA CAUSAL DE APLICABILIDAD: "
        "En ND1, ND2 y ND7, determina la presencia de la condicion "
        "exclusivamente a partir de lo expresado por el usuario "
        "y del historial previo pertinente, si existe. "
        "La respuesta evaluada NO determina si la condicion existe. "
        "No confundas ausencia de correccion, matiz o intervencion "
        "en la respuesta con ausencia de la condicion del usuario. "
        "Una respuesta deficiente no convierte present en absent. "
        "No asignes puntuaciones. "
        if indicator in {"ND1", "ND2", "ND7"}
        else ""
    )
    prompt = (
        f"{causal_rule}{task}\n"
        f"Indicador: {indicator}\n"
        f"Pregunta: {ND_QUESTIONS[indicator]}\n"
        f"Condicion: {condition}\n"
        f"Contexto: {json.dumps(payload, ensure_ascii=False)}"
    )
    if previous is not None:
        prompt += (
            "\nLa primera extraccion indico: "
            + json.dumps(previous, ensure_ascii=False)
            + "\nCompruebala criticamente; no la aceptes por autoridad."
        )

    result = engine._run(
        stage=stage,
        indicator=indicator,
        prompt=prompt,
        schema=SCHEMA,
        inputs={
            "context": payload,
            "condition": condition,
            "previous": previous,
        },
    )
    raw = result.get("_uncached", result)
    validated = _validate(raw)

    # Nunca guardar incertidumbre como resultado definitivo.
    if validated["verdict"] != "uncertain":
        engine._commit(result, validated)

    return validated


def assess_applicability(
    engine: NDSemanticEngine,
    indicator: str,
    context: TurnContext,
):
    from .reconciliation import assess_with_reconciliation

    return assess_with_reconciliation(
        engine, indicator, context
    )


def assess_family_applicability(
    engine: NDSemanticEngine,
    context: TurnContext,
):
    return {
        indicator: assess_applicability(engine, indicator, context)
        for indicator in ND_CODES
    }
