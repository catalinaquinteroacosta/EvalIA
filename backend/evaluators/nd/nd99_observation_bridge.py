"""Puente entre observaciones verificadas y hechos ND."""

from dataclasses import dataclass

from .contracts import Evidence, TurnContext
from .nd99_deterministic_contract import (
    DeterministicDecision,
)
from .nd99_evidence_guard import FACT_NAMES
from .nd99_verified_facts_adapter import (
    SemanticFactReview,
    evaluate_verified_facts,
)


@dataclass(frozen=True)
class FactObservation:
    fact_name: str
    extraction_value: str
    verification_value: str
    extraction_quote: str
    verification_quote: str
    extraction_reason: str
    verification_reason: str
    full_response_examined: bool


def score_from_observations(
    indicator: str,
    context: TurnContext,
    observations: tuple[FactObservation, ...],
) -> DeterministicDecision:

    def blocked(reason):
        return DeterministicDecision(
            indicator=indicator,
            status="BLOCKED",
            level=None,
            reason=reason,
        )

    if len(observations) != len(FACT_NAMES):
        return blocked("Cobertura incompleta")

    names = [item.fact_name for item in observations]

    if (
        len(set(names)) != len(names)
        or set(names) != set(FACT_NAMES)
    ):
        return blocked("Hechos duplicados o desconocidos")

    reviews = []

    for item in observations:
        if (
            item.extraction_value
            not in ("present", "absent", "uncertain")
            or item.verification_value
            not in ("present", "absent", "uncertain")
        ):
            return blocked(
                "Veredicto invalido: " + item.fact_name
            )

        if (
            item.extraction_value != item.verification_value
            or item.extraction_value == "uncertain"
        ):
            return blocked(
                "Desacuerdo semantico: " + item.fact_name
            )

        if not item.full_response_examined:
            return blocked(
                "Revision incompleta: " + item.fact_name
            )

        if (
            not item.extraction_reason.strip()
            or not item.verification_reason.strip()
        ):
            return blocked(
                "Justificacion incompleta: "
                + item.fact_name
            )

        positive = item.extraction_value == "present"

        if positive:
            if (
                not item.extraction_quote
                or not item.verification_quote
                or item.extraction_quote
                not in context.response
                or item.verification_quote
                not in context.response
            ):
                return blocked(
                    "Evidencia positiva invalida: "
                    + item.fact_name
                )

        else:
            if (
                item.extraction_quote
                and item.extraction_quote
                not in context.response
            ):
                return blocked(
                    "Cita invalida: " + item.fact_name
                )

            if (
                item.verification_quote
                and item.verification_quote
                not in context.response
            ):
                return blocked(
                    "Cita invalida: " + item.fact_name
                )

        evidence = (
            Evidence(
                source="response",
                quote=item.extraction_quote,
            ),
            Evidence(
                source="response",
                quote=item.verification_quote,
            ),
        ) if positive else ()

        reviews.append(
            SemanticFactReview(
                fact_name=item.fact_name,
                value=positive,
                evidence=evidence,
                extraction_verdict="supported",
                independent_verdict="supported",
                complete_response_examined=True,
                reason=(
                    item.extraction_reason
                    + " | "
                    + item.verification_reason
                ),
            )
        )

    return evaluate_verified_facts(
        indicator,
        context,
        tuple(reviews),
    )
