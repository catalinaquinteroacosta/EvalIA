import json
from backend.evaluators.nd.nd1_component_protocol import prompt, adjudicate_batch, DEFINITIONS
from backend.evaluators.nd.contracts import TurnContext

def test_verifier_receives_originals_not_extractor_claims():
    cases={"a":TurnContext("Soy incapaz", "Un resultado no demuestra incapacidad")}
    p=json.loads(prompt(cases,"independent_verify"))
    assert p["stage"]=="independent_verify" and p["cases"][0]["response"]==cases["a"].response
    assert "extracted" not in p
    assert set(p["components"])==set(DEFINITIONS)

def test_incomplete_case_blocks_without_stopping_other_cases():
    cases={"a":TurnContext("Estoy triste","Te escucho"),"b":TurnContext("Estoy triste","Te escucho")}
    results=adjudicate_batch(cases,{"cases":{}},{"cases":{}})
    assert all(r.status=="BLOCKED" and r.score is None for r in results.values())
