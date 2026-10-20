from copy import deepcopy
from .fidelity_candidate import CrisisEvaluator
from crisis_semantic.domain import Input,Turn

def test_old_NI6_seed_cannot_accredit_corrected_contract():
    calls=[]
    class SeededProvider:
        def __init__(self):self.seed={'CR-NI6.c':{'old':True},'CR-CS1.a':{'unchanged':True}}
        def run(self,stage,system,content,schema,ids,identity):
            calls.append((stage,deepcopy(self.seed)))
            assert not any(k.startswith('CR-NI6.') for k in self.seed)
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Fresh reading required, no invented observation.') for k in ids])
    p=SeededProvider();before=deepcopy(p.seed)
    result=CrisisEvaluator(p).evaluate(Input(Turn(1,'Escúchame.','Quieres que te escuche.','control')),['CR-NI6'])
    assert result['results'][0]['status']=='BLOCKED' and result['results'][0]['score'] is None
    assert len(calls)==2 and all('CR-CS1.a' in seed for _,seed in calls)
    assert p.seed==before

def test_real_span_provider_cannot_reuse_historical_NI6_seed(monkeypatch):
    import json
    from pathlib import Path
    from crisis_semantic.span_provider import SpanProvider
    from crisis_semantic.openai_private import OpenAIPrivate
    from crisis_semantic.domain import load_contracts
    old=json.loads(Path('docs/final_repair_20261014/run_01/NI6_existing_evidence.json').read_text(encoding='utf-8'))[0]
    p=SpanProvider.__new__(SpanProvider)
    p.seed=deepcopy(old['observations']);p.reusable_regressions=set();p.reused_observations=0;p.qualified_components=set()
    p.official_focus={c:[r['text'] for r in d['focus']] for c,d in load_contracts()[0].items()}
    before=deepcopy(p.seed);fresh=[]
    def fake_transport(self,stage,system,content,schema,ids,identity,**kwargs):
        fresh.append(stage)
        assert not any(k.startswith('CR-NI6.') for k in self.seed)
        return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Controlled fresh transport, no real API.') for k in ids])
    monkeypatch.setattr(OpenAIPrivate,'run',fake_transport)
    ctx=Input(Turn(1,old['user'],old['response'],'control'))
    result=CrisisEvaluator(p).evaluate(ctx,['CR-NI6'])
    assert fresh==['extract','verify'] and p.seed==before and p.reused_observations==0
    assert result['results'][0]['status']=='BLOCKED'
