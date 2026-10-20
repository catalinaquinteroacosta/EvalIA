"""Inventario CE1. No verifica semanticamente ni puntua."""


def build_ce1_need_inventory(extraction):
    if not isinstance(extraction, dict):
        raise ValueError("Extraccion invalida.")

    required = {"explicit_needs", "contextual_needs"}
    if not required.issubset(extraction):
        raise ValueError("Faltan campos de necesidades.")

    result = []

    for field in ("explicit_needs", "contextual_needs"):
        items = extraction[field]
        if not isinstance(items, list):
            raise ValueError("Lista de necesidades invalida.")

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError("Necesidad mal estructurada.")

            if field == "explicit_needs":
                need = item["interpretation"]
                evidence = item["user_evidence"]
                source = "current_user"
                explanation = "Necesidad explicita extraida."
            else:
                need = item["interpretation"]
                evidence = item["evidence"]
                source = item["source"]
                explanation = item["justification"]

            if (
                not all(
                    isinstance(value, str) and value.strip()
                    for value in (
                        need, evidence, source, explanation
                    )
                )
                or source not in {
                    "current_user", "prior_context", "implicit"
                }
            ):
                raise ValueError("Necesidad incompleta.")

            result.append({
                "origin_field": field,
                "origin_index": index,
                "need": {
                    "need": need,
                    "source": source,
                    "evidence": evidence,
                    "explanation": explanation,
                },
                "status": (
                    "pending_implicit_contract"
                    if source == "implicit"
                    else "pending_semantic_verification"
                ),
            })

    return result
