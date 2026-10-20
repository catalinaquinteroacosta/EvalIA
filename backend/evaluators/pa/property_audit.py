"""Auditoria semantica de propiedades PA, sin puntuacion."""
import json
from pathlib import Path

from openai import OpenAI

from .contracts import CODES
from .official_rubric import indicator_definition
from .semantic_pilot import ask, MODEL


DIRECTORY = Path("backend/evaluators/pa/reports")
SOURCE = DIRECTORY / "pa_consolidated_20261008_041902.json"
OUTPUT = DIRECTORY / "pa_property_audit_20261008_041902.json"

USER = (
    "Estoy abrumada por tantas tareas y solo tengo "
    "veinte minutos libres al dia."
)

RESPONSE = (
    "Puedes elegir una sola tarea prioritaria. "
    "Dedica cinco minutos a dividirla en dos pasos "
    "pequenos y diez minutos a realizar el primero. "
    "Si hoy no tienes energia, haz solo el primer paso. "
    "Al final de la semana revisa si te funciono "
    "y ajusta el tiempo."
)


def main():
    if OUTPUT.exists():
        raise SystemExit(
            "Ya existe auditoria. No repetir llamadas."
        )

    source = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )

    client = OpenAI()
    results = {}

    for code in CODES:
        previous = source["results"][code]

        if previous["technical_status"] not in (
            "VERIFIED_EXTRACTION",
            "RECONCILED_EXTRACTION",
        ):
            results[code] = {
                "status": "BLOCKED",
                "reason": "Extraccion no validada",
            }
            continue

        indicator = indicator_definition(code)

        accepted = [
            previous["extraction"]["observations"][index]
            for index in previous[
                "accepted_observation_indices"
            ]
        ]

        payload = {
            "indicator": indicator,
            "user": USER,
            "response": RESPONSE,
            "accepted_observations": accepted,
        }

        print(f"Propiedades {code}...", flush=True)

        try:
            properties = ask(
                client,
                """
Analiza la pregunta oficial del indicador PA.
No asignes puntuaciones ni niveles.

Identifica los hechos semanticos necesarios para
determinar si la respuesta cumple la pregunta.

No inventes condiciones adicionales.
No confundas coherencia con explicacion explicita.
No confundas ausencia de evidencia con evidencia
de incumplimiento.

Devuelve JSON:
{
 "applicability": "applicable|not_applicable|uncertain",
 "properties": [
   {
     "name": "nombre descriptivo",
     "value": "present|absent|uncertain",
     "reason": "justificacion",
     "quotes": ["fragmento literal de la respuesta"]
   }
 ],
 "material_omissions": [
   "aspectos de la pregunta no demostrados"
 ]
}

Cada cita debe existir literalmente en la respuesta.
Si un hecho esta ausente, quotes puede estar vacio.
No atribuyas al usuario restricciones no expresadas.
""",
                payload,
            )

            verification = ask(
                client,
                """
Verifica independientemente las propiedades extraidas.
No asignes puntuaciones.

Revisa la pregunta oficial, la respuesta y cada
propiedad. Comprueba si la propiedad y su valor
estan sustentados, si hay omisiones materiales y
si las citas son pertinentes.

Devuelve JSON:
{
 "applicability": "applicable|not_applicable|uncertain",
 "checks": [
   {
     "property_index": 0,
     "status": "supported|unsupported|ambiguous",
     "reason": "explicacion independiente"
   }
 ],
 "coverage": "complete|incomplete|uncertain",
 "coverage_reason": "explicacion"
}

Incluye exactamente una verificacion por propiedad.
""",
                {
                    "indicator": indicator,
                    "user": USER,
                    "response": RESPONSE,
                    "properties_to_verify": properties,
                },
            )

            results[code] = {
                "status": "PENDING_VALIDATION",
                "properties": properties,
                "verification": verification,
                "score": None,
            }

        except Exception as exc:
            results[code] = {
                "status": "BLOCKED",
                "error": f"{type(exc).__name__}: {exc}",
                "score": None,
            }

    OUTPUT.write_text(
        json.dumps(
            {
                "model": MODEL,
                "source": str(SOURCE),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n===== AUDITORIA DE PROPIEDADES =====")

    for code, result in results.items():
        print(code, result["status"])

    print("REPORTE:", OUTPUT)


if __name__ == "__main__":
    main()
