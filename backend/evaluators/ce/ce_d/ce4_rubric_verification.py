"""Verificación independiente del nivel de ejecución CE4."""

from .ce4_rubric_contract import score_verified_execution


DESCRIPTORS = {
    "omitted_or_opposite":
        "Omite la conducta solicitada o hace lo contrario.",
    "minimal_generic":
        "Muestra señal mínima o genérica sin ejecución suficiente.",
    "adequate_limited":
        "Ejecuta adecuadamente con precisión o adaptación limitada.",
    "clear_contextual_verifiable":
        "Ejecuta de forma clara, específica, contextualizada y comprobable.",
}


def verify_rubric_execution(
    *,
    response_text,
    applicable,
    analysis_complete,
    execution,
    verify_claim,
    reconcile_claim=None,
):
    if type(applicable) is not bool:
        raise ValueError("Aplicabilidad inválida")

    if type(analysis_complete) is not bool:
        raise ValueError("Análisis inválido")

    if not analysis_complete:
        return {"status": "insufficient_evidence", "score": None}

    if not applicable:
        return {"status": "not_applicable", "score": None}

    if execution not in DESCRIPTORS:
        return {"status": "insufficient_evidence", "score": None}

    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Respuesta inválida")

    if not callable(verify_claim):
        raise ValueError("Verificador inválido")

    condition = (
        "CE4. Evalúa la respuesta completa únicamente respecto "
        "a párrafos o enumeraciones funcionales cuando la extensión "
        "requiere estructura visual. Comprueba independientemente "
        "esta descripción: " + DESCRIPTORS[execution] +
        " Contrasta las demás categorías de la rúbrica, busca "
        "contraevidencia y no asignes puntajes."
    )

    verdict = verify_claim(
        response_text,
        response_text,
        condition,
    )

    if verdict != "supported":
        if reconcile_claim is not None:
            verdict = reconcile_claim(
                response_text,
                response_text,
                condition,
                "rubric_execution",
            )

        if verdict != "supported":
            return {
                "status": "BLOCKED",
                "score": None,
                "blocked_components": ["rubric_execution"],
            }

    return score_verified_execution(
        applicable=True,
        analysis_complete=True,
        semantic_verified=True,
        execution=execution,
    )
