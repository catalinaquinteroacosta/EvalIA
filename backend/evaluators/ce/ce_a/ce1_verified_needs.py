"""Contrato de necesidades verificadas CE1. No puntua."""

from copy import deepcopy

from .ce1_unaddressed_need import validate_unaddressed_need
from .ce1_unaddressed_verifier import validate_result
from .ce1_unaddressed_auditor import (
    validate_audit,
    aggregate_review,
)


class CE1VerifiedNeedsError(ValueError):
    pass


def build_verified_need(
    item,
    original,
    audit,
    *,
    user_text,
    response_text,
    prior_context="",
):
    """Incorpora una necesidad solo si supera ambos controles."""

    validate_unaddressed_need(
        item,
        user_text=user_text,
        prior_context=prior_context,
    )
    validate_result(original)
    validate_audit(audit, original["verdict"])

    if not isinstance(response_text, str) or not response_text.strip():
        raise CE1VerifiedNeedsError("Respuesta invalida.")

    decision = aggregate_review(original, audit)

    if not decision["verified"]:
        raise CE1VerifiedNeedsError(
            "Desacuerdo o incertidumbre: revision requerida."
        )

    return {
        "need": deepcopy(item),
        "coverage": decision["verdict"],
        "verification": {
            "original": deepcopy(original),
            "audit": deepcopy(audit),
        },
        "severity": None,
        "score": None,
    }
