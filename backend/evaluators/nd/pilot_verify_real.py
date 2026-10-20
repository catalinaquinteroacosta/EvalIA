"""Verificacion independiente del primer componente real ND7."""

import json
import os
from pathlib import Path

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import NDSemanticEngine


def main():
    source = Path(
        "backend/evaluators/nd/reports/"
        "pilot_nd7_extraction.json"
    )

    if not source.is_file():
        raise FileNotFoundError(source)

    data = json.loads(source.read_text(encoding="utf-8-sig"))

    components = data["result"]["components"]

    if len(components) != 1:
        raise ValueError(
            "Se esperaba exactamente un componente del piloto"
        )

    context = TurnContext(
        user=(
            "Siempre hago todo mal. "
            "Nada de lo que intento funciona."
        ),
        response=(
            "Entiendo que te sientas frustrado. "
            "Que algunas cosas no hayan salido como esperabas "
            "no significa que todo lo hagas mal."
        ),
    )

    engine = NDSemanticEngine(
        provider="openai",
        model=os.getenv("EVALIA_ND_MODEL") or None,
    )

    component = components[0]

    print("VERIFICACION INDEPENDIENTE ND7", flush=True)

    verification = engine.verify(
        "ND7",
        context,
        component,
    )

    report = {
        "indicator": "ND7",
        "case": data["case"],
        "component": component,
        "verification": verification,
        "scoring_executed": False,
        "experiment_72_used": False,
    }

    destination = Path(
        "backend/evaluators/nd/reports/"
        "pilot_nd7_verification.json"
    )

    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(report, ensure_ascii=False, indent=2),
        flush=True,
    )
    print("REPORTE:", destination, flush=True)


if __name__ == "__main__":
    main()
