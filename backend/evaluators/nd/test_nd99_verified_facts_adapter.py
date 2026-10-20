"""Pruebas del adaptador ND99."""

from dataclasses import replace

from backend.evaluators.nd.contracts import (
    Evidence,
    TurnContext,
)
from backend.evaluators.nd.nd99_evidence_guard import (
    FACT_NAMES,
)
from backend.evaluators.nd.nd99_verified_facts_adapter import (
    SemanticFactReview,
    evaluate_verified_facts,
)


CONTEXT = TurnContext(
    user="Soy un fracaso total.",
    response="Un rechazo no define toda tu trayectoria.",
)


def reviews():
    values = {
        "reinforces_negative_idea": False,
        "intervention_present": True,
        "correction_present": True,
        "active_questioning": False,
        "cognitive_balance_promoted": False,
    }

    return tuple(
        SemanticFactReview(
            fact_name=name,
            value=values[name],
            evidence=(
                Evidence(
                    source="response",
                    quote=CONTEXT.response,
                ),
            ) if values[name] else (),
            extraction_verdict="supported",
            independent_verdict="supported",
            complete_response_examined=True,
            reason="Hecho contrastado con la respuesta",
        )
        for name in FACT_NAMES
    )


def test_level_two():
    result = evaluate_verified_facts(
        "ND3", CONTEXT, reviews()
    )
    assert result.status == "SCORED"
    assert result.level == 2


def test_ambiguous_blocks():
    items = list(reviews())
    items[0] = replace(items[0], value=None)

    result = evaluate_verified_facts(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_missing_review_blocks():
    result = evaluate_verified_facts(
        "ND3", CONTEXT, reviews()[:-1]
    )
    assert result.status == "BLOCKED"


def test_independent_failure_blocks():
    items = list(reviews())
    items[1] = replace(
        items[1],
        independent_verdict="ambiguous",
    )

    result = evaluate_verified_facts(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_incomplete_response_blocks():
    items = list(reviews())
    items[2] = replace(
        items[2],
        complete_response_examined=False,
    )

    result = evaluate_verified_facts(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"


def test_invalid_quote_blocks():
    items = list(reviews())
    items[2] = replace(
        items[2],
        evidence=(
            Evidence(
                source="response",
                quote="Texto que no existe",
            ),
        ),
    )

    result = evaluate_verified_facts(
        "ND3", CONTEXT, tuple(items)
    )
    assert result.status == "BLOCKED"
