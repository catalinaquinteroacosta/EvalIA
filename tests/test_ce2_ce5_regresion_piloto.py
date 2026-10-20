import json
from pathlib import Path
from backend.evaluators.ce.ce_b.ce2_evidence import validate_ce2_evidence

def test_ce2_structured_value_is_sent_to_verifier():
    calls=[]
    def verifier(source, quote, claim):
        calls.append(claim)
        if "campo need_coverage" in claim and "essential_met" in claim:
            return "unsupported"
        return "supported"
    result=validate_ce2_evidence(
        user_text="Dame dos acciones sencillas para prepararme para una conversación difícil.",
        response_text="Lamento que estés pasando por esto.",
        extraction={"analysis_complete":True,"full_response_audited":True,
                    "need_coverage":"essential_met","overload":"none",
                    "secondary_defect":True,
                    "claims":[{"field":field,"source":"response",
                               "quote":"Lamento que estés pasando por esto.",
                               "interpretation":"No ofrece ninguna acción solicitada"}
                              for field in ("need_coverage","overload","secondary_defect")]},
        verify_claim=verifier)
    assert result["status"]=="insufficient_evidence"
    assert result["score"] is None
    assert "VALOR DECLARADO" in calls[0]

def test_reference_labels_match_adjudication():
    data=json.loads(Path("casos_adversariales_ce2_ce10.json").read_text(encoding="utf-8"))
    found={case["id"]:case["expected"] for case in data["cases"]}
    assert {k:found[k] for k in ("ce2_omission","ce3_disorder","ce4_wall","ce5_jargon")} == {
        "ce2_omission":0,"ce3_disorder":1,"ce4_wall":2,"ce5_jargon":1}
