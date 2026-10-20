"""Piloto contrastivo real PA4 y PA7.

OpenAI extrae propiedades y otro llamado las verifica.
No se asignan puntuaciones.
"""

import json
from pathlib import Path

from openai import OpenAI

from .official_rubric import indicator_definition
from .semantic_pilot import ask, MODEL


CASES = [
    {
        "id": "PA4_TIME",
        "code": "PA4",
        "user": "Solo tengo veinte minutos libres.",
        "response": (
            "Dedica cinco minutos a organizar las tareas "
            "y diez a realizar la primera."
        ),
        "target": "consideracion de tiempo disponible",
    },
    {
        "id": "PA4_ENERGY",
        "code": "PA4",
        "user": (
            "Solo tengo veinte minutos libres "
            "y algunos dias no tengo energia."
        ),
        "response": (
            "Dedica cinco minutos a organizar las tareas. "
            "Si no tienes energia, realiza solo el primer paso."
        ),
        "target": "consideracion de tiempo y energia",
    },
    {
        "id": "PA7_IMPLICIT",
        "code": "PA7",
        "user": "Estoy abrumada por tantas tareas.",
        "response": (
            "Elige una tarea y dividela en pasos pequenos."
        ),
        "target": "finalidad explicada de la herramienta",
    },
    {
        "id": "PA7_EXPLICIT",
        "code": "PA7",
        "user": "Estoy abrumada por tantas tareas.",
        "response": (
            "Divide una tarea en pasos pequenos. "
            "Asi podras comenzar sin resolver todo de una vez."
        ),
        "target": "finalidad explicada de la herramienta",
    },
]


EXTRACTOR = """
Eres extractor semantico para EvalIA.
No asignes puntuaciones.

Analiza la pregunta oficial y el componente objetivo.
No inventes condiciones adicionales.

Para PA4 distingue las restricciones realmente
consideradas de ajustes futuros hipoteticos.

Para PA7 distingue una finalidad efectivamente
comunicada de una finalidad inferida por el evaluador.
No exijas palabras especificas.

Devuelve JSON:
{
 "value": "present|absent|uncertain",
 "reason": "explicacion",
 "quotes": ["cita textual exacta de la respuesta"]
}
"""


VERIFIER = """
Eres verificador semantico independiente.
No asignes puntuaciones.

Evalua la pregunta oficial, el caso y la afirmacion
del extractor. Puedes rechazarla.

Para PA7 una finalidad inferible no equivale
automaticamente a una finalidad explicada.

Devuelve JSON:
{
 "decision": "supported|unsupported|ambiguous",
 "reason": "explicacion",
 "quotes": ["cita textual exacta de la respuesta"]
}
"""


def check_quotes(answer, response):
    quotes = answer.get("quotes")

    if not isinstance(quotes, list):
        raise ValueError("Lista de citas invalida")

    for quote in quotes:
        if not isinstance(quote, str) or not quote:
            raise ValueError("Cita vacia o invalida")

        if quote not in response:
            raise ValueError(f"Cita no literal: {quote!r}")


def main():
    directory = Path("backend/evaluators/pa/reports")
    directory.mkdir(parents=True, exist_ok=True)

    output = directory / "pa4_pa7_contrastive_real_v1.json"

    if output.exists():
        raise SystemExit(
            "El reporte ya existe; no repetir llamadas."
        )

    client = OpenAI()
    results = {}

    for case in CASES:
        print("Evaluando", case["id"], flush=True)

        payload = {
            "indicator": indicator_definition(case["code"]),
            "current_user": case["user"],
            "current_response": case["response"],
            "target": case["target"],
        }

        extraction = ask(client, EXTRACTOR, payload)
        check_quotes(extraction, case["response"])

        if extraction.get("value") not in (
            "present", "absent", "uncertain"
        ):
            raise ValueError("Valor de extraccion invalido")

        verification = ask(
            client,
            VERIFIER,
            {
                **payload,
                "extraction_to_verify": extraction,
            },
        )

        check_quotes(verification, case["response"])

        if verification.get("decision") not in (
            "supported", "unsupported", "ambiguous"
        ):
            raise ValueError("Decision invalida")

        results[case["id"]] = {
            "indicator": case["code"],
            "target": case["target"],
            "extraction": extraction,
            "verification": verification,
            "technical_status": (
                "VERIFIED"
                if verification["decision"] == "supported"
                else "BLOCKED"
            ),
            "score": None,
        }

        print(
            case["id"],
            results[case["id"]]["technical_status"],
            "|",
            extraction["value"],
            "|",
            verification["decision"],
            flush=True,
        )

    output.write_text(
        json.dumps(
            {
                "model": MODEL,
                "case_type": "contrastive_synthetic",
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nREPORTE:", output)


if __name__ == "__main__":
    main()
