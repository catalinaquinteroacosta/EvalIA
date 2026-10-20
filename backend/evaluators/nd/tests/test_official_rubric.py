import json
from pathlib import Path

import pytest

from backend.evaluators.nd.official_rubric import (
    EXPECTED_SHA256,
    LEVELS,
    load_official_nd_rubric,
)


def test_official_nd_complete():
    rubric = load_official_nd_rubric()

    assert rubric.criterion_code == "AD-04"
    assert set(rubric.indicators) == {
        f"ND{i}" for i in range(1, 9)
    }
    assert rubric.levels == LEVELS
    assert rubric.sha256 == EXPECTED_SHA256


def test_changed_descriptor_is_rejected(tmp_path):
    source = Path(
        "database/rubrics/ansiedad_depresion.json"
    )
    data = json.loads(
        source.read_text(encoding="utf-8-sig")
    )

    for criterion in data["criteria"]:
        if criterion.get("code") == "AD-04":
            criterion["levels"]["3"] = "CAMBIO NO AUTORIZADO"
            break

    modified = tmp_path / "modified.json"
    modified.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_official_nd_rubric(modified)


def test_changed_question_is_rejected(tmp_path):
    source = Path(
        "database/rubrics/ansiedad_depresion.json"
    )
    data = json.loads(
        source.read_text(encoding="utf-8-sig")
    )

    for criterion in data["criteria"]:
        if criterion.get("code") == "AD-04":
            criterion["indicators"][0]["question"] = "CAMBIO"
            break

    modified = tmp_path / "modified.json"
    modified.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_official_nd_rubric(modified)
