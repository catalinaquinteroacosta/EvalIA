
"""CE7-CE8: deteccion estricta de evidencia no literal.

No modifica citas, no asigna puntuaciones y no invoca APIs.
"""

from copy import deepcopy


def inspect_literal_claims(
    *,
    indicator,
    user_text,
    response_text,
    extraction,
):
    if indicator not in ("CE7", "CE8"):
        raise ValueError("Indicador no autorizado")

    if not isinstance(user_text, str):
        raise TypeError("user_text invalido")

    if not isinstance(response_text, str):
        raise TypeError("response_text invalido")

    if not isinstance(extraction, dict):
        raise TypeError("extraction invalida")

    claims = extraction.get("claims")

    if not isinstance(claims, list):
        raise ValueError("claims invalido")

    invalid = []

    for index, claim in enumerate(claims):

        if not isinstance(claim, dict):
            raise ValueError("Claim invalida")

        if set(claim) != {
            "source", "quote", "interpretation"
        }:
            raise ValueError("Contrato de claim invalido")

        source = claim["source"]
        quote = claim["quote"]

        if source not in ("user", "response"):
            raise ValueError("Fuente invalida")

        if not isinstance(quote, str):
            raise ValueError("Cita invalida")

        if not isinstance(
            claim["interpretation"], str
        ) or not claim["interpretation"].strip():
            raise ValueError("Interpretacion invalida")

        original = (
            user_text if source == "user"
            else response_text
        )

        if not quote.strip() or quote not in original:
            invalid.append({
                "claim_index": index,
                "source": source,
                "original_quote": quote,
                "interpretation": claim["interpretation"],
            })

    return {
        "indicator": indicator,
        "status": (
            "repair_required"
            if invalid else "literal_valid"
        ),
        "invalid_claims": invalid,
        "original_extraction": deepcopy(extraction),
    }
