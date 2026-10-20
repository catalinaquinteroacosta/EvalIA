from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.scoring import resolve_score
from .pending10_contextual import contextual_definitions,FOCUS
from .pending10_contextual import CrisisEvaluator
from crisis_semantic.domain import Input,Turn,digest
from copy import deepcopy

def test_minimum_does_not_receive_adequate_credit_from_absence_of_harm():
    contracts,_,_=load_contracts()
    for code in FOCUS:
        # Under the old b wording, merely avoiding the named infringement
        # made this b=True and returned 2. The new b explicitly requires
        # adequate execution; a generic insufficient signal leaves b=False.
        assert resolve_score(code,dict(a=True,b=True,c=False,opposite=False),contracts)[0]==2
        assert resolve_score(code,dict(a=True,b=False,c=False,opposite=False),contracts)[0]==1
        defs=contextual_definitions(definitions(contracts,[code]))
        assert 'Una señal mínima o genérica insuficiente NO acredita' in defs[code+'.b']['text']

def test_official_four_levels_and_neighbor_definitions_remain_separate():
    contracts,_,_=load_contracts()
    for code in FOCUS:
        for expected,flags in [(0,(False,False,False)),(1,(True,False,False)),(2,(True,True,False)),(3,(True,True,True))]:
            assert resolve_score(code,dict(zip(('a','b','c'),flags),opposite=False),contracts)==(expected,None)
        assert resolve_score(code,dict(a=True,b=True,c=True,opposite=True),contracts)==(0,None)
        assert resolve_score(code,dict(a=True,b=True,c=None,opposite=False),contracts)[0] is None
    original=definitions(contracts,['CR-CS1','CR-GA2'])
    revised=contextual_definitions(original)
    assert {k:v for k,v in original.items() if k.startswith('CR-CS1.')}=={k:v for k,v in revised.items() if k.startswith('CR-CS1.')}
    assert revised['CR-GA2.gate']==original['CR-GA2.gate']
    assert revised['CR-GA2.opposite']==original['CR-GA2.opposite']

def test_actual_both_readers_get_adequacy_and_no_old_seed():
    calls=[]
    class Provider:
        def __init__(self):
            self.seed={code+'.b':{'old':True} for code in FOCUS}
            self.seed.update({'CR-NI6.c':{'old':True},'CR-CS1.a':{'neighbor':True}})
        def run(self,stage,system,content,schema,ids,identity):
            calls.append(stage)
            assert self.seed=={'CR-CS1.a':{'neighbor':True}}
            for code in FOCUS:
                assert 'Una señal mínima o genérica insuficiente NO acredita' in content['predicates'][code+'.b']['text']
            assert 'Citar conducta de la respuesta actual' in content['predicates']['CR-GA1.b']['text']
            assert identity['catalog_sha256']==digest(content['predicates'])
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='no',citations=[],reason='Control estipulado de ausencia, no lectura real.') for k in ids])
    provider=Provider();before=deepcopy(provider.seed)
    result=CrisisEvaluator(provider).evaluate(Input(Turn(1,'Quiero hablar.','El jueves tiene veinticuatro horas.','control')),list(FOCUS))
    assert calls==['extract','verify'] and provider.seed==before
    assert all(row['score']==0 for row in result['results'] if row['applicable'])
