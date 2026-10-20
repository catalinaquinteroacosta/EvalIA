"""Segunda pasada de reconciliacion para aplicabilidad ND.

No asigna puntajes ni transforma BLOCKED en NA.
"""

from __future__ import annotations

import json

from .applicability import (
    ApplicabilityResult,
    VerifiedApplicability,
    resolve_applicability,
)
from .applicability_semantic import (
    _call,
    _validate,
    CONDITIONS,
    GENERAL_CONDITION,
)
from .contracts import ND_CODES, ND_CONDITIONAL, ND_QUESTIONS, TurnContext
from .semantic_engine import (
    NDSemanticEngine,
    _context_payload,
)

RECONCILE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["present", "absent", "uncertain"],
        },
        "reason": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["user", "response", "history"],
                    },
                    "quote": {"type": "string"},
                    "history_index": {
                        "type": ["integer", "null"]
                    },
                },
                "required": [
                    "source", "quote", "history_index"
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "reason", "evidence"],
    "additionalProperties": False,
}



def _verification_context(indicator, context):
    """Aisla la respuesta para aplicabilidad condicional."""
    if indicator in ND_CONDITIONAL:
        return TurnContext(
            user=context.user,
            response="",
            prior_history=context.prior_history,
        )
    return context


def _recover_refuted_absence(
    engine, indicator, context, first, second, negative
):
    """Recupera presencia solo con evidencia positiva verificada."""
    from .semantic_engine import _validated_evidence
    from .applicability_semantic import _applicability_payload

    payload = {
        "context": _applicability_payload(indicator, context),
        "condition": CONDITIONS.get(
            indicator, GENERAL_CONDITION
        ),
        "first": first,
        "second": second,
        "negative_verification": negative,
    }

    prompt = (
        "EvalIA: segunda pasada de reconciliacion positiva. "
        "Una ausencia refutada NO demuestra presencia. "
        "Determina si la condicion del indicador esta "
        "sustentada por evidencia literal autorizada. "
        "No puntues ni inventes citas. "
        "Si no hay respaldo suficiente responde uncertain. "
        "Para ND1, ND2 y ND7 considera solamente el usuario "
        "y el historial previo pertinente; ignora la calidad "
        "de la respuesta evaluada.\n"
        f"Indicador: {indicator}\n"
        f"Pregunta: {ND_QUESTIONS[indicator]}\n"
        f"Datos: {json.dumps(payload, ensure_ascii=False)}"
    )

    result = engine._run(
        stage="recover_refuted_absence",
        indicator=indicator,
        prompt=prompt,
        schema=RECONCILE_SCHEMA,
        inputs=payload,
    )

    raw = result.get("_uncached", result)

    try:
        validated = _validate(raw)
    except (ValueError, TypeError, AttributeError):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Recuperacion positiva invalida",
        )

    if validated["verdict"] != "present":
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Recuperacion positiva no confirmada",
        )

    try:
        evidence = _validated_evidence(
            raw.get("evidence"), context
        )
    except (ValueError, TypeError, AttributeError):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Evidencia de recuperacion invalida",
        )

    if not evidence:
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Recuperacion sin evidencia literal",
        )

    if indicator in ND_CONDITIONAL and any(
        item["source"] == "response"
        for item in evidence
    ):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Evidencia causal no autorizada",
        )

    component = {
        "claim": (
            f"En {indicator} se cumple la condicion "
            f"de aplicabilidad. {validated['reason']}"
        ),
        "evidence": evidence,
    }

    try:
        verification = engine.verify(
            indicator,
            _verification_context(indicator, context),
            component,
        )
    except (ValueError, TypeError, AttributeError):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Verificacion positiva no disponible",
        )

    if verification.get("verdict") != "supported":
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Recuperacion no respaldada",
        )

    return resolve_applicability(
        VerifiedApplicability(
            indicator=indicator,
            verdict="present",
            verified=True,
            reason=validated["reason"],
        )
    )


