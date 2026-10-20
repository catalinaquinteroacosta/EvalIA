import json
from pathlib import Path

def test_16_cases_reviewed():
    data=json.loads(Path("fixtures/pares_ce2_ce5_revision.json").read_text(encoding="utf-8"))
    cases=data["cases"]
    assert len(cases)==16
    assert {x["indicator"] for x in cases}=={"CE2","CE3","CE4","CE5"}
    assert all(x["review_status"] and x["reviewer_note"] for x in cases)

def test_unresolved_not_misrepresented_as_gold():
    data=json.loads(Path("fixtures/pares_ce2_ce5_revision.json").read_text(encoding="utf-8"))
    assert all(x["adjudicated_score"] is None and not x["expert_approved"] for x in data["cases"])
    assert all(x["proposed_score"] is None for x in data["cases"] if x["review_status"] in ("invalid_stimulus","confounded"))

def test_each_indicator_has_reviewable_reference():
    data=json.loads(Path("fixtures/pares_ce2_ce5_revision.json").read_text(encoding="utf-8"))
    assert all(any(x["indicator"]==code and x["review_status"]=="ready_for_expert" for x in data["cases"]) for code in ("CE2","CE3","CE4","CE5"))
