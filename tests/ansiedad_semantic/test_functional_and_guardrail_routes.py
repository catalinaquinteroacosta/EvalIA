"""Simulated component contrasts; no real semantic reader invoked."""
import copy
import pytest
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn
from backend.evaluators.ansiedad_semantic import functional_review as f, guardrail_review as g

POSITIVE=[c for c in f.POSITIVE_ATOMS if c.startswith(("PA","CE","PS"))]

def positive_reading(code,number):
    active=set()
    if number>0:active.add("recognizable_behavior")
    if number>1:active.update(f.POSITIVE_ATOMS[code]);active.add("central_function_realized")
    if number==2:active.add("secondary_precision_or_adaptation_defect")
    if number==3:active.add("clear_specific_contextual_execution")
    if f.conditional(code):active.add("gate_present")
    return reading(f.definitions(code),active)

def reading(definitions,active):
    return {"components":{name:{"value":name in active,"evidence":[{"source":"response","quote":"Respuesta evaluable","history_index":None}],"counterevidence":[],"complete_response_reviewed":True,"reason":"Revisión simulada de componentes"} for name in definitions}}

@pytest.mark.parametrize("code",POSITIVE)
@pytest.mark.parametrize("number",range(4))
def test_functional_individual_rules(code,number):
    a=positive_reading(code,number)
    d=f.adjudicate(code,TurnContext("Relato","Respuesta evaluable"),a,copy.deepcopy(a))
    assert (d["status"],d["score"])==("SCORED",number)

def guardrail_reading(code,number):
    harm,protection=g.CONSTRUCTS[code]
    active=set()
    if number==0:active.add(next(iter(harm)))
    if number>0:active.add("some_protection_preserved")
    if number>1:active.add("essential_protection_preserved")
    if number==1:active.add("relevant_failure_or_textual_ambiguity")
    if number==2:active.add("secondary_contextual_insufficiency")
    if number==3:active.add("consistent_protection_without_exception");active.update(protection)
    if f.conditional(code):active.add("gate_present")
    a=reading(g.definitions(code),active)
    if code=="CE10" and number==0:
        a["components"][next(iter(harm))]["counterevidence"]=[{"source":"history","quote":"Dato previo","history_index":0}]
    return a

@pytest.mark.parametrize("code",g.CONSTRUCTS)
@pytest.mark.parametrize("number",range(4))
def test_guardrail_individual_rules(code,number):
    a=guardrail_reading(code,number)
    context=TurnContext("Relato","Respuesta evaluable",(HistoryTurn("user","Dato previo"),))
    d=g.adjudicate(code,context,a,copy.deepcopy(a))
    assert (d["status"],d["score"])==("SCORED",number)

@pytest.mark.parametrize("code",g.CONSTRUCTS)
def test_no_automatic_three_without_full_protection_review(code):
    a=guardrail_reading(code,3);a["components"]["consistent_protection_without_exception"]["value"]=False
    assert g.adjudicate(code,TurnContext("Relato","Respuesta evaluable",(HistoryTurn("user","Dato previo"),)),a,a)["status"]=="BLOCKED"

def test_ce10_first_turn_na_and_no_future_rescue():
    a=guardrail_reading("CE10",3)
    a["components"]={"gate_present":a["components"]["gate_present"]};a["components"]["gate_present"]["value"]=False
    assert g.adjudicate("CE10",TurnContext("Relato","Respuesta evaluable"),a,a)["status"]=="N/A"

def test_ce10_requires_both_literal_endpoints_per_reader():
    a=guardrail_reading("CE10",0);b=copy.deepcopy(a)
    b["components"]["unjustified_prior_information_contradiction"]["counterevidence"]=[]
    context=TurnContext("Relato","Respuesta evaluable",(HistoryTurn("user","Dato previo"),))
    assert g.adjudicate("CE10",context,a,b)["status"]=="BLOCKED"

@pytest.mark.parametrize("code",POSITIVE)
def test_component_missing_cannot_be_rescued_by_central_function_assertion(code):
    a=positive_reading(code,2);a["components"][next(iter(f.POSITIVE_ATOMS[code]))]["value"]=False
    assert f.adjudicate(code,TurnContext("Relato","Respuesta evaluable"),a,a)["status"]=="BLOCKED"
