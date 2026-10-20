import pytest

from backend.evaluators.pa.criterion_ad05 import (
    official_criterion,
    evaluate_indicators,
    score_criterion,
)


def records():
    rubric = official_criterion()
    return {
        x["code"]: {
            "state": "SUPPORTED",
            "reason": "Evidencia verificada",
            "evidence": [{
                "source": "response",
                "quote": "Elige una tarea."
            }],
            "independent_verification": True,
        }
        for x in rubric["indicators"]
    }


def review(level=3):
    return {
        "level": level,
        "reason": "Contraste semantico independiente",
        "quotes": ["Elige una tarea."],
        "independent_verification": True,
        "descriptor_checks": {
            str(i): (
                "supported" if i == level
                else "unsupported"
            )
            for i in range(4)
        },
    }


def score(items=None, level_review=None):
    return score_criterion(
        items if items is not None else records(),
        level_review if level_review is not None else review(),
        response="Elige una tarea.",
        user="Tengo muchas tareas.",
        prior_history=[],
    )


def test_contract_has_eight_indicators():
    assert len(official_criterion()["indicators"]) == 8


def test_official_levels():
    assert set(official_criterion()["levels"]) == {
        "0", "1", "2", "3"
    }


def test_indicators_have_no_numeric_scores():
    result = evaluate_indicators(records())
    assert all(x["score"] is None for x in result.values())


def test_general_cannot_be_na():
    items = records()
    items["PA1"]["state"] = "N/A"
    assert evaluate_indicators(items)["PA1"]["state"] == "BLOCKED"


def test_conditional_can_be_na():
    items = records()
    items["PA2"]["state"] = "N/A"
    assert evaluate_indicators(items)["PA2"]["state"] == "N/A"


def test_unverified_indicator_blocks():
    items = records()
    items["PA4"]["independent_verification"] = False
    assert score(items)["status"] == "BLOCKED"


def test_ambiguous_level_blocks():
    r = review()
    r["descriptor_checks"]["2"] = "ambiguous"
    assert score(level_review=r)["status"] == "BLOCKED"


def test_two_supported_levels_block():
    r = review()
    r["descriptor_checks"]["2"] = "supported"
    assert score(level_review=r)["status"] == "BLOCKED"


def test_missing_level_verification_blocks():
    r = review()
    r["independent_verification"] = False
    assert score(level_review=r)["status"] == "BLOCKED"


def test_nonliteral_level_evidence_blocks():
    r = review()
    r["quotes"] = ["Texto que no existe"]
    assert score(level_review=r)["status"] == "BLOCKED"


@pytest.mark.parametrize("level", range(4))
def test_four_levels_accept_verified_contract(level):
    result = score(level_review=review(level))
    assert result["status"] == "SCORED"
    assert result["score"] == level
    assert result["official_descriptor"] == (
        official_criterion()["levels"][str(level)]
    )
