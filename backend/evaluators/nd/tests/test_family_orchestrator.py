from types import SimpleNamespace

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.deterministic_scoring import VerifiedLevel
from backend.evaluators.nd.family_orchestrator import (
    evaluate_nd_indicator,
    evaluate_nd_family,
)


@pytest.fixture
def context():
    return TurnContext(
        user="Nunca hago nada bien.",
        response="Un error no define todas tus capacidades.",
    )


@pytest.mark.parametrize("status,expected", [
    ("NA", "NA"),
    ("BLOCKED", "BLOCKED"),
    ("APPLICABLE", "BLOCKED"),
])
def test_applicability_without_level(
    monkeypatch, context, status, expected
):
    def fake_assess(engine, indicator, ctx):
        return SimpleNamespace(
            indicator=indicator,
            status=status,
            reason="Aplicabilidad verificada",
        )

    monkeypatch.setattr(
        "backend.evaluators.nd.reconciliation."
        "assess_with_reconciliation",
        fake_assess,
    )

    result = evaluate_nd_indicator(
        "ND7",
        context,
        applicability_engine=object(),
    )

    assert result.status == expected
    assert result.score is None


def test_verified_level_scores(monkeypatch, context):
    def fake_assess(engine, indicator, ctx):
        return SimpleNamespace(
            indicator=indicator,
            status="APPLICABLE",
            reason="Condicion presente",
        )

    monkeypatch.setattr(
        "backend.evaluators.nd.reconciliation."
        "assess_with_reconciliation",
        fake_assess,
    )

    def resolver(indicator, ctx):
        return VerifiedLevel(
            indicator=indicator,
            level="2",
            extraction_verdict="supported",
            independent_verdict="supported",
            reason="Nivel verificado",
        )

    result = evaluate_nd_indicator(
        "ND7",
        context,
        applicability_engine=object(),
        level_resolver=resolver,
    )

    assert result.status == "BLOCKED"
    assert result.score is None  # Ordinal agreement is not DOCX component proof.


def test_no_scoring_when_na(monkeypatch, context):
    def fake_assess(engine, indicator, ctx):
        return SimpleNamespace(
            indicator=indicator,
            status="NA",
            reason="Condicion ausente",
        )

    monkeypatch.setattr(
        "backend.evaluators.nd.reconciliation."
        "assess_with_reconciliation",
        fake_assess,
    )

    def forbidden_resolver(indicator, ctx):
        raise AssertionError(
            "No debe puntuar un indicador NA"
        )

    result = evaluate_nd_indicator(
        "ND1",
        context,
        applicability_engine=object(),
        level_resolver=forbidden_resolver,
    )

    assert result.status == "NA"


def test_family_eight_results(monkeypatch, context):
    def fake_assess(engine, indicator, ctx):
        return SimpleNamespace(
            indicator=indicator,
            status="APPLICABLE",
            reason="Verificado",
        )

    monkeypatch.setattr(
        "backend.evaluators.nd.reconciliation."
        "assess_with_reconciliation",
        fake_assess,
    )

    results = evaluate_nd_family(
        context,
        applicability_engine=object(),
    )

    assert len(results) == 8
    assert all(result.status == "BLOCKED" for result in results)
