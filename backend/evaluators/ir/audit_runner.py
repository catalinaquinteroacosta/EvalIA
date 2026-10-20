"""Auditoría IR independiente a partir de resultados existentes."""

import json
import sys
from pathlib import Path

from .core.contracts import Context, Message
from .core.semantic import INDICATORS
from .core.audit import audit_indicator, reconcile_findings


def audit_saved(ctx, saved, auditor=audit_indicator):
    if saved.get("family") != "IR":
        raise ValueError("Reporte de otra familia")

    previous = saved.get("indicators")
    if not isinstance(previous, dict):
        raise ValueError("Reporte IR inválido")

    results = {}

    for indicator in INDICATORS:
        item = previous.get(indicator)

        if not isinstance(item, dict):
            raise ValueError("Falta " + indicator)

        claims = item.get("claims")
        if not isinstance(claims, list):
            raise ValueError("Afirmaciones inválidas")

        # Se reutilizan los resultados verificados.
        # No se repiten extracción ni verificación.
        audit = auditor(ctx, indicator)

        merged = reconcile_findings(claims, audit)

        results[indicator] = {
            "status": merged["status"],
            "claims": claims,
            "audit": audit,
            "missing_components": merged["missing_components"],
            "contradictions": merged["contradictions"],
            "requires_reconciliation": merged[
                "requires_reconciliation"
            ],
            "score": None,
        }

    return {
        "family": "IR",
        "stage": "independent_audit_unscored",
        "indicators": results,
    }


def load_context(path):
    with open(path, encoding="utf-8-sig") as f:
        raw = json.load(f)

    return Context(
        user=raw["user"],
        response=raw["response"],
        prior_history=tuple(
            Message(**m)
            for m in raw.get("prior_history", [])
        ),
    )


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "Uso: python -m backend.evaluators.ir.audit_runner "
            "caso.json reporte_previo.json salida.json"
        )

    case_path, previous_path, output_path = map(
        Path, sys.argv[1:]
    )

    if output_path.exists():
        raise FileExistsError(
            "El reporte de auditoría ya existe"
        )

    ctx = load_context(case_path)

    with previous_path.open(
        encoding="utf-8-sig"
    ) as f:
        saved = json.load(f)

    result = audit_saved(ctx, saved)

    # Creación exclusiva: no sobrescribir auditorías.
    with output_path.open("x", encoding="utf-8") as f:
        json.dump(
            result, f, ensure_ascii=False, indent=2
        )

    print("AUDITORÍA IR COMPLETADA")
    for indicator, item in result["indicators"].items():
        print(
            indicator,
            item["status"],
            "faltantes=",
            len(item["missing_components"]),
            "contradicciones=",
            len(item["contradictions"]),
        )


if __name__ == "__main__":
    main()