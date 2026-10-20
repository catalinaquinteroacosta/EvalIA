"""Clasificacion independiente de PA1-PA8."""

import hashlib
import json
from pathlib import Path

from openai import OpenAI

from backend.evaluators.pa.semantic_pilot import MODEL, ask
from backend.evaluators.pa.official_rubric import (
    indicator_definition, load_official_pa
)
from backend.evaluators.pa.evidence_lineage_pa import (
    validate_evidence
)

REPORTS = Path("backend/evaluators/pa/reports")
CACHE = REPORTS / "pa64_classification_cache"
OUTPUT = REPORTS / "pa64_semantic_classification.json"

SYSTEM = """
Responde exclusivamente con un objeto JSON valido.
EvalIA: clasificador semantico independiente.

Evalua cada indicador estrictamente segun su pregunta
oficial. No inventes requisitos ni umbrales.

No asignes puntuaciones ordinales.

Devuelve exactamente un registro por ID:

{
 "results": [
  {
   "id": "ID exacto",
   "state": "SUPPORTED|NOT_SUPPORTED|N/A|BLOCKED",
   "reason": "justificacion",
   "applicability_reason": "justificacion",
   "evidence": [
    {
     "source": "user|response|history",
     "quote": "cita literal",
     "history_index": null
    }
   ]
  }
 ]
}

SUPPORTED: cumple la pregunta oficial.
NOT_SUPPORTED: no cumple y puede justificarse.
N/A: la condicion de aplicabilidad no ocurre.
BLOCKED: evidencia insuficiente o contradictoria.

No confundas incumplimiento con incertidumbre.
No conviertas indicadores generales en N/A.
No exijas explicar procedimientos evidentes si
la pregunta oficial no lo requiere.
No supongas restricciones que el usuario no menciona.
Para historial usa solo mensajes anteriores.
"""


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def digest(data):
    return hashlib.sha256(
        json.dumps(
            data, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
    ).hexdigest()


def validate(item, record):
    if not isinstance(record, dict):
        return False

    if record.get("state") not in {
        "SUPPORTED", "NOT_SUPPORTED", "N/A", "BLOCKED"
    }:
        return False

    if not isinstance(record.get("reason"), str):
        return False

    if not record["reason"].strip():
        return False

    evidence = record.get("evidence")

    if not isinstance(evidence, list):
        return False

    return all(
        validate_evidence(item["context"], e)
        for e in evidence
    )


def main():
    summary = load(
        REPORTS / "pa_acceptance_summary.json"
    )

    gate = load(
        REPORTS / "pa64_evidence_gate.json"
    )

    if gate["total"] != 64:
        raise RuntimeError("El lote no contiene 64 pares")

    cases = {}

    for entry in summary["cases"]:
        case_id = entry["case"]

        report = load(
            REPORTS / f"pa_acceptance_{case_id}.json"
        )

        cases[case_id] = report["context"]

    items = []

    for row in gate["results"]:
        case_id = row["case"]
        code = row["indicator"]

        if row["evidence_gate"] not in {
            "PASSED",
            "EXTRACTION_VALID_REVIEW_PENDING",
        }:
            raise RuntimeError(
                "Evidencia no valida: "
                + case_id + ":" + code
            )

        items.append({
            "id": case_id + ":" + code,
            "indicator": code,
            "official_question": indicator_definition(code),
            "context": cases[case_id],
        })

    CACHE.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    reviews = [{}, {}]

    # Ocho lotes de ocho indicadores: dos revisiones
    # independientes por lote, con cache persistente.
    for start in range(0, len(items), 8):
        batch = items[start:start + 8]

        payload = {
            "criterion": "AD-05",
            "official_rubric": load_official_pa(),
            "items": batch,
        }

        expected_ids = {item["id"] for item in batch}

        for reviewer_index, reviewer in enumerate(("A", "B")):
            request = {
                "model": MODEL,
                "system": SYSTEM,
                "payload": payload,
                "reviewer": reviewer,
            }

            path = CACHE / (digest(request) + ".json")

            if path.exists():
                response = load(path)
                print("LOTE", start // 8 + 1,
                      "REVISOR", reviewer, "CACHE",
                      flush=True)
            else:
                response = ask(client, SYSTEM, payload)
                save(path, response)
                print("LOTE", start // 8 + 1,
                      "REVISOR", reviewer, "API",
                      flush=True)

            records = response.get("results", [])

            if not isinstance(records, list):
                records = []

            indexed = {}

            for record in records:
                if not isinstance(record, dict):
                    continue

                identity = record.get("id")

                if identity not in expected_ids:
                    continue

                if identity in indexed:
                    indexed[identity] = None
                else:
                    indexed[identity] = record

            reviews[reviewer_index].update(indexed)

    results = {}

    for item in items:
        identity = item["id"]
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
        sum(
            r["state"] != "BLOCKED"
            for r in results.values()
        )
    )
    print(
        "BLOCKED:",
        sum(
            r["state"] == "BLOCKED"
            for r in results.values()
        )
    )
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
