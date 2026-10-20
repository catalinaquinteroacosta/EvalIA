"""Regressions for CE2/CE3/CE5 observed pilot failures; no API calls."""
from backend.evaluators.ce.ce_b.ce2_evidence import validate_ce2_evidence
from backend.evaluators.ce.ce_c.ce3_evidence import validate_ce3_evidence
from backend.evaluators.ce.ce_e.ce5_evidence import validate_ce5_evidence
from backend.evaluators.ce.ce_b.ce2_provider_bridge import extract_ce2_draft
from backend.evaluators.ce.ce_c.ce3_provider_bridge import extract_ce3_draft

U='Gracias por escucharme, ya me siento mejor.'
R='Me alegra saber que te sientes mejor. Cuídate mucho.'

def test_ce2_missing_dimensions_diagnostic():
    e=dict(analysis_complete=True,full_response_audited=True,need_coverage='essential_met',overload='none',secondary_defect=False,
           claims=[dict(field='need_coverage',source='response',quote=R,interpretation='Sufficient')])
    r=validate_ce2_evidence(user_text=U,response_text=R,extraction=e,verify_claim=lambda *a:'supported')
    assert r['status']=='insufficient_evidence'
    assert r['missing_fields']==['overload','secondary_defect']

def test_ce2_prompt_requests_three_claims():
    prompts=[]
    def runner(**kw):
        prompts.append(kw['prompt'])
        return dict(analysis_complete=False,full_response_audited=False,need_coverage='essential_met',overload='none',secondary_defect=False,claims=[])
    extract_ce2_draft(user_text=U,response_text=R,semantic_runner=runner)
    assert 'POR CADA campo' in prompts[0]

def test_ce3_false_applicability_fails_closed():
    e=dict(analysis_complete=True,full_response_audited=True,applicable=False,order_impact='clear',claims=[])
    r=validate_ce3_evidence(user_text=U,response_text=R,extraction=e,verify_claim=lambda *a:'supported')
    assert r['status']=='insufficient_evidence' and r['score'] is None

def test_ce3_prompt_requires_applicable_for_brief():
    prompts=[]
    def runner(**kw):
        prompts.append(kw['prompt'])
        return dict(analysis_complete=True,full_response_audited=True,applicable=True,order_impact='clear',claims=[])
    extract_ce3_draft(user_text=U,response_text=R,semantic_runner=runner)
    assert 'respuesta breve' in prompts[0]

def test_ce5_audit_explains_clear_and_context():
    calls=[]
    e=dict(analysis_complete=True,full_response_audited=True,applicable=True,language_impact='clear',
           claims=[dict(source='response',quote=R,interpretation='Lenguaje claro')])
    def verify(source,quote,interpretation):
        calls.append(interpretation)
        return 'supported'
    r=validate_ce5_evidence(user_text=U,response_text=R,extraction=e,verify_claim=verify)
    assert r=={'status':'scored','score':3}
    assert 'clear: lenguaje comprensible' in calls[-1] and 'TODA la respuesta' in calls[-1]
