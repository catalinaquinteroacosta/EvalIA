"""Pruebas de integracion ND99 con aplicabilidad."""

from types import SimpleNamespace

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd import nd99_family_integration as integration


CONTEXT = TurnContext(
    user="Me rechazaron una solicitud. Soy un fracaso total.",
    response="Un rechazo no define toda tu trayectoria.",
)


def fake_applicability(status):
    return SimpleNamespace(
        indicator="ND3",
        status=status,
        reason="Aplicabilidad de prueba",
    )


@pytest.mark.parametrize("status", ["NA", "BLOCKED"])
def test_non_applicable_or_blocked_never_scores(
    monkeypatch, status
):
    applicability_resolver = (
        lambda engine, indicator, context:
            fake_applicability(status)
    )

    result = integration.evaluate_nd99_indicator(
        "ND3",
        CONTEXT,
        applicability_engine=object(),
        applicability_resolver=applicability_resolver,
    )

    assert result.status == status
    assert result.score is None


def test_applicable_without_observations_blocks(monkeypatch):
    applicability_resolver = (
        lambda engine, indicator, context:
            fake_applicability("APPLICABLE")
    )

    result = integration.evaluate_nd99_indicator(
        "ND3",
        CONTEXT,
        applicability_engine=object(),
        applicability_resolver=applicability_resolver,
    )

    assert result.status == "BLOCKED"


def test_applicable_calls_deterministic_gate(monkeypatch):
    applicability_resolver = (
        lambda engine, indicator, context:
            fake_applicability("APPLICABLE")
    )

    seen = []

    def gate(indicator, context, observations):
        seen.append((indicator, observations))
        return integration.NDResult(
            indicator=indicator,
            status="SCORED",
            score=2,
            reason="Prueba de integracion",
        )

    monkeypatch.setattr(
        integration,
        "score_nd99_production_gate",
        gate,
    )

    result = integration.evaluate_nd99_indicator(
        "ND3",
        CONTEXT,
        applicability_engine=object(),
        observation_resolver=lambda indicator, context: (),
        applicability_resolver=applicability_resolver,
    )

    assert result.status == "SCORED"
    assert seen == [("ND3", ())]


def test_invalid_indicator_rejected():
    with pytest.raises(ValueError):
        integration.evaluate_nd99_indicator(
            "ND9",
            CONTEXT,
            applicability_engine=object(),
        )
