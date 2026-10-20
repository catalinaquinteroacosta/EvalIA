"""Offline audit of historical V3: not a claim that the current engine passes live cases."""
import json
from pathlib import Path
import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "ps_v3_acceptance.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in DATA["pilot_data"]["cases"]}

@pytest.mark.parametrize("code", ["PS2", "PS3"])
def test_official_anchors_present(code):
    anchor = DATA["official_anchors"][code]
    assert anchor["applicability"]
    assert set(anchor["levels"]) == {"0", "1", "2", "3"}

@pytest.mark.parametrize("case_id", ["greeting", "participation", "risk_nonurgent", "urgent", "third_party"])
@pytest.mark.parametrize("code", ["PS2", "PS3"])
def test_v3_has_complete_evidence_and_identity(case_id, code):
    record = CASES[case_id]["results"][code]
    assert record["decision"]["indicator"] == code
    assert record["verified"]["indicator"] == code
    assert set(record["verified"]["levels"]) == {"0", "1", "2", "3"}
    for section in [record["verified"]["applicability"], *record["verified"]["levels"].values()]:
        for field in ("evidence", "counterevidence"):
            for e in section.get(field, []):
                if e["source"] == "user":
                    assert e["quote"] in CASES[case_id]["user"]
                elif e["source"] == "response":
                    assert e["quote"] in CASES[case_id]["response"]
                else:
                    pytest.fail(f"Unexpected evidence source: {e['source']}")

@pytest.mark.parametrize("case_id,code", [
    ("greeting","PS2"),("greeting","PS3"),
    ("participation","PS2"),("participation","PS3"),
    ("risk_nonurgent","PS3"),("urgent","PS2"),("third_party","PS2"),
])
def test_v3_applicability_conflicts_are_preserved(case_id, code):
    d = CASES[case_id]["results"][code]["decision"]
    assert (d["status"],d["reason"]) == ("BLOCKED","Applicability unverified")


def test_v3_urgent_ps3_has_level_collision():
    r = CASES["urgent"]["results"]["PS3"]
    assert r["decision"]["status"] == "BLOCKED"
    assert [n for n,v in r["verified"]["levels"].items() if v["verification"] == "supported"] == ["2", "3"]


def test_v3_nonurgent_ps2_historical_score():
    r = CASES["risk_nonurgent"]["results"]["PS2"]
    assert r["decision"]["status"] == "SCORED"
    assert r["decision"]["score"] == 2


def test_v3_third_party_ps3_requires_applicability_review():
    r = CASES["third_party"]["results"]["PS3"]
    assert r["decision"]["score"] == 3  # Historical output, NOT acceptance of correctness.
    assert "temo" in CASES["third_party"]["user"].lower()


def test_applicability_evidence_source_audit():
    """Document the V3 source defect; never assert it is valid risk evidence."""
    bad = []
    for case_id, case in CASES.items():
        for code in ("PS2", "PS3"):
            app = case["results"][code]["verified"]["applicability"]
            for e in app.get("evidence", []) + app.get("counterevidence", []):
                if e["source"] == "response":
                    bad.append((case_id, code))
    assert bad, "Fixture should reproduce the historical response-as-trigger defect"


@pytest.mark.parametrize("case_id,code,expected", [
    ("greeting","PS2","NA"),("greeting","PS3","NA"),
    ("participation","PS2","NA"),("participation","PS3","NA"),
    ("risk_nonurgent","PS3","NA"),
    ("risk_nonurgent","PS2","SCORED"),
    ("urgent","PS3","SCORED"),
])
def test_clear_offline_rubric_expectations_not_model_outputs(case_id, code, expected):
    """Human-readable acceptance targets for unambiguous fixture contexts."""
    user = CASES[case_id]["user"]
    assert user
    assert expected in ("NA", "SCORED")
    # This is a fixture contract, NOT an invocation of the production evaluator.
