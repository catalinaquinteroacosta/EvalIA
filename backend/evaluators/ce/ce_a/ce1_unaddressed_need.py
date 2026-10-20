"""Contrato de necesidades no atendidas para CE1.

La validez estructural no demuestra que la necesidad
este realmente ignorada ni determina su gravedad.
"""


class CE1UnaddressedNeedError(ValueError):
    pass


def validate_unaddressed_need(
    item, *, user_text, prior_context=""
):
    required = {
        "need",
        "source",
        "evidence",
        "explanation",
    }

    if not isinstance(item, dict) or set(item) != required:
        raise CE1UnaddressedNeedError(
            "Estructura de necesidad ignorada invalida."
        )

    if any(
        not isinstance(item[key], str) or not item[key].strip()
        for key in required
    ):
        raise CE1UnaddressedNeedError(
            "Necesidad ignorada con campos vacios."
        )

    sources = {
        "current_user": user_text,
        "prior_context": prior_context,
    }

    if item["source"] not in sources:
        raise CE1UnaddressedNeedError(
            "Origen de evidencia desconocido."
        )

    source_text = sources[item["source"]]

    if item["evidence"] not in source_text:
        raise CE1UnaddressedNeedError(
            "La evidencia no aparece literalmente "
            "en la fuente declarada."
        )

    return item
