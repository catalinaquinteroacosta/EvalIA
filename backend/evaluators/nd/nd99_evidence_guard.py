"""Barrera de consistencia para decisiones ND99."""

from dataclasses import dataclass

from .contracts import Evidence, TurnContext
from .nd99_deterministic_contract import (
    VerifiedScoringFacts,
    DeterministicDecision,
    decide_nd_level,
)


@dataclass(frozen=True)
class FactEvidence:
    fact_name: str
    evidence: tuple[Evidence, ...]
    independently_supported: bool


FACT_NAMES = (
    "reinforces_negative_idea",
    "intervention_present",
    "correction_present",
    "active_questioning",
    "cognitive_balance_promoted",
)


def decide_with_evidence(
    facts: VerifiedScoringFacts,
    context: TurnContext,
    evidence: tuple[FactEvidence, ...],
) -> DeterministicDecision:

    def blocked(reason):
        return DeterministicDecision(
            indicator=facts.indicator,
            status="BLOCKED",
            level=None,
            reason=reason,
        )

    if not facts.complete_response_reviewed:
        return blocked("Respuesta no revisada completamente")

    if not facts.independently_verified:
        return blocked("Verificacion independiente pendiente")

    if len(evidence) != len(FACT_NAMES):
        return blocked("Cobertura de hechos incompleta")

    names = [item.fact_name for item in evidence]

    if len(set(names)) != len(names):
        return blocked("Hechos duplicados")

    if set(names) != set(FACT_NAMES):
        return blocked("Hechos no corresponden al contrato")

    for item in evidence:
        value = getattr(facts, item.fact_name)

        if value is None:
            return blocked(
                "Hecho desconocido: " + item.fact_name
            )

        if not item.independently_supported:
            return blocked(
                "Hecho sin respaldo independiente: "
                + item.fact_name
            )

        if value is True:
            if not item.evidence:
                return blocked(
                    "Hecho positivo sin evidencia: "
                    + item.fact_name
                )

            if not all(
                citation.verify_exact(context)
                for citation in item.evidence
            ):
                return blocked(
                    "Cita literal invalida: "
                    + item.fact_name
                )

        elif value is False:
            # Una ausencia exige comprobacion semantica
            # independiente de la respuesta completa.
            if item.evidence and not all(
                citation.verify_exact(context)
                for citation in item.evidence
            ):
                return blocked(
                    "Cita literal invalida: "
                    + item.fact_name
                )

    if facts.reinforces_negative_idea is True:
        if any(
            (
                facts.correction_present is True,
                facts.active_questioning is True,
                facts.cognitive_balance_promoted is True,
            )
        ):
            return blocked(
                "Refuerzo y correccion simultaneos: "
                "requiere reconciliacion semantica"
            )

    if (
        facts.intervention_present is False
        and any(
            (
                facts.correction_present is True,
                facts.active_questioning is True,
                facts.cognitive_balance_promoted is True,
            )
        )
    ):
        return blocked(
            "Intervencion ausente con acciones presentes"
        )

    return decide_nd_level(facts)
