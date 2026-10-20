from copy import deepcopy
from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a import (
    ce1_final_decision as mod,
)


def integrated(coverage="addressed", fragments=None):
    return {
        "status": "evidence_integrated",
        "primary_need": "Preparar entrevista",
        "primary_coverage": coverage,
        "fragments": fragments or [],
    }


def fragment(verdict):
    return {
        "verification": {
            "status": "verified",
            "interpretation": "Comentario adicional",
            "evidence": "Los volcanes son interesantes.",
            "decision": {
                "verified": True,
                "verdict": verdict,
            },
        },
    }


def classification(
    relevance="fully_related",
    deviation=False,
    issues=None,
):
    return {
        "primary_relevance": relevance,
        "total_deviation": deviation,
        "issues": issues or [],
        "analysis_complete": True,
    }


def issue(impact="minor"):
    return {
        "description": "Digresion innecesaria",
        "impact": impact,
        "evidence": "Los volcanes son interesantes.",
    }


def run(integrated_result, classified_result):
    with (
        patch.object(
            mod,
            "evaluate_ce1_integrated",
            return_value=integrated_result,
        ),
        patch.object(
            mod,
            "classify_ce1_relevance",
            return_value=classified_result,
        ),
    ):
        return mod.decide_ce1(
            user_text="Ayudame con una entrevista.",
            response_text=(
                "Practica tus respuestas. "
                "Los volcanes son interesantes."
            ),
        )


def test_full_relevance_scores_three():
    assert run(
        integrated(),
        classification(),
    )["score"] == 3


@pytest.mark.parametrize(
    "impact,expected",
    [
        ("minor", 2),
        ("major", 1),
    ],
)
def test_verified_digression_impact(impact, expected):
    result = run(
        integrated(
            fragments=[
                fragment("unnecessary_digression")
            ]
        ),
        classification(
            relevance="partially_related",
            issues=[issue(impact)],
        ),
    )
    assert result["score"] == expected


def test_unclassified_digression_blocks_three():
    result = run(
        integrated(
            fragments=[
                fragment("unnecessary_digression")
            ]
        ),
        classification(),
    )
    assert result["score"] is None


def test_useful_complement_does_not_penalize():
    result = run(
        integrated(
            fragments=[
                fragment("useful_complement")
            ]
        ),
        classification(),
    )
    assert result["score"] == 3


def test_total_deviation_scores_zero():
    result = run(
        integrated("unaddressed"),
        classification(
            relevance="unrelated",
            deviation=True,
        ),
    )
    assert result["score"] == 0


def test_unaddressed_is_not_automatically_zero():
    result = run(
        integrated("unaddressed"),
        classification(
            relevance="unrelated",
            deviation=False,
        ),
    )
    assert result["score"] is None


def test_contradiction_blocks_zero():
    result = run(
        integrated("addressed"),
        classification(
            relevance="unrelated",
            deviation=True,
        ),
    )
    assert result["score"] is None


def test_ce2_omission_does_not_lower_ce1():
    result = run(
        integrated("partially_addressed"),
        classification(),
    )
    assert result["score"] == 3


def test_incomplete_evidence_blocks_scoring():
    data = integrated()
    data["status"] = "review_required"

    result = run(data, classification())
    assert result["score"] is None
