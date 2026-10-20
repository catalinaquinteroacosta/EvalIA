import copy
from backend.evaluators.ansiedad_semantic import component_routes as routes
from backend.evaluators.ansiedad_semantic.closure_integral_live import source
from backend.evaluators.nd.contracts import TurnContext

def test_pa3_minimal_what_contract_and_reused_verifier():
    case,reuse=source('PA3-adjudicated')
    assert reuse['_reuse_stage']=='independent_verify'
    assert reuse['reading']['indicators']['PA3']['components']['recognizable_behavior']['value'] is True
    assert 'se admite como señal mínima de QUÉ' in routes.definitions('PA3')['recognizable_behavior']
    assert 'No acredita por sí sola CÓMO' in routes.definitions('PA3')['recognizable_behavior']

def test_pa3_verified_minimal_what_does_not_credit_how_or_complete():
    case,reuse=source('PA3-adjudicated')
    o=case['original'];ctx=TurnContext(o['user'],o['response'],())
    b=reuse['reading']['indicators']['PA3']
    result=routes.adjudicate('PA3',ctx,copy.deepcopy(b),b)
    assert result['status']=='SCORED' and result['score']==1
    # Controlled replay of existing facts, not a new semantic extraction.
    assert b['components']['what_and_how_explained']['value'] is False
    assert b['components']['clear_specific_contextual_execution']['value'] is False
