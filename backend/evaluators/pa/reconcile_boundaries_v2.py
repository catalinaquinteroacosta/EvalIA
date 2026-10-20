"""Reconciliacion focalizada PA4/PA7; sin scoring."""

import json
from pathlib import Path

from openai import OpenAI

from .official_rubric import indicator_definition
from .semantic_pilot import ask, MODEL


DIR = Path("backend/evaluators/pa/reports")
SOURCE = DIR / "pa_property_audit_20261008_041902.json"
CONTRAST = DIR / "pa4_pa7_contrastive_real_v1.json"
OUTPUT = DIR / "pa_boundary_reconciliation_v2.json"

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

TARGETS = (("PA4", 2), ("PA7", 0))

SYSTEM = """
Eres un auditor semantico independiente de EvalIA.
No asignes puntuaciones.

Evalua la propiedad disputada frente a la pregunta
oficial, al usuario y a la respuesta literal.

PA4: no confundas una revision futura con la
consideracion actual de recursos y restricciones.
Una propiedad puede mezclar afirmaciones respaldadas
y no respaldadas.

PA7: distingue finalidad comunicada efectivamente
de finalidad inferida por el evaluador.
No exijas palabras o estructuras especificas.

Los casos contrastivos son referencias para distinguir
conceptos, no respuestas obligatorias.

Devuelve exclusivamente JSON:
{
 "decision": "supported|unsupported|ambiguous",
 "corrected_value": "present|absent|uncertain",
 "reason": "justificacion",
 "supporting_quotes": ["cita exacta"]
}
"""


def validate(answer):
    decision = answer.get("decision")
    value = answer.get("corrected_value")

    if decision not in (
        "supported", "unsupported", "ambiguous"
    ):
        raise ValueError("Decision invalida")

    if value not in ("present", "absent", "uncertain"):
        raise ValueError("Valor invalido")

    if not isinstance(answer.get("reason"), str):
        raise ValueError("Justificacion invalida")

    if not answer["reason"].strip():
        raise ValueError("Justificacion vacia")

    quotes = answer.get("supporting_quotes")

    if not isinstance(quotes, list):
        raise ValueError("Citas invalidas")

    for quote in quotes:
        if not isinstance(quote, str) or not quote:
            raise ValueError("Cita invalida")
        if quote not in RESPONSE:
            raise ValueError("Cita no literal")


def main():
    if OUTPUT.exists():
        state = json.loads(
            OUTPUT.read_text(encoding="utf-8-sig")
        )
        if state.get("model") != MODEL:
            raise RuntimeError(
                "Modelo distinto: no reutilizar resultados"
            )
    else:
        state = {
            "model": MODEL,
            "results": {},
            "score": None,
        }

    audit = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )
    contrast = json.loads(
        CONTRAST.read_text(encoding="utf-8-sig")
    )

    client = OpenAI()

    for code, index in TARGETS:
        key = f"{code}_{index}"
        entry = state["results"].setdefault(key, {})

        prop = audit["results"][code][
            "properties"
        ]["properties"][index]

        related = {
            k: v
            for k, v in contrast["results"].items()
            if v["indicator"] == code
        }

        payload = {
            "indicator": indicator_definition(code),
            "current_user": USER,
            "current_response": RESPONSE,
            "disputed_property": prop,
            "contrastive_cases": related,
        }

        for reviewer in ("reviewer_a", "reviewer_b"):
            if reviewer in entry:
                validate(entry[reviewer])
                print(key, reviewer, "REUTILIZADO")
                continue

            print(key, reviewer, "LLAMADA REAL", flush=True)

            answer = ask(client, SYSTEM, payload)
            validate(answer)
            entry[reviewer] = answer

            OUTPUT.write_text(
                json.dumps(
                    state,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        a = entry["reviewer_a"]
        b = entry["reviewer_b"]

        if (
            a["corrected_value"] == b["corrected_value"]
            and a["decision"] == b["decision"]
            and a["decision"] != "ambiguous"
        ):
            entry["status"] = "AGREEMENT_REQUIRES_AUDIT"
        else:
            entry["status"] = "BLOCKED"

        OUTPUT.write_text(
            json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            key,
            entry["status"],
            a["corrected_value"],
            b["corrected_value"],
        )

    print("\nREPORTE:", OUTPUT)
    print("PUNTUACIONES: ninguna")


if __name__ == "__main__":
    main()
