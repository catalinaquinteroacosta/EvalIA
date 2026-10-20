"""Reconciliacion focalizada de bloqueos PA."""

import hashlib
import json
from pathlib import Path

from openai import OpenAI

from backend.evaluators.pa.contracts import Message, Turn
from backend.evaluators.pa.semantic_pilot import (
    MODEL, ask, evaluate_indicator
)
from backend.evaluators.pa.official_rubric import (
    indicator_definition, load_official_pa
)

ROOT = Path("backend/evaluators/pa")
REPORTS = ROOT / "reports"
QUEUE = REPORTS / "pa_acceptance_reconciliation_queue.json"
CACHE = REPORTS / "pa_acceptance_reconciliation_cache"
OUTPUT = REPORTS / "pa_acceptance_reconciled.json"

ALLOWED = {"SUPPORTED", "NOT_SUPPORTED", "N/A", "BLOCKED"}


def save(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def make_turn(context):
    return Turn(
        user=context["current_user"],
        response=context["current_response"],
        prior_history=tuple(
            Message(role=m["role"], text=m["text"])
            for m in context["prior_history"]
        ),
    )


def key_for(payload):
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main():
    queue = json.loads(
        QUEUE.read_text(encoding="utf-8-sig")
    )["items"]

    CACHE.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    results = {}

    semantic = [
        item for item in queue
        if item["kind"] == "SEMANTIC_RECONCILIATION"
    ]

    technical = [
        item for item in queue
        if item["kind"] == "TECHNICAL_ERROR"
    ]

    # Reintento tecnico aislado.
    for item in technical:
        identity = item["case_id"] + ":" + item["indicator"]
        turn = make_turn(item["context"])

        try:
            result = evaluate_indicator(
                client, turn, item["indicator"]
            )
            results[identity] = {
                "state": "BLOCKED",
                "technical_retry": result,
                "reason": (
                    "Reintento tecnico realizado; "
                    "requiere decision semantica."
                ),
            }
        except Exception as exc:
            results[identity] = {
                "state": "BLOCKED",
                "error": f"{type(exc).__name__}: {exc}",
            }

        print("REINTENTO:", identity, flush=True)

    payload = {
        "criterion": "AD-05",
        "rubric": load_official_pa(),
        "items": [
            {
                **item,
                "official_indicator": indicator_definition(
                    item["indicator"]
                ),
            }
            for item in semantic
        ],
    }

    system = """
Eres un auditor semantico independiente de EvalIA.
Analiza los casos uno por uno, usando solo la pregunta
oficial y el contexto temporal disponible.

No asignes niveles, puntuaciones ni porcentajes.
No inventes requisitos de la rubrica.

Para cada caso devuelve:
{
 "id": "CASE:PAx",
 "state": "SUPPORTED|NOT_SUPPORTED|N/A|BLOCKED",
 "reason": "explicacion especifica",
 "quotes": ["citas literales de current_response"],
 "applicability_reason": "justificacion"
}

SUPPORTED: la pregunta oficial esta respaldada.
NOT_SUPPORTED: se puede establecer que no se cumple.
N/A: la condicion oficial de aplicabilidad no ocurre.
BLOCKED: incertidumbre o evidencia contradictoria.

No confundas ausencia verificable con incertidumbre.
No conviertas un indicador general en N/A por falta
de informacion.

Devuelve JSON {"results": [ ... ]}.
Incluye exactamente un resultado por caso.
"""

    reviews = []

    for reviewer in ("A", "B"):
        request = {
            "model": MODEL,
            "system": system,
            "payload": payload,
            "reviewer": reviewer,
        }

        cache_file = CACHE / (
            key_for(request) + ".json"
        )

        if cache_file.exists():
            review = json.loads(
                cache_file.read_text(encoding="utf-8-sig")
            )
            print("REVISOR:", reviewer, "CACHE")
        else:
            review = ask(client, system, payload)
            save(cache_file, review)
            print("REVISOR:", reviewer, "API")

        reviews.append(review)

    identities = {
        item["case_id"] + ":" + item["indicator"]: item
        for item in semantic
    }

    indexed = []

    for review in reviews:
        entries = {}

        for record in review.get("results", []):
            identity = record.get("id")

            if identity in entries:
                continue

            entries[identity] = record

        indexed.append(entries)

    for identity, item in identities.items():
        a = indexed[0].get(identity, {})
        b = indexed[1].get(identity, {})

        response = item["context"]["current_response"]

        def valid(record):
            state = record.get("state")
            quotes = record.get("quotes")

            if state not in ALLOWED:
                return False

            if not isinstance(quotes, list):
                return False

            if any(
                not isinstance(q, str)
                or not q.strip()
                or q not in response
                for q in quotes
            ):
                return False

            return bool(
                str(record.get("reason", "")).strip()
            )

        if (
            valid(a)
            and valid(b)
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

    save(
        OUTPUT,
        {
            "criterion": "AD-05",
            "results": results,
            "ordinal_score": None,
        },
    )

    print("\nRECONCILIACION:", OUTPUT)
    print(
        "RESUELTOS:",
        sum(x["state"] != "BLOCKED" for x in results.values())
    )
    print(
        "BLOCKED:",
        sum(x["state"] == "BLOCKED" for x in results.values())
    )
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
