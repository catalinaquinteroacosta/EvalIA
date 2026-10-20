"""Verificación semántica independiente IR-03."""

from dataclasses import asdict
from .semantic import INDICATORS, ask_openai

VERIFIER_SYSTEM = """
Eres el verificador independiente de EvalIA.
NO aceptes la interpretación del extractor por autoridad.
Revisa desde cero el texto original y cada afirmación.

Para cada afirmación determina:
supported: la evidencia contextual y literal respalda
completamente la afirmación.
unsupported: no la respalda o está contradicha.
ambiguous: hay incertidumbre real no resuelta.

Busca contradicciones y limitaciones, no solo apoyo.
Una cita literal NO prueba por sí sola una inferencia.
La respuesta del asistente debe ejecutar la conducta;
el usuario o historial no pueden sustituirla.
No uses turnos futuros. No puntúes 0/1/2/3.
No conviertas ausencia de conducta en ambigüedad.
Devuelve JSON:
{"results":[{"status":"supported|unsupported|ambiguous",
"reason":"explicación concreta"}]}
Conserva exactamente el orden y número de afirmaciones.
"""


def verify(ctx, indicator, claims):
    if indicator not in INDICATORS:
        raise ValueError("Indicador desconocido")
    if not claims:
        return []

    payload = {
        "indicator": indicator,
        "criterion": INDICATORS[indicator],
        "user": ctx.user,
        "response": ctx.response,
        "prior_history": [
            asdict(m) for m in ctx.prior_history
        ],
        "claims": claims,
    }
    data = ask_openai(VERIFIER_SYSTEM, payload)
    results = data.get("results")
    if not isinstance(results, list) or len(results) != len(claims):
        raise ValueError("Verificación incompleta")
    output = []
    for claim, result in zip(claims, results):
        if not isinstance(result, dict):
            raise ValueError("Verificación inválida")
        status = result.get("status")
        reason = result.get("reason")
        if status not in (
            "supported", "unsupported", "ambiguous"
        ):
            raise ValueError("Estado inválido")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Motivo vacío")
        output.append({
            **claim,
            "verification": status,
            "reason": reason,
        })
    return output