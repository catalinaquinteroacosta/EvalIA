"""Contract fault injection across every official code; simulated readers only."""
import copy
import pytest
from backend.evaluators.nd.docx_components import contracts
from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.ansiedad_semantic import component_routes as routes, em_component_adapter as em
from backend.evaluators.ansiedad_semantic.result_tables import aggregate

CODES=tuple(contracts())
CONTEXT=TurnContext('Relato evaluable.','Respuesta evaluable.',())

def definitions(code):return em.COMPONENT_DESCRIPTIONS[code] if code.startswith('EM') else routes.definitions(code)
def adjudicate(code,a,b):return em.adjudicate(code,CONTEXT,a,b) if code.startswith('EM') else routes.adjudicate(code,CONTEXT,a,b)
def reading(code):
    return {'components':{name:{'value':False,'evidence':[],'counterevidence':[],
        'complete_response_reviewed':True,'reason':'Revisión simulada completa; no validación semántica.'} for name in definitions(code)}}
def essential(code):
    return 'important_information_missing' if code=='EM9' else 'gate_present' if 'gate_present' in definitions(code) else next(iter(definitions(code)))

@pytest.mark.parametrize('code',CODES)
@pytest.mark.parametrize('fault',['missing','uncertain','disagreement','invalid_literal'])
def test_every_code_blocks_an_impediment_to_adjudication(code,fault):
    a=reading(code);b=copy.deepcopy(a);name=essential(code)
    if fault=='missing':del b['components'][name]
    elif fault=='uncertain':b['components'][name]['value']=None
    elif fault=='disagreement':b['components'][name]['value']=True;b['components'][name]['evidence']=[{'source':'response','quote':CONTEXT.response,'history_index':None}]
    else:b['components'][name]['evidence']=[{'source':'response','quote':'EVIDENCIA INEXISTENTE','history_index':None}]
    result=adjudicate(code,a,b)
    assert result['status']=='BLOCKED' and result['score'] is None

CONDITIONAL=[code for code,contract in contracts().items() if 'CONDICIONAL' in contract['applicability_literal'] or contract['applicability_literal'].startswith('Condicional:')]
@pytest.mark.parametrize('code',CONDITIONAL)
def test_all_twenty_seven_official_gates_can_be_absent(code):
    a=reading(code)
    result=adjudicate(code,a,copy.deepcopy(a))
    assert result['status']=='N/A' and result['score'] is None
    assert contracts()[code]['applicability_literal'] in result['reason']

def test_duplicate_result_cannot_inflate_percentage():
    row={'conversation':'c','model':'m','turn':1,'code':'EM6','status':'SCORED','score':3,'applicability':'APPLICABLE'}
    with pytest.raises(ValueError,match='duplicada'):aggregate([row,row])
