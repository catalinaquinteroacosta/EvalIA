"""Reconciliación semántica dirigida. No puntúa."""

from dataclasses import asdict

from .contracts import Evidence
from .evidence import verify_exact_evidence
from .semantic import INDICATORS, ask_openai

SYSTEM = """
Eres un reconciliador independiente de EvalIA.

Analiza el criterio oficial, la respuesta original y
ÚNICAMENTE los hallazgos cuestionados.

No asumas que la auditoría previa tiene razón.
No inventes obligaciones ni requisitos de formato.
No puntúes ni decidas N/A.

Determina para cada hallazgo:
- supported: la cita demuestra la afirmación;
- unsupported: la cita no demuestra la afirmación;
- ambiguous: no se puede decidir con suficiente respaldo.

Para IR7, "sin recurrir a optimismo infundado" es una
restricción sobre la respuesta, NO una obligación de
mencionar explícitamente el optimismo.

Para IR6, proponer una reformulación o una técnica
NO demuestra automáticamente que se exploró si
el pensamiento resulta útil.

Devuelve exclusivamente JSON:
{
 "results": [
  {
   "id": "identificador recibido",
   "verdict": "supported|unsupported|ambiguous",
   "reason": "justificación específica",
   "quote": "cita literal de la respuesta o cadena vacía"
  }
 ]
}

Cada hallazgo recibido debe tener exactamente un resultado.
La cita es obligatoria cuando el veredicto es supported.
"""


def reconcile(ctx, indicator, findings):
    if indicator not in INDICATORS:
        raise ValueError("Indicador desconocido")

    if not isinstance(findings, list) or not findings:
        raise ValueError("Sin hallazgos")

    ids = [x["id"] for x in findings]

    if len(ids) != len(set(ids)):
        raise ValueError("IDs duplicados")

    payload = {
        "indicator": indicator,
        "criterion": INDICATORS[indicator],
        "user": ctx.user,
        "response": ctx.response,
        "prior_history": [asdict(m) for m in ctx.prior_history],
        "questioned_findings": findings,
    }

    raw = ask_openai(SYSTEM, payload)
    rows = raw.get("results")

    if not isinstance(rows, list):
        raise ValueError("Resultados inválidos")

    by_id = {}

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Resultado inválido")

        key = row.get("id")

        if key not in ids or key in by_id:
            raise ValueError("ID inesperado o duplicado")

        verdict = row.get("verdict")

        if verdict not in (
            "supported", "unsupported", "ambiguous"
        ):
            raise ValueError("Veredicto inválido")

        reason = row.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Justificación obligatoria")

        quote = row.get("quote", "")

        if not isinstance(quote, str):
            raise ValueError("Cita inválida")

        evidence = None

        if verdict == "supported":
            ev = Evidence(source="response", quote=quote)
            if not verify_exact_evidence(ctx, ev):
                raise ValueError("Cita no literal")
            evidence = asdict(ev)

        elif quote:
            ev = Evidence(source="response", quote=quote)
            if not verify_exact_evidence(ctx, ev):
                raise ValueError("Cita no literal")
            evidence = asdict(ev)

        by_id[key] = {
            "id": key,
            "verdict": verdict,
            "reason": reason,
            "evidence": evidence,
        }

    if set(by_id) != set(ids):
        raise ValueError("Faltan decisiones")

    return [by_id[key] for key in ids]