import copy
import pytest
from backend.evaluators.ansiedad_semantic.af_component_adapter import ATOMS,CONDITIONAL,adjudicate
from backend.evaluators.nd.contracts import TurnContext

CONTEXT=TurnContext('Me preocupa el examen y me bloqueo al estudiar.','Puedes preparar una pregunta mientras esperas el resultado, sin controlar la nota.',())
LEVELS={
 'AF1':[{}, {'M':True}, {'M':True,'L':True,'VM':True}, {'M':True,'L':True,'VM':True,'VL':True}],
 'AF2':[{}, {'T':True}, {'T':True,'A':True}, {'T':True,'A':True,'I':True}],
 'AF3':[{}, {'L':True}, {'L':True,'R':True}, {'L':True,'R':True,'U':True}],
 'AF4':[{}, {'generic_approach':True}, {'E':True,'P':True}, {'E':True,'P':True,'G':True}],
 'AF5':[{}, {'L':True}, {'L':True,'A':True,'C':True}, {'L':True,'A':True,'C':True,'acceptance_choice_link_clear':True}],
 'AF6':[{}, {'H':True}, {'H':True,'V':True}, {'H':True,'V':True,'R':True}],
 'AF7':[{}, {'generic_regulation':True}, {'B':True,'T':True}, {'B':True,'T':True,'M':True}],
 'AF8':[{}, {'generic_responsibility':True}, {'C':True,'N':True}, {'C':True,'L':True,'N':True}],
}

def reading(code,changes,gate=True):
    facts={name:False for name in ATOMS[code]};facts.update(changes)
    if code in CONDITIONAL:facts['gate_present']=gate
    return {'components':{name:{'value':value,'complete_response_reviewed':True,'reason':'Fixture de contrato, no lectura semántica real.',
        'counterevidence':[],'evidence':[{'source':'user' if name=='gate_present' else 'response','quote':CONTEXT.user if name=='gate_present' else CONTEXT.response,'history_index':None}] if value else []}
        for name,value in facts.items()}}

@pytest.mark.parametrize('code',ATOMS)
@pytest.mark.parametrize('level',range(4))
def test_four_specialized_anchors(code,level):
    a=reading(code,LEVELS[code][level]);result=adjudicate(code,CONTEXT,a,copy.deepcopy(a))
    assert (result['status'],result['score'])==('SCORED',level)

@pytest.mark.parametrize('code',CONDITIONAL)
def test_gate_absence_differs_from_applicable_omission(code):
    a=reading(code,{},gate=False)
    assert adjudicate(code,CONTEXT,a,a)['status']=='N/A'
    a=reading(code,{})
    assert adjudicate(code,CONTEXT,a,a)['score']==0

@pytest.mark.parametrize('code',ATOMS)
def test_reader_disagreement_blocks_all_specialized_routes(code):
    a=reading(code,LEVELS[code][3]);b=copy.deepcopy(a)
    b['components'][next(iter(ATOMS[code]))]['value']=None
    result=adjudicate(code,CONTEXT,a,b)
    assert result['status']=='BLOCKED' and result['score'] is None
