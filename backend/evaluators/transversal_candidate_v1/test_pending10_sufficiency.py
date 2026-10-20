from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from .pending10_contextual import contextual_definitions
from .pending10_sufficiency import sufficiency_definitions

def test_three_predicate_changes_preserve_other_targets_gates_and_scorers():
    contracts,_,_=load_contracts()
    before=contextual_definitions(definitions(contracts,['CR-CT10','CR-RE4','CR-GA1','CR-GA2','CR-CS1']))
    after=sufficiency_definitions(before)
    assert [key for key in before if before[key]!=after[key]]==['CR-CT10.c','CR-RE4.b','CR-GA2.b']
    assert 'sin opción o invitación' in after['CR-GA2.b']['text']
    assert 'No exigir varias alternativas' in after['CR-GA2.b']['text']
