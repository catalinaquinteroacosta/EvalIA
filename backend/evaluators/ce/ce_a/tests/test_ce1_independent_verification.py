import pytest
from unittest.mock import patch
from backend.evaluators.ce.ce_a import ce1_impact_verifier as v

USER='Necesito preparar una entrevista.'
RESPONSE='Practica tus respuestas. Los volcanes son interesantes.'

def classification(impact='minor',total=False):
    return {'analysis_complete':True,'total_deviation':total,'issues':[
        {'description':'Digresion','impact':impact,'evidence':'Los volcanes son interesantes.'}]}

def audit(impact='minor',global_status='rejected'):
    return {'global_total_deviation':global_status,'global_reason':'Examine toda la respuesta.',
            'issue_checks':[{'issue_index':0,'genuine_relevance_failure':'confirmed',
                             'independent_impact':impact,'reason':'Fragmento ajeno a la entrevista.',
                             'evidence':'Los volcanes son interesantes.'}]}

def check(a,c):
    return v.validate_independent_audit(a,c,user_text=USER,response_text=RESPONSE,prior_context='')

def test_minor_verified():
    assert check({**audit(),'global_total_deviation':'not_applicable'},classification())['issue_checks'][0]['independent_impact']=='minor'

def test_major_verified():
    assert check({**audit('major'),'global_total_deviation':'not_applicable'},classification('major'))

def test_disagreement_blocks():
    with pytest.raises(v.CE1IndependentVerificationError): check({**audit('major'),'global_total_deviation':'not_applicable'},classification('minor'))

def test_unsupported_issue_blocks():
    a={**audit(),'global_total_deviation':'not_applicable'}
    a['issue_checks'][0]['genuine_relevance_failure']='rejected'
    with pytest.raises(v.CE1IndependentVerificationError): check(a,classification())

def test_fake_evidence_blocks():
    a={**audit(),'global_total_deviation':'not_applicable'}
    a['issue_checks'][0]['evidence']='Inventado'
    with pytest.raises(v.CE1IndependentVerificationError): check(a,classification())

def test_missing_issue_blocks():
    a={**audit(),'global_total_deviation':'not_applicable'}; a['issue_checks']=[]
    with pytest.raises(v.CE1IndependentVerificationError): check(a,classification())

def test_total_zero_requires_second_confirmation():
    assert check(audit(global_status='confirmed'),classification(total=True))
    with pytest.raises(v.CE1IndependentVerificationError): check(audit(global_status='rejected'),classification(total=True))

def test_independent_provider_called_without_original_impact():
    with patch.object(v,'get_semantic_identity',return_value={'model':'test'}),patch.object(v,'run_structured_semantic',return_value=audit()) as provider:
        result=v.verify_ce1_classification_independently(classification=classification(),primary_need='Preparar entrevista',
          primary_coverage='addressed',verified_fragments=[],user_text=USER,response_text=RESPONSE)
    assert result['issue_checks'][0]['independent_impact']=='minor'
    prompt=provider.call_args.kwargs['prompt']
    assert '"impact": "minor"' not in prompt

def test_no_issues_skips_second_call():
    with patch.object(v,'run_structured_semantic') as provider:
        result=v.verify_ce1_classification_independently(classification={'analysis_complete':True,'total_deviation':False,'issues':[]},
          primary_need='Preparar entrevista',primary_coverage='addressed',verified_fragments=[],user_text=USER,response_text=RESPONSE)
    assert result['status']=='no_adverse_findings_to_verify'
    provider.assert_not_called()
