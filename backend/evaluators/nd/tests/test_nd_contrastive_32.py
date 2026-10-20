import json
from pathlib import Path

from backend.evaluators.nd.contracts import ND_CODES
from backend.evaluators.nd.official_rubric import LEVELS


FIXTURE = (
    Path("backend/evaluators/nd/fixtures")
    / "nd_contrastive_32.json"
)


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_exactly_32_cases():
    assert len(load()["cases"]) == 32


def test_each_indicator_has_four_hypotheses():
    cases = load()["cases"]

    for indicator in ND_CODES:
        levels = {
            case["hypothesis_level"]
            for case in cases
            if case["indicator"] == indicator
        }
        assert levels == {"0", "1", "2", "3"}


def test_descriptors_are_official():
    for case in load()["cases"]:
        assert (
            case["official_descriptor"]
            == LEVELS[case["hypothesis_level"]]
        )


def test_all_cases_have_unique_ids():
    ids = [case["id"] for case in load()["cases"]]
    assert len(ids) == len(set(ids))


def test_hypotheses_are_not_marked_validated():
    for case in load()["cases"]:
        assert case["review_status"] == "PENDING"


def test_contexts_are_nonempty():
    for case in load()["cases"]:
        assert case["user"].strip()
        assert case["response"].strip()
        assert case["prior_history"] == []
