"""Conexion de la decision CE1 con puntuacion Python."""

from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a import (
    ce1_final_decision as decision,
)
from backend.evaluators.ce.ce_a.ce1_scoring import (
    CE1ScoringError,
    score_ce1,
)


USER = "Ayudame a preparar una entrevista."
RESPONSE = (
    "Practica tus respuestas. "
    "Los volcanes son interesantes."
)
DIGRESSION = "Los volcanes son interesantes."


def evaluate(coverage, relevance, issues=(),
             deviation=False, fragments=()):
    integrated = {
        "status": "evidence_integrated",
        "primary_need": "Preparar una entrevista",
        "primary_coverage": coverage,
        "fragments": [
            {
                "verification": {
                    "status": "verified",
                    "interpretation": "Fragmento comprobado",
                    "evidence": evidence,
                    "decision": {
                        "verified": True,
                        "verdict": verdict,
                    },
                }
            }
            for evidence, verdict in fragments
        ],
    }

    classification = {
        "primary_relevance": relevance,
        "total_deviation": deviation,
        "issues": list(issues),
        "analysis_complete": True,
    }

    with (
        patch.object(
            decision,
            "evaluate_ce1_integrated",
            return_value=integrated,
        ),
        patch.object(
            decision,
            "classify_ce1_relevance",
            return_value=classification,
        ),
    ):
        return decision.decide_ce1(
            user_text=USER,
            response_text=RESPONSE,
        )


def issue(impact):
    return {
        "description": "Digresion comprobada",
        "impact": impact,
        "evidence": DIGRESSION,
        "context_justification": (
            "La informacion se aparta "
            "de la necesidad principal."
        ),
    }


@pytest.mark.parametrize(
    "coverage,relevance,issues,deviation,"
    "fragments,expected",
    [
        (
            "unaddressed", "unrelated",
            [], True, [], 0,
        ),
        (
            "addressed", "partially_related",
            [issue("major")], False,
            [(DIGRESSION, "unnecessary_digression")],
            1,
        ),
        (
            "addressed", "partially_related",
            [issue("minor")], False,
            [(DIGRESSION, "unnecessary_digression")],
            2,
        ),
        (
            "addressed", "fully_related",
            [], False,
            [(
                "Practica tus respuestas.",
                "relevant",
            )],
            3,
        ),
    ],
)
def test_four_scoring_routes(
    coverage, relevance, issues,
    deviation, fragments, expected,
):
    result = evaluate(
        coverage,
        relevance,
        issues,
        deviation,
        fragments,
    )
    assert result["status"] == "scored"
    assert result["score"] == expected


def test_no_maximum_with_verified_digression():
    result = evaluate(
        "addressed",
        "fully_related",
        fragments=[
            (
                DIGRESSION,
                "unnecessary_digression",
            )
        ],
    )
    assert result["score"] is None


def test_unverified_issue_rejected_by_python():
    with pytest.raises(CE1ScoringError):
        score_ce1(
            primary_coverage="addressed",
            issues=[{
                "description": "Incidencia",
                "impact": "minor",
                "evidence_verified": False,
            }],
            analysis_complete=True,
        )


def test_incomplete_analysis_cannot_score():
    result = score_ce1(
        primary_coverage="addressed",
        issues=[],
        analysis_complete=False,
    )
    assert result["score"] is None


def test_unaddressed_alone_does_not_mean_zero():
    result = score_ce1(
        primary_coverage="unaddressed",
        issues=[],
        analysis_complete=True,
    )
    assert result["score"] is None
    assert result["status"] == (
        "requires_total_deviation_check"
    )
