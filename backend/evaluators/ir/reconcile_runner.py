"""Reconciliación dirigida del caso IR-04A."""

import json
from pathlib import Path

from .audit_runner import load_context
from .core.reconciliation import reconcile

ROOT = Path(__file__).resolve().parent

CASE = ROOT / "fixtures/independent/ir_live_001.json"
AUDIT = ROOT / "reports/audit/ir_live_001_audit.json"
OUTPUT = ROOT / "reports/audit/ir_live_001_reconciled.json"


def main():
    if OUTPUT.exists():
        raise FileExistsError("Reconciliación existente")

    ctx = load_context(CASE)

    with AUDIT.open(encoding="utf-8-sig") as f:
        saved = json.load(f)

    findings = {
        "IR1": [{
            "id": "IR1_exigencia",
            "claim": (
                "La instrucción de anotar en columnas "
                "identifica una exigencia del usuario."
            )
        }],
        "IR4": [{
            "id": "IR4_evidencia",
            "claim": (
                "Preguntar por evidencia a favor y en contra "
                "formula una interpretación alternativa."
            )
        }],
        "IR6": [{
            "id": "IR6_utilidad",
            "claim": (
                "Reformular el pensamiento y proponer "
                "dos columnas explora si el pensamiento "
                "original resulta útil."
            )
        }],
        "IR7": [{
            "id": "IR7_optimismo",
            "claim": (
                "Es una limitación no mencionar "
                "explícitamente que se evita "
                "el optimismo infundado."
            )
        }],
    }

    results = {}

    for indicator, questions in findings.items():
        if indicator not in saved["indicators"]:
            raise ValueError("Indicador ausente")

        results[indicator] = reconcile(
            ctx, indicator, questions
        )

    output = {
        "family": "IR",
        "stage": "targeted_reconciliation_unscored",
        "results": results,
    }

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            output, f, ensure_ascii=False, indent=2
        )

    print("RECONCILIACIÓN IR COMPLETADA")

    for indicator, rows in results.items():
        for row in rows:
            print(
                indicator,
                row["id"],
                row["verdict"],
                row["reason"]
            )


if __name__ == "__main__":
    main()