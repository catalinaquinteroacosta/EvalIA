"""Integridad de reconciliación IR. No puntúa."""

VALID_VERDICTS = {
    "supported", "unsupported", "ambiguous"
}


def validate_reconciliation_rows(rows, expected_ids):
    """Valida cobertura y estructura de decisiones."""
    if not isinstance(rows, list):
        raise ValueError("Las decisiones deben ser lista")

    if not isinstance(expected_ids, (list, tuple)):
        raise ValueError("Los IDs esperados deben ser secuencia")

    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("IDs esperados duplicados")

    seen = set()

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Decisión inválida")

        identifier = row.get("id")
        verdict = row.get("verdict")
        reason = row.get("reason")

        if identifier not in expected_ids:
            raise ValueError("ID desconocido")

        if identifier in seen:
            raise ValueError("Decisión duplicada")

        if verdict not in VALID_VERDICTS:
            raise ValueError("Veredicto inválido")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Justificación vacía")

        seen.add(identifier)

    missing = set(expected_ids) - seen

    if missing:
        raise ValueError(
            "Decisiones pendientes: " + ", ".join(sorted(missing))
        )

    return True


def assess_integrity(indicator_result, expected_ids=()):
    """Estado técnico de integridad, no calificación."""
    rows = indicator_result.get("reconciliation", [])

    try:
        validate_reconciliation_rows(rows, expected_ids)
    except (ValueError, TypeError) as exc:
        return {
            "status": "BLOCKED",
            "reason": str(exc),
            "score": None,
        }

    if any(
        row["verdict"] == "ambiguous"
        for row in rows
    ):
        return {
            "status": "BLOCKED",
            "reason": "Persisten decisiones ambiguas",
            "score": None,
        }

    if indicator_result.get("status") == "BLOCKED":
        return {
            "status": "BLOCKED",
            "reason": "Bloqueo anterior no resuelto",
            "score": None,
        }

    return {
        "status": "INTEGRITY_CHECKED",
        "reason": (
            "Decisiones estructuralmente completas; "
            "sin validación semántica final"
        ),
        "score": None,
    }