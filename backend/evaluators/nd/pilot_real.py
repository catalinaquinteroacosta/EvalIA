"""Piloto ND: una extraccion real, sin scoring."""

import json
import os
from pathlib import Path

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import NDSemanticEngine


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada")

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

    print("PILOTO ND7 - EXTRACCION REAL", flush=True)
    print("No se ejecutara scoring.", flush=True)

    try:
        result = engine.extract("ND7", context)
    except Exception as exc:
        print(
            "ERROR:",
            type(exc).__name__,
            str(exc)[:1200],
            flush=True,
        )
        raise SystemExit(1)

    output = {
        "indicator": "ND7",
        "case": "nuevo_nd7_absolutismo_01",
        "result": result,
        "scoring_executed": False,
        "experiment_72_used": False,
    }

    destination = Path(
        "backend/evaluators/nd/reports/"
        "pilot_nd7_extraction.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(output, ensure_ascii=False, indent=2),
        flush=True,
    )
    print("REPORTE:", destination, flush=True)


if __name__ == "__main__":
    main()
