"""IR production route tests with declared simulated semantic readers."""
import copy
import json
import pytest
from backend.evaluators.ansiedad_semantic.functional_review import IR_ATOMS, definitions, adjudicate
from backend.evaluators.nd.contracts import TurnContext

def reader(code, number):
    active = set()
    if number > 0: active.add("recognizable_behavior")
    if number > 1: active.add("central_function_realized"); active.update(IR_ATOMS[code])
    if number == 2: active.add("secondary_precision_or_adaptation_defect")
    if number == 3: active.update(IR_ATOMS[code]); active.add("clear_specific_contextual_execution")
    if code == "IR8": active.add("gate_present")
    return {"components":{name:{"value":name in active,
        "evidence":[{"source":"response","quote":"Respuesta evaluable","history_index":None}],
        "counterevidence":[],"complete_response_reviewed":True,
        "reason":"Observación simulada para probar contrato"} for name in definitions(code)}}

@pytest.mark.parametrize("code", IR_ATOMS)
@pytest.mark.parametrize("number",range(4))
def test_docx_four_levels(code,number):
    context = TurnContext("Relato evaluable","Respuesta evaluable")
    r=reader(code,number)
    result=adjudicate(code,context,r,copy.deepcopy(r))
    assert (result["status"],result["score"]) == ("SCORED",number)

@pytest.mark.parametrize("code",IR_ATOMS)
def test_full_requires_every_construct_atom(code):
    r=reader(code,3); r["components"][next(iter(IR_ATOMS[code]))]["value"]=False
    assert adjudicate(code,TurnContext("Relato","Respuesta evaluable"),r,r)["status"] == "BLOCKED"

@pytest.mark.parametrize("defect",["unknown","disagree","literal","review","ordinal","missing"])
def test_independent_evidence_failure_blocks(defect):
    a=reader("IR6",3);b=copy.deepcopy(a)
    row=b["components"]["thought_utility_explored"]
    if defect=="unknown": row["value"]=None
    if defect=="disagree": row["value"]=False
    if defect=="literal": row["evidence"][0]["quote"]="inventada"
    if defect=="review": row["complete_response_reviewed"]=False
    if defect=="ordinal": b["components"]["level_3_matches"]={}
    if defect=="missing": b["components"].pop("thought_utility_explored")
    assert adjudicate("IR6",TurnContext("Relato","Respuesta evaluable"),a,b)["status"] == "BLOCKED"

def test_ir8_absent_gate_na_not_omission():
    r=reader("IR8",0);r["components"]={"gate_present":r["components"]["gate_present"]}
    r["components"]["gate_present"]["value"]=False
    assert adjudicate("IR8",TurnContext("Relato","Respuesta evaluable"),r,r)["status"] == "N/A"

def test_real_route_uses_blind_components_then_python(monkeypatch):
    from backend.evaluators.ir.core import level_engine
    from backend.evaluators.ir.core.contracts import Context
    calls=[]
    def fake(system,payload):
        request=json.loads(payload["request"])
        calls.append(request)
        assert "proposed_level" not in request and "extraction" not in request
        return reader("IR6",3)
    monkeypatch.setattr(level_engine,"ask_openai",fake)
    result=level_engine.evaluate_level(Context("Relato","Respuesta evaluable"),"IR6",[{"status":"supported"}])
    assert (result["status"],result["score"],result["verified_level"]) == ("VERIFIED",3,"high")
    assert [c["stage"] for c in calls] == ["extract","independent_verify"]

def test_real_route_ordinal_response_rejected(monkeypatch):
    from backend.evaluators.ir.core import level_engine
    from backend.evaluators.ir.core.contracts import Context
    monkeypatch.setattr(level_engine,"ask_openai",lambda *a:{"level":"high","reason":"ordinal","evidence":[]})
    assert level_engine.evaluate_level(Context("Relato","Respuesta evaluable"),"IR1",[{"status":"supported"}])["status"] == "BLOCKED"
