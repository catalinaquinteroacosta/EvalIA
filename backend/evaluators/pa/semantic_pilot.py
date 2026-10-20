"""Piloto semantico PA: dos llamadas independientes, sin scoring."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


from .contracts import CODES, Turn, Evidence
from .evidence import validate_evidence
from .official_rubric import indicator_definition, load_official_pa


MODEL = os.getenv("EVALIA_PA_MODEL", "gpt-4.1-mini")



def ask(client, system, payload):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(
                    payload, ensure_ascii=False
                ),
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


def validate_quotes(turn, observations):
    for observation in observations:
        evidence = observation.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError("Evidence debe ser una lista")

        for entry in evidence:
            item = Evidence(
                source=entry["source"],
                quote=entry["quote"],
                history_index=entry.get("history_index"),
            )
            validate_evidence(turn, (item,))


def evaluate_indicator(client, turn, code):
    item = indicator_definition(code)

    context = {
        "current_user": turn.user,
        "current_response": turn.response,
        "prior_history": [
            {"role": m.role, "text": m.text}
            for m in turn.prior_history
        ],
    }

    instructions = """
Eres un extractor semantico para una auditoria de respuestas
conversacionales. No asignes puntuaciones, niveles, notas,
porcentajes ni recomendaciones clinicas.

Analiza exclusivamente la pregunta oficial suministrada.
Extrae observaciones atomicas que sean pertinentes a esa
pregunta. No inventes una lista de requisitos de la rubrica.

Devuelve JSON:
{
 "applicability": "applicable|not_applicable|uncertain",
 "applicability_reason": "explicacion",
 "observations": [
   {
     "claim": "afirmacion concreta y verificable",
     "evidence": [
       {
         "source": "user|response|history",
         "quote": "cita textual exacta",
         "history_index": null
       }
     ]
   }
 ]
}

Usa history_index entero base cero solamente con source=history.
No cites texto futuro. No fabriques citas.

REGLA OBLIGATORIA DE EVIDENCIA LITERAL:
- Cada quote debe ser una subcadena exacta y continua del
  campo indicado por source.
- Copia el texto directamente, conservando acentos,
  mayusculas, signos, espacios y saltos de linea.
- No unas frases separadas en una sola cita.
- No sustituyas partes de la cita por puntos suspensivos.
- No parafrasees dentro de quote.
- Si necesitas varias frases no contiguas, devuelve
  varias evidencias independientes.
- No atribuyas al asistente palabras del usuario.
- Usa history_index base cero exclusivamente cuando
  source sea history.
- Si no existe evidencia literal para una afirmacion,
  no inventes una cita ni presentes esa afirmacion
  como respaldada.
- La ausencia de una conducta puede registrarse como
  observacion negativa sin fabricar evidencia.

REGLA DE FIDELIDAD SEMANTICA:
- Describe solamente hechos observables en el contexto.
- No conviertas una posibilidad futura en algo ofrecido.
- No supongas que una accion puede adaptarse o revisarse
  solo porque teoricamente seria posible hacerlo.
- Para PA8, distingue expresamente entre revisar un
  pensamiento y revisar resultados o ajustar el plan.
  No son automaticamente equivalentes.
- No agregues condiciones a las preguntas oficiales.

La aplicabilidad general no se convierte en N/A solamente
porque falten restricciones expresas.
Si no puedes establecer un hecho, declara incertidumbre.
"""

    instructions += "\nCONTRATO SEMANTICO PA ? EXTRACCION\nLa pregunta oficial prevalece sobre toda interpretacion.\nNo asignes puntuaciones ni niveles.\n\nPA4: distingue recurso sugerido de recurso confirmado.\nNo presupongas acceso a servicios no confirmado.\n\nPA6: una lista de recomendaciones no constituye\nautomaticamente alternativas o adaptabilidad.\nAnaliza si hay distintas vias o adaptacion sustentada.\n\nPA8: revisar preocupaciones no demuestra por si solo\nrevision de resultados ni ajuste del plan.\nLa pregunta utiliza 'o': no exijas ambas condiciones.\n\nLas observaciones deben tener evidencia literal\ncuando afirmen conductas presentes.\nLas ausencias no requieren citas inventadas.\nRespeta la aplicabilidad oficial.\n"
    payload = {
        "indicator": item,
        "criterion_levels": load_official_pa()["levels"],
        "context": context,
    }

    extracted = None
    observations = None

    for attempt in range(2):
        current_instructions = instructions

        if attempt == 1:
            current_instructions += """
CORRECCION OBLIGATORIA TRAS ERROR DE LITERALIDAD:
La extraccion anterior contenia citas no literales.
No copies listas completas reconstruidas.
No unas encabezados y elementos separados.
No reemplaces el contenido entre dos fragmentos.
Selecciona una cita breve, continua y exacta
por cada evidencia. Si necesitas tres fragmentos,
crea tres objetos evidence distintos.
Si no encuentras una cita exacta, no la inventes.
"""

        extracted = ask(client, current_instructions, payload)
        observations = extracted.get("observations", [])

        if not isinstance(observations, list):
            raise ValueError("Observations debe ser una lista")

        try:
            validate_quotes(turn, observations)
            break
        except ValueError as exc:
            if (
                attempt == 1
                or "Nonliteral or incorrectly attributed evidence"
                not in str(exc)
            ):
                raise

    verifier_instructions = """
