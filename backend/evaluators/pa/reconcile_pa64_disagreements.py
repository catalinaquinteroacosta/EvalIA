"""Reconciliacion focalizada PA, sin modificar clasificaciones."""

import json
import hashlib
from pathlib import Path

from openai import OpenAI

from backend.evaluators.pa.semantic_pilot import MODEL, ask
from backend.evaluators.pa.official_rubric import indicator_definition
from backend.evaluators.pa.evidence_lineage_pa import validate_evidence

ROOT = Path("backend/evaluators/pa/reports")
CACHE = ROOT / "pa64_reconciliation_cache"
OUTPUT = ROOT / "pa64_reconciliation_review.json"

SYSTEM = """
Responde exclusivamente con un objeto JSON valido.

Eres un verificador semantico independiente de EvalIA.
No ves ni debes inferir decisiones de otros revisores.

Responde solamente segun la pregunta oficial del indicador.
No inventes umbrales, condiciones ni exigencias adicionales.

Estados: SUPPORTED, NOT_SUPPORTED, N/A, BLOCKED.
N/A solamente si la pregunta oficial es condicional y
la condicion no ocurre.

Distingue ausencia verificable de verdadera incertidumbre.

Devuelve:
{
 "results": [
  {
   "id": "ID exacto",
   "state": "SUPPORTED|NOT_SUPPORTED|N/A|BLOCKED",
   "reason": "explicacion",
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

No puntues el criterio AD-05.
"""


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def main():
    previous = read(ROOT / "pa64_semantic_classification.json")
    summary = read(ROOT / "pa_acceptance_summary.json")

    contexts = {}

    for case in summary["cases"]:
        case_id = case["case"]
        report = read(ROOT / f"pa_acceptance_{case_id}.json")
        contexts[case_id] = report["context"]

    selected = {
        identity
        for identity, result in previous["results"].items()
        if result["state"] == "BLOCKED"
    }

    selected.add("PA_LIMITED:PA7")

    items = []

    for identity in sorted(selected):
        case_id, code = identity.rsplit(":", 1)

        items.append({
            "id": identity,
            "indicator": code,
            "official_question": indicator_definition(code),
            "context": contexts[case_id],
        })

    CACHE.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    output = {}

    # Lotes pequenos, independientes y cacheados.
    for start in range(0, len(items), 4):
        batch = items[start:start + 4]

        payload = {
            "criterion": "AD-05",
            "items": batch,
        }

        raw = json.dumps(
            {
                "model": MODEL,
                "system": SYSTEM,
                "payload": payload,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

        key = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

        cache_path = CACHE / f"{key}.json"

        if cache_path.exists():
            response = read(cache_path)
            print("LOTE", start // 4 + 1, "CACHE")
        else:
            response = ask(client, SYSTEM, payload)
            write(cache_path, response)
            print("LOTE", start // 4 + 1, "API")

        indexed = {}

        for record in response.get("results", []):
            if not isinstance(record, dict):
                continue
            identity = record.get("id")
            if identity in indexed:
                indexed[identity] = None
            else:
                indexed[identity] = record

        for item in batch:
            identity = item["id"]
            record = indexed.get(identity)

            valid = (
                isinstance(record, dict)
                and record.get("state") in {
                    "SUPPORTED", "NOT_SUPPORTED", "N/A", "BLOCKED"
                }
                and isinstance(record.get("reason"), str)
                and bool(record["reason"].strip())
                and isinstance(record.get("evidence"), list)
                and all(
                    validate_evidence(item["context"], evidence)
                    for evidence in record["evidence"]
                )
            )

            output[identity] = {
                "previous_state": previous["results"][identity]["state"],
                "new_review": record,
                "evidence_valid": bool(valid),
                "automatic_change": False,
            }

            state = (
                record.get("state")
                if valid else "INVALID_REVIEW"
            )

            print(identity, state, flush=True)

    write(
        OUTPUT,
        {
            "criterion": "AD-05",
            "reviewed": len(items),
            "results": output,
            "original_classifications_modified": 0,
            "ordinal_score": None,
        },
    )

    print("\\nREVISIONES:", len(items))
    print("INFORME:", OUTPUT)
    print("CLASIFICACIONES ORIGINALES MODIFICADAS: 0")
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
