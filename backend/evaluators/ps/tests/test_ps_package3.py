import pytest
from backend.evaluators.ps.rubric import rubric_for
from backend.evaluators.ps.cache import key_for,PrivateCache
from backend.evaluators.ps.contracts import Decision
from backend.evaluators.ps.semantic import SemanticResult
from backend.evaluators.ps.reconciliation import reconcile_blocked

def test_all_ten_full_anchors():
    for i in range(1,11):
        rubric=rubric_for(f'PS{i}')
        assert set(rubric['reference_levels'])=={'0','1','2','3'}
        assert all(rubric['reference_levels'][str(j)] for j in range(4))

def test_ps5_location_option():
    assert 'cómo encontrar ayuda local' in rubric_for('PS5')['reference_levels']['3']

def test_ps3_only_urgent():
    assert 'urgente actual o inminente' in rubric_for('PS3')['applicability']

def test_cache_keys_change_with_context():
    kwargs=dict(code='PS2',model='m',system='p',rubric={'v':1})
    assert key_for('extract',payload={'history':[]},**kwargs)!=key_for('extract',payload={'history':['x']},**kwargs)
    assert key_for('extract',payload={},**kwargs)!=key_for('verify',payload={},**kwargs)
    assert key_for('extract',payload={},**kwargs)!=key_for('extract',payload={},**{**kwargs,'rubric':{'v':2}})

def test_cache_rejects_blocked(tmp_path):
    cache=PrivateCache(tmp_path)
    key='a'*64
    with pytest.raises(ValueError):cache.write_verified(key,{'status':'BLOCKED'})
    assert cache.read(key) is None

def test_cache_verified_roundtrip(tmp_path):
    cache=PrivateCache(tmp_path); key='b'*64
    cache.write_verified(key,{'indicator':'PS1','status':'SCORED'})
    assert cache.read(key)['indicator']=='PS1'

def test_reconciliation_only_blocked():
    blocked=SemanticResult('PS2',Decision('PS2',None,'BLOCKED','ambiguous'),{}, {})
    scored=SemanticResult('PS1',Decision('PS1',3,'SCORED','ok'),{}, {})
    calls=[]
    def retry(code,old):
        calls.append(code)
        return SemanticResult(code,Decision(code,None,'BLOCKED','still ambiguous'),{}, {})
    result=reconcile_blocked({'PS1':scored,'PS2':blocked},retry)
    assert calls==['PS2'] and result.unresolved==('PS2',) and result.results['PS1']==scored
