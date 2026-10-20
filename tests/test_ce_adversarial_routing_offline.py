"""Preflight for the 29 adversarial cases; no semantic/API calls or score claims.
Run from EVALIA project root with pytest --import-mode=importlib.
"""
import json
from pathlib import Path
import pytest
from backend.evaluators.ce.pilot import integrate_ce2_ce10 as dispatcher

CASES = json.loads((Path(__file__).resolve().parents[1] / 'casos_adversariales_ce2_ce10.json').read_text(encoding='utf-8'))['cases']


def same_model_history(case, model='Modelo_A'):
    raw = case['prior_history']
    # For CE2–CE9 the list sometimes holds *cross-indicator annotations*, not dialogue.
    if case['indicator'] != 'CE10':
        return None
    pending = None
    pairs = []
    for msg in raw:
        if not isinstance(msg, dict) or msg.get('role') not in ('user', 'assistant') or not isinstance(msg.get('content'), str):
            raise ValueError('Malformed CE10 dialogue')
        if msg['role'] == 'user':
            if pending is not None:
                raise ValueError('Two consecutive user turns')
            pending = msg['content']
        else:
            if pending is None:
                raise ValueError('Assistant without user')
            if msg.get('model') == model:
                pairs.extend([{'role':'user','text':pending},{'role':'assistant','text':msg['content']}])
            pending = None
    if pending is not None:
        raise ValueError('Unpaired user turn')
    return pairs


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_case_routes_to_correct_family_without_api(monkeypatch, case):
    seen = []
    def fake(**kwargs):
        seen.append(kwargs)
        return {'indicator': kwargs['indicator'], 'status': 'preflight_only', 'score': None}
    monkeypatch.setattr(dispatcher.integrate_ce2_ce5, 'evaluate', fake)
    monkeypatch.setattr(dispatcher.integrate_ce6_ce8, 'evaluate', fake)
    monkeypatch.setattr(dispatcher, 'evaluate_verified', fake)
    kwargs = dict(indicator=case['indicator'], user_text=case['user_message'],
                  response_text=case['assistant_response'])
    if case['indicator'] == 'CE10':
        kwargs['history'] = same_model_history(case)
    if case['indicator'] in ('CE9', 'CE10'):
        kwargs['semantic_runner'] = lambda **k: None
        kwargs['verifier_runner'] = lambda **k: None
    else:
        kwargs['semantic_runner'] = lambda **k: None
        kwargs['verify_claim'] = lambda **k: 'not_supported'
    result = dispatcher.evaluate(**kwargs)
    if case['indicator'] == 'CE10' and not kwargs['history']:
        assert result['status'] == 'not_applicable'
        assert result['score'] is None
        assert not seen
    else:
        assert len(seen) == 1
        assert seen[0]['indicator'] == case['indicator']
        assert result['score'] is None  # No fabricated semantic result.
        if case['indicator'] == 'CE10':
            assert seen[0]['history'] == kwargs['history']


def test_other_model_excluded():
    c = next(x for x in CASES if x['id'] == 'ce10_other_model')
    assert same_model_history(c) == []


def test_chronological_same_model_history():
    for c in CASES:
        if c['indicator'] == 'CE10':
            assert all(set(pair) == {'role', 'text'} for pair in same_model_history(c))


def test_non_dialogue_annotations_are_not_used_as_history():
    for c in CASES:
        if c['indicator'] != 'CE10':
            assert same_model_history(c) is None
