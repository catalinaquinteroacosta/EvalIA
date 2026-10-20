"""Offline integration contract tests; no OpenAI calls."""
import pytest
from backend.evaluators.ce.pilot import integrate_ce2_ce10 as dispatcher

BASE = {'user_text': 'Me siento abrumada', 'response_text': 'Entiendo que estés abrumada.'}

@pytest.mark.parametrize('indicator', ['CE2', 'CE3', 'CE4', 'CE5'])
def test_ce2_ce5_routes(monkeypatch, indicator):
    seen = []
    monkeypatch.setattr(dispatcher.integrate_ce2_ce5, 'evaluate', lambda **kw: seen.append(kw) or {'status':'scored', 'score':3})
    assert dispatcher.evaluate(indicator=indicator, verify_claim=lambda *a: 'supported', semantic_runner=lambda **kw: {}, **BASE)['score'] == 3
    assert seen[0]['indicator'] == indicator

@pytest.mark.parametrize('indicator', ['CE6', 'CE7', 'CE8'])
def test_ce6_ce8_routes(monkeypatch, indicator):
    seen = []
    monkeypatch.setattr(dispatcher.integrate_ce6_ce8, 'evaluate', lambda **kw: seen.append(kw) or {'status':'scored', 'score':2})
    assert dispatcher.evaluate(indicator=indicator, verify_claim=lambda *a: 'supported', semantic_runner=lambda **kw: {}, **BASE)['score'] == 2
    assert seen[0]['indicator'] == indicator

@pytest.mark.parametrize('indicator', ['CE9', 'CE10'])
def test_ce9_ce10_routes(monkeypatch, indicator):
    seen = []
    monkeypatch.setattr(dispatcher, 'evaluate_verified', lambda **kw: seen.append(kw) or {'status':'scored','score':3})
    h = [{'role':'user','text':'Anterior'},{'role':'assistant','text':'Anterior respuesta'}] if indicator=='CE10' else None
    a, b = lambda **kw: {}, lambda **kw: {}
    assert dispatcher.evaluate(indicator=indicator, history=h, semantic_runner=a, verifier_runner=b, **BASE)['score']==3
    assert seen[0]['history']==h and seen[0]['extraction_runner'] is a and seen[0]['verifier_runner'] is b

def test_ce10_first_turn_no_api():
    assert dispatcher.evaluate(indicator='CE10', history=[], **BASE)=={'indicator':'CE10','status':'not_applicable','score':None,'reason':'first_turn'}

def test_ce10_missing_history_fails():
    with pytest.raises(ValueError, match='history'):
        dispatcher.evaluate(indicator='CE10', **BASE)

def test_ce10_malformed_history_fails():
    with pytest.raises(ValueError, match='history'):
        dispatcher.evaluate(indicator='CE10', history=[{'user':'a','assistant':'b','model':'other'}], **BASE)

def test_ce9_same_runner_fails():
    r=lambda **kw: {}
    with pytest.raises(ValueError, match='distinct'):
        dispatcher.evaluate(indicator='CE9', semantic_runner=r, verifier_runner=r, **BASE)

def test_ce8_no_verifier_fails():
    with pytest.raises(ValueError, match='verify_claim'):
        dispatcher.evaluate(indicator='CE8', semantic_runner=lambda **kw: {}, **BASE)

def test_ce2_no_live_by_default():
    with pytest.raises(ValueError, match='disabled'):
        dispatcher.evaluate(indicator='CE2', verify_claim=lambda *a:'supported', **BASE)

def test_ce1_excluded():
    with pytest.raises(ValueError, match='CE1'):
        dispatcher.evaluate(indicator='CE1', **BASE)
