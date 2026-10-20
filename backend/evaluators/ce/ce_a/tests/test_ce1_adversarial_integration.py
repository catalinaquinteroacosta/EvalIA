"""Pruebas adversariales de coherencia de CE1."""

from unittest.mock import patch

import pytest

from backend.evaluators.ce.ce_a import (
    ce1_final_decision as mod,
)


def evaluate(*, coverage, relevance, deviation=False,
             issues=None, fragments=None):
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
            for evidence, verdict in (fragments or [])
        ],
    }

    classification = {
        "primary_relevance": relevance,
        "total_deviation": deviation,
        "issues": issues or [],
        "analysis_complete": True,
    }

    with (
        patch.object(
            mod, "evaluate_ce1_integrated",
            return_value=integrated,
        ),
        patch.object(
            mod, "classify_ce1_relevance",
            return_value=classification,
        ),
    ):
        return mod.decide_ce1(
            user_text="Ayudame a preparar una entrevista.",
            response_text=(
                "Practica tus respuestas. "
                "Los volcanes son interesantes."
            ),
        )


def test_major_issue_cannot_coexist_with_full_relevance():
    result = evaluate(
        coverage="addressed",
        relevance="fully_related",
        issues=[{
            "description": "Desvio importante",
            "impact": "major",
            "evidence": "Los volcanes son interesantes.",
        }],
        fragments=[(
            "Los volcanes son interesantes.",
            "unnecessary_digression",
        )],
    )
    assert result["score"] is None


def test_total_deviation_cannot_have_primary_coverage():
    for coverage in (
        "addressed", "partially_addressed"
    ):
        result = evaluate(
            coverage=coverage,
            relevance="unrelated",
            deviation=True,
        )
        assert result["score"] is None


def test_verified_unnecessary_fragment_requires_issue():
    result = evaluate(
        coverage="addressed",
        relevance="fully_related",
        fragments=[(
            "Los volcanes son interesantes.",
            "unnecessary_digression",
        )],
    )
    assert result["score"] is None


def test_useful_complement_allows_maximum():
    result = evaluate(
        coverage="addressed",
        relevance="fully_related",
        fragments=[(
            "Practica tus respuestas.",
            "useful_complement",
        )],
    )
    assert result["score"] == 3


def test_full_relevance_with_minor_issue_is_inconsistent():
    result = evaluate(
        coverage="addressed",
        relevance="fully_related",
        issues=[{
            "description": "Digresion menor",
            "impact": "minor",
            "evidence": "Los volcanes son interesantes.",
        }],
        fragments=[(
            "Los volcanes son interesantes.",
            "unnecessary_digression",
        )],
    )
    assert result["score"] is None
