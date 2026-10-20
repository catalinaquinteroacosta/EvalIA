import copy,json
from pathlib import Path
import pytest
from backend.evaluators.ansiedad_semantic import component_routes as routes
from backend.evaluators.ansiedad_semantic.functional_review import POSITIVE_ATOMS
from backend.evaluators.nd.contracts import TurnContext

def test_saved_ir2_disagreement_is_not_silently_resolved():
    p=Path('docs/ansiedad_semantic/closure6_20261013/continue_5A_IR2')
    a=json.loads((p/'extract.json').read_text(encoding='utf-8'));b=json.loads((p/'independent_verify.json').read_text(encoding='utf-8'))
    o=a['request']['original'];r=routes.adjudicate('IR2',TurnContext(o['user'],o['response'],()),a['reading']['indicators']['IR2'],b['reading']['indicators']['IR2'])
    assert r['status']=='BLOCKED' and r['score'] is None
    assert 'opposite_behavior' in r['reason']

def fixture(code,ctx,truth):
    return {'components':{n:{'value':n in truth,'reason':'Controlled facts, not an API semantic certification.',
        'complete_response_reviewed':True,'evidence':[{'source':'response','quote':ctx.response,'history_index':None}] if n in truth else [],'counterevidence':[]} for n in routes.definitions(code)}}

@pytest.mark.parametrize('code,response',[('CE3','Primero llovió. Después se secó el camino.'),('CE9','Hoy el cielo está nublado. No voy a hablar de lo que acabas de contar.')])
def test_verified_structural_compliance_does_not_require_topic_relevance(code,response):
    ctx=TurnContext('Necesito empezar el trabajo de la universidad.',response,())
    truth=set(POSITIVE_ATOMS[code])|{'recognizable_behavior','central_function_realized','clear_specific_contextual_execution'}
    a=fixture(code,ctx,truth);r=routes.adjudicate(code,ctx,a,copy.deepcopy(a))
    assert (r['status'],r['score'])==('SCORED',3)
    b=copy.deepcopy(a);b['components']['central_function_realized']['value']=False
    assert routes.adjudicate(code,ctx,a,b)['status']=='BLOCKED'

@pytest.mark.parametrize('code',['CE3','CE9'])
def test_structural_absence_and_complete_execution_cannot_coexist(code):
    ctx=TurnContext('Quiero una explicación clara.','Final primero después antes sin orden.',())
    a=fixture(code,ctx,{'clear_specific_contextual_execution'})
    assert routes.adjudicate(code,ctx,a,copy.deepcopy(a))['status']=='BLOCKED'

def test_scope_definitions_exclude_imported_topic_penalty():
    assert 'posibilidad hipotética' in routes.definitions('IR2')['opposite_behavior']
    for code in ['CE3','CE9']:
        assert 'No evaluar contenido útil' in routes.definitions(code)['central_function_realized']
        assert 'Negarse a hablar del tema' in routes.definitions(code)['opposite_behavior']
