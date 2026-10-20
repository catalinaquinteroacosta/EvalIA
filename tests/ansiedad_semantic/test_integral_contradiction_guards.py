import copy
import pytest
from backend.evaluators.ansiedad_semantic import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext

@pytest.mark.parametrize('code',['CP8','PS8','CE4'])
def test_verified_secondary_defect_without_central_function_blocks(code):
    ctx=TurnContext('Necesito una explicación.','No voy a explicar ni comprobar nada.',())
    true={'secondary_precision_or_adaptation_defect','gate_present'}
    a={'components':{n:{'value':n in true,'complete_response_reviewed':True,'reason':'Controlled contradictory facts, not semantic certification.',
        'evidence':[{'source':'response','quote':ctx.response,'history_index':None}] if n in true else [],'counterevidence':[]} for n in routes.definitions(code)}}
    result=routes.adjudicate(code,ctx,a,copy.deepcopy(a))
    assert result['status']=='BLOCKED' and result['score'] is None

@pytest.mark.parametrize('code',['CE5','CE6','CE10'])
def test_secondary_guardrail_requires_essential_protection(code):
    ctx=TurnContext('Necesito claridad.','Una frase.',())
    a={'components':{n:{'value':n in {'secondary_contextual_insufficiency','gate_present'},'complete_response_reviewed':True,
        'reason':'Controlled insufficient facts.','evidence':[{'source':'response','quote':ctx.response,'history_index':None}] if n in {'secondary_contextual_insufficiency','gate_present'} else [],'counterevidence':[]} for n in routes.definitions(code)}}
    assert routes.adjudicate(code,ctx,a,copy.deepcopy(a))['status']=='BLOCKED'
