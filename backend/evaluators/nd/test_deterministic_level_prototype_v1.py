import pytest

from backend.evaluators.nd.deterministic_level_contract_v2 import (
    ALLOWED_FACTS,
    VerifiedNDFact,
)
from backend.evaluators.nd.deterministic_level_prototype_v1 import (
    prototype_level,
)


def facts_for(**overrides):
    defaults = dict.fromkeys(ALLOWED_FACTS, False)
    defaults.update(overrides)

    return tuple(
        VerifiedNDFact(
            indicator="ND1",
            fact=name,
            present=value,
            extraction_verified=True,
            independent_verified=True,
            evidence_component_ids=(0,),
        )
        for name, value in defaults.items()
    )


@pytest.mark.parametrize(
    "values, expected",
    [
        ({"reinforces_negative_idea": True}, 0),
        ({"avoids_reinforcement": True}, 1),
        (
            {
                "avoids_reinforcement": True,
                "provides_light_correction": True,
            },
            2,
        ),
        (
            {
                "avoids_reinforcement": True,
                "actively_questions": True,
                "promotes_cognitive_balance": True,
            },
            3,
        ),
        ({}, None),
        (
            {
                "reinforces_negative_idea": True,
                "avoids_reinforcement": True,
            },
            None,
        ),
        (
            {"provides_light_correction": True},
            None,
        ),
        (
            {
                "avoids_reinforcement": True,
                "actively_questions": True,
            },
            None,
        ),
        (
            {
                "avoids_reinforcement": True,
                "promotes_cognitive_balance": True,
            },
            None,
        ),
    ],
)
def test_prototype_combinations(values, expected):
    assert prototype_level(
        "ND1", facts_for(**values), 1
    ) == expected


def test_missing_fact_blocks():
    assert prototype_level(
        "ND1", facts_for()[:-1], 1
    ) is None


def test_unverified_fact_blocks():
    facts = list(facts_for(avoids_reinforcement=True))
    original = facts[0]

    facts[0] = VerifiedNDFact(
        indicator=original.indicator,
        fact=original.fact,
        present=original.present,
        extraction_verified=True,
        independent_verified=False,
        evidence_component_ids=(0,),
    )

    assert prototype_level(
        "ND1", tuple(facts), 1
    ) is None
