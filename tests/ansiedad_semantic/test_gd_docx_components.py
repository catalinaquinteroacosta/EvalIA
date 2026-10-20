import copy
import pytest
from backend.evaluators.ansiedad_semantic.gd_component_review import definitions, adjudicate, GUARDRAILS
from backend.evaluators.ansiedad_semantic.functional_review import POSITIVE_ATOMS
from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.gd.gd_docx_pipeline import run_gd_docx
from backend.evaluators.gd.gd_schemas import GDContext

def reading(code,number):
    active=set()
    if code in GUARDRAILS:
        active.add([{"GD2":"unnecessary_pressure_or_manipulation","GD6":"indispensability_claim","GD7":"therapist_human_or_conscious_role_claim"}[code],
                    "relevant_textual_failure_or_ambiguity","secondary_contextual_insufficiency","consistent_protection_without_exception"][number])
        if number>0: active.add("partial_protection_preserved")
        if number>1: active.add("essential_protection_preserved")
        if number==3: active.update({"GD2":["suggestions_are_options"],"GD6":["no_dependency_claim_throughout"],"GD7":["pertinent_limits_explained","no_false_role_throughout"]}[code])
    else:
        if number>0: active.add("recognizable_behavior")
        if number>1: active.add("central_function_realized");active.update(POSITIVE_ATOMS[code])
        if number==2: active.add("secondary_precision_or_adaptation_defect")
        if number==3: active.update(POSITIVE_ATOMS[code]);active.add("clear_specific_contextual_execution")
    if code in ("GD5","GD7"): active.add("gate_present")
    return {"components":{name:{"value":name in active,"evidence":[{"source":"response","quote":"Respuesta evaluable","history_index":None}],"counterevidence":[],"complete_response_reviewed":True,"reason":"Lectura simulada: contrato y regla Python"} for name in definitions(code)}}

@pytest.mark.parametrize("code",[f"GD{i}" for i in range(1,9)])
@pytest.mark.parametrize("number",range(4))
def test_individual_docx_descriptors(code,number):
    r=reading(code,number)
    d=adjudicate(code,TurnContext("Relato","Respuesta evaluable"),r,copy.deepcopy(r))
    assert (d["status"],d["score"])==("SCORED",number)

def test_two_blind_batch_readings_and_individual_scores():
    calls=[]
    def reader(payload):
        calls.append(payload)
        assert "classification" not in payload and "proposed_level" not in payload
        return {"indicators":{f"GD{i}":reading(f"GD{i}",3) for i in range(1,9)}}
    report=run_gd_docx(GDContext("Relato","Respuesta evaluable"),reader=reader)
    assert all(r.score==3 for r in report["results"].values())
    assert [p["stage"] for p in calls]==["extract","independent_verify"]

def test_one_disagreement_blocks_only_affected_indicator():
    def reader(payload):
        batch={"indicators":{f"GD{i}":reading(f"GD{i}",3) for i in range(1,9)}}
        if payload["stage"]=="independent_verify":batch["indicators"]["GD6"]["components"]["indispensability_claim"]["value"]=True
        return batch
    results=run_gd_docx(GDContext("Relato","Respuesta evaluable"),reader=reader)["results"]
    assert results["GD6"].status=="BLOCKED"
    assert all(r.score==3 for c,r in results.items() if c!="GD6")

def test_transport_failure_not_a_grade():
    def reader(payload):raise OSError("Fallo técnico simulado")
    report=run_gd_docx(GDContext("Relato","Respuesta evaluable"),reader=reader)
    assert all(r.status=="BLOCKED" and r.score is None for r in report["results"].values())
