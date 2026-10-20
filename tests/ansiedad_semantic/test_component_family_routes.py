"""Executable routes, blind originals and technical failures; no provider calls."""
import copy
import pytest
from backend.evaluators.ansiedad_semantic import component_routes as routes
from backend.evaluators.ansiedad_semantic import em_component_adapter as em
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn, authorized_context

@pytest.fixture
def identified():
    return authorized_context([OriginalTurn('c','m',1,'Estoy triste.','Te escucho.')],'c','m',1)

def test_sixty_eight_distinct_executable_component_routes():
    codes=[f'{family}{i}' for family,count in routes.COUNTS.items() for i in range(1,count+1)]
    assert len(set(codes))==68
    for code in codes:
        assert routes.route(code)
        assert routes.definitions(code)

@pytest.mark.parametrize('family',routes.COUNTS)
def test_transport_failure_is_never_numeric_or_na(identified,family):
    def fail(_):raise OSError('isolated transport unavailable')
    results=routes.run_family(identified,family,reader=fail)['results']
    assert len(results)==routes.COUNTS[family]
    assert all(row['status']=='BLOCKED' and row['score'] is None
               for code,row in results.items() if code!='CE10')
    if family=='CE':
        assert results['CE10']['status']=='N/A'
        assert results['CE10']['verified_gate_basis']['turn']==1

def test_blind_verifier_receives_unmodified_originals(identified):
    calls=[]
    def reader(payload):
        calls.append(copy.deepcopy(payload))
        payload['original']['user']='contaminated'
        return {'indicators':{code:{'components':{}} for code in payload['indicators']}}
    routes.run_family(identified,'IR',reader=reader)
    assert len(calls)==2
    assert calls[1]['original']['user']=='Estoy triste.'
    assert calls[1]['stage']=='independent_verify'
    assert 'extraction' not in calls[1]
    assert identified['user']=='Estoy triste.'

def test_em_transport_failure_covers_thirteen(identified):
    def fail(_):raise OSError('unavailable')
    rows=em.run_family(identified,reader=fail)['results']
    assert len(rows)==13
    assert all(row['status']=='BLOCKED' and row['score'] is None for row in rows.values())

def test_em13_general_verified_absence_can_score_three(identified):
    from backend.evaluators.nd.contracts import TurnContext
    context=TurnContext(identified['user'],identified['response'],())
    components={name:{'value':False,'evidence':[],'counterevidence':[],
        'complete_response_reviewed':True,'reason':'Whole response reviewed without this behavior.'}
        for name in em.COMPONENT_DESCRIPTIONS['EM13']}
    reading={'components':components}
    result=em.adjudicate('EM13',context,reading,copy.deepcopy(reading))
    assert (result['status'],result['score'])==('SCORED',3)
    reading['components']['external_framework_imposed']['value']=None
    assert em.adjudicate('EM13',context,reading,reading)['status']=='BLOCKED'
