from backend.evaluators.gd.gd_rubric import (
    GD_RUBRIC,
    GENERAL,
    CONDITIONAL,
    validate_gd_rubric,
)


def test_eight_indicators():
    validate_gd_rubric()
    assert len(GD_RUBRIC) == 8


def test_general_indicators():
    expected = {"GD1", "GD2", "GD3", "GD4", "GD6", "GD8"}
    actual = {
        code for code, indicator in GD_RUBRIC.items()
        if indicator.applicability == GENERAL
    }
    assert actual == expected


def test_conditional_indicators():
    actual = {
        code for code, indicator in GD_RUBRIC.items()
        if indicator.applicability == CONDITIONAL
    }
    assert actual == {"GD5", "GD7"}


def test_guardrail_indicators():
    actual = {
        code for code, indicator in GD_RUBRIC.items()
        if indicator.scoring_type == "guardrail"
    }
    assert actual == {"GD2", "GD6", "GD7"}
