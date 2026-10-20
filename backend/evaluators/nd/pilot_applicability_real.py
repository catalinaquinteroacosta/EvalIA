"""Piloto real de aplicabilidad ND7, sin puntuacion."""

import json
import os
from pathlib import Path

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import NDSemanticEngine
from backend.evaluators.nd.reconciliation import (
    assess_with_reconciliation,
)


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

    print("PILOTO REAL DE APLICABILIDAD ND7", flush=True)

    result = assess_with_reconciliation(
        engine,
        "ND7",
        context,
    )

    report = {
        "indicator": "ND7",
        "case": "nuevo_nd7_absolutismo_01",
        "applicability": {
            "status": result.status,
            "reason": result.reason,
        },
        "expected_for_manual_review": "APPLICABLE",
        "scoring_executed": False,
        "experiment_72_used": False,
    }

    destination = Path(
        "backend/evaluators/nd/reports/"
        "pilot_nd7_applicability.json"
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(report, ensure_ascii=False, indent=2),
        flush=True,
    )

    if result.status != "APPLICABLE":
        print(
            "ATENCION: revisar aplicabilidad antes de puntuar.",
            flush=True,
        )

    print("REPORTE:", destination, flush=True)


if __name__ == "__main__":
    main()
