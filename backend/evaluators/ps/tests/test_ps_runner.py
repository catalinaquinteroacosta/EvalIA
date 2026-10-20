from backend.evaluators.ps.contracts import Turn, HistoryMessage
from backend.evaluators.ps.runner import run_ps
from backend.evaluators.ps.cache import key_for
from backend.evaluators.ps.rubric import rubric_for


def extractor(system,payload):
    return {'indicator':payload['rubric']['code'],'components':[], 'evidence':[]}

def verified(system,payload):
    code=payload['rubric']['code']
    return {'indicator':code,'applicability':{'predicate':'applies','verification':'supported','evidence':[]},
            'levels':{str(i):{'verification':'supported' if i==3 else 'unsupported','evidence':[]} for i in range(4)}}

def test_runner_scores_and_cache_hits(tmp_path):
    t=Turn('Estoy preocupado','¿Qué paso pequeño prefieres intentar?')
    first=run_ps(t,extract_json=extractor,verify_json=verified,extract_model='x',verify_model='y',cache_dir=tmp_path,codes=('PS1',),enforce_evidence=False)
    assert first.results['PS1'].decision.score==3
    assert [x['source'] for x in first.events]==['api_call','api_call']
    def never(*args): raise AssertionError('API call repeated')
    second=run_ps(t,extract_json=never,verify_json=never,extract_model='x',verify_model='y',cache_dir=tmp_path,codes=('PS1',),enforce_evidence=False)
    assert second.results['PS1'].decision.score==3
    assert [x['source'] for x in second.events]==['cache_hit','cache_hit']

def test_history_changes_cache_identity():
    r=rubric_for('PS1')
    p1={'turn':{'user':'u','response':'r','prior_history':[]},'rubric':r}
    p2={'turn':{'user':'u','response':'r','prior_history':[{'role':'user','text':'earlier'}]},'rubric':r}
    assert key_for('extract',code='PS1',model='x',system='s',payload=p1,rubric=r)!=key_for('extract',code='PS1',model='x',system='s',payload=p2,rubric=r)

def test_ambiguous_not_cached_and_remains_blocked(tmp_path):
    calls=[]
    def ambiguous(system,payload):
        calls.append(1)
        v=verified(system,payload)
        v['levels']['3']['verification']='ambiguous'
        return v
    t=Turn('Problema','Respuesta')
    for _ in range(2):
        out=run_ps(t,extract_json=extractor,verify_json=ambiguous,extract_model='x',verify_model='y',cache_dir=tmp_path,codes=('PS1',),enforce_evidence=False)
        assert out.unresolved==('PS1',)
    assert len(calls)==2

def test_reconcile_only_blocked(tmp_path):
    t=Turn('Problema','Respuesta')
    def ambiguous(system,payload):
        v=verified(system,payload)
        v['levels']['3']['verification']='ambiguous'
        return v
    out=run_ps(t,extract_json=extractor,verify_json=ambiguous,
               reconcile_json=verified,extract_model='x',verify_model='y',cache_dir=tmp_path,codes=('PS1',),enforce_evidence=False)
    assert out.results['PS1'].decision.score==3
    assert any(e['stage']=='reconcile' for e in out.events)

def test_no_reconcile_on_scored(tmp_path):
    t=Turn('Problema','Respuesta')
    def fail(*args): raise AssertionError('Unnecessary reconcile')
    out=run_ps(t,extract_json=extractor,verify_json=verified,reconcile_json=fail,
               extract_model='x',verify_model='y',cache_dir=tmp_path,codes=('PS1',),enforce_evidence=False)
    assert out.unresolved==()
