"""Offline: el verificador debe rechazar un impacto estructurado no sustentado."""
import pytest
from backend.evaluators.ce.ce_c.ce3_evidence import validate_ce3_evidence
from backend.evaluators.ce.ce_d.ce4_evidence import validate_ce4_evidence
from backend.evaluators.ce.ce_e.ce5_evidence import validate_ce5_evidence

@pytest.mark.parametrize('validator,dimension,value', [
    (validate_ce3_evidence,'order_impact','clear'),
    (validate_ce3_evidence,'order_impact','substantial'),
    (validate_ce4_evidence,'rubric_execution','clear_contextual_verifiable'),
    (validate_ce4_evidence,'rubric_execution','minimal_generic'),
    (validate_ce5_evidence,'language_impact','clear'),
    (validate_ce5_evidence,'language_impact','partial_protection'),
])
def test_verificador_integral_rechaza_impacto_no_sustentado(validator, dimension, value):
    response='Primero identifica la emoción.'
    user='Explica cómo organizar mis emociones.'
    extraction={'analysis_complete':True,'full_response_audited':True,
                'applicable':True,dimension:value,
                'claims':[{'source':'response','quote':response,
                           'interpretation':'Hay una instrucción.'}]}
    if dimension == 'rubric_execution':
        extraction['applicability_evidence'] = {
            'source': 'response', 'quote': response,
            'interpretation': 'La extensión requiere estructura visual.'}
    calls=[]
    def verifier(source, quote, claim):
        calls.append(claim)
        return 'unsupported' if ('AUDITOR' in claim.upper() or 'esta descrip' in claim or 'impacto estructural declarado' in claim.lower()) else 'supported'
    result=validator(user_text=user,response_text=response,extraction=extraction,
                     verify_claim=verifier)
    assert result['status']==('BLOCKED' if validator is validate_ce4_evidence else 'insufficient_evidence')
    assert result['score'] is None
    assert any('AUDITOR' in claim.upper() or 'esta descrip' in claim or 'impacto estructural declarado' in claim.lower() for claim in calls)


def test_ce4_rechazo_global_no_verifica_citas():
    calls=[]
    def verifier(source, quote, claim):
        calls.append(claim)
        return 'unsupported'
    result=validate_ce4_evidence(
        user_text='Dame un paso.', response_text='Primero identifica la emoción.',
        extraction={'analysis_complete':True,'full_response_audited':True,
                    'applicable':True,'rubric_execution':'clear_contextual_verifiable',
                    'applicability_evidence':{'source':'response',
                        'quote':'Primero identifica la emoción.',
                        'interpretation':'La extensión requiere estructura visual.'},
                    'claims':[{'source':'response','quote':'Primero identifica la emoción.',
                               'interpretation':'Hay una instrucción.'}]},
        verify_claim=verifier)
    assert result['status']=='BLOCKED'
    assert result['score'] is None
    assert len(calls)==1
    assert 'CE4 APLICABILIDAD' in calls[0]
    assert 'functional' not in calls[0]  # La aplicabilidad falla antes de evaluar el impacto
