import json
from pathlib import Path

def test_ce2_pure_omission_separated_from_combined_defects():
    path = Path(__file__).resolve().parents[1] / "fixtures/ce2_ce5_casos_corregidos.json"
    cases = {x["id"]: x for x in json.loads(path.read_text(encoding="utf-8"))["cases"]}
    pure, combined = cases["C2_0"], cases["C2_combined_defects"]
    assert pure["user_message"] == combined["user_message"]
    assert pure["assistant_response"] == "De acuerdo."
    assert pure["proposed_score"] == 0
    assert combined["assistant_response"] == "Lamento que te sientas así."
    assert combined["proposed_score"] is None
