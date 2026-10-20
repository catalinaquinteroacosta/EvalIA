"""Reconciliacion focalizada PA2; no modifica el piloto original."""
import json
from pathlib import Path

from openai import OpenAI

from .contracts import Turn
from .official_rubric import indicator_definition
from .semantic_pilot import MODEL, ask


REPORT = Path(
    "backend/evaluators/pa/reports/"
    "pa_semantic_pilot_20261008_041902.json"
)


def main():
    data = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    result = data["results"]["PA2"]

    extracted = result["extraction"]
    checked = result["independent_verification"]

    if result["technical_status"] != "BLOCKED":
        raise ValueError("PA2 no esta bloqueado")

    disputed = [
        check for check in checked["checks"]
        if check["status"] != "supported"
    ]

    if not disputed:
        raise ValueError("No hay componentes por reconciliar")

    # Contexto exacto del piloto, sin historial posterior.
    turn = Turn(
        user=(
            "Estoy abrumada por tantas tareas y solo tengo "
            "veinte minutos libres al dia."
        ),
        response=(
            "Puedes elegir una sola tarea prioritaria. "
            "Dedica cinco minutos a dividirla en dos pasos "
            "pequenos y diez minutos a realizar el primero. "
            "Si hoy no tienes energia, haz solo el primer paso. "
            "Al final de la semana revisa si te funciono "
            "y ajusta el tiempo."
        ),
    )

    decisions = []

    for check in disputed:
        index = check["observation_index"]
        observation = extracted["observations"][index]

        answer = ask(
            OpenAI(),
            """
Eres un reconciliador semantico independiente.
No asignes puntuaciones.

La pregunta oficial PA2 es:
"Cuando la acción es compleja, ¿la organiza en
pasos pequeños y realizables?"

Examina exclusivamente la observacion disputada.
Decide si es:
- supported: evidencia pertinente y sustentada para PA2.
- irrelevant: afirmacion sustentada, pero ajena a PA2.
- unsupported: afirmacion no sustentada por el contexto.
- ambiguous: no se puede resolver con certeza.

No conviertas una observacion irrelevante en evidencia
favorable. No reinterpretes la rubrica.

Devuelve JSON:
{
 "decision": "supported|irrelevant|unsupported|ambiguous",
 "reason": "justificacion concreta"
}
""",
            {
                "indicator": indicator_definition("PA2"),
                "user": turn.user,
                "response": turn.response,
                "observation": observation,
                "previous_verification": check,
            },
        )

        decisions.append({
            "observation_index": index,
            "original_check": check,
            "reconciliation": answer,
        })

    allowed = {
        "supported", "irrelevant",
        "unsupported", "ambiguous"
    }

    for item in decisions:
        decision = item["reconciliation"].get("decision")
        if decision not in allowed:
            raise ValueError(
                f"Decision desconocida: {decision}"
            )
        if not item["reconciliation"].get("reason", "").strip():
            raise ValueError("Reconciliacion sin justificacion")

    output = REPORT.with_name(
        "pa2_reconciliation_20261008_041902.json"
    )

    if output.exists():
        raise FileExistsError(
            "La reconciliacion ya existe; no repetir llamadas."
        )

    output.write_text(
        json.dumps({
            "indicator": "PA2",
            "model": MODEL,
            "original_report": str(REPORT),
            "decisions": decisions,
            "score": None,
            "technical_status": "RECONCILIATION_REVIEW",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(
        decisions, ensure_ascii=False, indent=2
    ))
    print("REPORTE:", output)


if __name__ == "__main__":
    main()
