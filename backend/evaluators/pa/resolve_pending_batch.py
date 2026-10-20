"""Resolver pendientes semanticos PA sin modificar motores."""

import hashlib
import json
from pathlib import Path

from openai import OpenAI
from backend.evaluators.pa.semantic_pilot import MODEL, ask
from backend.evaluators.pa.official_rubric import (
    indicator_definition, load_official_pa
)

ROOT = Path("backend/evaluators/pa/reports")
SOURCE = ROOT / "pa_acceptance_reconciled_corrected.json"
QUEUE = ROOT / "pa_acceptance_reconciliation_queue.json"
CACHE = ROOT / "pa_pending_cache"
OUTPUT = ROOT / "pa_pending_resolved.json"

SYSTEM = """
Eres un auditor semantico independiente de EvalIA.

Analiza cada pregunta oficial usando el contexto del caso.
No asignes puntuaciones ni niveles.
No inventes requisitos ni interpretes los indicadores
como una lista de condiciones adicionales.

Distingue:
SUPPORTED: la pregunta esta respaldada.
NOT_SUPPORTED: la pregunta no se cumple.
N/A: la condicion oficial no ocurre.
BLOCKED: no puede decidirse con respaldo suficiente.

Una explicacion insuficiente puede justificar
NOT_SUPPORTED sin implicar incertidumbre.

No exijas pasos adicionales para acciones simples.
No exijas explicar como caminar si la accion es
directamente comprensible.
No exijas mencionar todos los recursos cuando solo
algunos sean pertinentes.
No conviertas finalidad implicita en explicada.

Devuelve JSON:
{
 "results": [
  {
   "id": "identificador exacto",
   "state": "SUPPORTED|NOT_SUPPORTED|N/A|BLOCKED",
   "reason": "justificacion semantica",
   "quotes": ["citas exactas de current_response"],
   "applicability_reason": "explicacion"
  }
 ]
}
"""


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def validate(item, review):
    if not isinstance(review, dict):
        return False

    state = review.get("state")
    quotes = review.get("quotes")
    response = item["context"]["current_response"]

    return (
        state in {
            "SUPPORTED", "NOT_SUPPORTED", "N/A", "BLOCKED"
        }
        and isinstance(quotes, list)
        and all(
            isinstance(q, str)
            and bool(q.strip())
            and q in response
            for q in quotes
        )
        and isinstance(review.get("reason"), str)
        and bool(review["reason"].strip())
        and isinstance(
            review.get("applicability_reason"), str
        )
        and bool(review["applicability_reason"].strip())
    )


def main():
    previous = read(SOURCE)["results"]
    queue = read(QUEUE)["items"]

    indexed = {
        x["case_id"] + ":" + x["indicator"]: x
        for x in queue
    }

    pending = [
        key for key, item in previous.items()
        if item["state"] == "BLOCKED"
        and key != "PA_CONCRETE:PA3"
    ]

    CACHE.mkdir(parents=True, exist_ok=True)

    payload = {
        "rubric": load_official_pa(),
        "items": [
            {
                **indexed[key],
                "id": key,
                "official_indicator": indicator_definition(
                    indexed[key]["indicator"]
                ),
                "prior_reviewers": {
                    "a": previous[key].get("reviewer_a"),
                    "b": previous[key].get("reviewer_b"),
                },
            }
            for key in pending
        ],
    }

    client = OpenAI()
    reviews = []

    for reviewer in ("A", "B"):
        request = {
            "model": MODEL,
            "system": SYSTEM,
            "payload": payload,
            "reviewer": reviewer,
        }

        key = hashlib.sha256(
            json.dumps(
                request,
                ensure_ascii=False,
                sort_keys=True
            ).encode("utf-8")
        ).hexdigest()

        path = CACHE / (key + ".json")

        if path.exists():
            result = read(path)
            print("REVISOR", reviewer, "CACHE")
        else:
            result = ask(client, SYSTEM, payload)
            save(path, result)
            print("REVISOR", reviewer, "API")

        reviews.append({
            item.get("id"): item
            for item in result.get("results", [])
            if isinstance(item, dict)
        })

    results = dict(previous)

    for identity in pending:
        item = indexed[identity]
        a = reviews[0].get(identity)
        b = reviews[1].get(identity)

        if (
            validate(item, a)
            and validate(item, b)
            and a["state"] == b["state"]
            and a["state"] != "BLOCKED"
        ):
            state = a["state"]
        else:
            state = "BLOCKED"

        results[identity] = {
            "state": state,
            "reviewer_a": a,
            "reviewer_b": b,
            "score": None,
        }

        print(identity, state, flush=True)

    # La extraccion tecnica recuperada no demuestra
    # por si sola el cumplimiento del indicador.
    technical = "PA_CONCRETE:PA3"
    results[technical] = previous[technical]

    save(
        OUTPUT,
        {
            "criterion": "AD-05",
            "results": results,
            "ordinal_score": None,
        },
    )

    print("\nREPORTE:", OUTPUT)
    print(
        "RESUELTOS:",
        sum(v["state"] != "BLOCKED" for v in results.values())
    )
    print(
        "BLOCKED:",
        sum(v["state"] == "BLOCKED" for v in results.values())
    )
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
