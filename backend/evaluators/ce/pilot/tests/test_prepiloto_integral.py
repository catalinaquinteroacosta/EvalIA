"""Prepiloto sin tokens: extracción simulada, verificación controlada y scorer real.
Los oráculos simulados NO demuestran exactitud semántica de OpenAI.
"""
import pytest
from backend.evaluators.ce.pilot.integrate_ce1_ce5 import evaluate
from backend.evaluators.ce.pilot.independent_verifier import build_verifier

USER = 'Necesito que me escuches.'
RESPONSE = 'Te escucho. Cuéntame qué ocurrió.'


def draft(indicator, impact):
    base = {'analysis_complete': True, 'full_response_audited': True}
    if indicator == 'CE2':
        return {**base, 'need_coverage': impact, 'overload': 'none',
                'secondary_defect': False, 'claims': [
                    {'field': f, 'source': 'response', 'quote': 'Te escucho.',
                     'interpretation': 'Componente de prueba '+f}
                    for f in ('need_coverage', 'overload', 'secondary_defect')]}
    field = {'CE3':'order_impact','CE4':'rubric_execution','CE5':'language_impact'}[indicator]
    return {**base, 'applicable': True, **({'applicability_evidence': {'source': 'response', 'quote': 'Te escucho.', 'interpretation': 'Condici?n de aplicabilidad simulada para probar la integraci?n'}} if indicator == 'CE4' else {}), field: impact, 'claims': [
        {'source': 'response', 'quote': 'Te escucho.', 'interpretation': 'Componente de prueba'}]}


@pytest.mark.parametrize('indicator,impact,expected', [
    ('CE2','essential_met',3), ('CE2','generic',1),
    ('CE3','clear',3), ('CE3','substantial',1),
    ('CE4','clear_contextual_verifiable',3), ('CE4','omitted_or_opposite',0),
    ('CE5','clear',3), ('CE5','secondary',2),
])
def test_real_orchestration_with_mock_semantics(indicator, impact, expected):
    calls=[]
    def runner(**kwargs):
        calls.append('extract')
        return draft(indicator, impact)
    def verifier(source, quote, interpretation):
        calls.append('verify')
        assert quote in source
        return 'supported'
    result=evaluate(indicator=indicator,user_text=USER,response_text=RESPONSE,
                    semantic_runner=runner,verify_claim=verifier)
    assert result['status']=='scored' and result['score']==expected
    assert calls.count('extract')==1 and calls.count('verify')>=2


@pytest.mark.parametrize('indicator,impact', [
    ('CE2','essential_met'),('CE3','clear'),('CE4','clear_contextual_verifiable'),('CE5','clear')])
def test_verifier_ambiguity_blocks_scoring(indicator, impact):
    result=evaluate(indicator=indicator,user_text=USER,response_text=RESPONSE,
                    semantic_runner=lambda **kw: draft(indicator,impact),
                    verify_claim=lambda *args:'ambiguous')
    assert result['score'] is None and result['status']==('BLOCKED' if indicator=='CE4' else 'insufficient_evidence')


def test_ce1_is_not_simulated_as_scientifically_verified():
    with pytest.raises(ValueError, match='allow_live'):
        evaluate(indicator='CE1',user_text=USER,response_text=RESPONSE)


def test_independent_verifier_rejects_contradictory_supported():
    verifier=build_verifier(indicator='CE3',user_text=USER,response_text=RESPONSE,
        semantic_runner=lambda **kw:{'verdict':'supported','reason':'Sí',
                                     'counterevidence':'Te escucho.'})
    assert verifier(RESPONSE,'Te escucho.','La respuesta es clara')=='ambiguous'


def test_independent_verifier_rejects_fabricated_counterevidence():
    verifier=build_verifier(indicator='CE5',user_text=USER,response_text=RESPONSE,
        semantic_runner=lambda **kw:{'verdict':'unsupported','reason':'No',
                                     'counterevidence':'Una frase inventada'})
    assert verifier(RESPONSE,'Te escucho.','La respuesta es clara')=='ambiguous'
