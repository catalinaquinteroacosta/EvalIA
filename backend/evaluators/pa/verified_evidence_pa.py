"""Control de evidencia previo a decisiones PA."""

from backend.evaluators.pa.evidence_lineage_pa import (
    validate_evidence,
    validate_response_quotes,
)


def validate_extraction(context, extraction):
    if not isinstance(extraction, dict):
        return False

    observations = extraction.get("observations")

    if not isinstance(observations, list):
        return False

    for observation in observations:
        if not isinstance(observation, dict):
            return False

        evidence = observation.get("evidence")

        if not isinstance(evidence, list):
            return False

        if not all(
            validate_evidence(context, item)
            for item in evidence
        ):
            return False

    return True


def validate_reviewer(context, review):
    if not isinstance(review, dict):
        return False

    return validate_response_quotes(
        context,
        review.get("quotes"),
    )


def evidence_gate(context, extraction, reviews):
    extraction_valid = validate_extraction(
        context, extraction
    )

    review_validity = [
        validate_reviewer(context, review)
        for review in reviews
    ]

    return {
        "extraction_valid": extraction_valid,
        "review_validity": review_validity,
        "all_valid": (
            extraction_valid
            and bool(review_validity)
            and all(review_validity)
        ),
    }
