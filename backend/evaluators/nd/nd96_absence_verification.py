"""Contrato experimental de certificacion de ausencia ND.

No ejecuta OpenAI ni asigna puntuaciones.
"""

from dataclasses import dataclass

from .nd94_indicator_facts import ND94Fact


@dataclass(frozen=True)
class VerifiedAbsence:
    indicator: str
    fact_name: str
    full_response_examined: bool
    independent_verdict: str
    independent_verified: bool
    reason: str


def certify_absence(
    fact: ND94Fact,
    certificate: VerifiedAbsence,
) -> bool:
    return all((
        fact.verdict == "absent",
        fact.extraction_verified,
        fact.independent_verified,
        fact.indicator == certificate.indicator,
        fact.name == certificate.fact_name,
        certificate.full_response_examined,
        certificate.independent_verdict == "absent",
        certificate.independent_verified,
        bool(certificate.reason.strip()),
    ))
