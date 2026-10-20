import pytest

from backend.evaluators.ce.ce_a.ce1_scoring import (
    CE1ScoringError,
    score_ce1,
)


def issue(impact):
    return {
        "description": "Falla de pertinencia verificada.",
        "impact": impact,
        "evidence_verified": True,
    }


@pytest.mark.parametrize(
    "coverage,issues,expected",
    [
        ("addressed", [], 3),
        ("addressed", [issue("minor")], 2),
        ("addressed", [issue("major")], 1),
        (
            "partially_addressed",
            [issue("minor")],
            2,
        ),
        (
            "partially_addressed",
            [issue("major")],
            1,
        ),
        (
            "addressed",
            [issue("minor"), issue("major")],
            1,
        ),
    ],
)
def test_verified_rubric_conditions(
    coverage, issues, expected
):
    result = score_ce1(
        primary_coverage=coverage,
        issues=issues,
        analysis_complete=True,
    )
    assert result["score"] == expected


def test_unaddressed_does_not_automatically_mean_zero():
    result = score_ce1(
        primary_coverage="unaddressed",
        issues=[],
        analysis_complete=True,
    )
    assert result["score"] is None
    assert result["status"] == (
        "requires_total_deviation_check"
    )


def test_ce2_omission_does_not_automatically_lower_ce1():
    result = score_ce1(
        primary_coverage="partially_addressed",
        issues=[],
        analysis_complete=True,
    )
    assert result["score"] is None


def test_incomplete_analysis_cannot_score():
    result = score_ce1(
        primary_coverage="addressed",
        issues=[],
        analysis_complete=False,
    )
    assert result["score"] is None


def test_unverified_issue_is_rejected():
    with pytest.raises(CE1ScoringError):
        score_ce1(
            primary_coverage="addressed",
            issues=[{
                "description": "Supuesto problema",
                "impact": "major",
                "evidence_verified": False,
            }],
            analysis_complete=True,
        )
