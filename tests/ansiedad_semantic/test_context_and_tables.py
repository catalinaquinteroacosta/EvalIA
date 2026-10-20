import json
import csv
import pytest
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn, authorized_context
from backend.evaluators.ansiedad_semantic.result_tables import aggregate, export_new

def test_history_excludes_future_other_model_and_conversation():
    originals = [OriginalTurn(c,m,t,f"{c}/{m}/{t}",f"respuesta {c}/{m}/{t}")
                 for c in ("72","other") for m in ("A","B") for t in (1,2,3)]
    payload = authorized_context(originals,"72","A",2)
    assert payload["prior_history"] == [{"role":"user","text":"72/A/1"},
                                         {"role":"assistant","text":"respuesta 72/A/1"}]
    changed = [OriginalTurn(r.conversation,r.model,r.turn,r.user,"futuro cambiado")
               if r.turn == 3 else r for r in originals]
    assert authorized_context(changed,"72","A",2) == payload

def test_history_gaps_and_duplicate_identity_rejected():
    a = OriginalTurn("72","A",1,"usuario","respuesta")
    with pytest.raises(ValueError): authorized_context([a,a],"72","A",1)
    with pytest.raises(ValueError): authorized_context([a],"72","A",2)

def scored(n): return {"status":"SCORED","score":n,"applicability":"APPLICABLE"}
def na(): return {"status":"N/A","score":None,"applicability":"NOT_APPLICABLE","gate_reason":"Condición oficial ausente verificada"}

def test_na_excluded_zero_included():
    result = aggregate([scored(3),scored(0),na()])
    assert result["percentage"] == 50 and result["scored_denominator"] == 6

@pytest.mark.parametrize("state", ["BLOCKED","PENDING"])
def test_unresolved_never_complete_percent(state):
    result = aggregate([scored(3),{"status":state,"score":None}])
    assert result["percentage"] is None and not result["complete"]
    assert result["scored_denominator"] == 3

def test_missing_expected_rows_incomplete():
    assert aggregate([scored(3)],expected_count=2)["percentage"] is None

@pytest.mark.parametrize("row", [
    {"status":"N/A","score":None,"applicability":"APPLICABLE","gate_reason":"omisión"},
    {"status":"SCORED","score":True,"applicability":"APPLICABLE"},
    {"status":"BLOCKED","score":0},
    {"status":"SCORED","score":3,"applicability":"NOT_APPLICABLE"}])
def test_invalid_conversion_rejected(row):
    with pytest.raises(ValueError): aggregate([row])

def test_export_roundtrip_and_preservation(tmp_path):
    rows = [scored(0),scored(3),na()]
    export_new(tmp_path,rows)
    assert json.loads((tmp_path/"observations.json").read_text(encoding="utf-8")) == rows
    with (tmp_path/"observations.csv").open(encoding="utf-8",newline="") as source:
        values = list(csv.DictReader(source))
    assert [row["score"] for row in values] == ["0","3",""]
    with pytest.raises(FileExistsError): export_new(tmp_path,rows)
