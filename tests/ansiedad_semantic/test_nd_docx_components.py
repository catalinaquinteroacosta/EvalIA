"""Mechanical contracts with simulated readers, not live semantic validation."""
from dataclasses import replace
import pytest
from backend.evaluators.nd.contracts import Evidence, TurnContext
from backend.evaluators.nd.nd1_official import ComponentReview
from backend.evaluators.nd.docx_components import SCHEMA, definitions, score
from backend.evaluators.nd.docx_protocol import prompt

def fixture(code, level):
    context = TurnContext("Relato evaluable", "Respuesta evaluable")
    if SCHEMA[code][0] == "negative":
        active = [{"prohibited_assertion_present"}, {"relevant_failure_or_textual_ambiguity"},
                  {"secondary_contextual_insufficiency"}, {"protection_throughout_response"}][level]
        if level > 0: active = active | {"some_protection_preserved"}
        if level > 1: active = active | {"essential_protection_preserved"}
    else:
        active = [set(), {"required_behavior_recognizable"},
                  {"required_behavior_recognizable", "central_function_accomplished", "secondary_contextual_insufficiency"},
                  {"required_behavior_recognizable", "central_function_accomplished", "specific_contextual_verifiable"}][level]
    if SCHEMA[code][1]: active = active | {"gate_present"}
    reviews = tuple(ComponentReview(name, name in active, name in active,
        (Evidence("user", context.user),) if name == "gate_present" else (Evidence("response", context.response),),
        (), True, "Componente simulado para verificar contrato Python") for name in definitions(code))
    return context, reviews

@pytest.mark.parametrize("code", SCHEMA)
@pytest.mark.parametrize("level", range(4))
def test_individual_literal_descriptor(code, level):
    context, reviews = fixture(code, level)
    from backend.evaluators.nd.nd99_production_gate import score_nd99_production_gate
    result = score_nd99_production_gate(code, context, reviews)
    assert (result.status, result.score) == ("SCORED", level)
    from backend.evaluators.nd.docx_components import contracts
    assert result.reason == contracts()[code]["levels"][str(level)]

@pytest.mark.parametrize("code", SCHEMA)
@pytest.mark.parametrize("defect", ["unknown", "disagree", "literal", "missing", "unreviewed"])
def test_fail_closed(code, defect):
    context, reviews = fixture(code, 3)
    rows = list(reviews); index = next(i for i,r in enumerate(rows) if r.name != "gate_present")
    if defect == "unknown": rows[index] = replace(rows[index], verified=None)
    if defect == "disagree": rows[index] = replace(rows[index], verified=not rows[index].extracted)
    if defect == "literal": rows[index] = replace(rows[index], evidence=(Evidence("response", "inventada"),))
    if defect == "missing": rows.pop(index)
    if defect == "unreviewed": rows[index] = replace(rows[index], complete_response_reviewed=False)
    assert score(code, context, tuple(rows)).status == "BLOCKED"

@pytest.mark.parametrize("code", ["ND2", "ND7"])
def test_official_gate_absent_only_na(code):
    context, _ = fixture(code, 0)
    row = ComponentReview("gate_present", False, False, (), (), True, "Condición ausente tras revisión")
    assert score(code, context, (row,)).status == "NA"

@pytest.mark.parametrize("code", ["ND3", "ND4", "ND5", "ND6", "ND8"])
def test_general_cannot_be_na(code):
    context, _ = fixture(code, 0)
    assert score(code, context, ()).status == "BLOCKED"

@pytest.mark.parametrize("code", SCHEMA)
def test_blind_prompt_has_no_extractor_conclusions_or_score_selection(code):
    context, _ = fixture(code, 0)
    import json
    payload = json.loads(prompt(code, {"case": context}, "independent_verify"))
    assert "levels" not in payload and "extraction" not in payload
    assert payload["components"] == definitions(code)
