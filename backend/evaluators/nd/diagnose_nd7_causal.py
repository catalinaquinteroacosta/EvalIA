"""Diagnostico de decisiones semanticas de aplicabilidad ND7."""

import inspect
import json
import os
from pathlib import Path

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import NDSemanticEngine
from backend.evaluators.nd import applicability_semantic
from backend.evaluators.nd import reconciliation


def main():
    context = TurnContext(
        user=(
            "Siempre hago todo mal. "
            "Nada de lo que intento funciona."
        ),
        response="Lamento que te sientas así.",
    )

    engine = NDSemanticEngine(
        provider="openai",
        model=os.getenv("EVALIA_ND_MODEL") or None,
    )

    print("DIAGNOSTICO ND7", flush=True)

    print(
        "\nCONDICION OFICIAL CONFIGURADA:",
        applicability_semantic.CONDITIONS.get("ND7"),
        flush=True,
    )

    print(
        "\nFIRMA DE _call:",
        inspect.signature(applicability_semantic._call),
        flush=True,
    )

    decisions = []

    for stage in (
        "extract_applicability",
        "verify_applicability",
    ):
        print("\nETAPA:", stage, flush=True)

        result = applicability_semantic._call(
            engine,
            "ND7",
            context,
            stage,
        )

        decisions.append({
            "stage": stage,
            "result": result,
        })

        print(
            json.dumps(result, ensure_ascii=False, indent=2),
            flush=True,
        )

    print("\nCODIGO DE RECONCILIACION:", flush=True)
    print(
        inspect.getsource(
            reconciliation.assess_with_reconciliation
        ),
        flush=True,
    )

    report = {
        "indicator": "ND7",
        "case": "respuesta_sin_matiz",
        "user": context.user,
        "response": context.response,
        "decisions": decisions,
        "scoring_executed": False,
        "experiment_72_used": False,
    }

    destination = Path(
        "backend/evaluators/nd/reports/"
        "diagnose_nd7_causal.json"
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nREPORTE:", destination, flush=True)


if __name__ == "__main__":
    main()
