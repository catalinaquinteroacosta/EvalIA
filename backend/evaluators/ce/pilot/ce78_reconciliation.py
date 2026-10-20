
"""Reconciliacion semantica CE7-CE8 sin scoring."""

from copy import deepcopy

from .ce78_literal_recovery import inspect_literal_claims


REPAIR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "quote": {"type": "string"},
        "interpretation": {"type": "string"},
    },
    "required": ["quote", "interpretation"],
}


def reconcile_literal_claims(
    *,
    indicator,
    user_text,
    response_text,
    extraction,
    semantic_runner,
    model=None,
    provider=None,
):
    inspection = inspect_literal_claims(
        indicator=indicator,
        user_text=user_text,
        response_text=response_text,
        extraction=extraction,
    )

    if inspection["status"] == "literal_valid":
        return {
            "status": "ready_for_verification",
            "extraction": deepcopy(extraction),
            "repaired_indices": [],
        }

    if not callable(semantic_runner):
        return {
            "status": "BLOCKED",
            "score": None,
            "reason": "missing_semantic_runner",
        }

    candidate = deepcopy(extraction)
    repaired = []

    for invalid in inspection["invalid_claims"]:
        index = invalid["claim_index"]
        source = invalid["source"]

        original = (
            user_text if source == "user"
            else response_text
        )

        prompt = (
            "EvalIA " + indicator +
            ". REEXTRACCION DE EVIDENCIA LITERAL. "
            "No asignes puntuaciones. "
            "No cambies la proposicion semantica. "
            "Copia una subcadena EXACTA de la fuente. "
            "No normalices caracteres, tildes, "
            "puntuacion ni espacios. "
            "Si no hay evidencia literal que respalde "
            "la proposicion, devuelve quote vacia. "
            "\nFUENTE: " + repr(original) +
            "\nPROPOSICION: " +
            repr(invalid["interpretation"]) +
            "\nCITA RECHAZADA: " +
            repr(invalid["original_quote"])
        )

        try:
            result = semantic_runner(
                prompt=prompt,
                schema=REPAIR_SCHEMA,
                model=model,
                provider=provider,
            )
        except Exception:
            return {
                "status": "BLOCKED",
                "score": None,
                "reason": "semantic_repair_error",
                "claim_index": index,
            }

        if (
            not isinstance(result, dict)
            or set(result) != {"quote", "interpretation"}
            or not isinstance(result["quote"], str)
            or not isinstance(result["interpretation"], str)
            or not result["quote"].strip()
            or result["quote"] not in original
            or result["interpretation"]
            != invalid["interpretation"]
        ):
            return {
                "status": "BLOCKED",
                "score": None,
                "reason": "unresolved_literal_evidence",
                "claim_index": index,
            }

        candidate["claims"][index]["quote"] = result["quote"]
        repaired.append(index)

    return {
        "status": "ready_for_verification",
        "extraction": candidate,
        "repaired_indices": repaired,
    }
