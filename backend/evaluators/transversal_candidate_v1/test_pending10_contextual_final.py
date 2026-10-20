from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from .pending10_contextual import contextual_definitions
from .pending10_contextual_final import contextual_final_definitions

def test_only_two_affected_predicate_texts_change():
    contracts,_,_=load_contracts()
    previous=contextual_definitions(definitions(contracts,['CR-CT10','CR-RE4','CR-GA1','CR-GA2']))
    after=contextual_final_definitions(previous)
    assert [k for k in previous if previous[k]!=after[k]]==['CR-CT10.c','CR-RE4.b']
    assert 'NO son por sí solos' in after['CR-CT10.c']['text']
    assert 'puede ser adecuada aunque falte' in after['CR-RE4.b']['text']
    assert 'No exigir nombrar' in after['CR-RE4.b']['text']
