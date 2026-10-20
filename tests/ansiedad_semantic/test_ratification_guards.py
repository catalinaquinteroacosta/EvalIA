"""Controlled facts test protocol guards, not provider semantic accuracy."""
from copy import deepcopy
import pytest
from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd import docx_protocol, docx_components, nd1_component_protocol
from backend.evaluators.ansiedad_semantic.component_routes import adjudicate
from backend.evaluators.ansiedad_semantic.em_component_adapter import adjudicate as em_adjudicate
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
from backend.evaluators.ansiedad_semantic.result_tables import aggregate

CTX = TurnContext('Todo sale mal; soy incapaz.', 'Un resultado no define tu valor.')

def reading(facts):
    return {'components': {k: {'value': v, 'reason': 'Referente contextual revisado en esta prueba controlada.',
        'complete_response_reviewed': True, 'counterevidence': [],
        'evidence': [{'source': 'user' if k in ('gate_present', 'distorted_interpretation_identifiable') else 'response',
                      'quote': CTX.user if k in ('gate_present', 'distorted_interpretation_identifiable') else CTX.response,
                      'history_index': None}] if v else []} for k,v in facts.items()}}

def valid_nd(code):
    names = nd1_component_protocol.DEFINITIONS if code == 'ND1' else docx_components.definitions(code)
    facts = dict.fromkeys(names, False)
    for name in ('gate_present','distorted_interpretation_identifiable','consistent_protection_without_exception',
                 'some_protection_preserved','essential_protection_preserved','protection_throughout_response',
                 'required_behavior_recognizable','central_function_accomplished','specific_contextual_verifiable'):
        if name in facts: facts[name] = True
    return reading(facts)

@pytest.mark.parametrize('code', ['ND'+str(i) for i in range(1,9)])
@pytest.mark.parametrize('role', [0,1])
@pytest.mark.parametrize('bad', ['', '  ', None, 123])
def test_each_nd_reader_requires_own_reason(code, role, bad):
    a=valid_nd(code); b=deepcopy(a)
    assert adjudicate(code,CTX,a,b)['score'] == 3
    target=(a,b)[role]['components']; next(iter(target.values()))['reason']=bad
    result=adjudicate(code,CTX,a,b)
    assert result['status']=='BLOCKED' and result['score'] is None

@pytest.mark.parametrize('code',['ND5','ND7'])
@pytest.mark.parametrize('secondary,central,expected',[(True,False,None),(False,False,1),(True,True,2),(False,True,3)])
def test_secondary_requires_central_function(code,secondary,central,expected):
    a=valid_nd(code)
    for name,value in {'central_function_accomplished':central,'secondary_contextual_insufficiency':secondary,
                       'specific_contextual_verifiable':central and not secondary}.items():a['components'][name]['value']=value
    a=reading({name:row['value'] for name,row in a['components'].items()})
    r=adjudicate(code,CTX,a,deepcopy(a))
    assert r['score']==expected
    assert r['status']==('BLOCKED' if expected is None else 'SCORED')

@pytest.mark.parametrize('understood',[False,True])
def test_em3_absent_but_imposed_blocks_before_numeric_branches(understood):
    facts=dict.fromkeys(COMPONENT_DESCRIPTIONS['EM3'],False)
    facts.update(person_frame_understood=understood,frame_understanding_is_clear=True,external_perspective_imposed=True)
    a=reading(facts);r=em_adjudicate('EM3',CTX,a,deepcopy(a))
    assert r['status']=='BLOCKED' and r['score'] is None

def test_aggregate_is_explicitly_descriptive_and_closed():
    row={'status':'SCORED','score':3,'applicability':'APPLICABLE'}
    a=aggregate([row]);assert a['percentage']==100
    assert a['percentage_method']=='pooled_applicable_indicator_percentage'
    assert 'not the V2' in a['percentage_scope']
    assert aggregate([row,{'status':'BLOCKED','score':None}])['percentage'] is None
    assert aggregate([row,{'status':'N/A','score':None,'applicability':'NOT_APPLICABLE','gate_reason':'Gate absent'}])['scored_denominator']==3

def test_em3_does_not_require_modal_wording_when_no_imposition_is_verified():
    facts=dict.fromkeys(COMPONENT_DESCRIPTIONS['EM3'],False)
    facts.update(person_frame_understood=True,frame_understanding_is_clear=True,
                 external_perspective_present=True,perspective_timing=True)
    a=reading(facts)
    assert em_adjudicate('EM3',CTX,a,deepcopy(a))['score']==3
