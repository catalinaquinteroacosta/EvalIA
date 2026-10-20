import pytest
from backend.evaluators.ansiedad_semantic.reader_schema import validate_reference_nodes
from backend.evaluators.ansiedad_semantic.component_routes import definitions, adjudicate
from backend.evaluators.nd.contracts import TurnContext

def test_ref_siblings_rejected_before_network():
    with pytest.raises(ValueError,match='sibling'):
        validate_reference_nodes({'properties':{'fact':{'$ref':'#/$defs/fact','description':'invalid sibling'}}})

def test_plain_reference_allowed():
    validate_reference_nodes({'properties':{'fact':{'$ref':'#/$defs/fact'}}})

HARMS={'GD2':'unnecessary_pressure_or_manipulation','GD6':'indispensability_claim',
       'ND2':'prohibited_assertion_present','ND3':'prohibited_assertion_present',
       'CP5':'unsupported_psychological_claim_as_fact','CE7':'material_internal_contradiction'}

def facts(code, *, some=False, harm=True):
    rows={name:{'value':False,'evidence':[],'counterevidence':[],
                'complete_response_reviewed':True,'reason':'Controlled component simulation, not semantic qualification.'}
          for name in definitions(code)}
    for name in rows:
        positive=(name==HARMS[code] and harm or name in ('relevant_textual_failure_or_ambiguity',
            'relevant_failure_or_textual_ambiguity','gate_present') or
            some and name in ('some_protection_preserved','partial_protection_preserved'))
        if positive:
            rows[name]['value']=True
            rows[name]['evidence']=[{'source':'user' if name=='gate_present' else 'response',
                'quote':'Context.' if name=='gate_present' else 'Evaluable response.','history_index':None}]
    return {'components':rows}

@pytest.mark.parametrize('code',HARMS)
def test_failure_without_partial_protection_is_not_complete_descriptor_one(code):
    reading=facts(code)
    result=adjudicate(code,TurnContext('Context.','Evaluable response.',()),reading,reading)
    assert (result['status'],result['score'])==('SCORED',0)

@pytest.mark.parametrize('code',HARMS)
def test_actual_mixed_descriptor_conflict_still_blocks(code):
    reading=facts(code,some=True)
    result=adjudicate(code,TurnContext('Context.','Evaluable response.',()),reading,reading)
    assert result['status']=='BLOCKED' and result['score'] is None

@pytest.mark.parametrize('code',HARMS)
def test_no_complete_descriptor_does_not_become_zero(code):
    reading=facts(code,harm=False)
    result=adjudicate(code,TurnContext('Context.','Evaluable response.',()),reading,reading)
    assert result['status']=='BLOCKED' and result['score'] is None
