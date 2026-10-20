from unittest.mock import patch

from backend.evaluators.ce.ce_a import (
    ce1_final_decision as mod,
)


def run(*, fragments, issues):
    integrated = {
        "status": "evidence_integrated",
        "primary_need": "Preparar entrevista",
        "primary_coverage": "addressed",
        "fragments": [
            {
                "verification": {
                    "status": "verified",
                    "interpretation": "Fragmento analizado",
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
        "primary_relevance": "partially_related",
        "total_deviation": False,
        "issues": issues,
        "analysis_complete": True,
    }

    with (
        patch.object(
            mod,
            "evaluate_ce1_integrated",
            return_value=integrated,
        ),
        patch.object(
            mod,
            "classify_ce1_relevance",
            return_value=classification,
        ),
    ):
        return mod.decide_ce1(
            user_text="Ayudame con mi entrevista.",
            response_text=(
                "Practica tus respuestas. "
                "Los volcanes son interesantes."
            ),
        )


def issue(evidence):
    return {
        "description": "Desvio menor",
        "impact": "minor",
        "evidence": evidence,
    }


def test_verified_digression_can_support_issue():
    result = run(
        fragments=[
            (
                "Los volcanes son interesantes.",
                "unnecessary_digression",
            )
        ],
        issues=[
            issue("Los volcanes son interesantes.")
        ],
    )
    assert result["score"] == 2


def test_unverified_response_issue_cannot_score():
    result = run(
        fragments=[],
        issues=[
            issue("Los volcanes son interesantes.")
        ],
    )
    assert result["score"] is None


def test_relevant_fragment_cannot_support_issue():
    result = run(
        fragments=[
            (
                "Los volcanes son interesantes.",
                "relevant",
            )
        ],
        issues=[
            issue("Los volcanes son interesantes.")
        ],
    )
    assert result["score"] is None


def test_invented_issue_evidence_cannot_score():
    result = run(
        fragments=[],
        issues=[
            issue("Una frase que no existe.")
        ],
    )
    assert result["score"] is None
