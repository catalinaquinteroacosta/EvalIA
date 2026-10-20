import pytest

from backend.evaluators.gd.gd_scoring import (
    VerifiedLevel,
    score_verified_level,
    POSITIVE_MAP,
    GUARDRAIL_MAP,
)


@pytest.mark.parametrize(
    "code",
    ["GD1", "GD3", "GD4", "GD5", "GD8"],
)
@pytest.mark.parametrize("level,score", POSITIVE_MAP.items())
def test_positive_levels(code, level, score):
    result = score_verified_level(
        VerifiedLevel(code, level, True, "Verificado"),
        applicable=True,
        response_evaluable=True,
    )
    assert result.status == "SCORED"
    assert result.score == score


@pytest.mark.parametrize(
    "code",
    ["GD2", "GD6", "GD7"],
)
@pytest.mark.parametrize("level,score", GUARDRAIL_MAP.items())
def test_guardrail_levels(code, level, score):
    result = score_verified_level(
        VerifiedLevel(code, level, True, "Verificado"),
        applicable=True,
        response_evaluable=True,
    )
    assert result.status == "SCORED"
    assert result.score == score


@pytest.mark.parametrize("code", ["GD5", "GD7"])
def test_conditional_na(code):
    level = (
        "clear_prohibited_conduct"
        if code == "GD7"
        else "absent_or_contrary"
    )
    result = score_verified_level(
        VerifiedLevel(code, level, True, "Verificado"),
        applicable=False,
        response_evaluable=True,
    )
    assert result.status == "NA"
    assert result.score is None


def test_general_na_not_automatic():
    result = score_verified_level(
        VerifiedLevel(
            "GD1", "absent_or_contrary", True, "Verificado"
        ),
        applicable=False,
        response_evaluable=True,
    )
    assert result.status == "BLOCKED"


def test_unverified_level_blocks():
    result = score_verified_level(
        VerifiedLevel(
            "GD2",
            "consistent_no_observable_exception",
            False,
            "Pendiente",
        ),
        applicable=True,
        response_evaluable=True,
    )
    assert result.status == "BLOCKED"


def test_missing_response_blocks():
    result = score_verified_level(
        VerifiedLevel(
            "GD6",
            "consistent_no_observable_exception",
            True,
            "Verificado",
        ),
        applicable=True,
        response_evaluable=False,
    )
    assert result.status == "BLOCKED"


def test_material_contradiction_blocks_three():
    result = score_verified_level(
        VerifiedLevel(
            "GD6",
            "consistent_no_observable_exception",
            True,
            "Conflicto",
            contradiction="Afirmación contraria verificada",
        ),
        applicable=True,
        response_evaluable=True,
    )
    assert result.status == "BLOCKED"


def test_wrong_level_family_rejected():
    with pytest.raises(ValueError):
        VerifiedLevel(
            "GD6",
            "complete_contextual_fulfillment",
            True,
            "Nivel incorrecto",
        )


def test_unverified_applicability_blocks():
    result = score_verified_level(
        VerifiedLevel(
            "GD5", "absent_or_contrary", True, "Verificado"
        ),
        applicable=False,
        response_evaluable=True,
        applicability_verified=False,
    )
    assert result.status == "BLOCKED"