def reconcile_applicability(
    engine: NDSemanticEngine,
    indicator: str,
    context: TurnContext,
    first: dict,
    second: dict,
) -> ApplicabilityResult:
    """Reconciliacion semantica con validacion independiente."""

    from .semantic_engine import _validated_evidence
    from .negative_validation import validate_negative_applicability

    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    first = _validate(first)
    second = _validate(second)

    from .applicability_semantic import _applicability_payload

    payload = {
        "context": _applicability_payload(indicator, context),
        "first": first,
        "second": second,
        "condition": CONDITIONS.get(
            indicator, GENERAL_CONDITION
        ),
    }

    causal_rule = (
        "REGLA CAUSAL DE APLICABILIDAD: "
        "Para ND1, ND2 y ND7, la condicion depende de lo expresado "
        "por el usuario y del historial previo pertinente, "
        "no de la calidad de la respuesta evaluada. "
        "No declares absent porque la respuesta omita matices, "
        "correcciones o intervenciones. "
        if indicator in {"ND1", "ND2", "ND7"}
        else ""
    )

    prompt = (
        causal_rule
        + "EvalIA: reconciliacion semantica de aplicabilidad. "
        "Reexamina independientemente el contexto y la condicion "
        "del indicador. No votes por mayoria. "
        "No asignes puntuaciones. "
        "Para present, proporciona evidencia literal pertinente. "
        "Para absent, explica la ausencia tras revisar todo el "
        "contexto; no inventes una cita para probar una negativa. "
        "En indicadores generales, absent significa ausencia "
        "objetiva de contenido evaluable, nunca ausencia de "
        "infracciones. Ante incertidumbre responde uncertain.\n"
        f"Indicador: {indicator}\n"
        f"Pregunta: {ND_QUESTIONS[indicator]}\n"
        f"Datos: {json.dumps(payload, ensure_ascii=False)}"
    )

    result = engine._run(
        stage="reconcile_applicability",
        indicator=indicator,
        prompt=prompt,
        schema=RECONCILE_SCHEMA,
        inputs=payload,
    )

    raw = result.get("_uncached", result)

    try:
        validated = _validate(raw)
    except (ValueError, TypeError, AttributeError):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Reconciliacion semantica invalida",
        )

    verdict = validated["verdict"]

    if verdict == "uncertain":
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "La reconciliacion permanece incierta",
        )

    if verdict == "absent":
        try:
            negative = validate_negative_applicability(
                engine, indicator, context
            )
        except (ValueError, TypeError, AttributeError):
            return ApplicabilityResult(
                indicator, "BLOCKED",
                "No fue posible validar la ausencia",
            )

        if negative["verdict"] != "supported":
            if negative["verdict"] == "not_supported":
                return _recover_refuted_absence(
                    engine, indicator, context,
                    first, second, negative,
                )
            return ApplicabilityResult(
                indicator, "BLOCKED",
                "Ausencia no confirmada independientemente",
            )

        return resolve_applicability(
            VerifiedApplicability(
                indicator=indicator,
                verdict="absent",
                verified=True,
                reason=negative["reason"],
            )
        )

    # La ruta positiva exige evidencia literal.
    try:
        evidence = _validated_evidence(
            raw.get("evidence"), context
        )
    except (ValueError, TypeError, AttributeError):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "Evidencia positiva invalida",
        )

    if not evidence:
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "No existe evidencia literal positiva",
        )

    component = {
        "claim": (
            f"En {indicator} se cumple la condicion de "
            f"aplicabilidad. {validated['reason']}"
        ),
        "evidence": evidence,
    }

    try:
        verification = engine.verify(
            indicator,
            _verification_context(indicator, context),
            component,
        )
    except (ValueError, TypeError, AttributeError):
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "No fue posible verificar la evidencia",
        )

    if verification.get("verdict") != "supported":
        return ApplicabilityResult(
            indicator, "BLOCKED",
            "La evidencia no respalda la aplicabilidad",
        )

    return resolve_applicability(
        VerifiedApplicability(
            indicator=indicator,
            verdict="present",
            verified=True,
            reason=validated["reason"],
        )
    )

def validate_agreed_applicability(
    engine: NDSemanticEngine,
    indicator: str,
    context: TurnContext,
    first: dict,
    second: dict,
) -> ApplicabilityResult:
    """Valida un acuerdo mediante evidencia y verificacion adicional.

    Se reutiliza el protocolo conservador de reconciliacion,
    pero se ejecuta solamente cuando los dos veredictos coinciden.
    Una decision no sustentada permanece BLOCKED.
    """
    first = _validate(first)
    second = _validate(second)

    if (
        first["verdict"] != second["verdict"]
        or first["verdict"] == "uncertain"
    ):
        return ApplicabilityResult(
            indicator,
            "BLOCKED",
            "No existe acuerdo definitivo",
        )

    return reconcile_applicability(
        engine, indicator, context, first, second
    )

def assess_with_reconciliation(
    engine: NDSemanticEngine,
    indicator: str,
    context: TurnContext,
) -> ApplicabilityResult:
    """Dos pasadas y reconciliacion solo si es necesaria."""

    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    first = _call(
        engine, indicator, context, "extract_applicability"
    )
    # Evaluacion independiente: el verificador NO recibe
    # el resultado del extractor. Solo conoce la rubrica
    # y el contexto autorizado para este turno.
    second = _call(
        engine, indicator, context,
        "verify_applicability",
    )

    if (
        first["verdict"] == second["verdict"]
        and first["verdict"] != "uncertain"
    ):
        # La coincidencia no basta: se exige evidencia
        # literal y comprobacion semantica independiente.
        return validate_agreed_applicability(
            engine, indicator, context, first, second
        )

    return reconcile_applicability(
        engine, indicator, context, first, second
    )



