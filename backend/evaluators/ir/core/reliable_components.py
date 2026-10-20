"""Extraccion IR con reintento estricto de contrato."""

from .component_engine import (
    extract_components,
    verify_components,
)


RETRYABLE_ERRORS = (
    "cita no literal",
    "fuente invalida",
    "componente positivo sin evidencia de respuesta",
    "evidencia invalida",
    "numero de componentes incorrecto",
    "componente fuera de orden",
    "extraccion de componentes invalida",
    "verificacion invalida",
    "cobertura de verificacion incompleta",
    "verificacion desalineada",
)


def normalize_error(message):
    import unicodedata

    normalized = unicodedata.normalize(
        "NFKD", message
    )

    normalized = "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    ).casefold()

    return normalized.replace("?", "u") if (
        "n?mero de componentes incorrecto" in normalized
    ) else normalized



def evaluate_reliably(ctx, code, max_attempts=2):
    if max_attempts < 1 or max_attempts > 3:
        raise ValueError("Numero de intentos no permitido")

    errors = []

    for attempt in range(1, max_attempts + 1):
        try:
            extracted = extract_components(ctx, code)
            verified = verify_components(
                ctx, code, extracted
            )

            return {
                "status": (
                    "BLOCKED"
                    if any(
                        row["status"] == "BLOCKED"
                        for row in verified
                    )
                    else "VERIFIED"
                ),
                "attempts": attempt,
                "errors": errors,
                "components": verified,
                "score": None,
            }

        except ValueError as exc:
            message = str(exc)

            if not any(
                marker in normalize_error(message)
                for marker in RETRYABLE_ERRORS
            ):
                raise

            errors.append({
                "attempt": attempt,
                "error_type": "semantic_contract",
                "detail": message,
            })

    return {
        "status": "BLOCKED",
        "attempts": max_attempts,
        "errors": errors,
        "components": [],
        "score": None,
        "reason": "No se obtuvo un contrato semantico valido",
    }
