"""Consolidación conservadora IR. Sin puntuación ni llamadas API."""

from copy import deepcopy


def consolidate(audit_report, reconciliation_report):
    if audit_report.get("family") != "IR":
        raise ValueError("Familia de auditoría inválida")

    if reconciliation_report.get("family") != "IR":
        raise ValueError("Familia de reconciliación inválida")

    audited = audit_report.get("indicators")
    decisions = reconciliation_report.get("results")

    if not isinstance(audited, dict):
        raise ValueError("Indicadores inválidos")

    if not isinstance(decisions, dict):
        raise ValueError("Reconciliaciones inválidas")

    output = {}

    for indicator, item in audited.items():
        result = deepcopy(item)
        rows = decisions.get(indicator, [])

        if not isinstance(rows, list):
            raise ValueError("Decisiones inválidas")

        unresolved = [
            row for row in rows
            if row.get("verdict") == "ambiguous"
        ]

        # Las decisiones individuales no reemplazan
        # automáticamente los hallazgos originales.
        # Se conserva la trazabilidad íntegra.
        result["reconciliation"] = deepcopy(rows)
        result["score"] = None

        if unresolved:
            result["status"] = "BLOCKED"
            result["requires_reconciliation"] = True

        elif result.get("status") == "BLOCKED":
            # Un BLOCKED anterior no se elimina
            # sin demostrar que su causa fue resuelta.
            result["requires_reconciliation"] = True

        else:
            result["status"] = "REVIEWED"
            result["requires_reconciliation"] = False

        output[indicator] = result

    return {
        "family": "IR",
        "stage": "consolidated_unscored",
        "indicators": output,
    }