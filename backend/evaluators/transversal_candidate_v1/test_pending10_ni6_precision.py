from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.scoring import resolve_score
from .pending10_ni6 import ni6_definitions
from .pending10_ni6_precision import ni6_precision_definitions

def test_only_precision_text_changes_and_official_scoring_is_preserved():
    contracts,_,_=load_contracts()
    before=ni6_definitions(definitions(contracts,['CR-NI6','CR-CS1']))
    after=ni6_precision_definitions(before)
    assert [key for key in before if before[key]!=after[key]]==['CR-NI6.c']
    assert 'correferencia inequívoca' in after['CR-NI6.c']['text']
    assert 'no convierte cualquier categoría pertinente' in after['CR-NI6.c']['text']
    for facts,score in [((False,False,False),0),((True,False,False),1),((True,True,False),2),((True,True,True),3)]:
        assert resolve_score('CR-NI6',dict(zip(('a','b','c'),facts),opposite=False),contracts)==(score,None)
    assert resolve_score('CR-NI6',dict(a=True,b=True,c=None,opposite=False),contracts)[0] is None
