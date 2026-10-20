"""Control independiente de aplicabilidad PA."""

from dataclasses import dataclass

from .contracts import CODES, CONDITIONAL
from .scoring_guard import (
    PropertyRecord,
    check_scoring_readiness,
)


@dataclass(frozen=True)
class ApplicabilityDecision:
    indicator: str
    status: str
    reason: str
    score: int | str | None = None


def assess_applicability(
    code: str,
    applicable: bool | None,
    independently_verified: bool,
    reason: str,
    properties: tuple[PropertyRecord, ...] = (),
    unresolved_discrepancy: bool = False,
) -> ApplicabilityDecision:
    if code not in CODES:
        raise ValueError(code)

    if not reason.strip():
        return ApplicabilityDecision(
            code, "BLOCKED", "Falta justificacion"
        )

    if not independently_verified:
        return ApplicabilityDecision(
            code, "BLOCKED",
            "Aplicabilidad sin verificacion independiente",
        )

    if unresolved_discrepancy or applicable is None:
        return ApplicabilityDecision(
            code, "BLOCKED",
            "Aplicabilidad o discrepancia no resuelta",
        )

    if applicable is False:
        if code not in CONDITIONAL:
            return ApplicabilityDecision(
                code, "BLOCKED",
                "No aplicabilidad general requiere "
                "justificacion metodologica adicional",
            )

        return ApplicabilityDecision(
            code, "NOT_APPLICABLE", reason, "N/A"
        )

    gate = check_scoring_readiness(
        code,
        applicable=True,
        properties=properties,
        unresolved_discrepancy=False,
    )

    return ApplicabilityDecision(
        code, gate.status, gate.reason
    )
