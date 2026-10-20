import copy
import pytest
from backend.evaluators.ansiedad_semantic import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext

@pytest.mark.parametrize('level,truth',[
    (0,set()),
    (1,{'recognizable_behavior','comprehensible_idea_order'}),
    (2,{'recognizable_behavior','comprehensible_idea_order','comprehensible_transitions','central_function_realized','secondary_precision_or_adaptation_defect'}),
    (3,{'recognizable_behavior','comprehensible_idea_order','comprehensible_transitions','central_function_realized','clear_specific_contextual_execution'})])
def test_verified_official_ce3_components_determine_level(level,truth):
    ctx=TurnContext('Petición.', 'Primero preparo el texto. Después lo reviso.', ())
    a={'components':{n:{'value':n in truth,'complete_response_reviewed':True,
       'reason':'Controlled facts for descriptor branches; not semantic certification of this fixture.',
       'evidence':[{'source':'response','quote':ctx.response,'history_index':None}] if n in truth else [],
       'counterevidence':[]} for n in routes.definitions('CE3')}}
    r=routes.adjudicate('CE3',ctx,a,copy.deepcopy(a))
    assert (r['status'],r['score'])==('SCORED',level)

def test_ce3_methodological_scope_is_explicit():
    d=routes.definitions('CE3')
    assert 'organización O transición' in d['recognizable_behavior']
    assert 'no conducta contraria' in d['opposite_behavior']
    assert 'No exigir que todas las ideas compartan tema' in d['comprehensible_idea_order']
