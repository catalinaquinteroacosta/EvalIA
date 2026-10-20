"""Contrato ND de reconciliacion independiente.

No ejecuta OpenAI ni asigna puntuaciones.
"""

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["present", "absent", "uncertain"]
Status = Literal["VERIFIED", "BLOCKED"]


@dataclass(frozen=True)
class IndependentReview:
    indicator: str
    fact_name: str
    verdict: Verdict
    evidence_verified: bool
    independent: bool
    reason: str


@dataclass(frozen=True)
class ReconciliationDecision:
    indicator: str
    fact_name: str
    status: Status
    verified_verdict: str | None
    reason: str


def reconcile(
    extraction: IndependentReview,
    verification: IndependentReview,
) -> ReconciliationDecision:
    same_target = (
        extraction.indicator == verification.indicator
        and extraction.fact_name == verification.fact_name
    )

    agreed = (
        same_target
        and extraction.verdict == verification.verdict
        and extraction.verdict in ("present", "absent")
        and extraction.evidence_verified
        and verification.evidence_verified
        and verification.independent
        and bool(extraction.reason.strip())
        and bool(verification.reason.strip())
    )

    if agreed:
        return ReconciliationDecision(
            indicator=extraction.indicator,
            fact_name=extraction.fact_name,
            status="VERIFIED",
            verified_verdict=extraction.verdict,
            reason="Acuerdo independiente verificado",
        )

    return ReconciliationDecision(
        indicator=extraction.indicator,
        fact_name=extraction.fact_name,
        status="BLOCKED",
        verified_verdict=None,
        reason="Discrepancia o evidencia insuficiente",
    )
