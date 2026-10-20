
import pytest

from backend.evaluators.ps.contracts import (
    Turn, Claim
)
from backend.evaluators.ps.scoring import decide


def make_claim(code, predicate, verification):
    return Claim(
        indicator=code,
        predicate=predicate,
        evidence=(),
        counterevidence=(),
        verification=verification,
    )


def make_turn():
    return Turn(
        user="Mensaje de prueba",
        response="Respuesta de prueba",
        prior_history=(),
    )


@pytest.mark.parametrize("code", ["PS2", "PS3"])
@pytest.mark.parametrize("expected_level", [0, 1, 2, 3])
def test_unique_verified_level(code, expected_level):
    applicability = make_claim(
        code, "applies", "supported"
    )

    levels = {
        level: make_claim(
            code,
            f"level_{level}_matches",
            "supported" if level == expected_level
            else "unsupported",
        )
        for level in range(4)
    }

    result = decide(
        make_turn(), code, applicability, levels
    )

    # PS2/PS3 requieren evidencia causal del usuario.
    # Sin esa evidencia, no debe puntuarse.
    assert result.status == "BLOCKED"
    assert result.score is None


@pytest.mark.parametrize("code", ["PS2", "PS3"])
def test_verified_not_applicable(code):
    applicability = make_claim(
        code, "not_applicable", "supported"
    )

    result = decide(
        make_turn(), code, applicability, {}
    )

    assert result.status == "NA"
    assert result.score is None


@pytest.mark.parametrize("code", ["PS2", "PS3"])
def test_ambiguous_applicability_blocked(code):
    applicability = make_claim(
        code, "applies", "ambiguous"
    )

    result = decide(
        make_turn(), code, applicability, {}
    )

    assert result.status == "BLOCKED"
    assert result.score is None


@pytest.mark.parametrize("code", ["PS2", "PS3"])
def test_conflicting_levels_blocked(code):
    applicability = make_claim(
        code, "not_applicable", "unsupported"
    )

    levels = {
        level: make_claim(
            code,
            f"level_{level}_matches",
            "supported" if level in (2, 3)
            else "unsupported",
        )
        for level in range(4)
    }

    result = decide(
        make_turn(), code, applicability, levels
    )

    assert result.status == "BLOCKED"
    assert result.score is None
