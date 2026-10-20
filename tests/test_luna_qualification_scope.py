"""Controlled offline fixture: it tests release guards, not model fidelity."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from backend.luna_reader import LunaProvider,LunaCrisisEvaluator,select_final,VERIFY
from crisis_semantic.domain import Input,Turn

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'docs/economic_readers_step3_20261015'

def controlled_provider(tamper_cap=False):
    proof=json.loads((BASE/'corrections_02/CE10_OWN_CERTIFICATE_STEP31_OP5.json').read_text(encoding='utf8'))
    case=next(r for r in proof['CR-CE10']['cases'] if r['case_id']=='qualified_final_ce10_complete_continuity')
    pairs={}
    for reading in case['readings']:
        artifacts={a['kind']:json.loads(Path(a['path']).read_text(encoding='utf8')) for a in reading['artifacts']}
        pairs[reading['stage']]=artifacts
    q=json.loads(pairs['extract']['request']['body']['input'][1]['content'])['conversation']
    ctx=Input(Turn(q['current_turn'],q['current_user'],q['current_ai'],q['model_evaluated']),tuple(Turn(h['number'],h['user'],h['ai'],h['model']) for h in q['history']))
    def transport(body,endpoint):
        stage='verify' if body['input'][0]['content'].startswith(VERIFY) else 'extract'
        wire=deepcopy(select_final(pairs[stage]['response']['response']['body'])[0])
        payload=json.loads(body['input'][1]['content'])
        for key in payload['predicates']:
            if key not in wire['claims']:wire['claims'][key]=dict(observation='uncertain',evidence=[],context=[],reason='Controlled guard fixture; no inference.')
        if tamper_cap:body['max_output_tokens']+=1
        return dict(model='gpt-6-luna',status='completed',usage=dict(input_tokens=1,output_tokens=1),output=[dict(type='message',role='assistant',phase='final_answer',content=[dict(type='output_text',text=json.dumps(wire))])])
    return LunaProvider(transport,certificates=proof),ctx

def test_isolated_exact_pair_release_guard_with_controlled_qualification(monkeypatch):
    p,ctx=controlled_provider()
    # Exercise pair scope separately from historical certificate validity.
    # This stub is strictly offline and does not issue or alter a certificate.
    monkeypatch.setattr(p,'qualified',lambda code: code=='CR-CE10')
    row=LunaCrisisEvaluator(p).evaluate(ctx,['CR-CE10'])['results'][0]
    assert row['score']==3 and row['luna_qualified'] is True

def test_mixed_package_not_promoted_by_controlled_single_code_qualification(monkeypatch):
    p,ctx=controlled_provider()
    monkeypatch.setattr(p,'qualified',lambda code: code=='CR-CE10')
    assert p.qualified('CR-CE10') is True
    rows=LunaCrisisEvaluator(p).evaluate(ctx,['CR-CE10','CR-OP4'])['results']
    row=next(r for r in rows if r['code']=='CR-CE10')
    assert row['status']=='BLOCKED' and row['score'] is None and row['luna_qualified'] is False
    assert row['technical_cause']=='luna_own_qualification_scope_required'
    assert p.qualified('CR-CE10') is True  # Certificate scope remains valid.

def test_different_output_limit_not_promoted(monkeypatch):
    p,ctx=controlled_provider(tamper_cap=True)
    monkeypatch.setattr(p,'qualified',lambda code: code=='CR-CE10')
    row=LunaCrisisEvaluator(p).evaluate(ctx,['CR-CE10'])['results'][0]
    assert row['status']=='BLOCKED' and row['score'] is None

def test_historical_certificate_cannot_release_changed_reader_identity():
    p,ctx=controlled_provider()
    assert p.qualified('CR-CE10') is False
    row=LunaCrisisEvaluator(p).evaluate(ctx,['CR-CE10'])['results'][0]
    assert row['status']=='BLOCKED' and row['score'] is None
    assert row['luna_qualified'] is False

def test_old_pair_cannot_qualify_new_evaluation_or_context():
    p,ctx=controlled_provider();LunaCrisisEvaluator(p).evaluate(ctx,['CR-CE10'])
    assert not p.qualified_for_pair('CR-CE10',ctx,len(p.audit))
    changed=Input(Turn(ctx.current.number,ctx.current.user+' Otro dato.',ctx.current.ai,ctx.current.model),ctx.history)
    assert not p.qualified_for_pair('CR-CE10',changed,0)
