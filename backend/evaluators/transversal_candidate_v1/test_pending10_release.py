from copy import deepcopy
import pytest
from crisis_semantic.domain import Input,Turn,load_contracts
from crisis_semantic.predicate_catalog import definitions
from .pending10_release import CrisisEvaluator,final_definitions,CHANGED
from .pending10_qualification import bind_qualification
from .pending10_provider import Pending10Provider

def test_release_effective_pair_invalidates_all_changed_seeds_and_keeps_neighbors():
    calls=[]
    class Reader:
        def __init__(self):
            self.seed={c+'.a':{'old':True} for c in CHANGED}
            self.seed['CR-CS1.a']={'neighbor':True}
        def run(self,stage,system,content,schema,ids,identity):
            assert self.seed=={'CR-CS1.a':{'neighbor':True}}
            calls.append((stage,deepcopy(content)))
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Offline protocol fixture.') for k in ids])
    p=Reader();original=deepcopy(p.seed);codes=sorted(CHANGED)
    CrisisEvaluator(p).evaluate(Input(Turn(1,'Necesito apoyo.','Podemos hablar.','test')),codes)
    assert p.seed==original and [s for s,_ in calls]==['extract','verify']
    expected=final_definitions(definitions(load_contracts()[0],codes))
    assert all(c['predicates']==expected for _,c in calls)
    old=definitions(load_contracts()[0],list(load_contracts()[0]))
    new=final_definitions(old)
    assert all(old[k]==new[k] for k in old if k.split('.',1)[0] not in CHANGED)

def test_wrong_reader_or_contract_cannot_inherit_qualification():
    class Wrong:
        qualified_components={'CR-CE10'}
        model='gpt-4.1-mini-2025-04-14'
        def run(self):pass
    with pytest.raises(ValueError,match='reader_identity'):
        bind_qualification(Wrong(),'CR-CE10',{}, {})
    p=Pending10Provider()
    with pytest.raises(ValueError,match='contract_or_protocol'):
        bind_qualification(p,'CR-RI2',{}, {})
    assert 'CR-RI2' not in p.qualified_components
