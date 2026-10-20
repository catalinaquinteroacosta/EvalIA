"""PA26: cierre auditable del piloto AD-05."""

import json
from pathlib import Path

from backend.evaluators.pa.criterion_ad05 import official_criterion

ROOT = Path("backend/evaluators/pa/reports")
OUTPUT = ROOT / "pa26_final_pilot.json"

EXPECTED = {
    "PA1": "SUPPORTED",
    "PA2": "SUPPORTED",
    "PA3": "SUPPORTED",
    "PA4": "SUPPORTED",
    "PA5": "SUPPORTED",
    "PA6": "SUPPORTED",
    "PA7": "NOT_SUPPORTED",
    "PA8": "SUPPORTED",
}


def read(name):
    return json.loads(
        (ROOT / name).read_text(encoding="utf-8-sig")
    )


def evaluate(pa25, pa24, pa21, pa20, rubric):
    problems = []

    context = pa25["context"]
    response = context["current_response"]

    for field in (
        "current_user", "current_response", "prior_history"
    ):
        if context.get(field) != pa24["context"].get(field):
            problems.append("PA24 contexto: " + field)

        if context.get(field) != pa20["context"].get(field):
            problems.append("PA20 contexto: " + field)

    actual = {
        code: item["state"]
        for code, item in pa25["indicators"].items()
    }

    if actual != EXPECTED:
        problems.append("Estados PA1-PA8 no coinciden")

    for code in ("PA2", "PA4", "PA7"):
        if (
            pa24["results"][code]["state"]
            != actual.get(code)
        ):
            problems.append("Discrepancia PA24: " + code)

    if pa25.get("technical_problems"):
        problems.append("PA25 reporta problemas tecnicos")

    if pa21.get("status") != "RECONCILED_FOR_AUDIT":
        problems.append("PA21 no reconciliado")

    decision = pa21.get("decision")

    if decision not in rubric["levels"]:
        problems.append("Descriptor no oficial")

    if pa25.get("ordinal_proposal") != decision:
        problems.append("Propuesta ordinal inconsistente")

    for reviewer in ("extractor", "verifier"):
        item = pa21.get(reviewer, {})

        if item.get("decision") != decision:
            problems.append(
                "Desacuerdo ordinal: " + reviewer
            )

        quotes = item.get("quotes")

        if (
            not isinstance(quotes, list)
            or not quotes
            or any(
                not isinstance(q, str)
                or not q.strip()
                or q not in response
                for q in quotes
            )
        ):
            problems.append(
                "Citas ordinales invalidas: " + reviewer
            )

        if not str(item.get("reason", "")).strip():
            problems.append(
                "Falta justificacion: " + reviewer
            )

    if problems:
        return {
            "status": "BLOCKED",
            "score": None,
            "problems": problems,
        }

    return {
        "status": "PILOT_SCORED",
        "score": int(decision),
        "descriptor": rubric["levels"][decision],
        "problems": [],
    }


def main():
    if OUTPUT.exists():
        print("PA26 YA EXISTE:", OUTPUT)
        print("No sobrescribir el expediente.")
        return

    pa25 = read("pa25_integrated_ad05.json")
    pa24 = read("pa24_resolved_indicators.json")
    pa21 = read("pa21_contrastive_ad05.json")
    pa20 = read("pa20_semantic_ad05.json")
    rubric = official_criterion()

    result = evaluate(
        pa25, pa24, pa21, pa20, rubric
    )

    # Prueba negativa: el desacuerdo debe bloquear.
    altered = json.loads(json.dumps(pa21))
    altered["verifier"]["decision"] = (
        "2" if pa21["decision"] == "3" else "3"
    )

    negative = evaluate(
        pa25, pa24, altered, pa20, rubric
    )

    assert negative["status"] == "BLOCKED"
    assert negative["score"] is None

    report = {
        "criterion": "AD-05",
        "context": pa25["context"],
        "indicators": pa25["indicators"],
        "result": result,
        "negative_test": "PASSED",
        "scope": "ONE_PILOT_ONLY",
        "general_engine_validated": False,
    }

    OUTPUT.write_text(
        json.dumps(
            report, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    print("PA26 CREADO:", OUTPUT)
    print("ESTADO:", result["status"])
    print("PUNTUACION:", result["score"])
    print("PRUEBA NEGATIVA: PASSED")

    for problem in result["problems"]:
        print("PROBLEMA:", problem)

    print("OTRAS FAMILIAS: SIN MODIFICACIONES")
    print("LLAMADAS API: 0")


if __name__ == "__main__":
    main()
