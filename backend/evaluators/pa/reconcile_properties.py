"""Reconciliacion focalizada de propiedades PA4 y PA7."""
import json
from pathlib import Path

from openai import OpenAI

from .official_rubric import indicator_definition
from .semantic_pilot import ask, MODEL


DIRECTORY = Path("backend/evaluators/pa/reports")
SOURCE = DIRECTORY / "pa_scoring_matrix_20261008_041902.json"
OUTPUT = DIRECTORY / "pa_property_reconciliation_20261008_041902.json"

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

TARGETS = {
    "PA4": [2],
    "PA7": [0],
}


def main():
    if OUTPUT.exists():
        raise SystemExit(
            "Ya existe reconciliacion. No repetir llamadas."
        )

    source = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    client = OpenAI()
    results = {}

    for code, indices in TARGETS.items():
        item = source["results"][code]
        properties = item["properties"]
        decisions = []

        for index in indices:
            prop = properties[index]

            print(
                f"Reconciliando {code} propiedad {index}...",
                flush=True,
            )

            answer = ask(
                client,
                """
Eres un reconciliador semantico independiente.
No asignes puntuaciones.

Analiza exclusivamente la pregunta oficial y
la propiedad disputada.

Distingue cuidadosamente:
- una finalidad coherente de una finalidad explicada;
- una posibilidad futura de ajuste de una restriccion
  real identificada;
- evidencia literal de inferencias no demostradas.

No agregues requisitos nuevos a la rubrica.

Devuelve JSON:
{
 "decision": "supported|unsupported|ambiguous",
 "corrected_value": "present|absent|uncertain",
 "reason": "justificacion precisa",
 "supporting_quotes": ["cita textual exacta"]
}

Si una propiedad esta formulada incorrectamente,
declara unsupported. No inventes citas.
""",
                {
                    "indicator": indicator_definition(code),
                    "current_user": USER,
                    "current_response": RESPONSE,
                    "property_to_reconcile": prop,
                },
            )

            if answer.get("decision") not in (
                "supported", "unsupported", "ambiguous"
            ):
                raise ValueError(
                    f"Decision invalida en {code}: {answer}"
                )

            if answer.get("corrected_value") not in (
                "present", "absent", "uncertain"
            ):
                raise ValueError(
                    f"Valor invalido en {code}: {answer}"
                )

            if not answer.get("reason", "").strip():
                raise ValueError(
                    f"Justificacion ausente en {code}"
                )

            quotes = answer.get("supporting_quotes", [])

            if not isinstance(quotes, list):
                raise ValueError("Citas mal formadas")

            for quote in quotes:
                if (
                    not isinstance(quote, str)
                    or not quote
                    or quote not in RESPONSE
                ):
                    raise ValueError(
                        f"Cita no literal en {code}"
                    )

            decisions.append({
                "property_index": index,
                "original_property": prop,
                "reconciliation": answer,
            })

        results[code] = decisions

    OUTPUT.write_text(
        json.dumps(
            {
                "model": MODEL,
                "source": str(SOURCE),
                "results": results,
                "score": None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n===== RECONCILIACION DE PROPIEDADES =====")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("\nREPORTE:", OUTPUT)


if __name__ == "__main__":
    main()
