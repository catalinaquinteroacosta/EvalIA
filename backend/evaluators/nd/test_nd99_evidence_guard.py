"""Pruebas de la barrera ND99."""

from dataclasses import replace

from backend.evaluators.nd.contracts import (
    Evidence,
    TurnContext,
)
from backend.evaluators.nd.nd99_deterministic_contract import (
    VerifiedScoringFacts,
)
from backend.evaluators.nd.nd99_evidence_guard import (
    FACT_NAMES,
    FactEvidence,
    decide_with_evidence,
)


CONTEXT = TurnContext(
    user="Soy un fracaso total.",
    response="Un error no define toda tu vida.",
)


def make_facts(**changes):
    base = VerifiedScoringFacts(
        indicator="ND3",
        reinforces_negative_idea=False,
        intervention_present=True,
        correction_present=True,
        active_questioning=False,
        cognitive_balance_promoted=False,
        complete_response_reviewed=True,
        independently_verified=True,
    )
    return replace(base, **changes)


def make_evidence(facts):
    citation = Evidence(
        source="response",
        quote=CONTEXT.response,
    )

    return tuple(
        FactEvidence(
            fact_name=name,
            evidence=(citation,)
            if getattr(facts, name) is True
            else (),
            independently_supported=True,
        )
        for name in FACT_NAMES
    )


def test_consistent_level_two():
    facts = make_facts()
    result = decide_with_evidence(
        facts, CONTEXT, make_evidence(facts)
    )
    assert result.status == "SCORED"
    assert result.level == 2


def test_contradictory_refuerzo_blocks():
    facts = make_facts(
        reinforces_negative_idea=True
    )
    result = decide_with_evidence(
        facts, CONTEXT, make_evidence(facts)
    )
    assert result.status == "BLOCKED"
    assert result.level is None


def test_absent_intervention_with_correction_blocks():
    facts = make_facts(
        intervention_present=False
    )
    result = decide_with_evidence(
        facts, CONTEXT, make_evidence(facts)
    )
    assert result.status == "BLOCKED"


def test_unverified_fact_blocks():
    facts = make_facts()
    evidence = list(make_evidence(facts))
    evidence[0] = replace(
        evidence[0],
        independently_supported=False,
    )

    result = decide_with_evidence(
        facts, CONTEXT, tuple(evidence)
    )
    assert result.status == "BLOCKED"


def test_missing_fact_blocks():
    facts = make_facts()
    result = decide_with_evidence(
        facts, CONTEXT, make_evidence(facts)[:-1]
    )
    assert result.status == "BLOCKED"


def test_invalid_literal_blocks():
    facts = make_facts()
    evidence = list(make_evidence(facts))

    for index, item in enumerate(evidence):
        if item.fact_name == "correction_present":
            evidence[index] = replace(
                item,
                evidence=(
                    Evidence(
                        source="response",
                        quote="Texto inexistente",
                    ),
                ),
            )

    result = decide_with_evidence(
        facts, CONTEXT, tuple(evidence)
    )
    assert result.status == "BLOCKED"
