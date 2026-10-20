"""Offline integration gates; never contact OpenAI."""
import pytest
from backend.evaluators.ce.pilot.integrate_ce1_ce5 import evaluate


def test_ce1_cannot_accidentally_call_api():
    with pytest.raises(ValueError, match='allow_live'):
        evaluate(indicator='CE1', user_text='Hola', response_text='Hola')


def test_ce1_cannot_substitute_unverified_decider():
    with pytest.raises(ValueError, match='override'):
        evaluate(indicator='CE1', user_text='Hola', response_text='Hola', ce1_decider=lambda **kw: {'score': 3})


def test_ce2_rejects_unverified_whole_response():
    called = []
    def runner(**kw):
        called.append(kw)
        raise AssertionError('Extractor must not run before whole-response gate')
    result = evaluate(indicator='CE2', user_text='Necesito ayuda', response_text='Hola',
                      semantic_runner=runner, verify_claim=lambda *a: 'ambiguous')
    assert result['status'] == 'insufficient_evidence' and result['score'] is None
    assert not called


@pytest.mark.parametrize('indicator,field,value,expected', [
    ('CE3', 'order_impact', 'clear', 3),
    ('CE3', 'order_impact', 'substantial', 1),
    ('CE4', 'rubric_execution', 'clear_contextual_verifiable', 3),
    ('CE4', 'rubric_execution', 'adequate_limited', 2),
    ('CE5', 'language_impact', 'clear', 3),
    ('CE5', 'language_impact', 'prohibited', 0),
])
def test_offline_extraction_verification_and_scoring(indicator, field, value, expected):
    def runner(**kw):
        return {'analysis_complete': True, 'full_response_audited': True,
                'applicable': True, **({'applicability_evidence': {'source': 'response', 'quote': 'Hola', 'interpretation': 'Condici?n de aplicabilidad simulada para probar la integraci?n'}} if indicator == 'CE4' else {}), field: value,
                'claims': [{'source': 'response', 'quote': 'Hola',
                            'interpretation': 'Hallazgo verificado por un oráculo de prueba'}]}
    def verifier(source, quote, claim):
        assert quote in source
        return 'supported'
    result = evaluate(indicator=indicator, user_text='Salúdame', response_text='Hola',
                      semantic_runner=runner, verify_claim=verifier)
    assert result['status'] == 'scored' and result['score'] == expected


@pytest.mark.parametrize('indicator,field,value', [
    ('CE3', 'order_impact', 'clear'), ('CE4', 'rubric_execution', 'clear_contextual_verifiable'),
    ('CE5', 'language_impact', 'clear')])
def test_ambiguous_independent_verification_never_scores(indicator, field, value):
    def runner(**kw):
        return {'analysis_complete': True, 'full_response_audited': True,
                'applicable': True, **({'applicability_evidence': {'source': 'response', 'quote': 'Hola', 'interpretation': 'Condici?n de aplicabilidad simulada para probar la integraci?n'}} if indicator == 'CE4' else {}), field: value,
                'claims': [{'source': 'response', 'quote': 'Hola', 'interpretation': 'Test'}]}
    result = evaluate(indicator=indicator, user_text='Salúdame', response_text='Hola',
                      semantic_runner=runner, verify_claim=lambda *args: 'ambiguous')
    assert result['score'] is None and result['status'] == ('BLOCKED' if indicator == 'CE4' else 'insufficient_evidence')
