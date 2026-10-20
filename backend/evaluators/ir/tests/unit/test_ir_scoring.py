import pytest

from backend.evaluators.ir.core.scoring import (
    load_ir_rubric,
    score_indicator,
)


def test_official_family_loaded():
    rubric = load_ir_rubric()
    assert len(rubric["indicators"]) == 8
    assert rubric["version"] == "2.0"


@pytest.mark.parametrize(
    "level,expected",
    [
        ("absent", 0),
        ("low", 1),
        ("adequate", 2),
        ("high", 3),
    ],
)
def test_verified_levels(level, expected):
    result = score_indicator(
        "IR1",
        applicability="applicable",
        verified_level=level,
        evidence_valid=True,
    )
    assert result["score"] == expected
    assert result["status"] == "SCORED"


def test_ir8_not_applicable():
    result = score_indicator(
        "IR8",
        applicability="not_applicable",
    )
    assert result["status"] == "N/A"
    assert result["score"] is None


def test_ir5_not_applicable_forbidden():
    result = score_indicator(
        "IR5",
        applicability="not_applicable",
    )
    assert result["status"] == "BLOCKED"


def test_ambiguous_applicability_blocks():
    result = score_indicator(
        "IR8",
        applicability="ambiguous",
    )
    assert result["status"] == "BLOCKED"


def test_unresolved_blocks():
    result = score_indicator(
        "IR6",
        applicability="applicable",
        verified_level="high",
        evidence_valid=True,
        unresolved=True,
    )
    assert result["status"] == "BLOCKED"


def test_unverified_positive_evidence_blocks():
    result = score_indicator(
        "IR4",
        applicability="applicable",
        verified_level="high",
        evidence_valid=False,
    )
    assert result["status"] == "BLOCKED"


def test_missing_level_blocks():
    result = score_indicator(
        "IR7",
        applicability="applicable",
        evidence_valid=True,
    )
    assert result["status"] == "BLOCKED"