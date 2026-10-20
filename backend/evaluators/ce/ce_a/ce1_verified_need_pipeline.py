"""Coordinador CE1: misma conversacion para ambos controles."""

from .ce1_unaddressed_need import validate_unaddressed_need
from .ce1_unaddressed_verifier import verify_unaddressed_need
from .ce1_unaddressed_auditor import audit_unaddressed_need
from .ce1_verified_needs import build_verified_need


def evaluate_verified_need(
    item,
    *,
    user_text,
    response_text,
    prior_context="",
    model=None,
    use_cache=True,
):
    validate_unaddressed_need(
        item,
        user_text=user_text,
        prior_context=prior_context,
    )

    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Respuesta invalida.")

    original = verify_unaddressed_need(
        item,
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
        model=model,
        use_cache=use_cache,
    )

    audit = audit_unaddressed_need(
        item,
        original,
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
        model=model,
        use_cache=use_cache,
    )

    return build_verified_need(
        item,
        original,
        audit,
        user_text=user_text,
        response_text=response_text,
        prior_context=prior_context,
    )
