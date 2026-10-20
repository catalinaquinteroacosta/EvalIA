from typing import Any

def reconcile_gd567(
    results: dict[str, Any],
    coherence: dict[str, Any],
    historical_gd6_disagreement: bool = True,
) -> dict[str, Any]:

    output = {}

    for code in ("GD5", "GD6", "GD7"):
        result = results[code]
        audit = coherence[code]

        reasons = list(audit.get("issues", []))

        if audit.get("status") != "CONSISTENT":
            reasons.append(
                "CURRENT_SEMANTIC_INCONSISTENCY"
            )

        if result.get("status") != "SCORED":
            reasons.append(
                "RESULT_NOT_VERIFIED_FOR_SCORING"
            )

        if code == "GD6" and historical_gd6_disagreement:
            reasons.append(
                "HUMAN_ADJUDICATION_PENDING"
            )

        output[code] = {
            "status": (
                "READY" if not reasons else "BLOCKED"
            ),
            "provisional_score": result.get("score"),
            "reasons": list(dict.fromkeys(reasons)),
        }

    return output
