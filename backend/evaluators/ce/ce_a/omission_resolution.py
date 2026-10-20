"""Deterministic resolution of independently verified CE-A omissions."""

from copy import deepcopy


class OmissionResolutionError(ValueError):
    pass


def resolve_omissions(extraction, omission_checks):
    """Preserve the original and produce a traceable resolved copy."""
    if not isinstance(extraction, dict):
        raise OmissionResolutionError("Invalid extraction.")

    original = extraction.get("ce2_essential_omissions")
    if not isinstance(original, list):
        raise OmissionResolutionError("Invalid omissions.")

    if not isinstance(omission_checks, list):
        raise OmissionResolutionError("Invalid checks.")

    if len(original) != len(omission_checks):
        raise OmissionResolutionError("Incomplete verification.")

    by_index = {}

    for check in omission_checks:
        if not isinstance(check, dict):
            raise OmissionResolutionError("Invalid check.")

        index = check.get("index")
        if type(index) is not int or index not in range(len(original)):
            raise OmissionResolutionError("Invalid index.")

        if index in by_index:
            raise OmissionResolutionError("Duplicate index.")

        item = original[index]
        if not isinstance(item, dict):
            raise OmissionResolutionError("Invalid omission.")

        for field in (
            "missing_information",
            "context_justification",
            "user_evidence",
        ):
            if check.get(field) != item.get(field):
                raise OmissionResolutionError(
                    "Verification does not match extraction."
                )

        verdict = check.get("verdict")
        if verdict not in ("supported", "not_supported"):
            raise OmissionResolutionError(
                "Unresolved or invalid verification."
            )

        by_index[index] = check

    resolved = deepcopy(extraction)
    retained = []
    decisions = []

    for index, item in enumerate(original):
        check = by_index[index]
        accepted = check["verdict"] == "supported"

        if accepted:
            retained.append(deepcopy(item))

        decisions.append({
            "field": "ce2_essential_omissions",
            "original_index": index,
            "original_item": deepcopy(item),
            "verification": deepcopy(check),
            "action": (
                "retained" if accepted
                else "excluded_after_verification"
            ),
        })

    resolved["ce2_essential_omissions"] = retained

    return {
        "resolved_extraction": resolved,
        "resolution_log": decisions,
        "scoring_authorized": False,
    }
