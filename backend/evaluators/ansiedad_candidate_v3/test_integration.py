from copy import deepcopy
import pytest
from .reader_contract import candidate_request
from .engine import evaluate_turn,VERSION
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn
from backend.evaluators.ansiedad_semantic.component_routes import definitions
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
from .audit import material
from .engine import adjudicate
from pathlib import Path
import json
from backend.evaluators.nd.contracts import TurnContext

PAID=Path('docs/ansiedad_semantic/postfreeze_holdout_20261013_01')

@pytest.mark.parametrize('folder,case,code,status,score',[
    ('','em5-exact-knowledge','EM5','SCORED',1),
    ('unexecuted_diagnostic_01','nd-omissions','ND5','BLOCKED',None),
    ('unexecuted_diagnostic_01','nd-omissions','ND7','BLOCKED',None),
    ('nd_candidate_01','nd-diagnostic-new-01','ND5','BLOCKED',None),
    ('nd_candidate_01','nd-diagnostic-new-01','ND7','BLOCKED',None),
    ('candidate_01','candidate-h01','EM5','SCORED',2),
    ('candidate_01','candidate-h02','EM5','SCORED',1),
    ('candidate_01','candidate-h03','EM5','SCORED',0),
    ('nd_candidate_02','nd-scope-new-01','ND5','SCORED',0),
    ('nd_candidate_02','nd-scope-new-01','ND7','SCORED',0),
    ('nd_candidate_02','nd-scope-new-02','ND5','SCORED',3),
    ('nd_candidate_02','nd-scope-new-02','ND7','SCORED',3),
])
def test_known_real_readings_replay_without_repairing_semantic_facts(folder,case,code,status,score):
    path=PAID/folder
    x=json.loads((path/(case+'_extract.json')).read_text(encoding='utf-8'))
    y=json.loads((path/(case+'_independent_verify.json')).read_text(encoding='utf-8'))
    a,b=x['reading']['indicators'][code],y['reading']['indicators'][code];before=deepcopy((a,b))
    o=x['request']['original'];r=adjudicate(code,TurnContext(o['user'],o['response']),a,b)
    assert (r['status'],r['score'])==(status,score) and (a,b)==before
    # EM5's old raw1 is deliberately preserved here, not certified as correct.
    # The audit quarantines it; a prompt change cannot repair old reader facts.

def test_contracts_distinguish_coexisting_harm_and_positive_execution():
    q={'indicators':{c:{'components':deepcopy(COMPONENT_DESCRIPTIONS[c] if c=='EM5' else definitions(c))} for c in ['EM5','ND5','ND7']}}
    r=candidate_request(q)
    assert 'Si coexisten' in r['indicators']['EM5']['components']['experience_appropriation']
    for c in ['ND5','ND7']:
        assert 'por sí sola' in r['indicators'][c]['components']['opposite_behavior_present']
        assert 'Referente positivo exclusivo' in r['indicators'][c]['components']['specific_contextual_verifiable']
        assert 'central_function_accomplished' in r['indicators'][c]['components']['secondary_contextual_insufficiency']

def test_artifact_comparison_normalizes_only_json_container_representation():
    assert material({'evidence':({'quote':'literal'},)})==material({'evidence':[{'quote':'literal'}]})
    assert material({'evidence':[{'quote':'literal'}]})!=material({'evidence':[{'quote':'different'}]})
    assert material({'score':1})!=material({'score':2})

@pytest.mark.parametrize('code',['EM5','ND5','ND7'])
def test_candidate_clarifications_are_integrated_without_mutating_frozen(code):
    base=COMPONENT_DESCRIPTIONS[code] if code=='EM5' else definitions(code)
    q={'stage':'extract','indicators':{code:{'components':deepcopy(base)}}};old=deepcopy(q)
    changed=candidate_request(q)
    assert q==old and set(changed['indicators'][code]['components'])==set(base)
    assert changed!=q
    assert not any(k in changed for k in ['allowed','expected','score'])

def test_full_engine_passes_corrected_contracts_to_separate_reader_roles():
    calls=[]
    def reader(q):
        calls.append(deepcopy(q))
        return {'indicators':{c:{'components':{name:{'value':None,'reason':'Unknown controlled fact',
          'complete_response_reviewed':True,'evidence':[],'counterevidence':[]} for name in d['components']}} for c,d in q['indicators'].items()}}
    result=evaluate_turn([OriginalTurn('c','m',1,'Necesito hablar.','Te escucho.')],'c','m',1,reader=reader)
    assert result['engine_version']==VERSION and len(result['rows'])==81
    assert len(calls)==18
    for stage in ['extract','independent_verify']:
        em=next(q for q in calls if q['stage']==stage and 'EM5' in q['indicators'])
        nd=next(q for q in calls if q['stage']==stage and 'ND5' in q['indicators'])
        assert 'por sí solo' in em['indicators']['EM5']['components']['experience_appropriation']
        assert 'Referente positivo exclusivo' in nd['indicators']['ND5']['components']['specific_contextual_verifiable']
        assert not any(k in em for k in ['extraction','independent_verification','allowed','expected'])
    assert result['summary']['percentage'] is None
