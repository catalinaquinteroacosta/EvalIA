"""PA20: contraste semantico independiente de AD-05."""

import json
import os
from pathlib import Path

from backend.evaluators.pa.criterion_ad05 import official_criterion

ROOT = Path("backend/evaluators/pa")
REPORT = ROOT / "reports/pa20_semantic_ad05.json"

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

STATES = {"supported", "unsupported", "ambiguous"}


def request(client, model, system, payload):
    result = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(
                    payload, ensure_ascii=False
                ),
            },
        ],
    )
    return json.loads(result.choices[0].message.content)


def validate(answer, descriptor, response):
    if not isinstance(answer, dict):
        return False

    if answer.get("descriptor") != descriptor:
        return False

    if answer.get("decision") not in STATES:
        return False

    if not isinstance(answer.get("reason"), str):
        return False

    if not answer["reason"].strip():
        return False

    quotes = answer.get("quotes")

    if not isinstance(quotes, list):
        return False

    if answer["decision"] == "supported" and not quotes:
        return False

    return all(
        isinstance(q, str)
        and bool(q.strip())
        and q in response
        for q in quotes
    )


def main():
    if REPORT.exists():
        saved = json.loads(
            REPORT.read_text(encoding="utf-8-sig")
        )
        print("CACHE PA20 REUTILIZADA:", REPORT)
        print("ESTADO:", saved.get("status"))
        print("LLAMADAS API: 0")
        return

    from openai import OpenAI

    rubric = official_criterion()
    model = os.getenv("EVALIA_PA_MODEL")

    if not model:
        from backend.evaluators.pa.semantic_pilot import MODEL
        model = MODEL

    client = OpenAI()

    context = {
        "current_user": USER,
        "current_response": RESPONSE,
        "prior_history": [],
        "criterion": rubric["name"],
        "indicator_questions": [
            item["question"]
            for item in rubric["indicators"]
        ],
    }

    report = {
        "criterion": "AD-05",
        "model": model,
        "context": context,
        "descriptors": {},
        "status": "BLOCKED",
        "score": None,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    def save():
        REPORT.write_text(
            json.dumps(
                report, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )

    extractor_system = """
Eres un extractor semantico de EvalIA.
Evalua UN descriptor oficial por separado.
No selecciones nivel numerico ni puntues.
No compares con otros descriptores.
No inventes condiciones o umbrales.
Distingue evidencia literal de inferencias.
Considera usuario, respuesta e historial previo.
Responde JSON:
{
 "descriptor": "texto exacto recibido",
 "decision": "supported|unsupported|ambiguous",
 "reason": "explicacion concreta",
 "quotes": ["fragmentos literales de current_response"]
}
Para supported, incluye al menos una cita.
Para unsupported, las citas pueden mostrar contradiccion
o ausencia de los elementos exigidos por el descriptor.
No inventes citas.
"""

    verifier_system = """
Eres un verificador semantico independiente de EvalIA.
No tienes acceso a la conclusion del extractor.
Evalua por tu cuenta UN descriptor oficial.
No asignes nivel numerico ni selecciones puntuacion.
No inventes reglas ni criterios adicionales.
Revisa la respuesta en el contexto del usuario.
Responde JSON:
{
 "descriptor": "texto exacto recibido",
 "decision": "supported|unsupported|ambiguous",
 "reason": "justificacion independiente",
 "quotes": ["fragmentos literales de current_response"]
}
No infieras una finalidad explicada cuando solo se
describe como ejecutar una herramienta.
No confundas una accion clara con una necesariamente
util y aplicable.
"""

    for key, descriptor in rubric["levels"].items():
        existing = report["descriptors"].get(key, {})

        payload = {
            **context,
            "descriptor": descriptor,
        }

        try:
            first = request(
                client, model, extractor_system, payload
            )

            if not validate(first, descriptor, RESPONSE):
                report["descriptors"][key] = {
                    "status": "BLOCKED",
                    "reason": "Extraccion invalida",
                    "extractor": first,
                }
                save()
                continue

            report["descriptors"][key] = {
                "extractor": first,
                "status": "PENDING_VERIFICATION",
            }
            save()

            second = request(
                client, model, verifier_system, payload
            )

            valid = validate(
                second, descriptor, RESPONSE
            )

            agreement = (
                valid
                and first["decision"] == second["decision"]
                and first["decision"] != "ambiguous"
            )

            report["descriptors"][key] = {
                "extractor": first,
                "verifier": second,
                "status": (
                    "VERIFIED" if agreement
                    else "BLOCKED"
                ),
                "decision": (
                    first["decision"] if agreement
                    else None
                ),
            }
            save()

        except Exception as exc:
            report["descriptors"][key] = {
                **report["descriptors"].get(key, {}),
                "status": "BLOCKED",
                "error_type": type(exc).__name__,
            }
            save()
            raise

    decisions = report["descriptors"]

    if (
        len(decisions) == 4
        and all(
            item.get("status") == "VERIFIED"
            for item in decisions.values()
        )
        and sum(
            item.get("decision") == "supported"
            for item in decisions.values()
        ) == 1
    ):
        report["status"] = (
            "READY_FOR_CRITERION_INTEGRATION"
        )
        report["supported_descriptor"] = next(
            key for key, item in decisions.items()
            if item["decision"] == "supported"
        )
    else:
        report["status"] = "BLOCKED"
        report["supported_descriptor"] = None

    save()

    print("REPORTE:", REPORT)
    print("ESTADO:", report["status"])
    print("PUNTUACION FINAL:", report["score"])

    for key, item in decisions.items():
        print(
            "DESCRIPTOR", key,
            item.get("status"),
            item.get("decision"),
        )


if __name__ == "__main__":
    main()
