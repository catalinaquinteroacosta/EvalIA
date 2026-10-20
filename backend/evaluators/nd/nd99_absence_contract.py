"""Verificacion explicita de ausencia semantica ND."""

from dataclasses import dataclass

from .nd99_observation_bridge import FactObservation
from .nd99_polarity_contract import (
    PolarityFinding,
    reconcile_polarity,
)


@dataclass(frozen=True)
class AbsenceFinding:
    fact_name: str
    explicitly_absent: bool | None
    reason: str
    complete_response_examined: bool


def reconcile_with_absence(
    fact_name: str,
    extraction: PolarityFinding,
    verification: PolarityFinding,
    absence_extraction: AbsenceFinding | None,
    absence_verification: AbsenceFinding | None,
    response: str,
) -> FactObservation:

    base = reconcile_polarity(
        fact_name,
        extraction,
        verification,
        response,
    )

    if base.extraction_value == "present":
        return base

    if (
        extraction.verdict != "not_supported"
        or verification.verdict != "not_supported"
    ):
        return base

    if (
        absence_extraction is None
        or absence_verification is None
    ):
        return base

    findings = (
        absence_extraction,
        absence_verification,
    )

    for finding in findings:
        if finding.fact_name != fact_name:
            return base

        if not finding.complete_response_examined:
            return base

        if not finding.reason.strip():
            return base

    if (
        absence_extraction.explicitly_absent is not True
        or absence_verification.explicitly_absent is not True
    ):
        return base

    return FactObservation(
        fact_name=fact_name,
        extraction_value="absent",
        verification_value="absent",
        extraction_quote="",
        verification_quote="",
        extraction_reason=(
            extraction.reason
            + " | AUSENCIA: "
            + absence_extraction.reason
        ),
        verification_reason=(
            verification.reason
            + " | AUSENCIA: "
            + absence_verification.reason
        ),
        full_response_examined=True,
    )
