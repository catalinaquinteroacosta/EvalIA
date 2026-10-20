"""Adaptador de necesidades implicitas CE1. No puntua."""

from .need_contract import validate_need
from .need_verifier import verify_need
from .ce1_verified_need_pipeline import evaluate_verified_need


class CE1ImplicitReviewRequired(ValueError):
    pass


def evaluate_implicit_need(
    item,
    *,
    user_text,
    response_text,
    prior_context="",
    model=None,
    use_cache=True,
):
    """Verifica primero la legitimidad de la necesidad."""

    if not isinstance(item, dict) or set(item) != {
        "interpretation",
        "source",
        "evidence",
        "justification",
    }:
        raise ValueError("Necesidad contextual invalida.")

    if item["source"] != "implicit":
        raise ValueError("Este adaptador solo admite implicit.")

    validate_need(
        item,
        user_text=user_text,
        prior_context=prior_context,
    )

    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Respuesta invalida.")

    legitimacy = verify_need(
        item,
        user_text=user_text,
        prior_context=prior_context,
        model=model,
        use_cache=use_cache,
    )

    if (
        not isinstance(legitimacy, dict)
        or set(legitimacy) != {"verdict", "reason"}
        or legitimacy["verdict"] not in {
            "supported", "not_supported", "ambiguous"
        }
        or not isinstance(legitimacy["reason"], str)
        or not legitimacy["reason"].strip()
    ):
        raise ValueError("Verificacion de legitimidad invalida.")

    if legitimacy["verdict"] != "supported":
        raise CE1ImplicitReviewRequired(
            "Necesidad implicita no autorizada: "
            + legitimacy["verdict"]
        )

    # La evidencia implicita debe quedar asociada
    # a una fuente literal concreta para el contrato CE1.
    in_current = item["evidence"] in user_text
    in_prior = item["evidence"] in prior_context

    if in_current and in_prior:
        raise CE1ImplicitReviewRequired(
            "Cita presente en ambas fuentes: "
            "procedencia exacta pendiente."
        )

    if not in_current and not in_prior:
        raise ValueError("Evidencia sin fuente literal.")

    ce1_item = {
        "need": item["interpretation"],
        "source": "current_user" if in_current else "prior_context",
        "evidence": item["evidence"],
        "explanation": item["justification"],
    }

    coverage = evaluate_verified_need(
        ce1_item,
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
        model=model,
        use_cache=use_cache,
    )

    return {
        "original_source": "implicit",
        "legitimacy": legitimacy,
        "coverage": coverage,
        "primary_need_confirmed": False,
        "severity": None,
        "score": None,
    }