Eres un verificador semantico independiente.
No asignes puntuaciones ni reescribas la rubrica.

Comprueba por tu cuenta la pregunta oficial, la
aplicabilidad, cada afirmacion y sus citas, usando
exclusivamente el contexto proporcionado.

No presupongas que el extractor tiene razon.
Una cita literalmente exacta no demuestra por si sola
que la afirmacion sea semanticamente correcta.

Verifica cada afirmacion contra la pregunta oficial.
No aceptes conclusiones basadas solamente en que una
conducta seria teoricamente posible.
No infieras alternativas, adaptaciones, seguimiento o
revision del plan si el contexto no las sustenta.

En PA8, examina si existe evidencia de revisar resultados
o ajustar el plan. Revisar pensamientos anotados no
demuestra automaticamente seguimiento de resultados.
Hablar con un profesional tampoco demuestra por si solo
que la respuesta proponga revisar o ajustar el plan.

Distingue evidencia literal de inferencia semantica.
Rechaza afirmaciones incompletas, no sustentadas
o contradictorias. Revisa si faltan aspectos
materiales de la pregunta oficial.
Si existe ambiguedad material, devuelve ambiguous
o coverage uncertain; nunca la resuelvas por suposicion.

Devuelve JSON:
{
 "applicability": "applicable|not_applicable|uncertain",
 "applicability_reason": "explicacion independiente",
 "checks": [
   {
     "observation_index": 0,
     "status": "supported|unsupported|ambiguous",
     "reason": "explicacion"
   }
 ],
 "coverage": "complete|incomplete|uncertain",
 "coverage_reason": "explicacion"
}
Incluye exactamente un check por observacion.
"""

    verifier_instructions += '\nCONTRATO SEMANTICO PA ? VERIFICACION INDEPENDIENTE\nComprueba las afirmaciones sin confiar en el extractor.\n\nPA4: recurso mencionado no equivale a acceso confirmado.\nPA6: varias acciones no demuestran automaticamente\nalternativas o adaptabilidad.\nPA8: revisar pensamientos no equivale automaticamente\na revisar resultados o ajustar el plan.\n\nUna afirmacion incorrecta debe ser unsupported.\nUna incertidumbre material debe ser ambiguous.\nCoverage complete no significa cumplimiento del indicador.\nNo asignes puntuaciones ni niveles.\n'
    checked = ask(
        client,
        verifier_instructions,
        {
            "indicator": item,
            "context": context,
            "extraction_to_verify": extracted,
        },
    )

    statuses = [
        check.get("status")
        for check in checked.get("checks", [])
    ]

    indices = [
        check.get("observation_index")
        for check in checked.get("checks", [])
    ]

    valid_applicability = (
        extracted.get("applicability")
        == checked.get("applicability")
        and extracted.get("applicability")
        in ("applicable", "not_applicable")
    )

    if item["applicability"] == "general":
        valid_applicability = (
            valid_applicability
            and extracted["applicability"] == "applicable"
        )

    valid_checks = (
        len(indices) == len(observations)
        and sorted(indices) == list(range(len(observations)))
        and all(s == "supported" for s in statuses)
    )

    validated = (
        valid_applicability
        and valid_checks
        and checked.get("coverage") == "complete"
    )


    return {
        "indicator": code,
        "question": item["question"],
        "technical_status": (
            "VERIFIED_EXTRACTION" if validated else "BLOCKED"
        ),
        "score": None,
        "extraction": extracted,
        "independent_verification": checked,
    }


def main():
    from .contracts import Message

    # Caso piloto sintetico, no es un caso del experimento 72.
    turn = Turn(
        user=(
            "Estoy abrumada por tantas tareas y solo tengo "
            "veinte minutos libres al dia."
        ),
        response=(
            "Puedes elegir una sola tarea prioritaria. "
            "Dedica cinco minutos a dividirla en dos pasos "
            "pequenos y diez minutos a realizar el primero. "
            "Si hoy no tienes energia, haz solo el primer paso. "
            "Al final de la semana revisa si te funciono "
            "y ajusta el tiempo."
        ),
        prior_history=(),
    )

    from openai import OpenAI  # Load SDK only for explicitly invoked live pilot.
    client = OpenAI()
    results = {}

    for code in CODES:
        print(f"Evaluando {code}...", flush=True)
        try:
            results[code] = evaluate_indicator(
                client, turn, code
            )
        except Exception as exc:
            results[code] = {
                "indicator": code,
                "technical_status": "BLOCKED",
                "score": None,
                "error": f"{type(exc).__name__}: {exc}",
            }

        print(
            code,
            results[code]["technical_status"],
            flush=True,
        )

    directory = (
        Path("backend/evaluators/pa/reports")
    )
    directory.mkdir(parents=True, exist_ok=True)

    filename = (
        "pa_semantic_pilot_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )

    output = directory / filename
    output.write_text(
        json.dumps(
            {
                "model": MODEL,
                "case_type": "synthetic",
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("REPORTE:", output)


if __name__ == "__main__":
    main()
