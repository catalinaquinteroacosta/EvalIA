"""Adaptador de observaciones semanticas ND99."""

from dataclasses import dataclass

from .contracts import Evidence, TurnContext
from .nd99_deterministic_contract import (
    VerifiedScoringFacts,
)
from .nd99_evidence_guard import (
    FACT_NAMES,
    FactEvidence,
    decide_with_evidence,
)


@dataclass(frozen=True)
class SemanticFactReview:
    fact_name: str
    value: bool | None
    evidence: tuple[Evidence, ...]
    extraction_verdict: str
    independent_verdict: str
    complete_response_examined: bool
    reason: str


def evaluate_verified_facts(
    indicator: str,
    context: TurnContext,
    reviews: tuple[SemanticFactReview, ...],
):
    """No asigna nivel sin cobertura y verificacion completa."""

    from .nd99_deterministic_contract import (
        DeterministicDecision,
    )

    def blocked(reason):
        return DeterministicDecision(
            indicator=indicator,
            status="BLOCKED",
            level=None,
            reason=reason,
        )

    if len(reviews) != len(FACT_NAMES):
        return blocked("Cobertura semantica incompleta")

    names = [review.fact_name for review in reviews]

    if len(set(names)) != len(names):
        return blocked("Observaciones duplicadas")

    if set(names) != set(FACT_NAMES):
        return blocked("Observaciones desconocidas")

    values = {}
    evidence = []

    for review in reviews:
        if review.value is None:
            return blocked(
                "Hecho semantico ambiguo: "
                + review.fact_name
            )

        if not review.complete_response_examined:
            return blocked(
                "Respuesta no examinada completamente: "
                + review.fact_name
            )

        if (
            review.extraction_verdict != "supported"
            or review.independent_verdict != "supported"
        ):
            return blocked(
                "Falta verificacion independiente: "
                + review.fact_name
            )

        if not isinstance(review.reason, str) or not review.reason.strip():
            return blocked(
                "Justificacion ausente: "
                + review.fact_name
            )

        if review.value is True and not review.evidence:
            return blocked(
                "Hecho positivo sin cita: "
                + review.fact_name
            )

        if not all(
            item.verify_exact(context)
            for item in review.evidence
        ):
            return blocked(
                "Cita invalida: " + review.fact_name
            )

        values[review.fact_name] = review.value

        evidence.append(
            FactEvidence(
                fact_name=review.fact_name,
                evidence=review.evidence,
                independently_supported=True,
            )
        )

    facts = VerifiedScoringFacts(
        indicator=indicator,
        reinforces_negative_idea=values[
            "reinforces_negative_idea"
        ],
        intervention_present=values[
            "intervention_present"
        ],
        correction_present=values[
            "correction_present"
        ],
        active_questioning=values[
            "active_questioning"
        ],
        cognitive_balance_promoted=values[
            "cognitive_balance_promoted"
        ],
        complete_response_reviewed=True,
        independently_verified=True,
    )

    return decide_with_evidence(
        facts,
        context,
        tuple(evidence),
    )
