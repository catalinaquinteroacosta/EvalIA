from pathlib import Path
import json
from backend.evaluators.ansiedad_semantic.validate_documentary import validate
from backend.evaluators.ansiedad_semantic.experiment072_manifest import build
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx"
CONTRACTS=ROOT/"docs/ansiedad_semantic/step2_20261012/contracts"

def test_independent_documentary_integrity():
    result=validate(SOURCE,CONTRACTS)
    assert result["documentary_integrity"] and result["indicators"]==81

def test_descriptor_tampering_is_detected(tmp_path):
    for p in CONTRACTS.glob("*.json"):
        data=json.loads(p.read_text(encoding="utf-8"))
        if p.stem=="ND":data["contracts"][0]["levels"]["3"]="Inventado"
        (tmp_path/p.name).write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    assert "ND1: level 3" in validate(SOURCE,tmp_path)["errors"]

def test_072_manifest_is_pending_and_history_exact():
    result=build(ROOT)
    assert len(result["tasks"])==2025 and not result["history_errors"]
    assert all(t["status"]=="PENDING" and t["score"] is None for t in result["tasks"])
    assert result["evaluations_executed"]==0
