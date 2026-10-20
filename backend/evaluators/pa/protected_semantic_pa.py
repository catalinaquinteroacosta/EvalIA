"""Evaluacion PA con control obligatorio de evidencia."""

from backend.evaluators.pa.semantic_pilot import (
    evaluate_indicator,
)
from backend.evaluators.pa.verified_evidence_pa import (
    validate_extraction,
)


def evaluate_protected(client, turn, code):
    result = evaluate_indicator(client, turn, code)

    context = {
        "current_user": turn.user,
        "current_response": turn.response,
        "prior_history": [
            {"role": m.role, "text": m.text}
            for m in turn.prior_history
        ],
    }

    extraction = result.get("extraction")

    if not validate_extraction(context, extraction):
        return {
            **result,
            "technical_status": "BLOCKED",
            "evidence_gate": "FAILED",
            "score": None,
        }

    return {
        **result,
        "evidence_gate": "PASSED",
    }
