"""PA25: integracion conservadora de AD-05."""

import json
from pathlib import Path

from backend.evaluators.pa.criterion_ad05 import official_criterion

ROOT = Path("backend/evaluators/pa/reports")
OUTPUT = ROOT / "pa25_integrated_ad05.json"


def read(name):
    return json.loads(
        (ROOT / name).read_text(encoding="utf-8-sig")
    )


def valid_quotes(review, response):
    if not isinstance(review, dict):
        return False

    quotes = review.get("quotes")

    return (
        isinstance(review.get("reason"), str)
        and bool(review["reason"].strip())
        and isinstance(quotes, list)
        and bool(quotes)
        and all(
            isinstance(q, str)
            and bool(q.strip())
            and q in response
            for q in quotes
        )
    )


def main():
    if OUTPUT.exists():
        result = read(OUTPUT.name)
        print("PA25 REUTILIZADO:", OUTPUT)
        print("ESTADO:", result["status"])
        print("PUNTUACION:", result["score"])
        return

    pa23 = read("pa23_evidence_acceptance.json")
    pa24 = read("pa24_resolved_indicators.json")
    pa21 = read("pa21_contrastive_ad05.json")
    pa20 = read("pa20_semantic_ad05.json")
    rubric = official_criterion()

    context = pa23["context"]
    response = context["current_response"]

    problems = []

    if context != pa24["context"]:
        problems.append("Contexto PA23/PA24 diferente")

    if context != pa20["context"] and (
        context.get("current_user")
        != pa20["context"].get("current_user")
        or response
        != pa20["context"].get("current_response")
        or context.get("prior_history")
        != pa20["context"].get("prior_history")
    ):
        problems.append("Contexto PA20 diferente")

    if pa21.get("status") != "RECONCILED_FOR_AUDIT":
        problems.append("PA21 no reconciliado")

    if pa21.get("decision") not in ("0", "1", "2", "3"):
        problems.append("Decision ordinal invalida")

    for reviewer in ("extractor", "verifier"):
        review = pa21.get(reviewer)
        if not valid_quotes(review, response):
            problems.append(
                "Evidencia ordinal invalida: " + reviewer
            )
        elif review.get("decision") != pa21.get("decision"):
            problems.append(
                "Discrepancia ordinal: " + reviewer
            )

    indicators = {}

    for number in range(1, 9):
        code = f"PA{number}"

        if code in pa24["results"]:
            item = pa24["results"][code]
            state = item["state"]
            provenance = "PA24_RECONCILED"
        else:
            item = pa23["results"][code]
            state = (
                "SUPPORTED"
                if item["status"] == "PROVENANCE_VALIDATED"
                else "BLOCKED"
            )
            provenance = "PA23_ORIGINAL_VERIFICATION"

        if state not in (
            "SUPPORTED", "NOT_SUPPORTED", "N/A"
        ):
            problems.append(code + " no resuelto")

        indicators[code] = {
            "state": state,
            "provenance": provenance,
            "score": None,
        }

    # El nivel propuesto se conserva como dato auditable.
    # No se transforma automaticamente en puntuacion:
    # falta una comprobacion semantica de consistencia
    # entre las ocho preguntas y el descriptor elegido.

    report = {
        "criterion": "AD-05",
        "official_levels": rubric["levels"],
        "context": context,
        "indicators": indicators,
        "ordinal_proposal": pa21.get("decision"),
        "ordinal_evidence": {
            "extractor": pa21.get("extractor"),
            "verifier": pa21.get("verifier"),
        },
        "status": "BLOCKED",
        "score": None,
        "technical_problems": problems,
        "pending": (
            [
                "Auditoria semantica conjunta de PA1-PA8 "
                "contra descriptor ordinal seleccionado"
            ]
            if not problems else []
        ),
    }

    OUTPUT.write_text(
        json.dumps(
            report, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    print("PA25 CREADO:", OUTPUT)
    print("PROPUESTA:", report["ordinal_proposal"])
    print("ESTADO:", report["status"])
    print("PUNTUACION:", report["score"])

    for code, item in indicators.items():
        print(code, item["state"])

    print("PROBLEMAS TECNICOS:", len(problems))
    for problem in problems:
        print(" -", problem)

    print("OTRAS FAMILIAS: SIN MODIFICACIONES")
    print("LLAMADAS API: 0")


if __name__ == "__main__":
    main()
