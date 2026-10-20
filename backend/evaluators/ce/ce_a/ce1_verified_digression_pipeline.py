"""Coordinador del doble control contextual CE1."""

from .ce1_digression_verifier import verify_ce1_digression
from .ce1_digression_auditor import (
    audit_ce1_digression,
    aggregate_digression,
)


def evaluate_verified_digression(
    *,
    interpretation,
    evidence,
    user_text,
    response_text,
    prior_context="",
    model=None,
    use_cache=True,
):
    args = {
        "interpretation": interpretation,
        "evidence": evidence,
        "user_text": user_text,
        "response_text": response_text,
        "prior_context": prior_context,
    }

    original = verify_ce1_digression(
        **args,
        model=model,
        use_cache=use_cache,
    )

    result = {
        "status": "review_required",
        "interpretation": interpretation,
        "evidence": evidence,
        "evidence_support": original["evidence_support"],
        "original": original["contextual_verdict"],
        "audit": None,
        "decision": None,
        "severity": None,
        "score": None,
    }

    if (
        original["status"] != "classified"
        or original["evidence_support"]["verdict"]
        != "supported"
        or original["contextual_verdict"] is None
    ):
        return result

    audit = audit_ce1_digression(
        **args,
        model=model,
    )

    decision = aggregate_digression(
        original["contextual_verdict"],
        audit,
    )

    result["audit"] = audit
    result["decision"] = decision

    if decision["verified"]:
        result["status"] = "verified"

    return result
