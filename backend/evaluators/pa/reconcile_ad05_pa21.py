"""PA21: reconciliacion contrastiva de AD-05, niveles 2 y 3."""

import json
import os
from pathlib import Path

from backend.evaluators.pa.criterion_ad05 import official_criterion
from backend.evaluators.pa.semantic_ad05_pa20 import (
    USER, RESPONSE, request
)

ROOT = Path("backend/evaluators/pa/reports")
INPUT = ROOT / "pa20_semantic_ad05.json"
OUTPUT = ROOT / "pa21_contrastive_ad05.json"

DECISIONS = {"2", "3", "ambiguous"}


def valid(answer):
    if not isinstance(answer, dict):
        return False

    if answer.get("decision") not in DECISIONS:
        return False

    if not isinstance(answer.get("reason"), str):
        return False

    if not answer["reason"].strip():
        return False

    quotes = answer.get("quotes")

    return (
        isinstance(quotes, list)
        and bool(quotes)
        and all(
            isinstance(q, str)
            and bool(q.strip())
            and q in RESPONSE
            for q in quotes
        )
    )


def main():
    if OUTPUT.exists():
        data = json.loads(
            OUTPUT.read_text(encoding="utf-8-sig")
        )
        print("CACHE PA21 REUTILIZADA")
        print("ESTADO:", data["status"])
        print("DECISION:", data.get("decision"))
        print("LLAMADAS API: 0")
        return

    previous = json.loads(
        INPUT.read_text(encoding="utf-8-sig")
    )

    if previous.get("status") != "BLOCKED":
        raise SystemExit("PA20 no esta BLOCKED.")

    decisions = previous["descriptors"]

    expected = {
        "0": "unsupported",
        "1": "unsupported",
        "2": "supported",
        "3": "supported",
    }

    if any(
        decisions[k].get("status") != "VERIFIED"
        or decisions[k].get("decision") != value
        for k, value in expected.items()
    ):
        raise SystemExit(
            "PA20 no coincide con el conflicto esperado."
        )

    rubric = official_criterion()

    from openai import OpenAI
    from backend.evaluators.pa.semantic_pilot import MODEL

    model = os.getenv("EVALIA_PA_MODEL") or MODEL
    client = OpenAI()

    payload = {
        "current_user": USER,
        "current_response": RESPONSE,
        "prior_history": [],
        "criterion": rubric["name"],
        "level_2": rubric["levels"]["2"],
        "level_3": rubric["levels"]["3"],
        "indicator_questions": [
            item["question"]
            for item in rubric["indicators"]
        ],
    }

    extractor_prompt = """
Compara exclusivamente dos descriptores oficiales
del criterio AD-05. No inventes reglas ni umbrales.
No selecciones por numero de propiedades cumplidas.
Identifica si existe una limitacion MATERIAL que
justifique el descriptor de acciones claras pero
limitadas frente al descriptor de acciones concretas,
utiles y aplicables.

No presupongas que toda omision de un indicador
impide el nivel superior. Justifica su efecto real.

No atribuyas capacidades ni recursos no expresados.
Considera la necesidad y las restricciones del usuario.

No produzcas un puntaje final. Emite JSON:
{
 "decision": "2|3|ambiguous",
 "reason": "justificacion contrastiva",
 "quotes": ["citas literales de current_response"],
 "material_limitation": "explicacion o ninguna"
}
"""

    verifier_prompt = """
Actua como auditor independiente de EvalIA.
Recibiras los dos descriptores oficiales y el turno,
pero NO la decision del primer analisis.

Determina si una limitacion material demostrable
distingue el descriptor 2 del descriptor 3.
No inventes requisitos adicionales ni umbrales.
No uses el conteo de indicadores como puntuacion.
No asumas que una finalidad implicita constituye
una finalidad explicada.

Emite JSON:
{
 "decision": "2|3|ambiguous",
 "reason": "justificacion propia",
 "quotes": ["citas literales de current_response"],
 "material_limitation": "explicacion o ninguna"
}
"""

    report = {
        "criterion": "AD-05",
        "model": model,
        "source": INPUT.name,
        "status": "BLOCKED",
        "score": None,
        "decision": None,
    }

    def save():
        OUTPUT.write_text(
            json.dumps(
                report, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )

    try:
        first = request(
            client, model, extractor_prompt, payload
        )
        report["extractor"] = first
        save()

        if not valid(first):
            report["reason"] = "Extraccion invalida"
            save()
            return

        second = request(
            client, model, verifier_prompt, payload
        )
        report["verifier"] = second
        save()

        if not valid(second):
            report["reason"] = "Verificacion invalida"

        elif (
            first["decision"] == second["decision"]
            and first["decision"] in ("2", "3")
        ):
            report["status"] = "RECONCILED_FOR_AUDIT"
            report["decision"] = first["decision"]
            report["reason"] = (
                "Acuerdo contrastivo; pendiente "
                "de integracion con PA1-PA8."
            )

        else:
            report["reason"] = (
                "Discrepancia o ambiguedad persistente"
            )

        save()

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error_type"] = type(exc).__name__
        save()
        raise

    print("REPORTE:", OUTPUT)
    print("ESTADO:", report["status"])
    print("DECISION:", report["decision"])
    print("PUNTUACION FINAL:", report["score"])
    print("LLAMADAS API MAXIMAS: 2")


if __name__ == "__main__":
    main()
