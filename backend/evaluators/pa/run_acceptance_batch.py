"""Lote PA: extraccion y verificacion independiente."""

import hashlib
import json
from pathlib import Path

from openai import OpenAI

from backend.evaluators.pa.contracts import (
    Message, Turn
)
from backend.evaluators.pa.semantic_pilot import (
    MODEL, evaluate_indicator
)
from backend.evaluators.pa.official_rubric import (
    load_official_pa
)

ROOT = Path("backend/evaluators/pa")
FIXTURE = ROOT / "fixtures/pa_acceptance_batch.json"
REPORTS = ROOT / "reports"
CACHE = REPORTS / "pa_acceptance_cache"
CODES = [f"PA{i}" for i in range(1, 9)]


def fingerprint(case, code):
    payload = {
        "case": case,
        "indicator": code,
        "model": MODEL,
        "rubric": load_official_pa(),
        "engine": Path(
            "backend/evaluators/pa/semantic_pilot.py"
        ).read_text(encoding="utf-8-sig"),
    }

    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def save(path, data):
    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(
            data, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    temporary.replace(path)


def main():
    data = json.loads(
        FIXTURE.read_text(encoding="utf-8-sig")
    )

    cases = data["cases"]

    if len(cases) != 8:
        raise ValueError("Se esperaban ocho casos.")

    REPORTS.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    client = OpenAI()
    summary = []

    for case in cases:
        case_id = case["id"]

        turn = Turn(
            user=case["user"],
            response=case["response"],
            prior_history=tuple(
                Message(
                    role=message["role"],
                    text=message["text"]
                )
                for message in case["prior_history"]
            ),
        )

        results = {}

        print("\nCASO:", case_id, flush=True)

        for code in CODES:
            key = fingerprint(case, code)
            cache_file = CACHE / (key + ".json")

            if cache_file.exists():
                result = json.loads(
                    cache_file.read_text(
                        encoding="utf-8-sig"
                    )
                )
                origin = "CACHE"
            else:
                try:
                    result = evaluate_indicator(
                        client, turn, code
                    )
                except Exception as exc:
                    result = {
                        "indicator": code,
                        "technical_status": "BLOCKED",
                        "score": None,
                        "error": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }

                # Solo cachear resultados con ambas
                # revisiones completas, no errores.
                if (
                    "extraction" in result
                    and "independent_verification" in result
                ):
                    save(cache_file, result)

                origin = "API"

            results[code] = result

            print(
                code,
                result["technical_status"],
                origin,
                flush=True,
            )

        report = {
            "case_id": case_id,
            "model": MODEL,
            "context": {
                "current_user": case["user"],
                "current_response": case["response"],
                "prior_history": case["prior_history"],
            },
            "results": results,
            "criterion_score": None,
            "criterion_status": "PENDING_ORDINAL_REVIEW",
        }

        save(
            REPORTS / (
                "pa_acceptance_" + case_id + ".json"
            ),
            report,
        )

        verified = sum(
            item["technical_status"]
            == "VERIFIED_EXTRACTION"
            for item in results.values()
        )

        summary.append({
            "case": case_id,
            "verified_extractions": verified,
            "blocked": 8 - verified,
        })

    save(
        REPORTS / "pa_acceptance_summary.json",
        {
            "model": MODEL,
            "cases": summary,
            "criterion_scores_assigned": 0,
        },
    )

    print("\nLOTE COMPLETADO")
    for item in summary:
        print(
            item["case"],
            "VERIFICADOS:",
            item["verified_extractions"],
            "BLOCKED:",
            item["blocked"],
        )

    print("PUNTUACIONES INVENTADAS: 0")
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
