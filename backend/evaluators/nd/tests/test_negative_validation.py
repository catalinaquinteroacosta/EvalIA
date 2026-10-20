"""Pruebas del contrato de ausencia semantica ND."""

import pytest

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.negative_validation import (
    validate_negative_applicability,
)


class FakeEngine:
    def __init__(self, verdict):
        self.verdict = verdict
        self.stages = []
        self.commits = []

    def _run(self, **kwargs):
        self.stages.append(kwargs)
        return {
            "_uncached": {
                "verdict": self.verdict,
                "reason": "Evaluacion independiente",
            },
            "_cache_key": "negative-test",
        }

    def _commit(self, result, validated):
        self.commits.append(validated)


@pytest.mark.parametrize(
    "indicator",
    [f"ND{i}" for i in range(1, 9)],
)
@pytest.mark.parametrize(
    "verdict",
    ["supported", "not_supported", "ambiguous"],
)
def test_negative_verification_contract(indicator, verdict):
    engine = FakeEngine(verdict)
    context = TurnContext("Hola", "Hola")

    result = validate_negative_applicability(
        engine, indicator, context
    )

    assert result["verdict"] == verdict
    assert len(engine.stages) == 1
    assert (
        engine.stages[0]["stage"]
        == "verify_negative_applicability"
    )

    if verdict == "ambiguous":
        assert engine.commits == []
    else:
        assert len(engine.commits) == 1


@pytest.mark.parametrize(
    "indicator",
    ["ND3", "ND4", "ND5", "ND6", "ND8"],
)
def test_general_absence_requires_no_evaluable_content(indicator):
    engine = FakeEngine("supported")

    validate_negative_applicability(
        engine,
        indicator,
        TurnContext(
            "Estoy preocupado",
            "Entiendo tu preocupacion",
        ),
    )

    prompt = engine.stages[0]["prompt"]

    assert "No existe contenido objetivamente evaluable" in prompt
    assert "No confundas falta de infraccion" in prompt


def test_invalid_indicator_rejected():
    with pytest.raises(ValueError):
        validate_negative_applicability(
            FakeEngine("supported"),
            "ND9",
            TurnContext("Hola", "Hola"),
        )
