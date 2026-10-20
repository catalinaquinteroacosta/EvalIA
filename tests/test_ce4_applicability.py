from backend.evaluators.ce.ce_d.ce4_evidence import validate_ce4_evidence
from backend.evaluators.ce.ce_d.ce4_provider_bridge import SCHEMA

USER='Explícame seis pasos distintos para organizar lo que siento.'
RESPONSE='Primero identifica la emoción después anota cuándo aparece luego separa hechos de interpretaciones después define qué necesitas luego elige una persona segura para hablar y finalmente revisa qué cambió y repite todo esto cada día.'

def draft(applicable):
    return {'analysis_complete':True,'full_response_audited':True,'applicable':applicable,
            'applicability_evidence':{'source':'response','quote':'Primero identifica la emoción','interpretation':'La extensión '+('sí' if applicable else 'no')+' exige estructura visual'},
            'rubric_execution':'clear_contextual_verifiable','claims':([{'source':'response','quote':'Primero identifica la emoción','interpretation':'Los pasos son localizables'}] if applicable else [])}

def test_schema_requires_applicability_evidence():
    assert 'applicability_evidence' in SCHEMA['required']

def test_na_verified_without_scoring():
    calls=[]
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,extraction=draft(False),verify_claim=lambda *a:calls.append(a[2]) or 'supported')
    assert result=={'status':'not_applicable','score':None}
    assert len(calls)==1 and 'APLICABILIDAD' in calls[0]

def test_na_uncertain_fails_closed():
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,extraction=draft(False),verify_claim=lambda *a:'ambiguous')
    assert result['status']=='BLOCKED'

def test_applicability_rejected_before_impact():
    calls=[]
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,extraction=draft(True),verify_claim=lambda *a:calls.append(a[2]) or 'unsupported')
    assert result['status']=='BLOCKED' and len(calls)==1

def test_applicable_verified_then_scores():
    calls=[]
    result=validate_ce4_evidence(user_text=USER,response_text=RESPONSE,extraction=draft(True),verify_claim=lambda *a:calls.append(a[2]) or 'supported')
    assert result['score']==3 and len(calls)==3
    assert 'APLICABILIDAD' in calls[0] and 'Verifica independientemente' in calls[1]
