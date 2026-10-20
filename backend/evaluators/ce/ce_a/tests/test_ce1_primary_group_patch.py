"""Regresiones offline: unidad compuesta, independencia y coberturas."""
from unittest.mock import patch
import pytest
from backend.evaluators.ce.ce_a import ce1_integrated as mod
from backend.evaluators.ce.ce_a.ce1_primary_group import validate_group

CANDIDATES = [{"need":"Agradecer","source":"current_user","evidence":"Gracias"},
              {"need":"Comunicar mejoria","source":"current_user","evidence":"me siento mejor"}]

def extraction():
    return {"primary_need":"Agradecer y comunicar mejoria",
            "explicit_needs":[{"interpretation":c["need"],"user_evidence":c["evidence"]} for c in CANDIDATES],
            "contextual_needs":[],"ce1_relevant_evidence":[],"ce1_digressions":[],
            "ce2_essential_information_present":[],"ce2_essential_omissions":[],"ce2_unnecessary_overload":[]}

def run(group_verdict, coverages=("addressed","addressed")):
    data=extraction()
    counter=iter(coverages)
    with (patch.object(mod,"validate_extraction",return_value=data),
          patch.object(mod,"audit_coverage",return_value={"verdict":"complete","findings":[],"reason":"ok"}),
          patch.object(mod,"verify_primary_identity",side_effect=lambda **kw:{"verdict":"confirmed","source":"current_user","evidence":kw["candidate_evidence"],"reason":"test"}),
          patch.object(mod,"verify_primary_group",return_value={"verdict":group_verdict,"member_indices":[0,1] if group_verdict=="single_composite" else [],"reason":"test"}) as group,
          patch.object(mod,"verify_need",return_value={"verdict":"supported","reason":"test"}),
          patch.object(mod,"evaluate_verified_need",side_effect=lambda *a,**kw:{"coverage":next(counter)})):
        result=mod.evaluate_ce1_integrated(user_text="Gracias, me siento mejor",response_text="Me alegra",extraction=data)
    return result,group

def test_grouped_both_addressed():
    result,group=run("single_composite")
    group.assert_called_once()
    assert result["status"]=="evidence_integrated"
    assert result["primary_coverage"]=="addressed"
    assert [n["is_primary"] for n in result["needs"]]==[True,True]
    assert result["score"] is None

def test_independent_stays_pending():
    result,_=run("independent")
    assert result["status"]=="review_required"
    assert any(x["type"]=="primary_group_unresolved" for x in result["pending"])
    assert result["score"] is None

def test_ambiguous_stays_pending():
    result,_=run("ambiguous")
    assert result["status"]=="review_required"
    assert result["score"] is None

def test_mixed_coverage_stays_pending():
    result,_=run("single_composite",("addressed","unaddressed"))
    assert result["status"]=="review_required"
    assert any(x["type"]=="primary_group_mixed_coverage" for x in result["pending"])
    assert result["primary_coverage"] is None

@pytest.mark.parametrize("verdict,indices",[("single_composite",[0]),("single_composite",[0,0]),("independent",[0]),("ambiguous",[1]),("single_composite",[0,True])])
def test_invalid_group_contract(verdict,indices):
    with pytest.raises(ValueError):
        validate_group({"verdict":verdict,"member_indices":indices,"reason":"test"},candidates=CANDIDATES)
