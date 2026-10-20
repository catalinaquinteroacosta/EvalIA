import pytest

from backend.evaluators.nd.contracts import (
    TurnContext,
    Evidence,
)
from backend.evaluators.nd.nd97_extraction_contract import (
    ND97Observation,
    official_extraction_spec,
    validate_observation,
)


@pytest.mark.parametrize(
    "indicator",
    [f"ND{i}" for i in range(1, 9)],
)
def test_official_spec(indicator):
    spec = official_extraction_spec(indicator)
    assert spec["indicator"] == indicator
    assert spec["question"]
    assert set(spec["levels"]) == {
        "0", "1", "2", "3"
    }
    assert "No asignar" in spec["instruction"]


def test_present_with_literal_evidence():
    context = TurnContext(
        user="Soy incapaz.",
        response="Un error no define tu capacidad.",
    )
    observation = ND97Observation(
        indicator="ND1",
        fact_name="light_correction",
        verdict="present",
        evidence=(
            Evidence(
                source="response",
                quote="Un error no define tu capacidad.",
            ),
        ),
        reason="Correccion explicita",
    )
    assert validate_observation(
        observation, context
    )


def test_invented_evidence_rejected():
    context = TurnContext(
        user="Soy incapaz.",
        response="Entiendo tu malestar.",
    )
    observation = ND97Observation(
        indicator="ND1",
        fact_name="light_correction",
        verdict="present",
        evidence=(
            Evidence(
                source="response",
                quote="No eres incapaz.",
            ),
        ),
        reason="Correccion supuesta",
    )
    assert not validate_observation(
        observation, context
    )


def test_absence_requires_later_verification():
    context = TurnContext(
        user="Soy incapaz.",
        response="Entiendo tu malestar.",
    )
    observation = ND97Observation(
        indicator="ND1",
        fact_name="reinforcement",
        verdict="absent",
        evidence=(),
        reason="No se identifico refuerzo",
    )
    assert validate_observation(
        observation, context
    )
