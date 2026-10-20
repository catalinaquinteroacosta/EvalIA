import pytest
from backend.evaluators.ce.pilot.integrate_ce2_ce5 import evaluate


def test_live_is_opt_in():
    with pytest.raises(ValueError, match='Live API disabled'):
        evaluate(indicator='CE2', user_text='Hola', response_text='Hola', verify_claim=lambda *args: 'supported')


def test_verifier_is_mandatory():
    with pytest.raises(ValueError, match='independent'):
        evaluate(indicator='CE2', user_text='Hola', response_text='Hola', semantic_runner=lambda **kw: {})


def test_ce1_not_falsely_advertised():
    with pytest.raises(ValueError, match='CE1'):
        evaluate(indicator='CE1', user_text='Hola', response_text='Hola', verify_claim=lambda *args: 'supported')


@pytest.mark.parametrize('indicator,field,impact', [
    ('CE3', 'order_impact', 'clear'), ('CE4', 'rubric_execution', 'clear_contextual_verifiable'),
    ('CE5', 'language_impact', 'clear')])
def test_unsupported_evidence_never_scores(indicator, field, impact):
    def fake_runner(**kwargs):
        return {'analysis_complete': True, 'full_response_audited': True,
                'applicable': True, **({'applicability_evidence': {'source': 'response', 'quote': 'Hola', 'interpretation': 'Condici?n de aplicabilidad simulada para probar la integraci?n'}} if indicator == 'CE4' else {}), field: impact,
                'claims': [{'source': 'response', 'quote': 'Hola', 'interpretation': 'Prueba'}]}
    result = evaluate(indicator=indicator, user_text='Salúdame', response_text='Hola',
                      semantic_runner=fake_runner, verify_claim=lambda *args: 'unsupported')
    assert result['score'] is None
    assert result['status'] == ('BLOCKED' if indicator == 'CE4' else 'insufficient_evidence')
