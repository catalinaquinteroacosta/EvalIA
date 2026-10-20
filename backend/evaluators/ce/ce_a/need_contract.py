"""Contrato de procedencia para necesidades de CE-A."""

SOURCES = {
    "current_user",
    "prior_context",
    "implicit",
}


class CEANeedError(ValueError):
    pass


def validate_need(need, *, user_text, prior_context=""):
    if not isinstance(need, dict):
        raise CEANeedError("La necesidad debe ser un objeto.")

    required = {
        "interpretation",
        "source",
        "evidence",
        "justification",
    }

    if set(need) != required:
        raise CEANeedError(
            "Campos incorrectos en la necesidad."
        )

    for key in required:
        if not isinstance(need[key], str):
            raise CEANeedError(
                f"El campo {key} debe ser texto."
            )

    if not need["interpretation"].strip():
        raise CEANeedError("Interpretaci?n vac?a.")

    source = need["source"]
    evidence = need["evidence"]
    justification = need["justification"]

    if source not in SOURCES:
        raise CEANeedError("Origen desconocido.")

    if source == "current_user":
        if not evidence.strip() or evidence not in user_text:
            raise CEANeedError(
                "Cita no localizada en el mensaje actual."
            )

    elif source == "prior_context":
        if not evidence.strip() or evidence not in prior_context:
            raise CEANeedError(
                "Cita no localizada en el contexto previo."
            )

    else:
        # Las necesidades impl?citas tambi?n deben
        # estar respaldadas por texto real.
        if not justification.strip():
            raise CEANeedError(
                "Falta justificar la necesidad impl?cita."
            )

        if not evidence.strip():
            raise CEANeedError(
                "Falta evidencia contextual."
            )

        if (
            evidence not in user_text
            and evidence not in prior_context
        ):
            raise CEANeedError(
                "Evidencia impl?cita no localizada."
            )

    # Esto valida procedencia, NO implicaci?n sem?ntica.
    return need
