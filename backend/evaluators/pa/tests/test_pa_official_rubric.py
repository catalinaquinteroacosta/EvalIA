import copy
import json

import pytest

from backend.evaluators.pa.contracts import CODES
from backend.evaluators.pa.official_rubric import (
    RUBRIC_PATH,
    indicator_definition,
    load_official_pa,
)


def test_official_rubric_has_eight_indicators():
    criterion = load_official_pa()
    assert tuple(
        item["code"] for item in criterion["indicators"]
    ) == CODES


@pytest.mark.parametrize("code", CODES)
def test_official_question_available(code):
    item = indicator_definition(code)
    assert item["code"] == code
    assert "¿" in item["question"] and item["question"].endswith("?")


@pytest.mark.parametrize("code", ("PA2", "PA3", "PA8"))
def test_conditional_indicators(code):
    assert (
        indicator_definition(code)["applicability"]
        == "conditional"
    )


@pytest.mark.parametrize(
    "code",
    ("PA1", "PA4", "PA5", "PA6", "PA7"),
)
def test_general_indicators(code):
    assert (
        indicator_definition(code)["applicability"]
        == "general"
    )


def test_modified_applicability_rejected(tmp_path):
    data = json.loads(
        RUBRIC_PATH.read_text(encoding="utf-8-sig")
    )
    altered = copy.deepcopy(data)

    criterion = next(
        c for c in altered["criteria"]
        if c["code"] == "AD-05"
    )
    criterion["indicators"][0]["applicability"] = (
        "conditional"
    )

    path = tmp_path / "altered.json"
    path.write_text(
        json.dumps(altered, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_official_pa(path)


def test_missing_indicator_rejected(tmp_path):
    data = json.loads(
        RUBRIC_PATH.read_text(encoding="utf-8-sig")
    )

    criterion = next(
        c for c in data["criteria"]
        if c["code"] == "AD-05"
    )
    criterion["indicators"].pop()

    path = tmp_path / "incomplete.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_official_pa(path)
