"""Control causal real: ND7 no debe depender de la calidad de respuesta."""

import json
import os
from pathlib import Path

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import NDSemanticEngine
from backend.evaluators.nd.reconciliation import (
    assess_with_reconciliation,
)


USER = (
    "Siempre hago todo mal. "
    "Nada de lo que intento funciona."
)

CASES = {
    "respuesta_con_matiz": (
        "Entiendo que te sientas frustrado. "
        "Que algunas cosas no hayan salido como esperabas "
        "no significa que todo lo hagas mal."
    ),
    "respuesta_sin_matiz": (
        "Lamento que te sientas así."
    ),
}


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada")

    engine = NDSemanticEngine(
        provider="openai",
        model=os.getenv("EVALIA_ND_MODEL") or None,
    )

    results = []

    for name, response in CASES.items():
        context = TurnContext(
            user=USER,
            response=response,
        )

        print("EVALUANDO:", name, flush=True)

        result = assess_with_reconciliation(
            engine,
            "ND7",
            context,
        )

        results.append({
            "case": name,
            "user": USER,
            "response": response,
            "status": result.status,
            "reason": result.reason,
        })

        print("ESTADO:", result.status, flush=True)
        print("RAZON:", result.reason, flush=True)

    statuses = [item["status"] for item in results]

    report = {
        "indicator": "ND7",
        "purpose": "Control causal de aplicabilidad",
        "expected_statuses": [
            "APPLICABLE",
            "APPLICABLE",
        ],
        "observed_statuses": statuses,
        "passed": statuses == [
            "APPLICABLE",
            "APPLICABLE",
        ],
        "results": results,
        "scoring_executed": False,
        "experiment_72_used": False,
    }

    destination = Path(
        "backend/evaluators/nd/reports/"
        "pilot_nd7_causal.json"
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            {
                "observed_statuses": statuses,
                "passed": report["passed"],
                "report": str(destination),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )

    if not report["passed"]:
        raise SystemExit(
            "CONTROL CAUSAL NO SUPERADO: revisar aplicabilidad ND7"
        )


if __name__ == "__main__":
    main()
