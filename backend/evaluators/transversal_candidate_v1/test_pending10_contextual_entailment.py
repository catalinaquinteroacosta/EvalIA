from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from .pending10_contextual_entailment import contextual_entailment_definitions

def test_only_three_demonstrated_entailment_conditions_change():
    contracts,_,_=load_contracts()
    before=definitions(contracts,['CR-CT10','CR-RE4','CR-GA1','CR-GA2','CR-CS1'])
    after=contextual_entailment_definitions(before)
    assert [key for key in before if before[key]!=after[key]]==['CR-CT10.b','CR-CT10.c','CR-RE4.opposite']
    assert 'puede ser señal mínima pertinente' in after['CR-CT10.b']['text']
    assert 'no convierte resolverla' in after['CR-CT10.c']['text']
    assert 'NO acreditan por sí solas' in after['CR-RE4.opposite']['text']
