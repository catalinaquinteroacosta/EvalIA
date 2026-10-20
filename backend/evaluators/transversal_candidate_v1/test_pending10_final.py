from copy import deepcopy
from crisis_semantic.domain import Input,Turn,load_contracts
from crisis_semantic.predicate_catalog import definitions
from .pending10_final import CrisisEvaluator,final_definitions,CHANGED

def test_effective_both_readers_use_final_contract_and_original_seed_is_untouched():
    class Reader:
        def __init__(self):
            self.seed={c+'.a':{'historical':True} for c in CHANGED}
            self.seed['CR-CS1.a']={'unchanged':True}
            self.calls=[]
        def run(self,stage,system,content,schema,ids,identity):
            assert all(k.split('.',1)[0] not in CHANGED for k in self.seed)
            assert 'CR-CS1.a' in self.seed
            self.calls.append((stage,deepcopy(content),identity))
            return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Controlled route test, not semantic certification.') for k in ids])
    p=Reader();before=deepcopy(p.seed)
    codes=list(CHANGED)
    CrisisEvaluator(p).evaluate(Input(Turn(1,'Necesito apoyo.','Podemos conversar.','test')),codes)
    assert p.seed==before
    assert [s for s,_,_ in p.calls]==['extract','verify']
    expected=final_definitions(definitions(load_contracts()[0],codes))
    assert all(content['predicates']==expected for _,content,_ in p.calls)

def test_changes_are_confined_to_eight_pending_contracts():
    original=definitions(load_contracts()[0],list(load_contracts()[0]))
    updated=final_definitions(original)
    assert set(original)==set(updated)
    assert all(updated[k]==v for k,v in original.items() if k.split('.',1)[0] not in CHANGED)
    assert updated['CR-NI6.b']!=original['CR-NI6.b']
    assert updated['CR-CE10.b']!=original['CR-CE10.b']
    assert updated['CR-GA1.b']!=original['CR-GA1.b']
