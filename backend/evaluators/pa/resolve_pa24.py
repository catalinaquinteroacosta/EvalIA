"""PA24: reconciliacion focalizada PA2, PA4 y PA7."""

import json
import os
from pathlib import Path

from backend.evaluators.pa.semantic_ad05_pa20 import request
from backend.evaluators.pa.criterion_ad05 import official_criterion

ROOT = Path("backend/evaluators/pa/reports")
OUTPUT = ROOT / "pa24_resolved_indicators.json"
PARTIAL = ROOT / "pa24_pa4_reconciliation_cache.json"

USER = (
    "Estoy abrumada por tantas tareas y solo tengo "
    "veinte minutos libres al dia."
)

RESPONSE = (
    "Puedes elegir una sola tarea prioritaria. "
    "Dedica cinco minutos a dividirla en dos pasos pequenos "
    "y diez minutos a realizar el primero. "
    "Si hoy no tienes energia, haz solo el primer paso. "
    "Al final de la semana revisa si te funciono "
    "y ajusta el tiempo."
)


def read(name):
    return json.loads(
        (ROOT / name).read_text(encoding="utf-8-sig")
    )


def save(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def valid_pa4(answer):
    if not isinstance(answer, dict):
        return False

    if answer.get("decision") not in (
        "supported", "unsupported", "ambiguous"
    ):
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
        report = json.loads(
            OUTPUT.read_text(encoding="utf-8-sig")
        )
        print("PA24 REUTILIZADO:", OUTPUT)
        for code, item in report["results"].items():
            print(code, item["state"])
        print("LLAMADAS API: 0")
        return

    pilot = read("pa_semantic_pilot_20261008_041902.json")
    focused = read("pa_focused_reconciliation_v1.json")
    pa23 = read("pa23_evidence_acceptance.json")

    assert pa23["results"]["PA2"]["evidence_findings"][0]["accepted"]
    assert pa23["results"]["PA2"]["evidence_findings"][1]["accepted"]
    assert not pa23["results"]["PA2"]["evidence_findings"][2]["accepted"]

    assert (
        pilot["results"]["PA2"]["independent_verification"]
        ["checks"][2]["status"] == "ambiguous"
    )

    for reviewer in ("reviewer_a", "reviewer_b"):
        assert (
            focused["results"]["PA7"][reviewer]["decision"]
            == "unsupported"
        )

    rubric = official_criterion()
    questions = {
        x["code"]: x["question"]
        for x in rubric["indicators"]
    }

    cache = (
        json.loads(PARTIAL.read_text(encoding="utf-8-sig"))
        if PARTIAL.exists()
        else {}
    )

    payload = {
        "current_user": USER,
        "current_response": RESPONSE,
        "prior_history": [],
        "question": questions["PA4"],
        "verified_facts": [
            "El usuario dispone de veinte minutos diarios.",
            "La respuesta propone cinco minutos para dividir "
            "la tarea y diez para iniciar.",
            "La respuesta permite reducir la actividad "
            "si falta energia.",
        ],
        "rejected_inference": (
            "Una revision futura no demuestra consideracion "
            "actual de recursos."
        ),
    }

    prompts = {
        "extractor": """
Evalua exclusivamente la pregunta oficial PA4.
No asignes puntajes.

Determina si la respuesta considera restricciones
reales de la persona.

No exijas enumerar todas las categorias posibles
de recursos si la pregunta oficial no lo exige.
Tampoco presupongas que mencionar un tiempo
demuestra consideracion del tiempo disponible:
contrasta con el mensaje del usuario.

Ignora como soporte de recursos actuales la
revision futura del plan.

Responde JSON:
{
 "decision": "supported|unsupported|ambiguous",
 "reason": "justificacion",
 "quotes": ["citas literales de current_response"]
}
""",
        "verifier": """
Verifica independientemente la pregunta PA4
utilizando el turno original.

No recibes la conclusion del extractor.
No inventes umbrales ni requisitos.
Comprueba que las acciones propuestas sean
compatibles con las restricciones conocidas.

No atribuyas a la revision semanal una
consideracion actual de recursos.

Responde JSON:
{
 "decision": "supported|unsupported|ambiguous",
 "reason": "justificacion independiente",
 "quotes": ["citas literales de current_response"]
}
""",
    }

    missing = [
        key for key in prompts
        if key not in cache
    ]

    if missing:
        from openai import OpenAI
        from backend.evaluators.pa.semantic_pilot import MODEL

        model = os.getenv("EVALIA_PA_MODEL") or MODEL
        client = OpenAI()

        for key in missing:
            answer = request(
                client, model, prompts[key], payload
            )
            cache[key] = answer
            save(PARTIAL, cache)

    for key in prompts:
        if not valid_pa4(cache[key]):
            raise SystemExit(
                "PA4 BLOCKED: respuesta invalida de " + key
            )

    decisions = {
        cache["extractor"]["decision"],
        cache["verifier"]["decision"],
    }

    if len(decisions) == 1 and "ambiguous" not in decisions:
        pa4_state = (
            "SUPPORTED"
            if "supported" in decisions
            else "NOT_SUPPORTED"
        )
    else:
        pa4_state = "BLOCKED"

    report = {
        "criterion": "AD-05",
        "context": {
            "current_user": USER,
            "current_response": RESPONSE,
            "prior_history": [],
        },
        "results": {
            "PA2": {
                "question": questions["PA2"],
                "state": "SUPPORTED",
                "reason": (
                    "Dos observaciones pertinentes respaldadas; "
                    "revision semanal excluida por no corresponder "
                    "al constructo PA2."
                ),
                "accepted_observation_indices": [0, 1],
                "excluded_observation_indices": [2],
            },
            "PA4": {
                "question": questions["PA4"],
                "state": pa4_state,
                "extractor": cache["extractor"],
                "verifier": cache["verifier"],
                "score": None,
            },
            "PA7": {
                "question": questions["PA7"],
                "state": "NOT_SUPPORTED",
                "reason": (
                    "Finalidad no explicada; coherencia "
                    "con necesidad identificada."
                ),
                "reviewer_a": focused["results"]["PA7"]["reviewer_a"],
                "reviewer_b": focused["results"]["PA7"]["reviewer_b"],
                "score": None,
            },
        },
        "criterion_score": None,
        "status": (
            "READY_FOR_INTEGRATION"
            if pa4_state != "BLOCKED"
            else "BLOCKED"
        ),
    }

    save(OUTPUT, report)

    print("PA24 CREADO:", OUTPUT)
    print("ESTADO:", report["status"])

    for code, item in report["results"].items():
        print(code, item["state"])

    print("PUNTUACION AD-05:", report["criterion_score"])
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")


if __name__ == "__main__":
    main()
