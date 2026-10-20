import json
from copy import deepcopy
from pathlib import Path
from collections import Counter
import pytest
from backend import luna_anxiety_economy as candidate,luna_reader as reader

PLAN=Path('.evalia-private/luna_ui/plans/f2ca66042f384c6289cb485168c284cd/manifest.json')

@pytest.fixture
def requests():
    return json.loads(PLAN.read_text(encoding='utf-8'))['requests']

def test_all_scopes_cover_exactly_once_and_preserve_originals(requests):
    pairs={}
    for row in requests:
        body=row['body'];req=json.loads(body['messages'][1]['content'])
        key=(req['original']['model'],req['original']['turn'],req['stage'])
        if len(req['indicators'])==1:continue
        pairs.setdefault(key,[]).append(req)
    assert len(pairs)==50
    for scopes in pairs.values():
        before=deepcopy(scopes);expected=set();counts=Counter()
        for request in scopes:
            expected.update(request['indicators'])
            reduced=candidate.family_request(request)
            assert reduced['original']==request['original']
            for code,row in reduced['indicators'].items():
                assert row==request['indicators'][code]
                counts[code]+=1
            for code in reader.ISOLATED_ANXIETY_CODES.intersection(request['indicators']):counts[code]+=1
        assert set(counts)==expected and set(counts.values())=={1}
        assert scopes==before

def test_composition_and_blind_stages(requests,monkeypatch):
    monkeypatch.setattr(reader,'decode_anxiety',lambda raw,request:{'indicators':{c:{'fixture':c} for c in request['indicators']}})
    for stage in ('extract','independent_verify'):
        request=next(json.loads(r['body']['messages'][1]['content']) for r in requests
                     if len(json.loads(r['body']['messages'][1]['content'])['indicators'])==8
                     and 'AF1' in json.loads(r['body']['messages'][1]['content'])['indicators']
                     and json.loads(r['body']['messages'][1]['content'])['stage']==stage)
        calls=[]
        def transport(body,endpoint):calls.append(body);return {}
        result=candidate.read_anxiety(request,transport)
        assert set(result['indicators'])==set(request['indicators'])
        assert len(calls)==3
        assert all(json.loads(b['messages'][1]['content'])['stage']==stage for b in calls)
        assert len(json.loads(calls[0]['messages'][1]['content'])['indicators'])==6
        for b in calls[1:]:
            own=json.loads(b['messages'][1]['content'])
            code=next(iter(own['indicators']))
            from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope
            expected=reader.adapt_body(envelope(reader.isolated_anxiety_request(request,code),reader.MODEL),'ansiedad_depresion',stage)
            assert b==expected

def test_pending_never_becomes_evaluation(requests):
    from backend.luna_application import BatchPending
    request=json.loads(requests[0]['body']['messages'][1]['content'])
    def transport(*args):raise BatchPending(['offline'])
    assert candidate.read_anxiety(request,transport)=={'indicators':{}}
