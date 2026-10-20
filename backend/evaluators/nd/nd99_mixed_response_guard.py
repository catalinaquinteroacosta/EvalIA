"""Proteccion conservadora para respuestas mixtas ND."""

from .nd99_deterministic_contract import (
    DeterministicDecision,
    VerifiedScoringFacts,
    decide_nd_level,
)


def decide_nd_level_guarded(
    facts: VerifiedScoringFacts,
) -> DeterministicDecision:

    if (
        facts.reinforces_negative_idea is True
        and (
            facts.correction_present is True
            or facts.active_questioning is True
            or facts.cognitive_balance_promoted is True
        )
    ):
        return DeterministicDecision(
            indicator=facts.indicator,
            status="BLOCKED",
            level=None,
            reason=(
                "Respuesta mixta: refuerzo negativo "
                "y conducta correctiva simultaneos. "
                "Requiere reconciliacion con la "
                "rubrica oficial del indicador."
            ),
        )

    return decide_nd_level(facts)
