
import json
from pathlib import Path

import pytest


RUBRIC_PATH = Path(
    "database/rubrics/ansiedad_depresion.json"
)

REPORTS = Path("backend/evaluators/cp/reports")

EXPECTED = {
    "CP1": "general",
    "CP2": "general",
    "CP3": "conditional",
    "CP4": "general",
    "CP5": "general",
    "CP6": "conditional",
    "CP7": "general",
    "CP8": "conditional",
}


@pytest.fixture(scope="module")
def criterion():
    data = json.loads(
        RUBRIC_PATH.read_text(encoding="utf-8-sig")
    )
    return next(
        item for item in data["criteria"]
        if item["code"] == "AD-02"
    )


def test_a847_official_criterion(criterion):
    official = json.loads(
        (
            REPORTS
            / "cp_a846_official_contract"
            / "cp_official_contract.json"
        ).read_text(encoding="utf-8-sig")
    )["criterion"]

    assert criterion["code"] == "AD-02"
    assert criterion["name"] == official["name"]



def test_a847_official_levels(criterion):
    official = json.loads(
        (
            REPORTS
            / "cp_a846_official_contract"
            / "cp_official_contract.json"
        ).read_text(encoding="utf-8-sig")
    )["criterion"]

    assert set(criterion["levels"]) == {
        "0", "1", "2", "3"
    }
    assert criterion["levels"] == official["levels"]



@pytest.mark.parametrize(
    "code,applicability",
    list(EXPECTED.items()),
)
def test_a847_indicator_applicability(
    criterion, code, applicability
):
    indicators = {
        item["code"]: item
        for item in criterion["indicators"]
    }

    assert set(indicators) == set(EXPECTED)
    assert indicators[code]["applicability"] == applicability


def test_a847_cp7_real_validation():
    path = (
        REPORTS
        / "cp_a840_cp7_revalidation"
        / "cp7_result.json"
    )

    data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    assert data["cp7_state"]["status"] == "validated"
    assert data["cp7_score"]["status"] == "scored"
    assert data["cp7_score"]["score"] == 3
    assert not data["cp7_state"]["blocked_components"]


def test_a847_cp3_remains_blocked():
    path = REPORTS / "cp_a841_integrated_pilot.json"

    data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    cp3 = data["results"]["CP3"]

    assert cp3["status"] == "blocked"
    assert cp3["score"] is None
    assert cp3["invariant_candidate"] == 0
    assert cp3["invariant_is_not_validation"] is True


def test_a847_integrated_pilot():
    path = REPORTS / "cp_a841_integrated_pilot.json"

    data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    assert data["scored_count"] == 7
    assert data["blocked_codes"] == ["CP3"]
    assert data["family_fully_validated"] is False
    assert data["contrastive_acceptance_completed"] is False

    expected_scores = {
        "CP1": 2,
        "CP2": 1,
        "CP4": 0,
        "CP5": 0,
        "CP6": 0,
        "CP7": 3,
        "CP8": 0,
    }

    for code, score in expected_scores.items():
        assert data["results"][code]["status"] == "scored"
        assert data["results"][code]["score"] == score


def test_a847_wrong_criterion_not_accepted():
    path = (
        REPORTS
        / "cp_a846_official_contract"
        / "cp_official_contract.json"
    )

    data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    assert data["criterion"]["code"] == "AD-02"
    assert data["previous_a845_valid_for_cp"] is False
